# src/meridian/validation.py
from __future__ import annotations

from typing import Any


class ContractError(ValueError):
    """Raised when a demo payload does not match the Meridian contract."""


def _is_json_object(value: Any) -> bool:
    return isinstance(value, dict)


def validate_demo_result(result: Any) -> dict:
    """
    Validate a single demo result before it goes to EuriClient.

    Contract:
      result must be a dict
      result["label"] must be a non-empty str
      result["draft"] must be a non-empty str
      result["needs_human_review"] must be a bool
    """
    if not _is_json_object(result):
        raise ContractError(
            f"Demo result for 'label' must be a JSON object, "
            f"got {type(result).__name__}"
        )

    label = result.get("label")
    if not isinstance(label, str) or not label.strip():
        raise ContractError(
            f"Demo result for 'label' must be a JSON object, "
            f"got {type(label).__name__} = {label!r}"
        )

    draft = result.get("draft")
    if not isinstance(draft, str) or not draft.strip():
        raise ContractError(
            f"Demo result for 'draft' must be a non-empty string, "
            f"got {type(draft).__name__}"
        )

    if not isinstance(result.get("needs_human_review"), bool):
        raise ContractError("'needs_human_review' must be a bool")

    return result