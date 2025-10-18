# ani-replica

## Requirements

- Python 3.11+
- Docker (for containerized run)
- Make (optional helper)

## Setup

```bash
uv venv
uv pip install -r requirements.txt
uv run uvicorn backend.app.main:app --reload
```

## Docker

```bash
docker compose up --build
```

Application is available at http://localhost:8000.
