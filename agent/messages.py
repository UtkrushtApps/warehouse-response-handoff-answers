"""Message contract shared by the dispatcher and robot agents."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Performative(str, Enum):
    REQUEST = "request"
    AGREE = "agree"
    REFUSE = "refuse"


@dataclass(frozen=True)
class AgentMessage:
    sender: str
    receiver: str
    conversation_id: str
    performative: Performative
    payload: dict[str, Any]

    def __post_init__(self) -> None:
        for field_name in ("sender", "receiver", "conversation_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if not isinstance(self.payload, dict):
            raise ValueError("payload must be an object")

    def to_dict(self) -> dict[str, Any]:
        performative = self.performative
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "conversation_id": self.conversation_id,
            "performative": (
                performative.value
                if isinstance(performative, Performative)
                else str(performative)
            ),
            "payload": self.payload,
        }
