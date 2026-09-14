# automation — Vision & Roadmap

## The Goal: n8n Inside Odoo

Transform `automation` into a best-in-class workflow engine with:

- **Visual DAG editor** (JointJS, vendored — see Decision 1)
- **Per-execution isolation** (every trigger creates an `automation.runtime`)
- **Typed nodes** (code, write, email, http, wait, branch, parallel, join,
  approval, subflow)
- **Conditional edges** (always / on_success / on_error / expression)
- **Full execution history** (what ran, when, on which record, what output)

The unique advantage over external workflow tools (n8n, Zapier, Temporal): nodes
operate directly on live Odoo business models with full ORM access, multi-company
context, and access control. An `approval` node that reads `partner_id.country_id`
fiscal rules and posts a `mail.activity` is trivial here.

---

## Design Decisions

All four decisions are locked. Decision 1 was reopened on 2026-08-26 — the
module it rested on had been deleted as unused on 2026-04-21, four months before
this document noticed — and closed again on 2026-08-29 on a different library.

### Decision 1: Visual Layer — LOCKED on JointJS, 2026-08-29

The library is **`@joint/core` 4.3.2** (MPL-2.0), bundled with
`@joint/layout-directed-graph` 4.3.0 for DAG auto-layout. It is vendored at
`addons/web/static/lib/joint/joint.esm.js` (508 KB), built by `addons/web/static/lib/joint/build.sh` with a pinned esbuild, declared as the bare specifier `joint` in
`web`'s manifest under `esm.external_libs`, and pinned in
`addons/web/static/lib/versions.json`.

It lives in `web`, not in this module, because `partner_relationship`
(`agromarin/`) needs the same canvas for a kinship network and CI checks `odoo`
out alone — a library in `addons/automation` could not serve it, and `web` is
the universal dependency that can. That module drives the same graph shape from
the other side: a finished server-side traversal with no renderer.

**Reach it only through a dynamic `import("joint")`.** The declaration costs
nothing on its own — an import-map entry is not a fetch — but a top-level import
in `web.assets_backend` would resolve on every backend page. The 2.9 MB
`web_flow` charged every session is the cautionary measurement, and
geoengine's geo_libs helper in the agromarin checkout is the pattern to copy.

**This decision was reopened on 2026-08-26** because the module it rested on —
`agromarin/web_flow`, a BPMN-js and Mermaid editor registering a `flow` view
type — had been deleted as unused on 2026-04-21 (`agromarin` `60b5a7eef`, task
21062) and nothing connected the deletion to this document, which went on
naming it for four months. **Read that removal before proposing BPMN again:**

>     flow_diagram table has 0 records in marin190
>     No module declares web_flow as a dependency (web_flow_demo,
>     its only consumer, was removed in T-21048)
>     Bundled 2.9MB of dead JS assets (bpmn-js + mermaid) served
>     on every session
>     The `flow` view type has no active consumers

That is this fork's own measured verdict on a BPMN canvas: nobody drew a diagram
with it, and it cost every session 2.9 MB to offer.

**Why JointJS, over the alternatives that were measured.** Every size below was
built with the pinned esbuild over the package's full public entry; the full
comparison is in
the 2026-08-29 diagram/flow view research note in the knowledge vault.

| Candidate | Licence | minified | Verdict |
|---|---|---:|---|
| `@joint/core` + layout | MPL-2.0 | **506 KB** | chosen |
| `cytoscape` + dagre + edgehandles | MIT | 497 KB | runner-up |
| `diagram-js` | MIT | 87 KB | editor toolbox only — no layouts, no graph analysis |
| `@antv/x6` | MIT | 589 KB | heaviest, needs `tslib`, no single-file build |
| `vis-network` | Apache-2.0 OR MIT | 653 KB | six *peer* dependencies |
| `elkjs` | EPL-2.0 OR GPL-3.0-or-later | 1426 KB | half of what `web_flow` was deleted for |
| `sequential-workflow-designer` | MIT | 96 KB | models series-parallel, not an arbitrary DAG |

Weight did not decide it: JointJS and cytoscape are within 25 KB of each other
and both sit under geoengine's vendored OpenLayers build (676 KB). Fit did.

* **The editor is the hard requirement.** This canvas must drag nodes, draw and
  *reconnect* edges, attach them at ports, badge each node with live
  `automation.runtime.line.state` and write coordinates back. JointJS ships all
  of it in core: `linkTools` (Vertices, Segments, Arrowhead, Anchor), `cellTools`
  (Connect, Button, Control, HoverConnect), `elementTools`, `highlighters`, the
  orthogonal/manhattan/rightAngle `routers`, and first-class ports
  (`src/layout/ports/`). Cytoscape has a canvas renderer, no ports and
  stylesheet-only node content; every one of those affordances works against its
  grain, and edge drawing is a third-party extension.
* **SVG in the DOM themes from Odoo's own SCSS.** A JointJS node is real DOM. A
  cytoscape node is pixels on a canvas, which would mean a second colour system
  that does not follow the theme.
* **Cytoscape's strength is capability this fork does not need.** Its 20 graph
  algorithms are its reason to exist, and `partner_relationship` already
  implements its traversal in Python — `_get_relation_degree_map`,
  `_get_relation_strength_map`, `_get_relation_path`, batched one query per
  degree, carrying `max_degree` policy and `weight_risk` semantics no generic
  shortest-path knows.
* **BPMN is the wrong notation and was already tried.** It models processes with
  pools, lanes and gateways; this engine is a plain DAG of server actions.
* **No React.** The fork is OWL and vendors no React, so a React SDK — including
  `synergycodes/workflowbuilder`, the proposal that prompted the 2026-08-26
  review — is rejected on runtime grounds: two component systems, two state
  systems and two theming systems on one page. The objection is *not* the build
  step; the fork bundles with esbuild 0.25 and would compile it fine. `rete` is
  rejected for the neighbouring reason: its core is framework-agnostic but every
  shipped renderer is a React/Vue/Angular/Svelte plugin.

**Two costs booked against JointJS, neither disqualifying.** It ships no
single-file ESM — its joint.mjs is a 97-byte re-export shim over the package's src/ tree and
its dist/joint.js is UMD — so it needs the ol-style build script, which it has.
And it does not tree-shake: `{dia, shapes, util}` alone is 431 KB of the 462 KB
full surface, which is why `addons/web/static/lib/joint/entry.js` re-exports everything
rather than curating a symbol list.

**MPL-2.0 is cleared against this tree's LGPL-3.** MPL §3.3 permits combining
Covered Software with LGPL-2.1+/GPL-2+/AGPL-3 work unless the code carries the
Exhibit B "Incompatible With Secondary Licenses" notice. No file in
`@joint/core@4.3.2` carries it — the only occurrences of the phrase are inside
the verbatim MPL text in `LICENSE`, where §1.5 and Exhibit B define it.

**This decision is not blocking, and settling it changed nothing about what
is.** Phase 2 (`workflow.edge`) and node coordinate storage gate the canvas, and
no library supplies either — see Phase 4.

### Decision 2: Async / Wait Nodes

The `wait` node type (pause execution, resume after delay) will be implemented
as a **temporal/polling system**: a separate cron job checks for paused
executions whose resume time has passed and re-enters the DAG.

**This temporal system is explicitly provisional.** It will be deprecated and
replaced when real async infrastructure ships at the framework level (see the
ongoing async work in other fork layers). Design the temporal system for easy
removal: isolate it in a single method `_resume_waiting_executions()` and a
dedicated cron job. No other code should depend on the polling behavior.

### Decision 3: Node Model

`ir.actions.server` is kept as the node model for now. This preserves
compatibility with Odoo's existing action system (buttons, server actions in
menus, etc.) and allows the DAG concept to be proven without a full model
extraction. The extension is in `models/ir_actions_server.py`.

When the engine matures, evaluate whether to extract to a dedicated
`workflow.node` model. Criteria: does the current coupling to `ir.actions.server`
cause real problems (naming confusion, unwanted field pollution, permission
model mismatch)?

### Decision 4: Document Before Code

Architectural changes to this module require updating this `machine_doc_v1/`
first. The doc is the design contract; the code implements it.

---

## Current State vs Target

| Concern | Current State | Target |
|---------|--------------|--------|
| Execution isolation | **done** — all state on `automation.runtime.line` | — |
| `automation.runtime` scope | **done** — `automation_id` carries no domain | — |
| `use_workflow_dag` flag | **done** — removed, every automation is DAG-capable | — |
| Trigger coverage | **done, opt-in** — `create_runtime_instance` routes any trigger through a runtime | — |
| Edge model | **done** — `workflow.edge`, typed | — |
| Node types | **done** — `action`, `wait`, `approval`, `subflow`; the rest were already sayable | — |
| Node coordinates | **done** — `pos_x` / `pos_y` on `ir.actions.server` | — |
| Visual layer | **done** — the Workflow page's canvas, JointJS | — |
| Execution history | `automation.runtime` per DAG run; `last_run` only for the rest | Full history per trigger |

---

## Phased Roadmap

### Phase 1 — Execution Model Foundation — DONE

Goal: make `automation.runtime` the canonical execution record for all triggers.

1. ~~Remove `use_workflow_dag` and `auto_execute_workflow` from `automation.rule`.~~
   **Done** — neither field exists; every automation is DAG-capable.
2. ~~Remove `action_state`, `is_ready`, `error_message` from `ir.actions.server`.~~
   **Done** — none is declared there, and `error_message` now lives on
   `automation.runtime.line` where it belongs. `factcheck.sh` asserts all three
   stay gone, so a reintroduction fails the gate rather than silently
   resurrecting the corruption this phase removed.
3. ~~Remove domain restriction on `automation.runtime.automation_id`.~~
   **Done** — the field declares no domain.
4. ~~Every trigger path can create a runtime.~~ **Done, opt-in.** This step's
   own description was wrong about the starting point, which is worth recording:
   `_process` did **not** create a runtime for an automation whose actions carry
   predecessors. It created none at all. Only `action_manual_trigger` built one,
   so every `on_create`, `on_write`, `on_time` and webhook run executed its
   actions directly, with no history — and, after Phase 2, with **no condition
   evaluation**, because `_sorted_by_dependency` reads the edges' direction and
   ignores their `condition`. Verified by probe before the change.

   `automation.rule.create_runtime_instance` (default **False**) now routes
   `_process` through `_run_through_runtimes`, the same helper
   `action_manual_trigger` uses. Off by default for the reason *What NOT to
   Build Here* gives: a high-volume trigger would write one runtime per event.
   On, a run is recorded **and** correctly routed.

   **A runtime records a failing step instead of raising, so the trigger it
   fired on is not aborted.** That is a real semantic difference from the direct
   path, which re-raises, and it is why this is opt-in rather than the default.

   The combination in which a condition would be silently ignored — a
   conditional edge on an automation that neither records its runs nor triggers
   manually — is refused by a constraint on both sides
   (`automation.rule._check_conditions_can_be_honoured` and
   `workflow.edge._check_condition_is_honoured`). Either side alone leaves a way
   to reach it.
5. Preserve backward-compat: simple automations with one action still work;
   the runtime record is created transparently.

Outcome: every automation execution is traceable when the automation asks to
be. The `action_state` corruption on concurrent runs was eliminated by 1–3.

### Phase 2 — Edge Model — DONE

Goal: conditional routing between nodes.

1. ~~Add `workflow.edge`.~~ **Done** — see models.md for the field list and the
   constraint set.
2. ~~Migrate the many2many data.~~ **Done** — `migrations/1.6/post-migrate.py`
   moves both relation tables and drops them. `post-` rather than `pre-`: the
   destination tables are created by the schema update, so nothing can be
   written into them earlier, and the source tables survive it because Odoo does
   not drop a relation table whose field has gone. Every migrated edge is
   `on_success`, which is what the untyped edge meant.
3. ~~Use edge conditions in DAG resolution.~~ **Done** — and one more change was
   needed than this step admitted: **the runtime aborted on the first failed
   step**, which made `on_error` unreachable, because the run was over before
   its target could be activated. `action_execute` now aborts only when nothing
   handles the failure (`_has_error_handler`), and `action_mark_error` activates
   successors just as `action_mark_done` does.
4. ~~Remove `predecessor_ids` / `successor_ids`.~~ **Done** — from
   `ir.actions.server` and from `automation.runtime.line`. `_get_predecessors()`
   / `_get_successors()` on both models are what callers use now.

Outcome: IF-node behaviour (branch on success/error/expression), and a failure
that a graph declares a handler for no longer kills the run.

**One naming question is left open.** The model is `workflow.edge` because this
document named it that, and Decision 4 makes the document the contract — but
every other model in the module is `automation.*` (`automation.rule`,
`automation.runtime`, `automation.runtime.line`, and the new
`automation.runtime.edge`). Decision 3 also envisages a `workflow.node`. Settle
`workflow.*` vs `automation.*` as one namespace question when `workflow.node` is
considered, not piecemeal; renaming one model twice costs two migrations.

### Phase 3 — Node Type System — DONE, four rows deleted and three built

**This table was written before Phase 2, and four of its seven rows turned out
to be things this fork could already do** — three by the edge model, one by a
server action state that predates the roadmap. None should be built: each would
be a second way to say something already sayable.

| Was proposed | Why it is gone |
|---|---|
| `http_request` — "call an external HTTP endpoint" | **Already a server action state.** `ir.actions.server.state = "webhook"` posts to `webhook_url`, and its own help already directs anything needing a credential, a retry or an audit trail to `integration`. A node type would be a second spelling of an action this module already runs. |
| `parallel` — "activate all outgoing edges (fan-out)" | Already the behaviour. A node with several outgoing edges fans out; `test_parallel_branches_both_ready` and `test_run_all_parallel_branches` pin it. |
| `join` — "wait until ALL incoming edges complete" | Already the behaviour. `_predecessors_satisfied` is an AND across the incoming edges; `test_diamond_join` pins it. |
| `branch` — "evaluate expression, activate the matching edge" | Already the behaviour. An `expression` edge is the branch, and unlike a branch *node* it needs no node to own the decision. |

What remains:

| Type | State |
|------|---------|
| `wait` | **Done.** `node_type="wait"` with `wait_delay` / `wait_unit`, the line state `paused` carrying `date_resume`, the runtime state `waiting_resume`, and `_resume_waiting_executions()` behind its own cron. |
| `approval` | **Done.** `approval_user_ids` raise one `mail.activity` each; the step pauses with **no** `date_resume`, because it waits on a person rather than a clock, so the resume cron never sees it. `mail.activity._action_done` and `unlink` call back into `_check_approval_complete`, which releases the step only when no active activity is left — every named approver must act. **Refusal routes through the edge model**: `action_refuse_approval` marks the step `error`, so an `on_error` edge is the rejection path and nothing new was needed for it. |
| `subflow` | **Done.** Creates a child `automation.runtime` on the same record, links it both ways (`parent_line_id`, and `created_record_ref`, which already selected `automation.runtime`), and pauses. The child completing releases the parent step; the child failing marks it `error`, so an `on_error` edge is the recovery path. A cycle — direct or through a chain — is refused. |

**A dependency constraint the roadmap did not record.** `odoo/addons/approval`
(Base Approval) **depends on `automation`**, so the node type here cannot use
`approval.request` — that direction is closed. The node built here is therefore
deliberately generic, on `mail.activity`, which `automation` already has
transitively. A richer node backed by `approval.request` is possible, but it
belongs **in the `approval` module**, extending this one.

`wait` was the right one to build first: it is the only one that is *purely*
mechanical, so it established the cross-transaction machinery without also
deciding anyone's semantics. `approval` then reused it whole — one node type,
two fields and a `mail.activity` back-link — and `subflow` likewise: one node
type, one many2one, one back-link. **No new state machine after `wait`.**

All three pause the same way and are released by different things: a clock, a
person, a child run. All three route failure through an `on_error` edge rather
than owning a failure path, which is Phase 2 paying for itself a third time.

**The pause is isolated, as Decision 2 requires.** One line state, one datetime,
one method (`_resume_waiting_executions`, now the first step of
`_dispatch_due_steps`) and one cron record. Nothing else
depends on the polling, so replacing it when real async infrastructure ships is
a deletion rather than an unpicking.

One thing the roadmap did not anticipate: `action_run_all` ends by settling
every line the run left unfinished, which existed to clean up after a failure
and marked a *paused* line `error` as well. A paused run is not a finished one;
both that sweep and the runtime-state guards now say so.

### Phase 4 — Visual Integration — DONE

Goal: `automation.rule` form view shows the workflow as an interactive DAG.

0. ~~**Add node coordinate storage.**~~ **Done** — `pos_x` / `pos_y` on
   `ir.actions.server`, copied with the action, and asserted by
   `TestWorkflowDAG`'s Canvas Layout block. An unplaced node reads `(0, 0)`;
   see models.md for why that is the auto-layout signal rather than a flag.
1. ~~Settle Decision 1, then vendor the chosen library.~~ **Done** —
   `@joint/core` is vendored at `addons/web/static/lib/joint/joint.esm.js` and
   declared as the specifier `joint`. Reach it through a dynamic `import()`,
   never a top-level one.
2. ~~Replace the `action_server_ids` kanban with an OWL component.~~ **Done,
   but added beside the kanban rather than replacing it.** The canvas is a
   `view_widgets` entry, `automation_workflow_canvas`, on a new **Workflow**
   page. Replacing the Actions tab was tried once before and reverted, because
   it changed the tab for every automation and swapped out the widget the tours
   drive; that reasoning is recorded here rather than in the view, where a
   comment-stripping pass removed it.
3. ~~Saving a diagram creates nodes and edges via RPC, with the server still
   enforcing.~~ **Done, and there is no write-side API.** The canvas reads
   through one method, `automation.rule.get_workflow_graph`, and *writes*
   through the plain ORM — `ir.actions.server` for coordinates, `workflow.edge`
   for the graph. So `_check_no_cycle`, `_check_same_automation` and the
   uniqueness constraint judge a dragged connection exactly as they judge a
   typed one, with no second code path to keep in step. A refusal is reported
   and the canvas reloaded, never patched up client-side.
4. ~~Execution monitoring, live.~~ **Done, over the bus.**
   `get_workflow_graph(runtime_id=...)` returns each node's
   `automation.runtime.line.state` and the canvas paints it
   (`o_workflow_canvas_run_<state>`); a run announces every settling on its
   rule's channel, and an open canvas reloads. No polling.

   **Both identifiers come from the client, so both are checked.** The
   `runtime_id` is matched against this automation before its states are
   returned. The channel is a *string* — `automation.workflow/<rule id>` — because
   `ir.websocket` accepts only strings from a client; `_build_bus_channel_list`
   translates it into the record channel `(rule, "WORKFLOW")` **only for a rule
   the user may read**, and drops it otherwise. That is the shape `im_livechat`
   uses for `looking_for_help`, and it matters here because `automation.rule` is
   readable by `base.group_system` alone: without the check, any logged-in user
   could name the channel and watch an administrator's workflows advance.

---

## What NOT to Build Here

- **Per-record state machines**: Odoo's native computed fields + `state` Selection
  field pattern handles this better (sale.order, account.move, etc.). The workflow
  engine handles *cross-model, multi-step, human-in-the-loop* orchestration that
  no single model owns.

- **Replacing `ir.cron`**: cron stays for scheduled jobs. The workflow engine
  uses cron as a trigger and as the resume mechanism for `wait` nodes, but does
  not replace it.

- **High-frequency event streaming**: automations on high-volume write triggers
  (e.g., stock.move) that create a runtime record per event will generate huge
  history tables. Provide a `create_runtime_instance` boolean on `automation.rule`
  to let lightweight automations opt out of history tracking.
