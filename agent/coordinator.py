"""Dispatcher agent and its local view of warehouse task state."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, NoReturn

from agent.messages import AgentMessage, Performative
from agent.specialists import RobotAgent

logger = logging.getLogger(__name__)


class CoordinationError(RuntimeError):
    """Raised when the robot response cannot safely update assignment state."""


@dataclass(frozen=True)
class TaskState:
    status: str
    robot_id: str | None = None
    reason: str | None = None


class DispatcherAgent:
    """Allocates warehouse tasks while retaining dispatcher-owned task state."""

    def __init__(self, agent_id: str = "dispatcher") -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id must be a non-empty string")
        self.agent_id = agent_id
        self._tasks: dict[str, TaskState] = {}

    def create_request(
        self,
        *,
        robot_id: str,
        conversation_id: str,
        task: dict[str, Any],
    ) -> AgentMessage:
        if not isinstance(task, dict):
            raise ValueError("task must be an object")
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task.task_id must be a non-empty string")
        return AgentMessage(
            sender=self.agent_id,
            receiver=robot_id,
            conversation_id=conversation_id,
            performative=Performative.REQUEST,
            payload={"task": dict(task)},
        )

    def dispatch(
        self,
        *,
        robot: RobotAgent,
        conversation_id: str,
        task: dict[str, Any],
    ) -> tuple[AgentMessage, AgentMessage, TaskState]:
        request = self.create_request(
            robot_id=robot.agent_id,
            conversation_id=conversation_id,
            task=task,
        )
        response = robot.handle_message(request)
        state = self.handle_response(request, response)
        return request, response, state

    def handle_response(
        self, request: AgentMessage, response: AgentMessage
    ) -> TaskState:
        """Validate and apply a robot response for one assignment handoff.

        A response is correlated using the dispatcher and robot identities, the
        conversation identifier, and the task identifier. All validation is
        completed before dispatcher-owned state is mutated.
        """

        def reject(message: str) -> NoReturn:
            logger.warning("rejecting warehouse assignment response: %s", message)
            raise CoordinationError(message)

        if not isinstance(request, AgentMessage):
            reject("request must be an AgentMessage")
        if not isinstance(response, AgentMessage):
            reject("response must be an AgentMessage")

        if request.performative is not Performative.REQUEST:
            reject("handoff context is not an assignment request")
        if request.sender != self.agent_id:
            reject(
                "request sender does not match this dispatcher "
                f"(expected {self.agent_id!r}, got {request.sender!r})"
            )

        task = request.payload.get("task")
        if not isinstance(task, dict):
            reject("request payload must contain a task object")
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            reject("request task_id must be a non-empty string")

        if response.receiver != self.agent_id:
            reject(
                "response is addressed to another dispatcher "
                f"(expected {self.agent_id!r}, got {response.receiver!r})"
            )
        if response.sender != request.receiver:
            reject(
                "response sender does not match the requested robot "
                f"(expected {request.receiver!r}, got {response.sender!r})"
            )
        if response.conversation_id != request.conversation_id:
            reject(
                "response conversation_id does not match the active handoff "
                f"(expected {request.conversation_id!r}, "
                f"got {response.conversation_id!r})"
            )

        response_task_id = response.payload.get("task_id")
        if not isinstance(response_task_id, str) or not response_task_id.strip():
            reject("response payload must contain a non-empty task_id")
        if response_task_id != task_id:
            reject(
                "response task_id does not match the requested task "
                f"(expected {task_id!r}, got {response_task_id!r})"
            )

        if response.performative is Performative.AGREE:
            status = "assigned"
        elif response.performative is Performative.REFUSE:
            status = "refused"
        else:
            reject(
                "unsupported assignment response performative: "
                f"{response.performative!r}; expected agree or refuse"
            )

        reason = response.payload.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            reject("response payload must contain a non-empty reason")

        state = TaskState(
            status=status,
            robot_id=response.sender,
            reason=reason,
        )
        self._tasks[task_id] = state
        logger.info(
            "warehouse assignment response processed: conversation_id=%s "
            "task_id=%s robot_id=%s status=%s reason=%s",
            request.conversation_id,
            task_id,
            response.sender,
            status,
            reason,
        )
        return state

    def task_state(self, task_id: str) -> TaskState | None:
        return self._tasks.get(task_id)
