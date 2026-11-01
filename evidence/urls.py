from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),

    path(
        "upload-audio/",
        views.upload_audio,
        name="upload_audio"
    ),

    path(
        "verify-audio/<int:evidence_id>/",
        views.verify_audio,
        name="verify_audio"
    ),

    path(
    "transcribe/<int:evidence_id>/",
    views.transcribe_evidence,
    name="transcribe_evidence"
),

path(
    "analyze/<int:evidence_id>/",
    views.analyze_audio_evidence,
    name="analyze_audio_evidence"
),

path(
    "analysis/<int:evidence_id>/",
    views.get_audio_analysis,
    name="get_audio_analysis",
),
]