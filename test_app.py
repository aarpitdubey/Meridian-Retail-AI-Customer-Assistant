"""Contract and section tests for the Meridian review tool."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.meridian import app as app_module  # noqa: E402
from src.meridian import config  # noqa: E402

REQUIRED_KEYS = {"case_id", "decision", "policy_lines", "draft_reply",
                 "needs_human_review", "reason"}
VALID_DECISIONS = {"eligible_for_review", "not_eligible", "needs_more_info", "unavailable"}


def test_config_paths_exist():
    assert config.POLICY_PATH.name == "policy.md"
    assert config.CASES_PATH.name == "cases.json"
    assert config.POLICY_PATH.exists()
    assert config.CASES_PATH.exists()


def test_policy_has_four_lines():
    lines = [l for l in config.POLICY_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 4


def test_cases_have_c1_c2_c3():
    cases = json.loads(config.CASES_PATH.read_text(encoding="utf-8"))
    assert set(cases) == {"C1", "C2", "C3"}
    assert cases["C2"]["delivery_date"] is None


def test_offline_demo_contract_for_every_case():
    for case_id in ("C1", "C2", "C3"):
        result = app_module.run_case(case_id, offline_demo=True)
        assert REQUIRED_KEYS == set(result)
        assert result["case_id"] == case_id
        assert result["decision"] in VALID_DECISIONS
        assert result["needs_human_review"] is True
        assert isinstance(result["policy_lines"], list) and result["policy_lines"]
        assert result["draft_reply"].strip()


def test_offline_demo_matches_frozen_output():
    frozen = json.loads((ROOT / "demo_outputs.json").read_text(encoding="utf-8"))
    for case_id, expected in frozen.items():
        assert app_module.run_case(case_id, offline_demo=True) == expected


def test_timeout_returns_safe_unavailable():
    result = app_module.run_case("C1", simulate_timeout=True)
    assert result["decision"] == "unavailable"
    assert result["needs_human_review"] is True
    assert REQUIRED_KEYS == set(result)


def test_unknown_case_raises():
    with pytest.raises(KeyError):
        app_module.run_case("C9", offline_demo=True)


def test_cli_offline_demo_prints_json():
    proc = subprocess.run(
        [sys.executable, "app.py", "--case", "C1", "--offline-demo"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["case_id"] == "C1"
    assert payload["needs_human_review"] is True
