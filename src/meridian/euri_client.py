from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests


class EuriError(RuntimeError):
    """Raised when the Euri API cannot return a usable draft."""


@dataclass(frozen=True)
class EuriClient:
    api_key: str
    model: str = "euri-auto"
    base_url: str = "https://api.euron.one/api/v1/euri"
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "EuriClient":
        return cls(
            api_key=os.environ.get("APP_EURI_API_KEY", ""),
            model=os.environ.get("APP_EURI_MODEL", "euri-auto"),
            base_url=os.environ.get("APP_EURI_BASE_URL", "https://api.euron.one/api/v1/euri"),
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip())

    def draft(self, policy: str, case: dict[str, Any]) -> str:
        if not self.configured:
            raise EuriError("APP_EURI_API_KEY is not set")
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise EuriError("APP_EURI_BASE_URL must be a valid HTTPS URL")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Draft a customer-support reply using the supplied policy. Do not claim a refund, resolution, message delivery, or record change has occurred. Return only draft text.\n\nPOLICY:\n" + policy},
                {"role": "user", "content": (
                    f"Case {case['case_id']}\nCustomer message: {case['customer_question']}\n"
                    f"Issue status: {case['issue_status']}\nIssue details: {case.get('issue_details', '')}\n"
                    f"Order: {case.get('order_id', '')}; product: {case.get('product', '')}\n"
                    f"Delivery date: {case.get('delivery_date')}"
                )},
            ],
            "temperature": 0.2,
        }
        try:
            response = requests.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise EuriError("Euri request timed out") from exc
        except requests.RequestException as exc:
            raise EuriError(f"Euri request failed: {type(exc).__name__}") from exc
        if not response.ok:
            # Do not echo provider response bodies, which may contain sensitive data.
            raise EuriError(f"Euri returned HTTP {response.status_code}")
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise EuriError("Unexpected Euri response shape") from exc
        if not isinstance(content, str) or not content.strip():
            raise EuriError("Euri returned an empty draft")
        return content.strip()
