import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types
except ImportError as exc:  # pragma: no cover - depends on the local environment
    genai = None
    types = None
    _IMPORT_ERROR: ImportError | None = exc
else:
    _IMPORT_ERROR = None


load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_CLIENT: Any = None


def _get_client():
    global _CLIENT
    if _IMPORT_ERROR is not None:
        raise RuntimeError("google-genai is not installed") from _IMPORT_ERROR

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Copy .env.example to .env and add your key."
        )

    if _CLIENT is None:
        _CLIENT = genai.Client(api_key=api_key)
    return _CLIENT


def _decode_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```").strip()

    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("The model returned JSON that was not an object")
    return value


def call_json(system_prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Call Gemini and return one validated JSON object."""
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0,
        response_mime_type="application/json",
    )
    contents = json.dumps(payload, ensure_ascii=False)

    last_error: Exception | None = None
    for _ in range(2):
        try:
            response = _get_client().models.generate_content(
                model=MODEL_NAME,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            if status_code == 429:
                raise RuntimeError(
                    "Gemini rate limit reached. Wait briefly and try again."
                ) from exc
            raise RuntimeError(f"Gemini request failed: {exc}") from exc
        try:
            return _decode_json(response.text or "")
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc

    raise RuntimeError("Gemini did not return a valid JSON object") from last_error
