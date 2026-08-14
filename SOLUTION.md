# Solution Steps

1. Keep the shared message contract centered on sender, receiver, conversation ID, performative, and payload so both agents use the same correlation fields.

2. Validate task identifiers when the dispatcher creates a request, and preserve the requested robot as the expected response sender.

3. In `DispatcherAgent.handle_response`, validate the original request before interpreting the reply: it must be a dispatcher-originated assignment request containing a valid task.

4. Correlate the response with the active handoff by checking its receiver, robot sender, conversation ID, and payload task ID against the request.

5. Accept only `AGREE` and `REFUSE` response performatives. Map agreement to an `assigned` task state and refusal to a `refused` task state, retaining the robot ID and reason in both cases.

6. Require a non-empty response reason and raise `CoordinationError` with a clear message for malformed, unsupported, or unrelated responses.

7. Perform every validation before writing to `_tasks`, ensuring an invalid response cannot create or overwrite dispatcher state.

8. Emit warning logs when rejecting responses and a structured informational log when a valid assignment outcome is recorded.

9. Validate the robot decision client result and convert its boolean `accepted` value into the corresponding agreement or refusal response while echoing the conversation and task identifiers.

10. Run `pytest -q` to verify the offline assignment, refusal, conversation mismatch, task mismatch, and unsupported-response invariants. Run `bash run.sh` for the package and fixture readiness check.

11. For an optional real model-backed interaction, configure `OPENAI_API_KEY` and any provider-specific `OPENAI_BASE_URL`/`AGENT_MODEL` values in `.env`, then run `python -m agent fixtures/example.json --run-agent`.

