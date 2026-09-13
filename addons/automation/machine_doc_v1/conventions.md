# automation — Conventions & Gotchas

## Naming

| Concept | Name | Notes |
|---------|------|-------|
| Rule definition | `automation.rule` | Historical name, keep for compat |
| Node | `ir.actions.server` (extended) | Keep until Phase 3 decision |
| Edge | `predecessor_ids` / `successor_ids` | Transitional — target is `workflow.edge` |
| Execution instance | `automation.runtime` | The right model, wrong scope today |
| Execution step | `automation.runtime.line` | Correct pattern — isolated per execution |
| Visual diagram | — | No model yet; the layout layer is undecided along with the editor |

## Readiness Is `state`, and Only `state`

`automation.runtime.line` deliberately has **no `is_ready` field**. It existed
as a stored computed boolean that read `False` for a line already in state
`ready`, nothing gated on it, and a line could sit `waiting` with `is_ready`
True forever with nothing reconciling the two — which is exactly how a run with
an unresolvable dependency wedged silently. Use
`line._predecessors_satisfied()` when you need to ask whether a step may start.

## A Failed Step Is an Outcome, Not an Exception

`automation.runtime.line.action_execute()` runs the server action inside its own
savepoint and, on failure, rolls that savepoint back, records `error` plus the
message on the line, marks the run `error`, and **returns `False` without
re-raising**. Re-raising unwound the whole transaction and destroyed the
runtime, its lines and the error message — the execution history was erased by
precisely the failures it exists to record. Do not "fix" this back into a raise.

## Predecessors Are Scoped to One Automation

`_check_predecessors_scope` rejects a `predecessor_ids` entry belonging to a
different `automation_rule_id`. Such an edge used to be accepted and then
dropped at runtime, leaving the node `waiting` with nothing that could ever
complete it. Correspondingly, `_create_action_lines` decides readiness from the
*resolved* lines, never from the definition's edges.

## What NOT to Add to `ir.actions.server`

Do not add fields to `ir.actions.server` that track execution state.
`action_state`, `is_ready`, and `error_message` were mistakes and have been
removed in Phase 1. All execution state belongs on `automation.runtime.line`.

If you need to know "what state is this action in", you are asking the wrong
question — ask "what state is this *execution step* (`runtime.line`) in".

## Removed Transitional Fields (Phase 1 Complete)

`use_workflow_dag` and `auto_execute_workflow` have been **removed** from
`automation.rule`. All automations are now DAG-capable. Do not re-add these
fields under any name.

## The `__action_done` Context Key

`context["__action_done"]` is a `dict[automation.rule → recordset]` that
prevents the same automation from firing twice on the same record within one
transaction. It is the recursion guard.

Rules:
- In `__action_feedback` mode (during domain evaluation): mutate the dict in-place.
- Normal mode: copy the dict before adding entries (preserves immutability for
  parallel branches).
- Never clear or remove entries from this dict within a transaction.

## `_filter_pre` vs `_filter_post`

| Method | When evaluated | Domain field | Used by |
|--------|---------------|-------------|---------|
| `_filter_pre` | Before write | `filter_pre_domain` | WRITE triggers only |
| `_filter_post` | After event | `filter_domain` | All triggers |
| `_filter_post_export_domain` | After event | `filter_domain` | Returns `(records, domain)` |

`_filter_pre` is evaluated with old values still in the DB.
`_filter_post` is evaluated after the write has committed to memory.

## safe_eval Usage

All domain evaluation (`filter_domain`, `filter_pre_domain`, `record_getter`)
uses `safe_eval.safe_eval()` with a restricted context from `_prepare_eval_context()`.
Never pass user-controlled strings to Python `eval()`.

The `DOMAIN_FIELDS_RE` regex (not `safe_eval`) is used to extract field names
from domain strings inside compute methods — because compute methods can be
triggered from malicious onchange calls.

## Cron Interval — Only Decreases Automatically

`_update_cron()` only lowers the cron interval when a faster schedule is needed.
It does not automatically increase the interval when short-delay automations are
removed. If the last 1-minute automation is deleted, the cron stays at 1-minute
until manually reset or Odoo restarts. This is acceptable — over-frequent cron
execution is harmless (just slightly wasteful).

## `automation.runtime` Domain Restriction — REMOVED

The `automation_id` domain was removed in Phase 1; any automation can have
runtime instances. This section previously said the restriction was
"intentional … do not work around it", contradicting `models.md` and the code.
Nothing to preserve here — do not reintroduce a domain.

## `_prepare_logging_values` (not `_prepare_loggin_values`)

The correct spelling is `_prepare_logging_values`. Upstream's misspelling
(`_prepare_loggin_values`) is not present in this fork.

## There Is No Visual Editor Yet

Earlier revisions of this file described integrating a `web_flow` module from
`agromarin/` via a `flow.diagram` model and BPMN element mappings. That module was
**deleted as unused** on 2026-04-21 (`agromarin` `60b5a7eef`). Its replacement
is chosen but not written: JointJS is vendored in `web` as the specifier
`joint`, and `vision.md` Decision 1 carries why.

**Import it dynamically.** `const joint = await import("joint")`, inside the
component that needs a canvas — never a top-level import in a
`web.assets_backend` file, which would resolve on every backend page. That is
the mistake `web_flow` shipped, at 2.9 MB per session.

Two model-side things gate the canvas regardless of library:

* **Positions are stored; edges still carry nothing.** `pos_x` / `pos_y` on
  `ir.actions.server` hold the canvas layout, so a diagram round-trips. Write
  them as plain integers — an unplaced node reads `(0, 0)`, and "every node at
  the origin" is what tells a canvas to auto-layout.
* **An edge can carry no attributes.** `predecessor_ids`/`successor_ids` are two
  views of one self-referential many2many, which is why both carry `copy=False`.
  A canvas can *draw* a conditional branch but has nowhere to persist the
  condition until `workflow.edge` lands in Phase 2.

## Test Tags

- `test_automation.py`: `@tagged("post_install", "-at_install")` — correct
- `test_triggers.py`: no `@tagged` — runs at-install, correct for basic model tests
- `test_workflow_dag.py`: no `@tagged` — runs at-install, correct
- `test_audit_regressions.py`: `@tagged("post_install", "-at_install")`

Do not add `@tagged("post_install")` to `test_triggers.py` or
`test_workflow_dag.py` — these tests do not require post-install state.

## Stdout is Empty

All test output goes to `./odoo.log` (set in `conf/odoo.conf`). Always:

```bash
> ./odoo.log && ./odoo/odoo-bin -c ./conf/odoo.conf -d test_db \
    --test-tags '/automation' -u automation --stop-after-init --workers=0
grep "tests when loading" ./odoo.log
```

## Two traps this module has already paid for

**`self.env._()` names its first parameter `source`.** So
`self.env._("%(source)s ...", source=x)` dies with *"got multiple values for
argument 'source'"*. The module-level `_()` does not have that parameter and is
safe. `workflow.edge._compute_display_name` hit it, and only a constraint that
built its message from `display_name` surfaced it.

**Reading one stored field prefetches every stored field of the model.** Adding
any field read to `automation.rule._process` therefore seats the whole row in
the cache at that moment. `test_automation`'s `test_004_check_method_process`
asserted `automation.last_run` straight afterwards and read the prefetched
empty value, while the row in the database was correct throughout. Reproducible
with `self.trigger` as readily as with a new field, so it is not about which
field. The assertions now invalidate before reading.

## The run must settle, and a pause must not stop the world

Four defects found by an adversarial pass on 2026-08-29, all of which the suite
had been green through. Each is now pinned by `TestRunSettlement`.

**An `error` line is a settled line.** `action_mark_done`'s completion check
excluded only `done` and `cancel`, so a run whose failure was *handled* settled
every line and then sat in `in_progress` for ever. Including `error` is safe
because an *unhandled* failure has already set the runtime to `error` before the
check runs, and `action_done` refuses to move a runtime that is not
`in_progress` or `waiting_resume`.

**Only `action_run_all` decides that a run is waiting.** A pause used to call
`runtime.action_wait()` itself, which changed the state mid-loop and so broke
out of the execution loop — halting every *other* ready branch. The loop already
had the right rule (`no ready line, but something paused` → wait), so the pause
methods now do nothing but pause their own line.

**A finished run leaves nothing paused.** The stranded sweep runs inside
`action_error`, once the run has already failed, so it can settle `paused` lines
safely; excluding them left a failed run showing a step as *Paused* for ever.
Not a live leak — the resume cron filters on the runtime's state — but a lie in
the UI. (It used to run at the end of `action_run_all`, which a refused approval
never reaches.)

**Deleting an approval activity is not approval.**
`mail.activity._action_done` sets `active = False`; it does **not** unlink. So an
unlink is a separate act, and treating it as completion meant a user deleting
their to-do silently approved the step. It now fails the step, which an
`on_error` edge can handle.

The common shape: **three of the four were invisible because the tests asserted
on `line.state` and never on `runtime.state`**, and the fourth because every
pause test used a single pause.

## The canvas draws from a DOM patch, never from `load()`

`draw()` needs `useRef`'s element, and that element exists only after OWL has
patched the DOM. Calling it at the end of `load()` — which runs in
`onWillStart`, *before* the first render — left the paper `<div>` empty on every
real page load. A `useEffect` keyed on the status and a redraw token is what
drives it.

**This shipped, and nothing but a browser could see it.** The RPC succeeded, the
toolbar rendered `3 steps, 2 connections`, the HOOT suite passed, the views
rendered under `get_views`, and 362 Python tests were green — while the canvas
was blank for every user. Two things hid it: the draw ran off a microtask
(`await Promise.resolve()`), which resolves long before a patch; and a missing
element returned silently, so there was no error state and no log line. A
missing canvas element is now a reported error.

`test_automation`'s `test_workflow_canvas` tour is the guard. It is the only
test in the workspace that proves the vendored bundle resolves through the
import map in a browser, that the layout runs, and — with the assertion that
follows it in Python — that the coordinates reach the database.

## JointJS must never be given OWL's element

`dia.Paper` takes ownership of the element it is constructed with, and
`paper.remove()` **destroys that element**. Handing it the component's
`t-ref` div meant the first teardown deleted a node OWL still believed it
owned; from then on the ref was null and the canvas reported *the canvas
element was not mounted* for the rest of the session.

`draw()` therefore creates a plain `<div>` inside the ref, hands JointJS that,
and lets `paper.remove()` take it. The ref div is OWL's and stays OWL's.

**This would have broken the canvas the first time anything changed**, since a
reload follows every edge create, every edge removal and every bus
notification. It survived a full Python suite, a HOOT suite and a `get_views`
render check, and was found by the second browser tour.

Two smaller traps found with it, both in the *test* rather than the code:

* `.joint-type-standard-link` counts a labelled edge **twice** — JointJS repeats
  the group's class on its entry in the labels layer. Count the widget's own
  classes (`.o_workflow_canvas_link`, `.o_workflow_canvas_node`) instead.
* A tour trigger requires a **visible** element, and a horizontal edge's
  `<line>` has zero height, so it never qualifies. Trigger on the paper's host
  div and count inside `run()`, where visibility does not apply.

## The node body is a PASSIVE magnet, and connections come from a handle

A JointJS magnet on the body means dragging the body starts a link. Since the
body fills the node, a real pointer always lands on it — so with `magnet: true`
a user could **never move a step**, only connect it. Every drag became a
connection.

The body is therefore `magnet: "passive"` — it can be the *target* of a
connection but does not originate one — and each element view carries an
`elementTools.HoverConnect`, which is what a user drags from. Body drag moves;
handle drag connects.

Tools are attached with `paper.findViewByModel(cell).addTools(...)`. There is no
`paper.getViews()`; an earlier attempt used one behind `?.()`, which silently
attached nothing — no handles, no error, and connections simply could not be
made.

**Three tour traps, all in the test rather than the code**, recorded because
each cost a run to find:

* `drag_and_drop` always starts from `this.anchor`. The helper reads the trigger
  element and ignores any source given in options, so the trigger must be the
  thing being dragged.
* Hoot dispatches the drag on the element it is *given*. Triggering on the
  `<g>` produced a move even while the body was an active magnet, which
  disguised the usability bug above; triggering on the body reproduced it.
* A tour trigger needs a visible element. A horizontal edge's `<line>` has zero
  height and never qualifies — assert inside `run()` instead.
