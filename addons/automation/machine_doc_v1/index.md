# automation — Machine Documentation v1

## Purpose

`automation` is the **workflow engine** for this Odoo fork. It is being
evolved into an n8n-style visual workflow manager: DAG-based, per-execution
isolated, with typed nodes and full execution history.

This is a **strategic core module**. It sits at the intersection of the ORM
trigger system and async infrastructure. Upstream Odoo removed their workflow
engine in v11; this module fills that gap with a modern design.

**The engine and the canvas both exist.** Nodes, typed edges, cycle and scope
constraints, topological ordering, per-execution runtimes, per-step state, node
coordinates, and an editable JointJS canvas on the automation form's Workflow
page. Execution monitoring is live: a run announces each settling on its rule's bus
channel and an open canvas reloads.

## Files at a Glance

| File | Purpose |
|------|---------|
| `models/automation_rule.py` | Rule definition, trigger system, ORM patching, cron |
| `models/ir_actions_server.py` | Node extension: edge one2manys, canvas coordinates, `_sorted_by_dependency` |
| `models/workflow_edge.py` | The typed DAG edge: condition, cycle/scope/self-edge constraints |
| `models/automation_runtime_edge.py` | That edge snapshotted per run, and `_is_satisfied()` — the routing rule |
| `models/automation_runtime.py` | Per-execution instance: state, progress, line orchestration |
| `models/automation_runtime_line.py` | Per-step execution state within a runtime instance |
| `models/ir_cron.py` | Thin bridge: cron → `action_view_automation()` |
| `models/mail_activity.py` | The Approval node's back-link: an activity finishing releases its step |
| `models/ir_websocket.py` | Turns the canvas's requested string channel into a record channel the user may read |
| `models/automation_canvas_viewport.py` | Where each reader last left the canvas of each automation |
| `models/_canvas.py` | The canvas geometry contract both of those read; not a model |
| `static/src/workflow_canvas.js` | The Workflow page's canvas: draws the DAG, drags nodes, draws edges |
| `static/src/workflow_graph.js` | Its pure parts — the connection guard and the class/label maps |
| `tests/test_automation.py` | Core trigger tests (`@tagged post_install`) |
| `tests/test_triggers.py` | All trigger types (no `@tagged`, runs at-install) |
| `tests/test_workflow_dag.py` | DAG dependency and orchestration (no `@tagged`) |
| `tests/test_mail_composer.py` | Mail trigger tests |
| `tests/test_audit_regressions.py` | Regressions from the audit (`@tagged post_install`) |
| `tests/test_registry_hooks.py` | Only rules whose trigger patches a model reload the registry |
| `tests/test_runtime_sync.py` | Skip reasons, root start delays, syncing running runs to an edited definition, adding steps, archived rules, the error policy |
| `tests/test_step_validity.py` | A step skipped once its validity has passed |
| `tests/test_queued_dispatch.py` | Queued runs, the batched dispatcher, commit policy |
| `tests/test_timed_event_edges.py` | Delayed edges, event and no-event edges, exclusive events, the scheduled state |
| `tests/test_run_completion.py` | Dead-path skipping, run completion after a pause, exact resume triggers |
| `tests/test_workflow_canvas.py` | Canvas state: node size bounds, per-reader viewport, stored counts |

## Related Modules

`web` carries the vendored diagramming library this module's canvas will use:
`addons/web/static/lib/joint/`, reachable as the bare specifier `joint`. It sits
there rather than here because `partner_relationship` needs the same
canvas and CI checks `odoo` out alone.

Earlier revisions listed a `web_flow` module in `agromarin/` as the visual DAG
editor. It was **deleted as unused** by `agromarin` `60b5a7eef` (2026-04-21)
four months before this line was corrected — see [`vision.md`](vision.md)
Decision 1 for the removal rationale, which constrained its replacement.

## Read Next

- [`models.md`](models.md) — All models, fields, relationships, known issues
- [`architecture.md`](architecture.md) — Trigger system, hook patching, execution flow
- [`vision.md`](vision.md) — n8n target, phased roadmap, design decisions
- [`conventions.md`](conventions.md) — Naming, patterns, gotchas, what NOT to do
