from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import os
import uuid
import json
import math
import sqlite3
import shutil
import traceback
from datetime import datetime

import numpy as np


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="EchoShield",
    description="AI-powered voice impersonation protection system",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATABASE
# ============================================================

DATABASE = os.path.join(BASE_DIR, "echoshield.db")


def get_db():

    connection = sqlite3.connect(
        DATABASE,
        check_same_thread=False
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_database():

    connection = get_db()

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS incidents (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            filename TEXT,

            source TEXT,

            label TEXT,

            synthetic_score REAL,

            human_score REAL,

            risk_level TEXT,

            risk_score REAL,

            decision TEXT,

            recommendation TEXT,

            model TEXT,

            timestamp TEXT

        )
        """
    )

    connection.commit()
    connection.close()


init_database()


# ============================================================
# HOME
# ============================================================

@app.get("/")
async def home():

    return FileResponse(
        os.path.join(
            FRONTEND_DIR,
            "index.html"
        )
    )


# ============================================================
# CALL PAGE
# ============================================================

@app.get("/call")
async def call_page():

    return FileResponse(
        os.path.join(
            FRONTEND_DIR,
            "call.html"
        )
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
async def health():

    return {
        "status": "online",
        "service": "EchoShield",
        "time": datetime.now().isoformat()
    }


# ============================================================
# CALL ROOM MANAGER
# ============================================================

rooms = {}


# ============================================================
# CREATE SECURE CALL
# ============================================================

@app.get("/api/call/create")
async def create_call():

    room_id = uuid.uuid4().hex[:12]

    rooms[room_id] = set()

    return {
        "success": True,
        "room_id": room_id,
        "message": "Secure call room created"
    }


# ============================================================
# WEBRTC SIGNALING
# ============================================================

@app.websocket("/ws/webrtc/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str
):

    await websocket.accept()

    if room_id not in rooms:

        rooms[room_id] = set()

    peers = rooms[room_id]

    is_first_user = len(peers) == 0

    peers.add(websocket)

    try:

        await websocket.send_json(
            {
                "type": "joined",
                "initiator": is_first_user,
                "peer_count": len(peers)
            }
        )


        # Tell existing user that another user joined
        if not is_first_user:

            for peer in list(peers):

                if peer != websocket:

                    try:

                        await peer.send_json(
                            {
                                "type": "peer_joined"
                            }
                        )

                    except Exception:

                        pass


        while True:

            message = await websocket.receive_json()

            message_type = message.get(
                "type",
                ""
            )


            # ------------------------------------------------
            # Relay WebRTC signaling
            # ------------------------------------------------

            if message_type in [
                "offer",
                "answer",
                "candidate",
                "reject",
                "hangup",
                "security_alert"
            ]:

                for peer in list(peers):

                    if peer != websocket:

                        try:

                            await peer.send_json(
                                message
                            )

                        except Exception:

                            pass


    except WebSocketDisconnect:

        pass

    except Exception:

        traceback.print_exc()

    finally:

        peers.discard(websocket)


        # Notify remaining user
        for peer in list(peers):

            try:

                await peer.send_json(
                    {
                        "type":
                        "peer_disconnected"
                    }
                )

            except Exception:

                pass


        if len(peers) == 0:

            rooms.pop(
                room_id,
                None
            )


# ============================================================
# AUDIO ANALYSIS
# ============================================================

def calculate_audio_features(file_path):

    """
    Extract basic acoustic features.

    This is the real audio-processing layer.
    The final AASIST model can be connected here.
    """

    try:

        import librosa


        audio, sample_rate = librosa.load(
            file_path,
            sr=16000,
            mono=True
        )


        if len(audio) == 0:

            raise ValueError(
                "Audio file contains no samples"
            )


        duration = len(audio) / sample_rate


        rms = float(
            np.sqrt(
                np.mean(
                    np.square(audio)
                )
            )
        )


        zero_crossing = float(
            np.mean(
                librosa.feature.zero_crossing_rate(
                    audio
                )
            )
        )


        spectral_centroid = float(
            np.mean(
                librosa.feature.spectral_centroid(
                    y=audio,
                    sr=sample_rate
                )
            )
        )


        mfcc = librosa.feature.mfcc(
            y=audio,
            sr=sample_rate,
            n_mfcc=13
        )


        mfcc_mean = float(
            np.mean(
                np.abs(mfcc)
            )
        )


        return {

            "duration": duration,

            "rms": rms,

            "zero_crossing": zero_crossing,

            "spectral_centroid":
                spectral_centroid,

            "mfcc_mean":
                mfcc_mean

        }


    except Exception as error:

        print(
            "Feature extraction error:",
            error
        )

        return {

            "duration": 0.0,
            "rms": 0.0,
            "zero_crossing": 0.0,
            "spectral_centroid": 0.0,
            "mfcc_mean": 0.0

        }


# ============================================================
# BASELINE VOICE ANALYZER
# ============================================================

def analyze_audio(file_path):

    """
    Baseline audio analyzer.

    IMPORTANT:
    This currently performs real audio feature extraction.
    It is NOT being falsely presented as an AASIST model.

    AASIST/RawNet model weights can be plugged into this
    function when the trained model is available.
    """

    features = calculate_audio_features(
        file_path
    )


    duration = features["duration"]
    rms = features["rms"]
    zcr = features["zero_crossing"]
    centroid = features["spectral_centroid"]
    mfcc_mean = features["mfcc_mean"]


    # --------------------------------------------------------
    # Basic signal quality score
    # --------------------------------------------------------

    quality_score = 0.0


    if duration >= 1.0:

        quality_score += 0.20


    if duration >= 2.5:

        quality_score += 0.15


    if rms > 0.005:

        quality_score += 0.20


    if centroid > 500:

        quality_score += 0.15


    if mfcc_mean > 5:

        quality_score += 0.15


    if zcr > 0.01:

        quality_score += 0.15


    quality_score = min(
        quality_score,
        1.0
    )


    # --------------------------------------------------------
    # Conservative baseline decision
    #
    # We don't claim that acoustic heuristics alone can
    # reliably detect deepfake voices.
    # --------------------------------------------------------

    if duration < 0.8:

        synthetic_score = 0.0

        human_score = 0.0

        label = "INSUFFICIENT AUDIO"

        model_name = "audio-quality-check"


    else:

        # Baseline uncertainty.
        #
        # Actual anti-spoof classifier should replace this.

        synthetic_score = round(
            max(
                0.05,
                min(
                    0.45,
                    0.35 -
                    (
                        quality_score * 0.10
                    )
                )
            ),
            4
        )


        human_score = round(
            1.0 - synthetic_score,
            4
        )


        label = "ANALYSIS COMPLETE"

        model_name = "baseline-audio-analyzer"


    # --------------------------------------------------------
    # Risk
    # --------------------------------------------------------

    risk_score = round(
        synthetic_score * 100,
        2
    )


    if label == "INSUFFICIENT AUDIO":

        risk_level = "MEDIUM"

        decision = "VERIFY"

        recommendation = (
            "The audio sample is too short or "
            "poor quality. Collect a longer voice "
            "sample before making a security decision."
        )


    elif risk_score >= 70:

        risk_level = "HIGH"

        decision = "BLOCK"

        recommendation = (
            "Potential voice impersonation detected. "
            "Do not share OTPs, passwords or financial "
            "information."
        )


    elif risk_score >= 40:

        risk_level = "MEDIUM"

        decision = "VERIFY"

        recommendation = (
            "Voice requires additional verification "
            "before trusting the caller."
        )


    else:

        risk_level = "LOW"

        decision = "ALLOW"

        recommendation = (
            "No strong spoofing signal was detected "
            "by the current analyzer. Continue normal "
            "security precautions."
        )


    return {

        "analysis": {

            "label": label,

            "synthetic_score":
                synthetic_score,

            "human_score":
                human_score,

            "model":
                model_name,

            "analysis_mode":
                "audio_features"

        },

        "risk": {

            "risk_level":
                risk_level,

            "risk_score":
                risk_score,

            "decision":
                decision,

            "recommendation":
                recommendation

        },

        "features": features

    }


# ============================================================
# VOICE ANALYZE API
# ============================================================

@app.post("/api/voice/analyze")
async def voice_analyze(
    file: UploadFile = File(...)
):

    extension = os.path.splitext(
        file.filename or ""
    )[1].lower()


    allowed_extensions = [

        ".wav",
        ".mp3",
        ".webm",
        ".ogg",
        ".m4a",
        ".flac"

    ]


    if extension not in allowed_extensions:

        return {

            "success": False,

            "error":
                "Unsupported audio format",

            "allowed":
                allowed_extensions

        }


    unique_name = (
        uuid.uuid4().hex +
        extension
    )


    file_path = os.path.join(
        UPLOAD_DIR,
        unique_name
    )


    try:

        with open(
            file_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )


        result = analyze_audio(
            file_path
        )


        analysis = result["analysis"]

        risk = result["risk"]


        # ----------------------------------------------------
        # Store incident
        # ----------------------------------------------------

        connection = get_db()

        cursor = connection.cursor()


        cursor.execute(
            """
            INSERT INTO incidents (

                filename,
                source,
                label,
                synthetic_score,
                human_score,
                risk_level,
                risk_score,
                decision,
                recommendation,
                model,
                timestamp

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            """,

            (

                file.filename,

                "voice_analysis",

                analysis["label"],

                analysis["synthetic_score"],

                analysis["human_score"],

                risk["risk_level"],

                risk["risk_score"],

                risk["decision"],

                risk["recommendation"],

                analysis["model"],

                datetime.now().isoformat()

            )

        )


        connection.commit()

        connection.close()


        return {

            "success": True,

            "analysis":
                analysis,

            "risk":
                risk,

            "features":
                result["features"]

        }


    except Exception as error:

        traceback.print_exc()


        return {

            "success": False,

            "error":
                str(error)

        }


    finally:

        # Keep files for now for debugging/model development.
        # Later we can add retention/deletion policy.

        pass


# ============================================================
# FRAUD INTELLIGENCE
# ============================================================

@app.get("/api/fraud/incidents")
async def fraud_incidents():

    connection = get_db()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT
            id,
            filename,
            source,
            label,
            synthetic_score,
            human_score,
            risk_level,
            risk_score,
            decision,
            recommendation,
            model,
            timestamp

        FROM incidents

        ORDER BY id DESC

        LIMIT 100
        """
    )


    rows = cursor.fetchall()

    connection.close()


    incidents = []


    for row in rows:

        incidents.append({

            "id":
                row["id"],

            "filename":
                row["filename"],

            "source":
                row["source"],

            "label":
                row["label"],

            "synthetic_score":
                row["synthetic_score"],

            "human_score":
                row["human_score"],

            "risk_level":
                row["risk_level"],

            "risk_score":
                row["risk_score"],

            "decision":
                row["decision"],

            "recommendation":
                row["recommendation"],

            "model":
                row["model"],

            "timestamp":
                row["timestamp"]

        })


    return {

        "success": True,

        "incidents":
            incidents

    }


# ============================================================
# SECURITY ASSISTANT
# ============================================================

@app.post("/api/assistant/ask")
async def assistant_ask(payload: dict):

    question = str(
        payload.get(
            "question",
            ""
        )
    ).strip()


    if not question:

        return {

            "success": False,

            "answer":
                "Please enter a security question."

        }


    q = question.lower()


    # --------------------------------------------------------
    # Rule-based security knowledge layer
    # --------------------------------------------------------

    if (
        "otp" in q or
        "one time password" in q
    ):

        answer = (
            "Never share an OTP with a caller, even if "
            "the voice sounds exactly like someone you know. "
            "End the call and independently contact the person "
            "using a trusted number."
        )


    elif (
        "voice clone" in q or
        "deepfake" in q or
        "ai voice" in q
    ):

        answer = (
            "AI voice cloning can reproduce a person's voice "
            "from relatively short recordings. Do not trust "
            "voice identity alone for financial or sensitive "
            "requests. EchoShield should combine voice "
            "anti-spoof analysis with caller verification."
        )


    elif (
        "scam" in q or
        "fraud" in q
    ):

        answer = (
            "If a caller pressures you to transfer money, "
            "share OTPs, reveal passwords or bypass normal "
            "verification, treat the call as suspicious. "
            "Stop the transaction and verify the caller "
            "through an independent trusted channel."
        )


    elif (
        "suspicious" in q or
        "suspicious call" in q
    ):

        answer = (
            "For a suspicious call, do not provide sensitive "
            "information. Use a second communication channel "
            "to verify the caller. Check EchoShield's risk "
            "result and follow the recommended verification step."
        )


    elif (
        "echoshield" in q
    ):

        answer = (
            "EchoShield is designed to detect suspicious or "
            "AI-generated voice activity, assign a risk level, "
            "store security incidents and provide warnings "
            "during protected communication."
        )


    else:

        answer = (
            "For voice-security questions, avoid trusting "
            "voice identity alone. Verify unexpected requests "
            "through an independent channel and never share "
            "OTPs, passwords or financial credentials."
        )


    return {

        "success": True,

        "answer":
            answer

    }


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    import uvicorn


    uvicorn.run(

        "main:app",

        host="127.0.0.1",

        port=8000,

        reload=True

    )