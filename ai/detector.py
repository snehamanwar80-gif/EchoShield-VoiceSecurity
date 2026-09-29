from .aasist_adapter import analyze_with_aasist


def analyze_audio(audio_path):
    try:
        result = analyze_with_aasist(audio_path)
        return result

    except Exception as error:
        return {
            "status": "MODEL_ERROR",
            "analysis_mode": "AASIST_ERROR",
            "model": "AASIST",
            "synthetic_score": 0.0,
            "human_score": 0.0,
            "confidence": 0.0,
            "label": "MODEL ERROR",
            "error": str(error)
        }