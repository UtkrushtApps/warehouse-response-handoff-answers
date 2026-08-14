from __future__ import annotations

from typing import Any

import pytest

from agent.coordinator import CoordinationError, DispatcherAgent
from agent.messages import AgentMessage, Performative
from agent.specialists import RobotAgent

DISPATCHER_ID = "dispatcher"
ROBOT_ID = "robot-07"
CONVERSATION_ID = "wave-41"
TASK_ID = "pick-1842"
ASSIGNED = "assigned"
REFUSED = "refused"
LOW_BATTERY = "battery below safe assignment threshold"
READY = "ready for assignment"


class LocalDecision:
    def __init__(self, *, accepted: bool, reason: str) -> None:
        self.accepted = accepted
        self.reason = reason
        self.calls = 0

    def decide_assignment(
        self, *, task: dict[str, Any], telemetry: dict[str, Any]
    ) -> dict[str, Any]:
        self.calls += 1
        return {"accepted": self.accepted, "reason": self.reason}


def make_robot(decision: LocalDecision) -> RobotAgent:
    return RobotAgent(
        agent_id=ROBOT_ID,
        telemetry={"available": decision.accepted},
        decision_client=decision,
    )


def test_agreement_records_assignment() -> None:
    decision = LocalDecision(accepted=True, reason=READY)
    dispatcher = DispatcherAgent(agent_id=DISPATCHER_ID)

    request, response, state = dispatcher.dispatch(
        robot=make_robot(decision),
        conversation_id=CONVERSATION_ID,
        task={"task_id": TASK_ID},
    )

    assert request.conversation_id == response.conversation_id
    assert response.performative is Performative.AGREE
    assert state.status == ASSIGNED
    assert state.robot_id == ROBOT_ID
    assert decision.calls == 1


def test_refusal_does_not_record_assignment() -> None:
    decision = LocalDecision(accepted=False, reason=LOW_BATTERY)
    dispatcher = DispatcherAgent(agent_id=DISPATCHER_ID)

    _, response, state = dispatcher.dispatch(
        robot=make_robot(decision),
        conversation_id=CONVERSATION_ID,
        task={"task_id": TASK_ID},
    )

    assert response.performative is Performative.REFUSE
    assert state.status == REFUSED
    assert state.robot_id == ROBOT_ID
    assert state.reason == LOW_BATTERY
    assert dispatcher.task_state(TASK_ID) == state


def test_mismatched_conversation_cannot_change_state() -> None:
    dispatcher = DispatcherAgent(agent_id=DISPATCHER_ID)
    request = dispatcher.create_request(
        robot_id=ROBOT_ID,
        conversation_id=CONVERSATION_ID,
        task={"task_id": TASK_ID},
    )
    response = AgentMessage(
        sender=ROBOT_ID,
        receiver=DISPATCHER_ID,
        conversation_id="another-wave",
        performative=Performative.AGREE,
        payload={"task_id": TASK_ID, "reason": READY},
    )

    with pytest.raises(CoordinationError):
        dispatcher.handle_response(request, response)

    assert dispatcher.task_state(TASK_ID) is None


def test_mismatched_task_cannot_change_state() -> None:
    dispatcher = DispatcherAgent(agent_id=DISPATCHER_ID)
    request = dispatcher.create_request(
        robot_id=ROBOT_ID,
        conversation_id=CONVERSATION_ID,
        task={"task_id": TASK_ID},
    )
    response = AgentMessage(
        sender=ROBOT_ID,
        receiver=DISPATCHER_ID,
        conversation_id=CONVERSATION_ID,
        performative=Performative.REFUSE,
        payload={"task_id": "pick-elsewhere", "reason": LOW_BATTERY},
    )

    with pytest.raises(CoordinationError):
        dispatcher.handle_response(request, response)

    assert dispatcher.task_state(TASK_ID) is None


def test_unsupported_response_cannot_change_state() -> None:
    dispatcher = DispatcherAgent(agent_id=DISPATCHER_ID)
    request = dispatcher.create_request(
        robot_id=ROBOT_ID,
        conversation_id=CONVERSATION_ID,
        task={"task_id": TASK_ID},
    )
    response = AgentMessage(
        sender=ROBOT_ID,
        receiver=DISPATCHER_ID,
        conversation_id=CONVERSATION_ID,
        performative=Performative.REQUEST,
        payload={"task_id": TASK_ID},
    )

    with pytest.raises(CoordinationError):
        dispatcher.handle_response(request, response)

    assert dispatcher.task_state(TASK_ID) is None
