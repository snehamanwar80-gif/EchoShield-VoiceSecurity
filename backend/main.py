from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
import sqlite3
import uuid
import shutil
import traceback

from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "echoshield.db"

DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)


# =========================================================
# AASIST IMPORT
# =========================================================

try:
    from ai.inference.aasist_adapter import (
        analyze_with_aasist,
        aasist_status
    )
except Exception as exc:
    analyze_with_aasist = None

    def aasist_status():
        return {
            "available": False,
            "pretrained": False,
            "model": "AASIST",
            "error": str(exc)
        }


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="EchoShield API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# =========================================================
# DATABASE
# =========================================================

def init_database():
    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS incidents (
            id TEXT PRIMARY KEY,
            filename TEXT,
            risk_score REAL,
            risk_level TEXT,
            decision TEXT,
            model TEXT,
            human_score REAL,
            synthetic_score REAL,
            duration REAL,
            created_at TEXT
        )
        """
    )

    existing = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(incidents)"
        ).fetchall()
    }

    additions = {
        "filename": "TEXT",
        "risk_score": "REAL",
        "risk_level": "TEXT",
        "decision": "TEXT",
        "model": "TEXT",
        "human_score": "REAL",
        "synthetic_score": "REAL",
        "duration": "REAL",
        "created_at": "TEXT"
    }

    for column_name, column_type in additions.items():
        if column_name not in existing:
            try:
                conn.execute(
                    f"ALTER TABLE incidents ADD COLUMN {column_name} {column_type}"
                )
            except sqlite3.OperationalError:
                pass

    conn.commit()
    conn.close()


init_database()


# =========================================================
# SAVE INCIDENT
# =========================================================

def save_incident(
    filename: str,
    risk_score: float,
    risk_level: str,
    decision: str,
    model: str,
    human_score: float,
    synthetic_score: float,
    duration: float
):
    incident_id = "INC-" + uuid.uuid4().hex[:10].upper()

    created_at = datetime.now(
        timezone.utc
    ).isoformat()

    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        INSERT INTO incidents (
            id,
            filename,
            risk_score,
            risk_level,
            decision,
            model,
            human_score,
            synthetic_score,
            duration,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            incident_id,
            filename,
            float(risk_score),
            risk_level,
            decision,
            model,
            float(human_score),
            float(synthetic_score),
            float(duration),
            created_at
        )
    )

    conn.commit()
    conn.close()

    return incident_id


# =========================================================
# RISK CALCULATION
# =========================================================

def calculate_risk(synthetic_score: float, confidence=None):
    """
    synthetic_score is ALWAYS a 0-100 percentage in EchoShield.
    It is a model signal, not a calibrated real-world probability.
    """
    synthetic_score = max(0.0, min(100.0, float(synthetic_score)))

    if confidence is not None:
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = None

    # High synthetic signal -> block/hold.
    if synthetic_score >= 75.0:
        risk_level = "HIGH"
        decision = "BLOCK"

    # Borderline signal or low model confidence -> verify.
    elif synthetic_score >= 45.0 or (
        confidence is not None and confidence < 55.0
    ):
        risk_level = "MEDIUM"
        decision = "VERIFY"

    else:
        risk_level = "LOW"
        decision = "ALLOW"

    return {
        "risk_level": risk_level,
        "decision": decision,
        "risk_score": round(synthetic_score, 2),
        "synthetic_signal": round(synthetic_score, 2),
        "confidence": round(confidence, 2) if confidence is not None else None,
    }


# =========================================================
# FRONTEND
# =========================================================

@app.get("/")
def home():
    return FileResponse(
        FRONTEND_DIR / "index.html"
    )


@app.get("/call")
def call_page():
    return FileResponse(
        FRONTEND_DIR / "call.html"
    )


# =========================================================
# HEALTH
# =========================================================

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "EchoShield",
        "aasist": aasist_status()
    }


@app.get("/api/aasist/status")
def aasist_status_api():
    try:
        return aasist_status()
    except Exception as exc:
        return {
            "available": False,
            "model": "AASIST",
            "pretrained": False,
            "error": str(exc)
        }


# =========================================================
# VOICE ANALYSIS
# =========================================================

@app.post("/api/voice/analyze")
async def analyze_voice(
    file: UploadFile = File(...)
):
    filename = file.filename or "voice.wav"

    if not filename.lower().endswith(".wav"):
        return {
            "success": False,
            "error": "Only WAV audio files are supported."
        }

    status = aasist_status()

    if not status.get("available", False):
        return {
            "success": False,
            "error": "AASIST model is not available.",
            "aasist": status
        }

    safe_name = Path(filename).name

    unique_name = (
        uuid.uuid4().hex
        + "_"
        + safe_name
    )

    saved_path = UPLOAD_DIR / unique_name

    try:
        with saved_path.open("wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer
            )

        if analyze_with_aasist is None:
            raise RuntimeError(
                "AASIST adapter could not be loaded."
            )

        result = analyze_with_aasist(
            saved_path
        )

        if (
            isinstance(result, dict)
            and result.get("status") == "WAITING_FOR_AUDIO"
        ):
            return {
                "success": False,
                "status": "WAITING_FOR_AUDIO",
                "error": result.get(
                    "message",
                    "Audio is too short."
                ),
                "required_seconds": result.get(
                    "required_seconds",
                    status.get(
                        "required_seconds",
                        4.04
                    )
                ),
                "duration_seconds": result.get(
                    "duration_seconds",
                    0
                )
            }

        if not isinstance(result, dict):
            raise RuntimeError(
                "AASIST returned an invalid response."
            )

        # AASIST adapter returns percentages (e.g. 48.14), but
        # older adapters may return fractions (e.g. 0.4814).
        raw_synthetic = float(
            result.get(
                "synthetic_score",
                result.get("synthetic_percent", result.get("spoof_score", 0))
            )
        )
        raw_human = float(
            result.get(
                "human_score",
                result.get("human_percent", result.get("bona_fide_score", 0))
            )
        )

        synthetic_score = raw_synthetic * 100.0 if 0.0 <= raw_synthetic <= 1.0 else raw_synthetic
        human_score = raw_human * 100.0 if 0.0 <= raw_human <= 1.0 else raw_human

        synthetic_score = max(0.0, min(100.0, synthetic_score))
        human_score = max(0.0, min(100.0, human_score))

        # Keep the two displayed signals internally consistent.
        total = synthetic_score + human_score
        if total > 0 and abs(total - 100.0) > 0.5:
            synthetic_score = (synthetic_score / total) * 100.0
            human_score = (human_score / total) * 100.0

        confidence = result.get("confidence")
        try:
            confidence = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            confidence = None

        # If the model did not provide confidence, use the stronger class
        # as a simple decision-confidence signal.
        if confidence is None:
            confidence = max(synthetic_score, human_score)

        risk = calculate_risk(synthetic_score, confidence)

        duration = float(
            result.get(
                "duration_seconds",
                result.get("duration", 0)
            )
        )

        windows_analyzed = result.get("windows_analyzed")
        sample_rate = result.get("sample_rate", 16000)

        incident_id = save_incident(
            filename=filename,
            risk_score=risk["risk_score"],
            risk_level=risk["risk_level"],
            decision=risk["decision"],
            model="AASIST",
            human_score=human_score,
            synthetic_score=synthetic_score,
            duration=duration
        )

        if risk["decision"] == "BLOCK":
            recommendation = (
                "BLOCK/HOLD: Stop the conversation, "
                "do not share sensitive information, "
                "and verify the caller using another trusted channel."
            )

        elif risk["decision"] == "VERIFY":
            recommendation = (
                "VERIFY: Hold sensitive actions and "
                "verify the caller through a trusted method."
            )

        else:
            recommendation = (
                "ALLOW: The voice appears relatively genuine "
                "according to the model. Continue with normal "
                "security precautions."
            )

        return {
            "success": True,
            "status": "ANALYZED",
            "incident_id": incident_id,
            "filename": filename,
            "model": "AASIST",
            "analyzed_by": "Pretrained AASIST Model",
            "pretrained": True,

            # Canonical analysis values used by the frontend.
            "analysis": {
                "model": "AASIST",
                "pretrained": True,
                "analyzed_by": "Pretrained AASIST Model",
                "synthetic_score": round(synthetic_score, 2),
                "human_score": round(human_score, 2),
                "confidence": round(confidence, 2) if confidence is not None else None,
                "duration_seconds": round(duration, 2),
                "sample_rate": sample_rate,
                "windows_analyzed": windows_analyzed,
            },

            # Canonical security decision. risk_score MUST equal the
            # synthetic signal; it must never be a second transformed score.
            "risk": {
                **risk,
                "recommendation": recommendation,
                "score_source": "AASIST synthetic signal",
                "calibrated_probability": False,
            },

            # Backward-compatible flat fields.
            "synthetic_score": round(synthetic_score, 2),
            "human_score": round(human_score, 2),
            "ai_score": round(synthetic_score, 2),
            "genuine_score": round(human_score, 2),
            "risk_score": round(synthetic_score, 2),
            "risk_level": risk["risk_level"],
            "decision": risk["decision"],
            "recommendation": recommendation,
            "confidence": round(confidence, 2) if confidence is not None else None,
            "duration": round(duration, 2),
            "duration_seconds": round(duration, 2),
            "windows_analyzed": windows_analyzed,
            "sample_rate": sample_rate,
            "aasist": status,
            "message": "Voice analyzed by pretrained AASIST. Scores are screening signals, not calibrated probabilities."
        }

    except Exception as exc:
        print("VOICE ANALYSIS ERROR:")
        traceback.print_exc()

        return {
            "success": False,
            "error": str(exc),
            "detail": "Real AASIST analysis failed."
        }


# =========================================================
# FRAUD INTELLIGENCE
# =========================================================

@app.get("/api/fraud/incidents")
def get_incidents():
    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            id,
            filename,
            risk_score,
            risk_level,
            decision,
            model,
            human_score,
            synthetic_score,
            duration,
            created_at
        FROM incidents
        ORDER BY created_at DESC
        """
    ).fetchall()

    conn.close()

    return {
        "success": True,
        "incidents": [
            dict(row)
            for row in rows
        ]
    }


# =========================================================
# REPORTS
# =========================================================

@app.get("/api/reports/stats")
def report_stats():
    conn = sqlite3.connect(DB_PATH)

    rows = conn.execute(
        """
        SELECT
            risk_level,
            COUNT(*)
        FROM incidents
        GROUP BY risk_level
        """
    ).fetchall()

    conn.close()

    stats = {
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0
    }

    for level, count in rows:
        if level in stats:
            stats[level] = int(count)

    return {
        "success": True,
        "HIGH": stats["HIGH"],
        "MEDIUM": stats["MEDIUM"],
        "LOW": stats["LOW"],
        "total": sum(stats.values())
    }


# =========================================================
# SECURITY ASSISTANT
# =========================================================

class AssistantRequest(BaseModel):
    question: str
    analysis: Optional[dict] = None


def build_analysis_reason(
    analysis: dict
):
    if not analysis:
        return (
            "There is no voice analysis attached "
            "to this question yet."
        )

    synthetic = float(
        analysis.get(
            "synthetic_score",
            analysis.get(
                "ai_score",
                0
            )
        )
    )

    human = float(
        analysis.get(
            "human_score",
            analysis.get(
                "genuine_score",
                100.0 - synthetic
            )
        )
    )

    risk = str(
        analysis.get(
            "risk_level",
            "UNKNOWN"
        )
    ).upper()

    decision = str(
        analysis.get(
            "decision",
            "VERIFY"
        )
    ).upper()

    model = analysis.get(
        "model",
        analysis.get(
            "analyzed_by",
            "AASIST"
        )
    )

    if synthetic >= 75:
        signal = (
            f"AASIST produced a high synthetic/AI "
            f"signal of {synthetic:.2f}%."
        )

    elif synthetic >= 45:
        signal = (
            f"AASIST placed the synthetic/AI signal "
            f"in the review range at {synthetic:.2f}%."
        )

    else:
        signal = (
            f"AASIST produced a relatively low "
            f"synthetic/AI signal of {synthetic:.2f}%."
        )

    return (
        f"{signal} "
        f"The human/genuine signal was {human:.2f}%. "
        f"The resulting risk level was {risk} and "
        f"the decision was {decision}. "
        f"The analysis was performed using {model}. "
        f"AASIST is an anti-spoofing classifier, so "
        f"it does not directly provide human-readable "
        f"causes such as a specific pitch, accent, "
        f"or robotic tone."
    )


@app.post("/api/assistant/ask")
def assistant_ask(
    request: AssistantRequest
):
    question = request.question.strip()

    if not question:
        return {
            "answer": "Please enter a question."
        }

    q = question.lower()

    analysis_reason = build_analysis_reason(
        request.analysis or {}
    )

    if (
        "why" in q
        and (
            "fake" in q
            or "flag" in q
            or "synthetic" in q
        )
    ):
        answer = (
            "The voice was flagged based on the "
            "real AASIST anti-spoofing result. "
            + analysis_reason
        )

    elif (
        "pattern" in q
        or "detect" in q
    ) and (
        "aasist" in q
        or "voice" in q
    ):
        answer = (
            "AASIST analyzes learned spectro-temporal "
            "audio representations to distinguish "
            "spoofed/synthetic speech from bona-fide "
            "human speech. "
            + analysis_reason
        )

    elif (
        "suspicious" in q
        or "precaution" in q
        or "fraud call" in q
        or "scam" in q
    ):
        answer = (
            "For a suspicious call, do not share OTPs, "
            "passwords, PINs, banking credentials or "
            "recovery codes. Do not transfer money because "
            "of urgency or pressure. End the call and "
            "verify the person through a trusted second "
            "channel. If EchoShield gives HIGH/BLOCK, "
            "hold the sensitive action."
        )

    elif "aasist" in q:
        answer = (
            "AASIST stands for Audio Anti-Spoofing using "
            "Integrated Spectro-Temporal graph attention "
            "networks. EchoShield uses a pretrained AASIST "
            "anti-spoofing model to distinguish synthetic/"
            "spoofed speech from bona-fide human speech."
        )

    elif (
        "live voice" in q
        or "live protection" in q
        or "record" in q
    ):
        answer = (
            "Live Voice records microphone audio in the "
            "browser. EchoShield converts the recording "
            "to WAV and sends it to the backend. The real "
            "pretrained AASIST model analyzes the audio. "
            "At least about 4.04 seconds of usable audio "
            "are required."
        )

    elif (
        "how do i use" in q
        or "how to use" in q
        or "use the app" in q
    ):
        answer = (
            "Use Live Voice to record and analyze microphone "
            "audio. Use Voice Scanner to upload a WAV file. "
            "Secure Calls provides WebRTC calling. Fraud "
            "Intelligence shows saved incidents. Security "
            "Reports shows real HIGH/MEDIUM/LOW counts."
        )

    elif (
        "risk" in q
        or "threshold" in q
        or "level" in q
    ):
        answer = (
            "EchoShield currently maps the AASIST synthetic "
            "score as follows: below 45% is LOW/ALLOW, "
            "45% to below 75% is MEDIUM/VERIFY, and 75% "
            "or above is HIGH/BLOCK."
        )

    elif (
        "continue" in q
        or "should i" in q
    ):
        if request.analysis:
            decision = str(
                request.analysis.get(
                    "decision",
                    "VERIFY"
                )
            ).upper()

            if decision == "BLOCK":
                answer = (
                    "No. The latest analysis recommends "
                    "BLOCK/HOLD. Stop the sensitive "
                    "conversation and verify the caller "
                    "through another trusted channel."
                )

            elif decision == "VERIFY":
                answer = (
                    "Use caution. The latest analysis "
                    "recommends VERIFY. Avoid sensitive "
                    "actions until the caller is independently "
                    "verified."
                )

            else:
                answer = (
                    "The latest analysis is in the ALLOW "
                    "range, but normal security precautions "
                    "should still be followed."
                )

        else:
            answer = (
                "I need a voice-analysis result to give "
                "a specific recommendation. Until then, "
                "verify unexpected callers independently."
            )

    else:
        answer = (
            "I can help with EchoShield voice analysis, "
            "AASIST, suspicious calls, Live Voice, risk "
            "levels, Secure Calls, Fraud Intelligence and "
            "security precautions."
        )

    return {
        "answer": answer
    }


# =========================================================
# SECURE CALL
# =========================================================

@app.post("/api/call/create")
def create_call():
    room_id = uuid.uuid4().hex[:12]

    return {
        "success": True,
        "room_id": room_id,
        "url": f"/call?room={room_id}"
    }


# =========================================================
# WEBRTC
# =========================================================

rooms = {}


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str
):
    await websocket.accept()

    if room_id not in rooms:
        rooms[room_id] = []

    rooms[room_id].append(websocket)

    try:
        while True:
            message = await websocket.receive_text()

            for peer in rooms.get(
                room_id,
                []
            ):
                if peer is not websocket:
                    try:
                        await peer.send_text(
                            message
                        )
                    except Exception:
                        pass

    except WebSocketDisconnect:
        if room_id in rooms:
            if websocket in rooms[room_id]:
                rooms[room_id].remove(
                    websocket
                )

            if not rooms[room_id]:
                del rooms[room_id]


# =========================================================
# STATIC FRONTEND
# =========================================================

if FRONTEND_DIR.exists():
    app.mount(
        "/frontend",
        StaticFiles(
            directory=FRONTEND_DIR
        ),
        name="frontend"
    )