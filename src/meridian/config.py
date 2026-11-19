"""Paths and environment defaults. No network calls here."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def _find_root(marker: str = "policy.md") -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / marker).exists():
            return parent
    raise FileNotFoundError(f"Could not find {marker!r} above {here}")

ROOT = _find_root()
# ROOT = Path(__file__).resolve().parent.parent.parent
POLICY_PATH = ROOT / "policy.md"
CASES_PATH = ROOT / "cases.json"
DEMO_OUTPUTS_PATH = ROOT / "demo_outputs.json"


DEFAULT_MODEL = "euri-auto"
DEFAULT_BASE_URL = "https://api.euron.one/api/v1/euri"
REQUEST_TIMEOUT_SECONDS = 30

API_KEY_ENV = "APP_EURI_API_KEY"
MODEL_ENV = "APP_EURI_MODEL"
BASE_URL_ENV = "APP_EURI_BASE_URL"


def api_key() -> str:
    return (os.getenv(API_KEY_ENV) or "").strip()


def model() -> str:
    return (os.getenv(MODEL_ENV) or "").strip() or DEFAULT_MODEL


def base_url() -> str:
    return (os.getenv(BASE_URL_ENV) or "").strip() or DEFAULT_BASE_URL


def load_policy_text() -> str:
    return POLICY_PATH.read_text(encoding="utf-8")


def policy_lines() -> list[str]:
    return [l.strip() for l in load_policy_text().splitlines() if l.strip()]

if __name__ == "__main__":
    print("ROOT       :", ROOT)
    print("POLICY_PATH:", POLICY_PATH, POLICY_PATH.exists())
    print("CASES_PATH :", CASES_PATH, CASES_PATH.exists())
