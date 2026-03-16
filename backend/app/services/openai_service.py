from __future__ import annotations

from typing import AsyncGenerator, Literal
import math
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI, AsyncAzureOpenAI

from app.utils.format_message import format_user_message

load_dotenv()

ReasoningEffort = Literal["low", "medium", "high"]

# ---------------------------------------------------------------------------
# Azure OpenAI configuration helpers
# ---------------------------------------------------------------------------

def _is_azure_configured() -> bool:
    """Return True when all required Azure OpenAI env vars are present."""
    return all([
        os.getenv("AZURE_OPENAI_API_KEY", "").strip(),
        os.getenv("AZURE_OPENAI_ENDPOINT", "").strip(),
        os.getenv("AZURE_OPENAI_DEPLOYMENT", "").strip(),
    ])


def _get_azure_deployment() -> str:
    return os.getenv("AZURE_OPENAI_DEPLOYMENT", "").strip()


def _get_azure_api_version() -> str:
    return os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview").strip()


def _create_azure_client() -> AsyncAzureOpenAI:
    return AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY", "").strip(),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "").strip(),
        api_version=_get_azure_api_version(),
        max_retries=2,
        timeout=600,
    )


def _is_reasoning_model(deployment: str) -> bool:
    """True for o-series models that accept reasoning_effort on Azure."""
    return deployment.lower().startswith(("o1", "o3", "o4"))


def _count_tokens_with_tiktoken(system_prompt: str, user_prompt: str) -> int:
    """Best-effort token count using tiktoken (cl100k_base encoding)."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        # 4 overhead tokens per message + 2 for reply priming (Chat Completions spec)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        count = 2  # reply priming
        for msg in messages:
            count += 4 + len(enc.encode(msg["content"]))
        return count
    except Exception:
        return math.ceil((len(system_prompt) + len(user_prompt)) / 4)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class OpenAIService:
    def __init__(self):
        self.default_api_key = os.getenv("OPENAI_API_KEY")

    def _resolve_api_key(self, override_api_key: str | None = None) -> str:
        api_key = (override_api_key or self.default_api_key or "").strip()
        if not api_key:
            raise ValueError(
                "Missing OpenAI API key. Set OPENAI_API_KEY or provide api_key in request."
            )
        return api_key

    def _should_use_azure(self, override_api_key: str | None) -> bool:
        """
        Use Azure when:
        - Azure env vars are fully configured, AND
        - The caller did NOT supply their own API key override (which implies vanilla OpenAI).
        """
        if override_api_key and override_api_key.strip():
            return False
        return _is_azure_configured()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        # Mirrors Next.js fallback heuristic.
        return math.ceil(len(text) / 4)

    @staticmethod
    def _build_input(system_prompt: str, user_prompt: str) -> list[dict]:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    @staticmethod
    def _create_vanilla_client(api_key: str) -> AsyncOpenAI:
        # Keep explicit config local to this service.
        return AsyncOpenAI(
            api_key=api_key,
            max_retries=2,
            timeout=600,
        )

    # ------------------------------------------------------------------
    # Azure path — Chat Completions API
    # ------------------------------------------------------------------

    async def _stream_azure_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        reasoning_effort: ReasoningEffort | None,
        max_output_tokens: int | None,
    ) -> AsyncGenerator[str, None]:
        deployment = _get_azure_deployment()
        client = _create_azure_client()
        params: dict = {
            "model": deployment,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": True,
        }
        if max_output_tokens:
            params["max_tokens"] = max_output_tokens
        # reasoning_effort is only supported for o-series models on Azure
        if reasoning_effort and _is_reasoning_model(deployment):
            params["reasoning_effort"] = reasoning_effort

        stream = await client.chat.completions.create(**params)
        try:
            async for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
        finally:
            await client.close()

    # ------------------------------------------------------------------
    # Vanilla OpenAI path — Responses API (backup)
    # ------------------------------------------------------------------

    async def _stream_vanilla_completion(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        api_key: str,
        reasoning_effort: ReasoningEffort | None,
        max_output_tokens: int | None,
    ) -> AsyncGenerator[str, None]:
        payload: dict = {
            "model": model,
            "stream": True,
            "input": self._build_input(system_prompt, user_prompt),
        }
        if reasoning_effort:
            payload["reasoning"] = {"effort": reasoning_effort}
        if max_output_tokens:
            payload["max_output_tokens"] = max_output_tokens

        client = self._create_vanilla_client(api_key)
        stream = await client.responses.create(**payload)
        try:
            async for event in stream:
                if event.type == "response.output_text.delta":
                    delta = getattr(event, "delta", None)
                    if isinstance(delta, str) and delta:
                        yield delta
                    continue

                if event.type == "error":
                    message = getattr(event, "message", None) or "OpenAI stream failed."
                    raise ValueError(str(message))
        finally:
            await stream.close()
            await client.close()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def stream_completion(
        self,
        *,
        model: str,
        system_prompt: str,
        data: dict[str, str | None],
        api_key: str | None = None,
        reasoning_effort: ReasoningEffort | None = None,
        max_output_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        user_prompt = format_user_message(data)

        if self._should_use_azure(api_key):
            async for chunk in self._stream_azure_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                reasoning_effort=reasoning_effort,
                max_output_tokens=max_output_tokens,
            ):
                yield chunk
        else:
            resolved_api_key = self._resolve_api_key(api_key)
            async for chunk in self._stream_vanilla_completion(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                api_key=resolved_api_key,
                reasoning_effort=reasoning_effort,
                max_output_tokens=max_output_tokens,
            ):
                yield chunk

    async def count_input_tokens(
        self,
        *,
        model: str,
        system_prompt: str,
        data: dict[str, str | None],
        api_key: str | None = None,
        reasoning_effort: ReasoningEffort | None = None,
    ) -> int:
        user_prompt = format_user_message(data)

        if self._should_use_azure(api_key):
            # Azure Chat Completions does not expose a dedicated token-count endpoint;
            # use tiktoken for an accurate pre-flight estimate.
            return _count_tokens_with_tiktoken(system_prompt, user_prompt)

        # Vanilla OpenAI — use the Responses input-tokens API (backup path)
        resolved_api_key = self._resolve_api_key(api_key)
        payload: dict = {
            "model": model,
            "input": self._build_input(system_prompt, user_prompt),
        }
        if reasoning_effort:
            payload["reasoning"] = {"effort": reasoning_effort}

        client = self._create_vanilla_client(resolved_api_key)
        try:
            response = await client.responses.input_tokens.count(**payload)
            input_tokens = getattr(response, "input_tokens", None)
            if not isinstance(input_tokens, int):
                raise ValueError("OpenAI input token count returned invalid payload.")
            return input_tokens
        finally:
            await client.close()
