import traceback
from pathlib import Path

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import AudioEvidence, AudioAnalysisResult
from .utils import (
    calculate_sha256,
    transcribe_audio,
    analyze_audio_transcript,
)


ALLOWED_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".ogg",
    ".flac",
    ".mp4"
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def home(request):
    return HttpResponse("Audio Evidence Agent API is running!")


@api_view(["POST"])
def upload_audio(request):
    audio = request.FILES.get("audio")
    case_id = request.data.get("case_id")

    if not audio:
        return Response(
            {"error": "Please upload an audio file."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not case_id:
        return Response(
            {"error": "case_id is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    extension = Path(audio.name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        return Response(
            {"error": "Unsupported audio file extension."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if audio.size > MAX_FILE_SIZE:
        return Response(
            {"error": "File size must not exceed 50 MB."},
            status=status.HTTP_400_BAD_REQUEST
        )

    

    evidence = AudioEvidence(
    case_id=case_id,
    audio_file=audio
)

    evidence.sha256_hash = calculate_sha256(audio)
    evidence.save()

    return Response(
        {
            "message": "Audio uploaded successfully.",
            "evidence_id": evidence.id,
            "case_id": evidence.case_id,
            "status": evidence.status
        },
        status=status.HTTP_201_CREATED
    )

@api_view(["GET"])
def verify_audio(request, evidence_id):

    try:
        evidence = AudioEvidence.objects.get(
            id=evidence_id
        )

    except AudioEvidence.DoesNotExist:
        return Response(
            {"error": "Evidence not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if not evidence.sha256_hash:
        return Response(
            {
                "error": "No original hash is recorded for this evidence."
            },
            status=status.HTTP_409_CONFLICT
        )

    try:
        with evidence.audio_file.open("rb") as audio:
            current_hash = calculate_sha256(audio)

    except (OSError, ValueError):
        return Response(
            {"error": "Unable to read the stored audio file."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    is_valid = current_hash == evidence.sha256_hash

    return Response(
        {
            "evidence_id": evidence.id,
            "stored_hash": evidence.sha256_hash,
            "current_hash": current_hash,
            "integrity_verified": is_valid,
            "message": (
                "Integrity verification passed."
                if is_valid
                else "Integrity verification failed. "
                     "The file differs from the recorded hash."
            )
        },
        status=(
            status.HTTP_200_OK
            if is_valid
            else status.HTTP_409_CONFLICT
        )
    )


@api_view(["POST"])
def transcribe_evidence(request, evidence_id):
    try:
        evidence = AudioEvidence.objects.get(id=evidence_id)
    except AudioEvidence.DoesNotExist:
        return Response(
            {"error": "Evidence not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if not evidence.sha256_hash:
        return Response(
            {"error": "No original SHA-256 hash recorded."},
            status=status.HTTP_409_CONFLICT
        )

    # Step 1: Verify audio integrity
    try:
        with evidence.audio_file.open("rb") as audio:
            current_hash = calculate_sha256(audio)

    except (OSError, ValueError):
        return Response(
            {"error": "Unable to read the stored audio file."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    if current_hash != evidence.sha256_hash:
        return Response(
            {
                "error": "Integrity verification failed. "
                         "Transcription blocked."
            },
            status=status.HTTP_409_CONFLICT
        )

    # Step 2: Transcribe audio after integrity verification
    try:
        result = transcribe_audio(evidence.audio_file.path)

    except Exception as e:
        traceback.print_exc()

        return Response(
            {
                "error": "Transcription failed.",
                "details": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Step 3: Return transcription results
    return Response(
        {
            "evidence_id": evidence.id,
            "integrity_verified": True,
            "language": result["language"],
            "language_probability": result["language_probability"],
            "full_text": result["full_text"],
            "segments": result["segments"]
        },
        status=status.HTTP_200_OK
    )

@api_view(["POST"])
def analyze_audio_evidence(request, evidence_id):
    # 1. Find the evidence record.
    try:
        evidence = AudioEvidence.objects.get(id=evidence_id)
    except AudioEvidence.DoesNotExist:
        return Response(
            {"error": "Evidence not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # 2. Check that the original hash exists.
    if not evidence.sha256_hash:
        return Response(
            {"error": "Original SHA-256 hash is missing."},
            status=status.HTTP_409_CONFLICT,
        )

    # 3. Verify the current audio file's integrity.
    try:
        with evidence.audio_file.open("rb") as audio:
            current_hash = calculate_sha256(audio)
    except (OSError, ValueError):
        return Response(
            {"error": "Unable to read the stored audio file."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if current_hash != evidence.sha256_hash:
        return Response(
            {
                "error": "Integrity verification failed. "
                         "Analysis blocked."
            },
            status=status.HTTP_409_CONFLICT,
        )

    # 4. Return cached results if the audio has not changed.
    try:
        saved_result = evidence.analysis_result
    except AudioAnalysisResult.DoesNotExist:
        saved_result = None

    if (
        saved_result is not None
        and saved_result.processed_hash == current_hash
    ):
        return Response(
            {
                "evidence_id": evidence.id,
                "integrity_verified": True,
                "cached": True,
                "transcription": saved_result.transcription,
                "analysis": saved_result.analysis,
            },
            status=status.HTTP_200_OK,
        )

    # 5. Transcribe and analyze the audio if no valid result exists.
    try:
        transcription = transcribe_audio(evidence.audio_file.path)

        analysis = analyze_audio_transcript(
            transcription["full_text"],
            evidence.id,
        )

        # 6. Save new results or update the existing record.
        saved_result, created = AudioAnalysisResult.objects.update_or_create(
            evidence=evidence,
            defaults={
                "transcription": transcription,
                "analysis": analysis,
                "processed_hash": current_hash,
            },
        )

        evidence.status = "analyzed"
        evidence.save(update_fields=["status"])

        return Response(
            {
                "evidence_id": evidence.id,
                "integrity_verified": True,
                "cached": False,
                "transcription": saved_result.transcription,
                "analysis": saved_result.analysis,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        traceback.print_exc()

        return Response(
            {
                "error": "Audio analysis failed.",
                "details": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def get_audio_analysis(request, evidence_id):
    try:
        evidence = AudioEvidence.objects.get(id=evidence_id)
    except AudioEvidence.DoesNotExist:
        return Response(
            {"error": "Evidence not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        saved_result = evidence.analysis_result
    except AudioAnalysisResult.DoesNotExist:
        return Response(
            {
                "error": "Analysis has not been generated for this evidence."
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        {
            "evidence_id": evidence.id,
            "case_id": evidence.case_id,
            "integrity_hash_at_processing": saved_result.processed_hash,
            "transcription": saved_result.transcription,
            "analysis": saved_result.analysis,
            "created_at": saved_result.created_at,
            "updated_at": saved_result.updated_at,
        },
        status=status.HTTP_200_OK,
    )
