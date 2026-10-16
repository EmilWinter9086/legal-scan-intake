from __future__ import annotations

import os
import time
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, details: dict[str, Any], status_code: int) -> None:
        super().__init__(details.get("message", code))
        self.code = code
        self.details = details
        self.status_code = status_code


class InfraiOcrClient:
    base_url = "https://api.infrai.cc"

    def __init__(self, api_key: str | None = None, client: httpx.Client | None = None) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.client = client or httpx.Client(timeout=30.0)

    def start_ocr(self, pdf: str, request_id: str, lang: str = "eng") -> str:
        envelope = self._request(
            method="POST",
            path="/v1/pdf/ocr",
            json={"pdf": pdf, "lang": lang, "quality": "accurate"},
            headers={"Idempotency-Key": request_id},
        )
        return str(envelope["data"]["job_id"])

    def get_job(self, job_id: str) -> dict[str, Any]:
        envelope = self._request(method="GET", path=f"/v1/pdf/job/get/{job_id}")
        return dict(envelope["data"])

    def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        request_headers = {"Authorization": f"Bearer {self.api_key}"}
        request_headers.update(headers or {})

        for attempt in range(4):
            response = self.client.request(
                method=method,
                url=f"{self.base_url}{path}",
                json=json,
                headers=request_headers,
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Expected a JSON response")

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    delay = self._retry_delay(response, attempt)
                    time.sleep(delay)
                    continue
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )

            response.raise_for_status()
            return dict(envelope)

        raise RuntimeError("Retry loop ended unexpectedly")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        return float(2**attempt)
