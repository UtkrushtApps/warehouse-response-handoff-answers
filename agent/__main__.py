"""Fixture readiness check and optional real end-to-end entry point."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from agent.config import Settings
from agent.coordinator import DispatcherAgent
from agent.llm_client import LLMDecisionClient
from agent.specialists import RobotAgent


def load_fixture(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("fixture must be a JSON object")

    required = ("conversation_id", "robot", "task")
    missing = [name for name in required if name not in data]
    if missing:
        raise ValueError(f"fixture missing fields: {', '.join(missing)}")

    conversation_id = data["conversation_id"]
    if not isinstance(conversation_id, str) or not conversation_id.strip():
        raise ValueError("fixture conversation_id must be a non-empty string")
    if not isinstance(data["robot"], dict) or not isinstance(data["task"], dict):
        raise ValueError("robot and task fixture values must be objects")
    if "robot_id" not in data["robot"] or "telemetry" not in data["robot"]:
        raise ValueError("robot fixture is incomplete")
    if not isinstance(data["robot"]["telemetry"], dict):
        raise ValueError("robot telemetry must be an object")
    if "task_id" not in data["task"]:
        raise ValueError("task fixture is incomplete")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Warehouse assignment simulator")
    parser.add_argument(
        "fixture",
        type=Path,
        nargs="?",
        default=Path("fixtures/example.json"),
    )
    parser.add_argument(
        "--run-agent",
        action="store_true",
        help="execute the real model-backed two-agent interaction",
    )
    args = parser.parse_args()
    fixture = load_fixture(args.fixture)

    if not args.run_agent:
        print(f"fixture ready: {fixture['conversation_id']}")
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    client = LLMDecisionClient(Settings.from_env())
    robot = RobotAgent(
        agent_id=fixture["robot"]["robot_id"],
        telemetry=fixture["robot"]["telemetry"],
        decision_client=client,
    )
    dispatcher = DispatcherAgent()
    request, response, state = dispatcher.dispatch(
        robot=robot,
        conversation_id=fixture["conversation_id"],
        task=fixture["task"],
    )
    print(
        json.dumps(
            {
                "request": request.to_dict(),
                "response": response.to_dict(),
                "state": {
                    "status": state.status,
                    "robot_id": state.robot_id,
                    "reason": state.reason,
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
