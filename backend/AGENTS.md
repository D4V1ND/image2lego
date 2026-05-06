# Backend architecture instructions

Goal: clean up the backend architecture safely and incrementally.

Rules:
- Work only inside backend unless the task explicitly requires otherwise.
- Preserve existing API behavior and response shapes.
- Do not change database schema unless explicitly requested.
- Do not rewrite the backend from scratch.
- Keep each change small and reviewable.
- Add or update tests when touching behavior.
- Separate routing/controllers, business logic/services, data access/repositories, validation/schemas, and external integrations.
- Avoid circular dependencies.
- Move duplicated logic into shared backend utilities only when there is real duplication.
- Isolate side effects such as database access, network calls, queues, filesystem access, and auth/session handling.
- Run backend tests, lint, and type checks before finishing.
- Summarize what changed, why it improves architecture, what checks were run, and remaining risks.