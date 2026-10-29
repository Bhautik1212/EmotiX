#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
export EMOTIX_SECRET_KEY="${EMOTIX_SECRET_KEY:-change-this-local-secret-before-deployment}"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
