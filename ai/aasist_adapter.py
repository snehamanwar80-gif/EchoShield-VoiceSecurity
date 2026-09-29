from pathlib import Path
import json
import subprocess
import tempfile

import numpy as np
import librosa
import torch


# ============================================================
# EchoShield - AASIST Adapter
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

AASIST_ROOT = BASE_DIR / "ai" / "aasist"

CONFIG_FILE = AASIST_ROOT / "config" / "AASIST.conf"

MODEL_FILE = AASIST_ROOT / "models" / "weights" / "AASIST.pth"


# ============================================================
# AUDIO CONFIG
# ============================================================

SAMPLE_RATE = 16000

TARGET_SAMPLES = 64600

MIN_DURATION = TARGET_SAMPLES / SAMPLE_RATE


# ============================================================
# MODEL CACHE
# ============================================================

MODEL = None


# ============================================================
# AASIST STATUS
# ============================================================

def aasist_status():

    if not CONFIG_FILE.exists():
        return {
            "available": False,
            "pretrained": False,
            "model": "AASIST",
            "error": f"AASIST config not found: {CONFIG_FILE}"
        }

    if not MODEL_FILE.exists():
        return {
            "available": False,
            "pretrained": False,
            "model": "AASIST",
            "error": f"AASIST weights not found: {MODEL_FILE}"
        }

    return {
        "available": True,
        "pretrained": True,
        "model": "AASIST",
        "sample_rate": SAMPLE_RATE,
        "target_samples": TARGET_SAMPLES,
        "required_seconds": round(MIN_DURATION, 4)
    }


# ============================================================
# LOAD AASIST MODEL
# ============================================================

def load_model():

    global MODEL

    if MODEL is not None:
        return MODEL

    status = aasist_status()

    if not status.get("available"):
        raise FileNotFoundError(
            status.get("error", "AASIST model is unavailable.")
        )

    # Import actual AASIST model
    from ai.aasist.models.AASIST import Model

    # Load configuration
    with open(
        CONFIG_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        config = json.load(f)

    model_config = config["model_config"]

    # Create model
    model = Model(model_config)

    # Load pretrained checkpoint
    checkpoint = torch.load(
        MODEL_FILE,
        map_location="cpu"
    )

    # --------------------------------------------------------
    # Extract state dictionary from different checkpoint types
    # --------------------------------------------------------

    if isinstance(checkpoint, dict):

        if "state_dict" in checkpoint:
            checkpoint = checkpoint["state_dict"]

        elif "model_state_dict" in checkpoint:
            checkpoint = checkpoint["model_state_dict"]

        elif "model" in checkpoint and isinstance(
            checkpoint["model"],
            dict
        ):
            checkpoint = checkpoint["model"]

    if not isinstance(checkpoint, dict):
        raise RuntimeError(
            "Invalid AASIST checkpoint format."
        )

    # --------------------------------------------------------
    # Remove common prefixes
    # --------------------------------------------------------

    cleaned_checkpoint = {}

    for key, value in checkpoint.items():

        new_key = key

        if new_key.startswith("module."):
            new_key = new_key[7:]

        if new_key.startswith("model."):
            new_key = new_key[6:]

        cleaned_checkpoint[new_key] = value

    # --------------------------------------------------------
    # Load weights
    # --------------------------------------------------------

    model.load_state_dict(
        cleaned_checkpoint,
        strict=True
    )

    model.to("cpu")

    model.eval()

    MODEL = model

    print(
        "AASIST pretrained model loaded successfully."
    )

    return MODEL


# ============================================================
# LOAD AUDIO
#
# Supports:
#   WAV
#   MP3
#   M4A
#   WebM / Opus
#   Other FFmpeg-supported audio formats
#
# WebM is important for Live Voice because the browser
# MediaRecorder creates WebM/Opus recordings.
# ============================================================

def _load_audio(
    path,
    sample_rate=SAMPLE_RATE
):

    path = Path(path)

    if not path.exists():
        raise RuntimeError(
            f"Audio file not found: {path}"
        )

    direct_error = None

    # --------------------------------------------------------
    # First try normal librosa loading
    # --------------------------------------------------------

    try:

        audio, sr = librosa.load(
            str(path),
            sr=sample_rate,
            mono=True
        )

        audio = np.asarray(
            audio,
            dtype=np.float32
        )

        if audio.size > 0:

            return audio, sample_rate

    except Exception as exc:

        direct_error = str(exc)

    # --------------------------------------------------------
    # WebM / Opus fallback
    # Use FFmpeg bundled with imageio-ffmpeg.
    # --------------------------------------------------------

    try:

        import imageio_ffmpeg

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    except Exception as exc:

        raise RuntimeError(
            "FFmpeg decoder is unavailable.\n"
            f"Original audio error: {direct_error}\n"
            f"FFmpeg error: {exc}"
        ) from exc

    temp_wav = None

    try:

        # Temporary WAV file
        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        ) as temp_file:

            temp_wav = temp_file.name

        # ----------------------------------------------------
        # Convert input → 16 kHz mono PCM WAV
        # ----------------------------------------------------

        command = [
            ffmpeg_exe,
            "-y",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
            temp_wav
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )

        if result.returncode != 0:

            error_text = (
                result.stderr[-3000:]
                if result.stderr
                else "Unknown FFmpeg error."
            )

            raise RuntimeError(
                error_text
            )

        # ----------------------------------------------------
        # Read converted WAV
        # ----------------------------------------------------

        audio, sr = librosa.load(
            temp_wav,
            sr=sample_rate,
            mono=True
        )

        audio = np.asarray(
            audio,
            dtype=np.float32
        )

        if audio.size == 0:
            raise RuntimeError(
                "FFmpeg produced an empty audio file."
            )

        return audio, sample_rate

    except Exception as exc:

        raise RuntimeError(
            "Unable to decode the audio file.\n"
            f"File: {path}\n"
            f"Original decoder error: {direct_error}\n"
            f"FFmpeg decoder error: {exc}"
        ) from exc

    finally:

        # Delete temporary WAV
        if temp_wav:

            try:
                Path(temp_wav).unlink(
                    missing_ok=True
                )
            except Exception:
                pass


# ============================================================
# PREPARE AUDIO
# ============================================================

def prepare_audio(audio):

    audio = np.asarray(
        audio,
        dtype=np.float32
    )

    # Remove invalid numbers
    audio = np.nan_to_num(
        audio,
        nan=0.0,
        posinf=0.0,
        neginf=0.0
    )

    if audio.size == 0:

        return np.zeros(
            TARGET_SAMPLES,
            dtype=np.float32
        )

    # --------------------------------------------------------
    # Trim silence
    # --------------------------------------------------------

    try:

        trimmed, _ = librosa.effects.trim(
            audio,
            top_db=35
        )

        if trimmed.size > 0:
            audio = trimmed

    except Exception:
        pass

    if audio.size == 0:

        return np.zeros(
            TARGET_SAMPLES,
            dtype=np.float32
        )

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    peak = np.max(
        np.abs(audio)
    )

    if peak > 1e-6:

        audio = (
            audio / peak
        ) * 0.95

    # --------------------------------------------------------
    # Repeat short audio
    # --------------------------------------------------------

    if len(audio) < TARGET_SAMPLES:

        repetitions = int(
            np.ceil(
                TARGET_SAMPLES / len(audio)
            )
        )

        audio = np.tile(
            audio,
            repetitions
        )

        audio = audio[
            :TARGET_SAMPLES
        ]

    # --------------------------------------------------------
    # Crop long audio
    # --------------------------------------------------------

    else:

        audio = audio[
            :TARGET_SAMPLES
        ]

    return audio.astype(
        np.float32
    )


# ============================================================
# CREATE WINDOWS
# ============================================================

def create_windows(audio):

    audio_length = len(audio)

    # --------------------------------------------------------
    # One window
    # --------------------------------------------------------

    if audio_length <= TARGET_SAMPLES:

        return [
            prepare_audio(audio)
        ]

    # --------------------------------------------------------
    # Multiple overlapping windows
    # --------------------------------------------------------

    number_of_windows = min(
        5,
        max(
            2,
            audio_length // (
                TARGET_SAMPLES // 2
            )
        )
    )

    starts = np.linspace(
        0,
        audio_length - TARGET_SAMPLES,
        num=number_of_windows,
        dtype=int
    )

    windows = []

    for start in starts:

        end = (
            start
            + TARGET_SAMPLES
        )

        chunk = audio[
            start:end
        ]

        windows.append(
            prepare_audio(chunk)
        )

    return windows


# ============================================================
# ANALYZE ONE WINDOW
# ============================================================

def _predict_window(
    model,
    window
):

    input_tensor = torch.from_numpy(
        window
    ).float().unsqueeze(0)

    with torch.no_grad():

        output = model(
            input_tensor
        )

    # Official AASIST returns:
    #
    # last_hidden, output
    #
    # output shape:
    # [batch, 2]

    if isinstance(output, tuple):

        if len(output) < 2:

            raise RuntimeError(
                "AASIST returned an incomplete model output."
            )

        logits = output[1]

    else:

        logits = output

    if not torch.is_tensor(logits):

        raise RuntimeError(
            "AASIST output is not a tensor."
        )

    if logits.ndim != 2:

        raise RuntimeError(
            f"Unexpected AASIST output shape: {logits.shape}"
        )

    if logits.shape[1] != 2:

        raise RuntimeError(
            "AASIST must return exactly 2 class scores."
        )

    probabilities = torch.softmax(
        logits,
        dim=1
    )[0].cpu().numpy()

    return probabilities


# ============================================================
# MAIN AASIST ANALYSIS
# ============================================================

def analyze_with_aasist(
    audio_path
):

    audio_path = Path(
        audio_path
    )

    if not audio_path.exists():

        raise FileNotFoundError(
            f"Audio file not found: {audio_path}"
        )

    # --------------------------------------------------------
    # Load model
    # --------------------------------------------------------

    model = load_model()

    # --------------------------------------------------------
    # Load audio
    # --------------------------------------------------------

    audio, sample_rate = _load_audio(
        audio_path,
        SAMPLE_RATE
    )

    audio = np.asarray(
        audio,
        dtype=np.float32
    )

    audio = np.nan_to_num(
        audio,
        nan=0.0,
        posinf=0.0,
        neginf=0.0
    )

    # --------------------------------------------------------
    # Duration
    # --------------------------------------------------------

    duration_seconds = (
        len(audio)
        / SAMPLE_RATE
    )

    # --------------------------------------------------------
    # Minimum duration
    # --------------------------------------------------------

    if duration_seconds < MIN_DURATION:

        return {
            "status": "WAITING_FOR_AUDIO",
            "success": True,
            "message": (
                "Please provide at least "
                f"{MIN_DURATION:.2f} seconds of audio."
            ),
            "required_seconds": round(
                MIN_DURATION,
                2
            ),
            "duration_seconds": round(
                duration_seconds,
                2
            )
        }

    # --------------------------------------------------------
    # Create windows
    # --------------------------------------------------------

    windows = create_windows(
        audio
    )

    if not windows:

        raise RuntimeError(
            "No valid audio windows were created."
        )

    # --------------------------------------------------------
    # AASIST inference
    # --------------------------------------------------------

    probabilities = []

    for window in windows:

        probability = _predict_window(
            model,
            window
        )

        probabilities.append(
            probability
        )

    probability_matrix = np.stack(
        probabilities
    )

    # --------------------------------------------------------
    # Median aggregation
    # --------------------------------------------------------

    final_probability = np.median(
        probability_matrix,
        axis=0
    )

    # --------------------------------------------------------
    # AASIST class mapping
    #
    # ASVspoof convention:
    #
    # Class 0 = spoof / synthetic
    # Class 1 = bona-fide / human
    # --------------------------------------------------------

    spoof_probability = float(
        final_probability[0]
    )

    human_probability = float(
        final_probability[1]
    )

    # --------------------------------------------------------
    # Convert to percentages
    # --------------------------------------------------------

    synthetic_score = (
        spoof_probability * 100.0
    )

    human_score = (
        human_probability * 100.0
    )

    synthetic_score = max(
        0.0,
        min(
            100.0,
            synthetic_score
        )
    )

    human_score = max(
        0.0,
        min(
            100.0,
            human_score
        )
    )

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    confidence = max(
        synthetic_score,
        human_score
    )

    # --------------------------------------------------------
    # Label
    # --------------------------------------------------------

    if confidence < 55.0:

        label = "VERIFY"

    elif synthetic_score > human_score:

        label = "LIKELY SYNTHETIC"

    else:

        label = "LIKELY HUMAN"

    # --------------------------------------------------------
    # Final backend-compatible result
    # --------------------------------------------------------

    return {

        "status": "ANALYZED",

        "success": True,

        "analysis_mode": "AASIST_INFERENCE",

        "model": "AASIST",

        "pretrained": True,

        "analyzed_by": (
            "Pretrained AASIST Model"
        ),

        "ai_score": round(
            synthetic_score,
            2
        ),

        "genuine_score": round(
            human_score,
            2
        ),

        "synthetic_score": round(
            synthetic_score,
            2
        ),

        "human_score": round(
            human_score,
            2
        ),

        "confidence": round(
            confidence,
            2
        ),

        "label": label,

        "score_0": round(
            spoof_probability,
            6
        ),

        "score_1": round(
            human_probability,
            6
        ),

        "windows_analyzed": len(
            windows
        ),

        "duration_seconds": round(
            duration_seconds,
            2
        ),

        "sample_rate": SAMPLE_RATE,

        "target_samples": TARGET_SAMPLES
    }


# ============================================================
# COMPATIBILITY FUNCTION
# ============================================================

def analyze_audio(
    audio_path
):

    return analyze_with_aasist(
        audio_path
    )


# ============================================================
# COMPATIBILITY ALIAS
# ============================================================

analyze = analyze_with_aasist


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("EchoShield AASIST Adapter")
    print("=" * 60)

    print(
        "Project:",
        BASE_DIR
    )

    print(
        "AASIST:",
        AASIST_ROOT
    )

    print(
        "Config:",
        CONFIG_FILE
    )

    print(
        "Weights:",
        MODEL_FILE
    )

    print(
        "Sample Rate:",
        SAMPLE_RATE
    )

    print(
        "Target Samples:",
        TARGET_SAMPLES
    )

    print(
        "Required Seconds:",
        f"{MIN_DURATION:.2f}"
    )

    print("=" * 60)

    print()
    print("AASIST STATUS:")

    status = aasist_status()

    print(status)

    if status.get("available"):

        load_model()

        print()
        print(
            "AASIST MODEL LOADED SUCCESSFULLY"
        )

    else:

        print()
        print(
            "AASIST MODEL NOT AVAILABLE"
        )