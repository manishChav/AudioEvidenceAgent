from django.db import models


class AudioEvidence(models.Model):
    case_id = models.CharField(max_length=100)
    audio_file = models.FileField(upload_to="audio_evidence/")
    sha256_hash = models.CharField(
        max_length=64,
        blank=True,
        default=""
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=30,
        default="uploaded"
    )

    def __str__(self):
        return f"Audio Evidence {self.id}"


class AudioAnalysisResult(models.Model):
    evidence = models.OneToOneField(
        AudioEvidence,
        on_delete=models.CASCADE,
        related_name="analysis_result",
    )

    transcription = models.JSONField()
    analysis = models.JSONField()

    processed_hash = models.CharField(max_length=64)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analysis for Evidence {self.evidence_id}"