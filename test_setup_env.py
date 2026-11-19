"""Tests for the .env writer."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from setup_env import DEFAULT_BASE_URL, DEFAULT_MODEL, write_env  # noqa: E402


def test_write_env_creates_file_with_all_keys(tmp_path):
    target = tmp_path / ".env"
    write_env("test-key-123", path=target)
    text = target.read_text(encoding="utf-8")
    assert "APP_EURI_API_KEY=test-key-123" in text
    assert f"APP_EURI_MODEL={DEFAULT_MODEL}" in text
    assert f"APP_EURI_BASE_URL={DEFAULT_BASE_URL}" in text


def test_write_env_rejects_blank_key(tmp_path):
    with pytest.raises(ValueError):
        write_env("   ", path=tmp_path / ".env")


def test_write_env_falls_back_to_defaults(tmp_path):
    target = tmp_path / ".env"
    write_env("k", model="", base_url="", path=target)
    text = target.read_text(encoding="utf-8")
    assert f"APP_EURI_MODEL={DEFAULT_MODEL}" in text
    assert f"APP_EURI_BASE_URL={DEFAULT_BASE_URL}" in text


def test_write_env_does_not_leave_partial_file_on_error(tmp_path):
    target = tmp_path / ".env"
    with pytest.raises(ValueError):
        write_env("", path=target)
    assert not target.exists()
