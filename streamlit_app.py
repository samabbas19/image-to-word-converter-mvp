"""Streamlit Community Cloud entrypoint."""

from pathlib import Path


APP_FILE = Path(__file__).with_name("app.py")
exec(compile(APP_FILE.read_text(encoding="utf-8"), str(APP_FILE), "exec"))
