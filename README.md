# Audio Evidence Agent

An AI-powered audio evidence processing system built with Django REST Framework. It helps investigators process audio evidence, verify file integrity, generate transcriptions, and extract meaningful information using AI.

## Features

- Upload audio evidence through a REST API.
- Verify audio file integrity using SHA-256 hashing.
- Transcribe audio using Faster-Whisper.
- Analyze transcripts using a local LLM through Ollama.
- Store transcription and analysis results in a database.
- Reuse previously saved results to avoid unnecessary reprocessing.
- Retrieve saved analysis through an API endpoint.

## Technologies Used

- Python
- Django
- Django REST Framework
- Faster-Whisper
- Ollama
- Qwen3 4B
- SQLite

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/manishChav/AudioEvidenceAgent.git
cd AudioEvidenceAgent
```

### 2. Create and activate a virtual environment

Windows:

```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install and run Ollama

Install Ollama, then download the model:

```bash
ollama pull qwen3:4b
```

Ensure Ollama is running before using the analysis endpoint.

### 5. Apply database migrations

```bash
python manage.py migrate
```

### 6. Start the Django server

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`.

## API Endpoints

| Method | Endpoint                           |Purpose                  |
|---     |---                                 |---                      |
| POST   | `/api/evidence/upload-audio/`      | Upload audio evidence   |
| GET    | `/api/evidence/verify-audio/<id>/` | Verify file integrity   |
| POST   | `/api/evidence/transcribe/<id>/`   | Transcribe audio        |
| POST   | `/api/evidence/analyze/<id>/`      | Analyze audio           |
| GET    | `/api/evidence/analysis/<id>/`     | Retrieve saved analysis |

## Notes

- Ollama and the required language model must be installed locally for AI analysis.
- Uploaded audio files and local database files are not included in the repository.
- This project is intended as an academic and portfolio project. Verify AI-generated findings before using them in real investigations.