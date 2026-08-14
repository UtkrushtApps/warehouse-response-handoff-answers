"""Real OpenAI-compatible decision client used by the robot agent."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from agent.config import Settings


class LLMDecisionClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for an end-to-end run")
        self._model = settings.model
        self._client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)

    def decide_assignment(
        self, *, task: dict[str, Any], telemetry: dict[str, Any]
    ) -> dict[str, Any]:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a warehouse robot decision component. Determine whether "
                        "the robot can safely accept the supplied pick task from its current "
                        "telemetry. Return JSON only with boolean 'accepted' and string "
                        "'reason'. Refuse when telemetry explicitly marks the robot unavailable."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({"task": task, "telemetry": telemetry}),
                },
            ],
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("model returned an empty decision")

        try:
            decision = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("model decision must be valid JSON") from exc

        if not isinstance(decision, dict):
            raise ValueError("model decision must be a JSON object")
        return decision
