"""Robot agent that owns local availability and assignment decisions."""

from __future__ import annotations

from typing import Any, Protocol

from agent.messages import AgentMessage, Performative


class DecisionClient(Protocol):
    def decide_assignment(
        self, *, task: dict[str, Any], telemetry: dict[str, Any]
    ) -> dict[str, Any]: ...


class RobotAgent:
    def __init__(
        self,
        *,
        agent_id: str,
        telemetry: dict[str, Any],
        decision_client: DecisionClient,
    ) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id must be a non-empty string")
        if not isinstance(telemetry, dict):
            raise ValueError("telemetry must be an object")
        self.agent_id = agent_id
        self.telemetry = dict(telemetry)
        self._decision_client = decision_client

    def handle_message(self, message: AgentMessage) -> AgentMessage:
        if not isinstance(message, AgentMessage):
            raise ValueError("message must be an AgentMessage")
        if message.receiver != self.agent_id:
            raise ValueError("request addressed to another robot")
        if message.performative is not Performative.REQUEST:
            raise ValueError("robot only handles assignment requests")

        task = message.payload.get("task")
        if not isinstance(task, dict):
            raise ValueError("request payload must contain a task object")
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id must be a non-empty string")

        decision = self._decision_client.decide_assignment(
            task=dict(task),
            telemetry=dict(self.telemetry),
        )
        if not isinstance(decision, dict):
            raise ValueError("robot decision must be an object")

        accepted = decision.get("accepted")
        reason = decision.get("reason")
        if (
            not isinstance(accepted, bool)
            or not isinstance(reason, str)
            or not reason.strip()
        ):
            raise ValueError("robot decision must contain accepted and reason")

        return AgentMessage(
            sender=self.agent_id,
            receiver=message.sender,
            conversation_id=message.conversation_id,
            performative=Performative.AGREE if accepted else Performative.REFUSE,
            payload={"task_id": task_id, "reason": reason},
        )
