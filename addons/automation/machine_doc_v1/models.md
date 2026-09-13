# automation — Models

## automation.rule (Rule Definition)

The workflow *definition*. Owns the trigger configuration, filter conditions,
and the set of `ir.actions.server` nodes that form the DAG.

### Key Fields

| Field | Type | Purpose |
|-------|------|---------|
| `trigger` | Selection (18 values) | When this workflow fires |
| `model_id` | Many2one `ir.model` | Target model (required) |
| `filter_pre_domain` | Char | Pre-condition: record state *before* write |
| `filter_domain` | Char | Post-condition: record state *after* event |
| `action_server_ids` | One2many `ir.actions.server` | DAG nodes |
| `trigger_field_ids` | Many2many `ir.model.fields` | Write-trigger field watch list |
| `on_change_field_ids` | Many2many `ir.model.fields` | Onchange field watch list |
| `trg_date_id` | Many2one `ir.model.fields` | Date field for time triggers |
| `trg_date_range` | Integer | Delay amount (always positive) |
| `trg_date_range_type` | Selection | minute / hour / day / month, the shared `time_unit_selection` units |
| `trg_date_range_mode` | Selection | before / after the trigger date |
| `trg_date_calendar_id` | Many2one `resource.calendar` | Working-day calendar |
| `last_run` | Datetime | Last successful cron execution |
| ~~`use_workflow_dag`~~ | ~~Boolean~~ | **REMOVED in Phase 1** — all automations are DAG-capable |
| ~~`auto_execute_workflow`~~ | ~~Boolean~~ | **REMOVED in Phase 1** — execution is always auto-advancing |

### Trigger Categories

```
CREATE triggers:   on_create, on_create_or_write, on_priority_set,
                   on_stage_set, on_state_set, on_tag_set, on_user_set

WRITE triggers:    on_write, on_archive, on_unarchive, on_create_or_write,
                   on_priority_set, on_stage_set, on_state_set, on_tag_set,
                   on_user_set

TIME triggers:     on_time, on_time_created, on_time_updated

MAIL triggers:     on_message_received, on_message_sent

UNLINK trigger:    on_unlink

MANUAL trigger:    on_hand
ONCHANGE trigger:  on_change  (UI-only, form view onchange)
```

Every one of the 18 values appears above; `factcheck.sh` asserts that both ways,
so a value added to the Selection without a line here fails the gate.

### Constants (module-level)

| Constant | Value | Meaning |
|----------|-------|---------|
| `CRON_INTERVAL_TOLERANCE_PERCENT` | 0.10 | 10% of min delay → cron frequency |
| `DEFAULT_CRON_INTERVAL_MINUTES` | 240 | 4 hours, when no time automations |
| `MIN_CRON_INTERVAL_MINUTES` | 1 | Floor |
| `MAX_CRON_INTERVAL_MINUTES` | 240 | Ceiling |
| `MONTH_APPROXIMATION_DAYS` | 30 | Used for `timedelta` month conversion |
| `RUNTIME_HISTORY_LIMIT` | 10 | Recent runs the canvas offers in its run selector |

`models/_canvas.py` holds the geometry contract the canvas persists, read by
both `ir.actions.server` and `automation.canvas.viewport`:

| Constant | Value | Meaning |
|----------|-------|---------|
| `NODE_SIZE_DEFAULT` | 200 x 140 | A step nobody has resized |
| `NODE_SIZE_MIN` | 160 x 72 | Floor a stored rect is checked against |
| `NODE_SIZE_MAX` | 480 x 320 | Ceiling a stored rect is checked against |
| `NODE_HEADER_HEIGHT` | 34 | Where a step's body, and so its ports, start |
| `SCALE_MIN` / `SCALE_MAX` | 0.2 / 2.0 | Zoom the editor can draw, mirrored server-side |

---

## ir.actions.server (extended as DAG Node)

Extended by `models/ir_actions_server.py`. Serves as both the standard Odoo
server action model AND the workflow node definition.

### Added Fields

| Field | Type | Purpose |
|-------|------|---------|
| `automation_rule_id` | Many2one `automation.rule` | Owning rule |
| `usage` | Selection (extended) | Added `"automation"` value |
| `edge_in_ids` | One2many `workflow.edge` | Edges that must be satisfied before this node runs |
| `edge_out_ids` | One2many `workflow.edge` | Edges this node's outcome can satisfy |
| ~~`predecessor_ids`~~ | ~~Many2many self~~ | **REMOVED in Phase 2** — replaced by `workflow.edge` |
| ~~`successor_ids`~~ | ~~Many2many self~~ | **REMOVED in Phase 2** — replaced by `workflow.edge` |
| `node_type` | Selection | `action` (default), `wait`, `approval` or `subflow`. No `parallel`/`join`/`branch` — the edge model is already all three — and no `http_request`, because `state="webhook"` already is one. See vision.md Phase 3 |
| `approval_user_ids` / `approval_note` | Many2many `res.users` / Char | Who must approve, and what the activity asks |
| `subflow_automation_id` | Many2one `automation.rule` | What a Sub-workflow step runs; a cycle is refused |
| `wait_delay` / `wait_unit` | Integer / Selection | How long a `wait` node pauses the run; a non-positive delay is refused |
| `start_delay` / `start_delay_unit` | Integer / Selection | For a step with no incoming edge only: how long after its line was created (the run's start, or the sync that added it) it becomes ready; the line is `scheduled` until then |
| `validity_delay` / `validity_unit` | Integer / Selection | How long after its line became ready (`date_ready`) the step may still run; a line reached later is skipped with the reason in `error_message`. Zero never expires; a negative value is refused |
| `pos_x` | Integer | Node's horizontal position on the workflow canvas |
| `pos_y` | Integer | Node's vertical position on the workflow canvas |
| `pos_width` / `pos_height` | Integer | Node's rect on the canvas; 0 means the default, and any other value is checked against `NODE_SIZE_MIN` / `NODE_SIZE_MAX` |
| ~~`action_state`~~ | ~~Selection~~ | **REMOVED in Phase 1** — was broken (global state, not per-execution) |
| ~~`is_ready`~~ | ~~Boolean~~ | **REMOVED in Phase 1** — use `automation.runtime.line.is_ready` |
| ~~`error_message`~~ | ~~Text~~ | **REMOVED in Phase 1** — use `automation.runtime.line.error_message` |

### What an edge draws

The condition is the port an edge leaves from, so it is not written on the edge
as well. What IS written there is `workflow.edge.label`, the reader's own
annotation, and for an `expression` edge the `condition_expr` it evaluates when
no label overrides it. A plain `on_success`, `on_error` or `always` edge carries
no text, because its port already names it.

This needed a capability the ported editor did not have. `FlowConnection` drew
two paths and nothing else, so between the port and this change `label` was drawn
nowhere while its help string said it was shown, and an `expression` edge offered
a port reading "if" with the expression visible nowhere at all. `FlowEditor` now
takes a `getConnectionLabel` prop, symmetric with `getConnectionClass`, and draws
the result at the midpoint `getConnectionGeometry` already computes.

### What a typed step draws

`get_workflow_graph` ships the parameter that gives each `node_type` its meaning:
`wait_delay` and `wait_unit` for a Wait, `approver_names` for an Approval, and
`subflow_name` for a Sub-workflow. The canvas renders one line from whichever
applies, so a reader sees "36 hours", the approvers by name, or the automation a
Sub-workflow runs, rather than the bare type word. A plain Action draws the `detail`
its application gives it through `ir.actions.server._workflow_step_detail()`
(empty by default; a marketing activity answers "Email: <mailing>"). The type word alone was what the canvas showed before, which told a reader
that a step waits without telling them how long.

An application also names its events. `automation.rule._workflow_event_labels()`
maps `(condition, event_code)` to a label, empty by default, and the payload sends
each edge's `event_label`. The canvas then draws "Mail: opened, then 1 hours" or
"Mail: not opened within 2 days" instead of the raw code, in the words the
campaign's own activity tree uses, which is how decision D12 keeps the campaign
kanban and this canvas speaking one vocabulary over one graph.

### Removal from the canvas

`get_workflow_graph` gives every step a `deletable` flag, and the canvas offers
its remove button only where the flag is true. The flag is a server fact rather
than a client rule: `automation.runtime.line.action_id` is `ondelete="restrict"`,
so a step any recorded run reached cannot be unlinked at all, and nothing on the
step itself records that a run once reached it. `_recorded_step_ids` answers for
every step of one automation in a single grouped read.

That read is under `sudo`, and it has to be. `automation.runtime.line` carries a
global multi-company rule, so an ordinary read returns no line for a run of a
company the reader is not in — the flag then reads true, the canvas offers the
button, and the constraint refuses the unlink, which is the one outcome the flag
exists to prevent. The question is what Postgres will allow, not what this reader
may see, so the answer must not vary with who asks.

Removing a step removes the edges that touch it, through the cascade on
`workflow.edge`'s `source_node_id` and `target_node_id`. The editor then retires
each of those connections through the canvas's disconnect callback, which reports
an edge its own bookkeeping has already lost as removed rather than unlinking an
id the database has dropped.

### Execution State — Phase 1 Complete

All execution state has been moved from `ir.actions.server` (definition) to
`automation.runtime.line` (per-execution instance). `ir.actions.server` now
stores **only definition data**: the DAG topology (`edge_in_ids`,
`edge_out_ids`, both onto `workflow.edge`) and the canvas layout
(`pos_x`, `pos_y`). Concurrent executions
are isolated: each `automation.runtime` instance has its own
`automation.runtime.line` records with independent state.

`pos_x` / `pos_y` are Integer, so an unplaced node reads as `(0, 0)` — the
column returns 0 for NULL and cannot say "unset". A laid-out graph never leaves
*every* node at the origin, so "all nodes at (0, 0)" is the canvas's signal to
auto-layout; one node there among placed siblings is a real position. They carry
the default `copy=True`, unlike the edges, so a duplicated automation opens on
the layout its source had.

---

## workflow.edge (Phase 2 — Complete)

One typed, directed edge between two nodes of one automation's DAG. Replaces the
self-referential Many2many that carried the topology before: a many2many row is
two integers and has nowhere to put a condition, so every edge meant the same
thing.

| Field | Type | Purpose |
|-------|------|---------|
| `source_node_id` | Many2one `ir.actions.server` | Where the edge starts |
| `target_node_id` | Many2one `ir.actions.server` | What it releases |
| `automation_rule_id` | Many2one, **related-stored** from the source | Scope, and the inverse of `automation.rule.edge_ids` |
| `condition` | Selection | `on_success` (default) / `on_error` / `always` / `expression` |
| `condition_expr` | Char | Python expression, required when `condition` is `expression` |
| `label` | Char | Shown on the edge when the workflow is drawn |

**Constraints.** `UNIQUE(source_node_id, target_node_id)` in SQL; the rest in
Python, so they raise `ValidationError` rather than a raw database error:
both ends in the same automation, no cycle, no self-edge, and no `expression`
edge without an expression. The self-edge check is deliberately **not** a SQL
`CHECK` — that fires from inside the INSERT, before any `@api.constrains` runs,
so the caller would see a `CheckViolation` where every other malformed edge
raises `ValidationError`.

---

## automation.runtime.edge (Phase 2 — Complete)

The same edge, snapshotted for one run: `runtime_id`, `source_line_id`,
`target_line_id`, `condition`, `condition_expr`. The condition is copied at
`action_start` for the same reason the topology is — editing the automation
while a run is in flight must not change how that run routes.

`_is_satisfied()` is the whole routing rule:

| `condition` | Satisfied when the source line is |
|---|---|
| `on_success` | `done` |
| `on_error` | `error` |
| `always` | settled, however it settled |
| `expression` | settled **and** `condition_expr` is truthy |
| `event` | settled **and** has received `event_code` |
| `no_event` | settled **and** has not received `event_code` within `delay` (a zero window fires as the source settles, unless the event already arrived) |

An **unsettled** source satisfies nothing, whatever the condition: the answer is
not yet knowable, and treating "not yet" as "no" would race the target into
`ready` before its predecessor ran. A raising expression blocks its edge and is
logged rather than propagated — letting it out would abort the run from inside
the readiness check, where no line owns the failure and nothing records it.

### Timing and events

Every edge also carries `delay` + `delay_unit` (the shared time units), copied onto
the runtime edge with `event_code`. `automation.runtime.edge._verdict(now)` answers
for one edge: *false*, *pending* (an `event` edge whose event has not arrived),
*true*, or *true from a due time*. The due time is `delay` after the anchor: the
source's `date_settled`, or the edge's `date_event` for an `event` edge. A
`no_event` edge is the race partner. It is due `delay` after the source settled,
and turns false the moment the event arrives, so its target is skipped by the
dead-path rule below.

`automation.runtime.line._receive_event(code, exclusive=False)` stamps
`date_event` on the line's matching outgoing edges and re-settles their targets.
`exclusive` revokes every other outgoing edge of the line, which is how a bounce
closes a campaign's follow-ups. Events are generic: nothing in `automation` emits
one. An application such as `marketing_automation` calls it from its own event
sources.

A waiting line with a target in the future becomes **`scheduled`**, carrying
`date_resume` and a trigger on the resume cron, which re-settles it once due. A
run whose only outstanding lines wait for events stays `waiting_resume`: it is
waiting, not blocked, the way a marketing participant stays running.

Readiness is **AND across the live incoming edges**: a step with two
predecessors waits for both. `automation.runtime.line._settle_readiness()` decides
a waiting line once every source has settled:

- an edge whose source is **`skipped`** is *dead* and ignored;
- no live edge, or any live edge *false* → **`skipped`**, and the skip propagates
  to the line's successors;
- any live edge *pending* → stays `waiting`;
- any live edge due in the future → `scheduled` until the latest due time;
- otherwise → `ready`.

This is the WS-BPEL dead-path rule. It is what lets an if/else rejoin (the
untaken branch's edge is dead, so the join runs), and what stops a branch that
was never taken from failing the run. Before it, the untaken step sat `waiting`,
`action_run_all` found it blocked, and marked it and the run `error`: every
exclusive choice failed its run. A failure only propagates when it is
*handled*. `action_mark_error` activates successors only for a line with an
`on_error` or `always` edge, so an unhandled failure still fails the run and
its successors are settled `error` by `action_error`, not `skipped`.

---

## automation.runtime (Execution Instance)

A single *run* of a workflow. Stores isolated execution context and drives
step-by-step progress through the DAG.

### Phase 1 Changes (Complete)

The `automation_id` domain restriction has been **removed**. Any automation
(regardless of target model) can now have `automation.runtime` instances.

Two new fields support general-purpose automations:
- `res_model` (Char) — the model of the record being automated (e.g. `res.partner`)
- `res_id` (Integer) — the specific record ID

`partner_id` is now optional. `action_run_all()` executes all ready branches
in a loop until the runtime completes — enabling fully automatic DAG traversal
from a single call in `action_manual_trigger()`.

### Key Fields

| Field | Type | Purpose |
|-------|------|---------|
| `automation_id` | Many2one `automation.rule` | The rule being executed |
| `partner_id` | Many2one `res.partner` | Primary partner context |
| `diff_partner_id` | Many2one `res.partner` | Secondary partner context |
| `company_id` | Many2one `res.company` | Company isolation |
| `multicompany_id` | Many2one `res.company` | Target company for cross-company ops |
| `currency_id` | Many2one `res.currency` | Monetary context |
| `amount` | Monetary | Operation amount |
| `reference` | Char | External reference |
| `date` | Date | Reference date |
| `state` | Selection | draft / in_progress / waiting_resume / done / error / cancel |
| `line_ids` | One2many `automation.runtime.line` | Execution steps |
| `progress` | Integer (computed) | 0–100% completion |
| `progress_display` | Char (computed) | "3/5 steps" |

### State Machine

```
draft → in_progress ⇄ waiting_resume
            ↓   ↓            ↓
         error  done       cancel
```

`action_start()`: creates `automation.runtime.line` records from the
automation's `action_server_ids`, sets first-in-sequence to `ready`.

`action_next_step()`: executes next `ready` line, auto-marks `done` if all
lines complete.

`action_run_all()`: runs ready lines until the run settles. With no line ready it
asks `_finish_if_settled()` first, then waits if something is paused, and only
then treats outstanding lines as blocked and fails the run.

`_finish_if_settled()`: the one completion rule — a run in `in_progress` or
`waiting_resume` whose every line is in `SETTLED_STATES` (`done`, `error`,
`cancel`, `skipped`) is done. Resume, approval and subflow release all end in
`action_run_all`, so a run ending on a pause finishes; before it, such a run
stayed `in_progress` for ever.

`action_error()`: terminal failure state, set when a step raises or when the run
can no longer advance. It settles every unsettled line `error` ("Step never
ran"), so a failure reached outside `action_run_all` — a refused approval with
no handler — leaves no line `waiting` inside a failed run.

---

## automation.runtime.line (Execution Step)

One node's execution state within an `automation.runtime` instance.
Fully isolated per-execution — no shared state with the definition.

### Key Fields

| Field | Type | Purpose |
|-------|------|---------|
| `runtime_id` | Many2one `automation.runtime` | Parent execution |
| `action_id` | Many2one `ir.actions.server` | Node being executed |
| `name` | Char | Copied from action at creation |
| `sequence` | Integer | Execution order |
| `state` | Selection | waiting/scheduled/ready/paused/in_progress/done/skipped/cancel/error |
| `error_message` | Text | Error details |
| `date_resume` | Datetime | When a scheduled step or a paused Wait step is due |
| `date_ready` | Datetime | When the step became ready; its node's validity counts from here |
| `skip_reason` | Selection | Why a `skipped` line was skipped: `branch` (dead path or false edge), `revoked` (an exclusive event), `expired` (validity), `filtered` and `cancelled` (set by a caller through `_skip(reason=, message=)`) |
| `date_settled` | Datetime | When the step settled; delays on its outgoing edges count from here |
| `edge_in_ids` / `edge_out_ids` | One2many `automation.runtime.edge` | DAG dependency at execution level |

| `created_record_ref` | Reference | Record created by this step |

### DAG Resolution

`action_mark_done()`: marks self done, lets each waiting successor settle its
readiness (`_settle_readiness()`, above), then asks the run to finish.
This is the correct per-instance DAG propagation pattern. (An earlier
`ir.actions.server.action_mark_done()` that mutated the global definition
was removed in Phase 1 along with `action_state`/`is_ready`/`error_message` —
see the "What NOT to Add" section in `conventions.md`; this doc previously
still referenced it.)

---

## automation.canvas.viewport (Per-Reader Canvas State)

Defined by `models/automation_canvas_viewport.py`. Where one reader last left
the workflow canvas of one automation: personal, so two people looking at the
same automation pan and zoom independently, and scoped to its owner by a global
record rule rather than left readable by anyone who may configure automations.

### Key Fields

| Field | Type | Purpose |
|-------|------|---------|
| `user_id` | Many2one `res.users` | The reader the viewport belongs to |
| `automation_rule_id` | Many2one `automation.rule` | The automation it frames |
| `pos_x` / `pos_y` | Float | Canvas translation, in screen pixels |
| `scale` | Float | Zoom, checked against `SCALE_MIN` / `SCALE_MAX` |

`_viewport_uniq` keeps one row per reader per automation, and `_update_viewport`
recovers from the race two of a reader's own tabs create through
`odoo.db.get_or_create_row` rather than a hand-rolled savepoint. The canvas
reads it from `get_workflow_graph`'s payload and writes it back through
`automation.rule.set_workflow_viewport`, debounced, so a pan costs one row and
not one row per frame.

---

## flow.diagram — does not exist

Earlier revisions of this file documented a `flow.diagram` model in
agromarin/web_flow/models/flow_diagram.py (plain prose: another repo, and a
deleted file), storing BPMN 2.0 XML and an
`element_mappings` JSON blob, as the visual layout layer for `automation.rule`.

**Both were deleted on 2026-04-21** (`agromarin` `60b5a7eef`), and the removal
commit records that `flow_diagram` held **0 records in production** — the fields
tabulated here were queryable and never queried. `vision.md` Decision 1 carries
the full rationale and the replacement constraints; the layout layer is undecided
along with the editor, and storing node coordinates is an open design question
rather than a solved one.


---

## The pause, and why it is shaped this way (Phase 3)

A `wait` node does not run its server action. `automation.runtime.line.action_execute`
diverts to `action_pause`, which sets the line to **`paused`** with a
`date_resume`, and the runtime to **`waiting_resume`**.

`automation.runtime._resume_waiting_executions()` — one `@api.model` method
behind one cron record — finds runs whose paused line is due, returns the
runtime to `in_progress`, marks the line `done` and re-enters `action_run_all`.
Marking it `done` rather than inventing a "resumed" state is what lets the
existing edge conditions release the successors unchanged: an `on_success` edge
out of a wait means "after the wait".

`action_pause` also calls the resume cron's `_trigger(at=date_resume)`, so a
wait wakes at its due time rather than at the next poll; the cron itself is an
hourly backstop. It shipped `active=False` and nothing ever enabled it, so
outside tests — which call `_resume_waiting_executions()` by hand — no wait ever
resumed. It now ships active, and migration `1.9` enables it on existing
databases and triggers it once.

**Decision 2 requires this to be easy to delete.** It is one line state, one
datetime, one method and one cron record; nothing else consults the polling.

**One trap it exposed.** A sweep settles every unfinished line `error` to clean
up whatever a *failure* stranded. A paused line is unfinished but not stranded,
so the sweep must never run on a live run. It first sat at the end of
`action_run_all`, guarded against `in_progress` and `waiting_resume`; without
that guard a wait node's own line was marked failed the moment it paused, which
is what the first run of `TestWaitNode` reported. It now lives in
`action_error`, which only a failed run reaches.

## Queued runs and the dispatcher

`automation.rule.run_mode` is `immediate` (the default: a run executes as soon as
it starts, and whenever a step becomes ready) or `queued`. A queued run does
nothing inline. `automation.runtime._launch()` starts it and triggers the cron,
and `_advance()`, which every resume, approval, subflow and event path now goes
through, only re-triggers the cron. The cron record the resume cron used to be
now runs `_dispatch_due_steps()` (migration `1.10` rewrites its code and name):

1. `_resume_waiting_executions()` promotes due `scheduled` and `paused` lines, as
   before;
2. it takes up to `DISPATCH_BATCH_SIZE` ready lines of queued runs and groups
   them by node;
3. it hands each group to `ir.actions.server._execute_runtime_lines(lines)`. The
   default executes each line through `action_execute` and its savepoint; a node
   type may override it to act on the whole batch at once, as a mailing does;
4. it settles the runs left idle, commits progress through
   `ir.cron._commit_progress` when it runs under a cron (never in a test), and
   loops until no ready line is left that it has not already handed out.

Immediate runs are never dispatched: a run that a person steps through with
`action_next_step` keeps its ready lines until they click. Neither are the queued runs of an
archived rule: both `_resume_waiting_executions` and the dispatcher filter on
`automation_id.active`, so archiving a rule pauses its runs where they stand and
unarchiving resumes them.

`_dispatch_due_steps(rules=None)` and `_resume_waiting_executions(rules=None)`
take an optional recordset of rules, so an application can dispatch its own rules
now (a campaign's "execute" button) without touching anyone else's queue. Rules
named that way are dispatched even when archived: asking for a rule by name is
the explicit request the archive otherwise withholds.

### What a failed step does

`automation.rule.step_error_policy` decides what an *unhandled* failure does.
`fail_run`, the default and the behaviour until now, stops the run and settles
its unfinished steps `error`. `close_branch` treats the failure as handled:
`automation.runtime.line._contains_its_error()` is true, so the failed step's
successors are settled by their edges (an `on_success` successor is skipped) and
the run's other branches carry on. Every path that used to ask
`_has_error_handler()` before failing a run now asks `_contains_its_error()`:
step execution, `action_mark_error`, a refused or deleted approval, and a failed
subflow. A campaign uses `close_branch`, so one bounced SMS does not cancel a
participant's other branches.

The dispatcher re-filters each node's group to lines still `ready` before
handing it over, because a failure earlier in the same page can already have
settled a run's other ready lines.

### Editing a workflow under running runs

A run snapshots its lines and edges at start (decision D11 keeps that eager).
`automation.runtime._sync_to_definition()` brings runs still in progress or
waiting up to date with an edited definition, without rewriting history:

- a node the run has no line for gets one, with its edges (`_materialize`, which
  `_create_action_lines` also uses);
- a runtime edge whose target is still `waiting` or `scheduled` takes the
  definition's condition, event and delay again (`workflow.edge._runtime_copy_vals`);
  an edge into a step already ready, running or settled keeps what it ran under;
- every waiting or scheduled line is re-settled, so a longer delay reschedules it
  and a new branch whose source already settled runs;
- a finished run is left alone.

`_add_steps(actions)` is the narrower form: it gives running runs lines for those
nodes only, and settles them. A campaign uses it when a child activity is added,
so participants already underway reach it, while a new *root* waits for the
explicit sync, as marketing's "Update" always required.

### Queued runs are built and settled in batches

A queued rule is the high-volume path, so its runs do not behave like a person's
run in the chatter or in the query log:

- `_launch()` builds every draft run of a rule at once. `_materialize` takes a
  recordset of runs and creates all their lines and edges in one create each.
- queued runs draw no `ir.sequence` number (their name is the rule's), post no
  chatter messages (`_log_run_message`), and are launched and dispatched with
  `tracking_disable`.
- readiness is decided for a recordset: `_settle_readiness` fetches the edges and
  their sources once, asks `_readiness_decision` per line, and writes each outcome
  (skip, wait, schedule at a due time, ready) as one write per group. Successor
  activation, `_finish_if_settled`, `action_mark_done`, `action_resume` and
  `_sync_to_definition` all take recordsets too. This fork's ORM neither batches
  x2many reads across a loop nor defers the flush of dependent stored fields
  past a write, so looping one line at a time turned every step into several
  statements.
- cron triggers are deduplicated per transaction: `_request_dispatch` once, and
  `_trigger_resume_at` once per due time.

A line that becomes ready from a due time already past keeps that due time in
`date_resume`, so "when was this step due" survives until it runs.
