"""Environment configuration for real model-backed runs."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    base_url: str
    model: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(".env")
        return cls(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("AGENT_MODEL", "gpt-4o-mini"),
        )
