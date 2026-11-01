import hashlib
import json
import requests

from faster_whisper import WhisperModel


def calculate_sha256(file_obj):
    """Calculate the SHA-256 hash of a file."""
    sha256 = hashlib.sha256()

    for chunk in file_obj.chunks():
        sha256.update(chunk)

    return sha256.hexdigest()


def transcribe_audio(audio_path):
    """Transcribe an audio file using Faster Whisper."""
    model = WhisperModel(
        "base",
        device="cpu",
        compute_type="int8",
    )

    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
    )

    transcript = []

    for segment in segments:
        transcript.append({
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip(),
        })

    full_text = " ".join(
        segment["text"] for segment in transcript
    )

    return {
        "language": info.language,
        "language_probability": round(
            info.language_probability, 3
        ),
        "segments": transcript,
        "full_text": full_text,
    }


def analyze_audio_transcript(transcript, evidence_id):
    """Analyze a transcript using the local Ollama model."""
    url = "http://localhost:11434/api/chat"

    prompt = f"""
Analyze this audio transcript for a digital forensics investigation.

Evidence ID: {evidence_id}

Transcript:
{transcript}

Return a JSON object with these fields:
{{
    "summary": "Brief summary of the conversation",
    "people_mentioned": [],
    "dates_and_times": [],
    "locations_mentioned": [],
    "key_statements": [],
    "uncertainties": [],
    "requires_human_review": true
}}

Rules:
- Use only information supported by the transcript.
- Do not invent facts or identities.
- Use empty lists when information is unavailable.
- Keep the summary concise.
- This is preliminary investigative assistance, not proof of wrongdoing.
"""

    payload = {
        "model": "qwen3:4b",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a concise digital forensics assistant. "
                    "Return only the requested JSON object. "
                    "Do not include explanations outside the JSON."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "stream": False,
        "think": False,
        "format": "json",
        "options": {
            "num_predict": 400,
            "temperature": 0,
        },
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=600,
        )

        response.raise_for_status()

        result = response.json()
        content = result.get("message", {}).get("content", "")

        if not content.strip():
            raise ValueError(
                "Ollama returned empty analysis content. "
                f"Response: {result}"
            )

        try:
            analysis = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Ollama returned invalid JSON: {content}"
            ) from exc

        return analysis

    except requests.exceptions.Timeout as exc:
        raise RuntimeError(
            "Ollama timed out while analyzing the transcript. "
            "Try again or use a shorter transcript."
        ) from exc

    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(
            f"Ollama HTTP error: {exc}. "
            f"Response body: {response.text}"
        ) from exc

    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            f"Could not connect to Ollama: {exc}"
        ) from exc
