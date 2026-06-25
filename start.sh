#!/bin/bash
source "$(dirname "$0")/venv/bin/activate"
cd "$(dirname "$0")"
exec python3 app.py
