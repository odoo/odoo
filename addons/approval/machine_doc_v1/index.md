# Approval Module -- Machine Documentation v1

## Purpose

Multi-level approval workflow engine: categories routed by steps (pools of approvers,
in order or not, applying by conditions on the request or its document), delegation,
consent-based auto-approval, SLA tracking, smart escalation with priority-based
reminders, approver-requested mid-flow changes, cancel / reset-to-draft recovery,
approval mixin for source document integration, and comprehensive analytics
dashboards.

## Module Metadata

| Key | Value |
|-----|-------|
| Technical name | `approval` |
| Version | 19.0.2.10.2 (matches `__manifest__.py`) |
| Category | Human Resources/Approvals |
| Dependencies | `mail`, and nothing else. `approval_automation` (which needs `automation`) and `approval_analytics` (which needs `mixin_report_sql`) were split out at 19.0.2.0.0 so that adopting `mixin.approval` costs one manifest row rather than nineteen prerequisites; both auto-install |
| Conflicts | `approvals` (upstream module — the two cannot coexist, and NOTHING enforces it: this fork's loader reads no `excludes` manifest key, so the one that used to sit here was inert) |
| Application | No: the Approvals application (menu root, generic request categories, demo) is `approval_app`, so the modules adopting `mixin.approval` pull in no application tile. Configuration without it: Settings > Technical > Approvals |
| License | LGPL-3 |
| Python models | 12 own + 5 extensions, across 35 files in `models/` (plus `__init__.py`), + 2 wizards + 3 report models. One of the 35 declares no model: `approval_trace.py`, the campaign instrumentation (conventions.md, "Campaign Instrumentation") |
| Views | 15 XML files (9 `views/` + 4 `reports/` + 2 `wizards/`) |
| Wizards | 2 transient models |
| Reports | 4 (2 SQL views + 1 singleton dashboard + 1 QWeb PDF) |
| Cron jobs | 4 (escalation, auto-expire, consent, delegated activity hand-over) |
| Test files | 47 (+ `common.py` shared fixtures); the reporting and reset suites went to the two split modules |
| JS files | 25 (14 `static/src` + 11 `static/tests`, the tours and the mock-server models included) |
| Migrations | 19 script directories between 1.0.1 and 1.0.26, named by the bare module version. The missing numbers (.9, .15, .16, .18, .19, .20, .25) **were** released — the manifest bumped through them; they simply needed no script |

## File Inventory

### Models (`models/`)

| File | Models | Purpose |
|------|--------|---------|
| `approval_category.py` | `approval.category` | Category blueprint: field visibility, privacy visibility, approval minimums, escalation, SLA, consent, dashboard |
| `approval_request.py` | `approval.request` | Core request: fields, CRUD, smart-copy defaults, `ESCALATION_RULES` constant |
| `approval_request_access.py` | extends `approval.request` | Who may write, unlink, decide or re-route: the `_check_access_*` and locked-field rules |
| `approval_request_lifecycle.py` | extends `approval.request` | The transitions: confirm, approve/refuse (`_apply_decision` funnel), withdraw, cancel, reset, change requests, `_force_terminal`, activities and row locking |
| `approval_request_routing.py` | extends `approval.request` | Who approves: `_sync_approvers`, `_get_desired_approvers` over the applicable steps, live rerouting, auto-action rules, category snapshot |
| `approval_request_escalation.py` | extends `approval.request` | When: deadline, overdue, SLA (compute + search), the three crons, reminders and escalation |
| `approval_request_prediction.py` | extends `approval.request` | On-demand outcome prediction (`action_predict_outcome`) |
| `approval_approver.py` | `approval.approver` | Individual approver: state, delegation, CRUD access control |
| `approval_decision_log.py` | `approval.decision.log`, extends `approval.request` | The append-only decision ledger: one `verdict` per fact (approved, refused, withdrawn, granted, revoked, cancelled, reset) with the acting user, the `principal_id` a delegate acted for, the caller's elevation and the `state_after`. Written by every funnel through `_append_decision_log`; `write` and `unlink` refuse always. Read through `approval.request.decision_log_ids` |
| `mixin_approval_source.py` | `mixin.approval.source` (Abstract) | What every record an approval request is raised for may answer: `_filter_approval_step_user_ids()` (who its own policy lets decide) and `_get_approval_activity_type()` (which activity asks them). Parent of both adopter shapes |
| `mixin_approval.py` | `mixin.approval` (Abstract) | Mixin for source documents (PO, SO, etc.) to integrate with approvals: one request per document, `approval_request_id` |
| `mixin_approval_gate.py` | `mixin.approval.gate` (Abstract) | A document that gates its own terminal transitions: `_run_through_approval(operation, run)` splits the records, runs what needs no approval, raises a request for the rest, and re-runs the operation once when the grant arrives. `_check_approval_admits` holds the gate at the operation's checkpoint, watching before it enforces |
| `mixin_approval_lifecycle.py` | `mixin.approval.lifecycle` (Abstract) | A `mixin.lifecycle` document whose confirmation waits for approval when a category applies: `action_confirm` confirms what needs none or holds a grant, raises a request for what does, and refuses while one is waiting or while a refused one is still needed. The grant confirms a draft; cancelling refuses a waiting request; a reset clears a refused link |
| `mixin_approval_access.py` | `mixin.approval.access` (Abstract) | A record whose access a partner asks for: the subject is the partner and role, and the adopter says whether the access is held and writes the grant on approval |
| `mixin_approval_subjects.py` | `mixin.approval.subjects` (Abstract) | A record holding one request per subject (`subject_key`): a course and each partner asking to join it, an engineering change and each stage it passes. Raises, looks up and is told about each subject's request |
| `mixin_approval_state_sync.py` | `mixin.approval.state.sync` (Abstract) | A source document whose own state drives its request: a state change syncs the request (decision, grant, revoke, force, reset), a request-side decision reaches the document through the document's own policy, and the request refuses being moved from the approvals app. Adopted by `hr.leave` and `hr.leave.allocation` |
| `mixin_approval_threshold.py` | `mixin.approval.threshold` (Abstract) | Base of `approval.rule` and `approval.category.step`: `company_id` + `currency_id`, the numeric condition on the request (`condition_field`, `operator`, `threshold`, `threshold_max`, `_get_field_value()`, `_compare()`), `_convert_request_amount()` (a request's amount is converted into the record's currency before any comparison) and `_intervals_overlap()` |
| `approval_refusal_reason.py` | `approval.refusal.reason` | Predefined refusal reasons with usage tracking |
| `approval_rule.py` | `approval.rule` | Conditional rules: auto-approve, auto-refuse, and step conditions a step applies by (`when_rule_ids`, `unless_rule_ids`). A rule compares a normalized figure on the request (amount / quantity / date range / priority) or, by `condition_type`, reads the SOURCE DOCUMENT through a domain or a field value |
| `mixin_approval_domain.py` | `mixin.approval.domain` (Abstract) | Base of `approval.rule` and `approval.binding`: parses a subject domain and walks every dotted path in it against the registry at save time, because a condition that never matches reads as "approval was not required" |
| `approval_category_step.py` | `approval.category.step`, `approval.category.step.member` | Steps: a category that needs several pools, each with its own quorum, declares them. A pool is its members (each with an optional end date, so a delegation is a membership that expires) together with a group. Every request routes by the steps that apply to it |
| `approval_binding.py` | `approval.binding` | Gates a model's method on an approval by wrapping it at registry load: Observe, Block or Request, with a `sudo_policy` that tells the real superuser apart from an ordinary user elevated by `sudo()` |
| `approval_gate.py` | `approval.gate` | One row per terminal transition a model gates in its own code, discovered from the registry at `_register_hook` rather than created: the place to record, per operation, whether the gate has stopped watching and started refusing |
| `approval_observation.py` | `approval.observation` | Append-only record of each gated call with the caller's elevation and whether Block would have refused it — how a binding is sized before it is switched on |
| `approval_binding_client.py` | extends `approval.binding` | What the approval button asks: `get_button_approvals`, `check_button_approval`, `action_decide_approval`, `action_withdraw_decision`, and the gated-model set `get_views` reads |
| `approval_binding_editor.py` | extends `approval.binding` | What Studio's editor asks: `create_step_for_button` (binds the button on its first step), `action_open_button_steps` (a kanban of the button's steps first) |
| `ir_actions_server.py` | `ir.actions.server` (extended) | `run()` consults the bindings on the action before running, on the server. web_studio gated a server action only in the browser, so any RPC caller ran it unchecked |
| `ir_actions_report.py` | `ir.actions.report` (extended) | The PDF, HTML and text render entry points consult the bindings on the report. Checked at the entry, because a PDF stored as an attachment is returned without rendering again |
| `approval_utils.py` | — (no model) | Module-level helpers shared across the split files: `is_approval_manager(env)` and `boolean_search_domain()` (the `search=` builder behind `is_overdue`, `is_delegated`, `is_pending_my_review`) |
| `approval_trace.py` | — (no model) | **TEMPORARY campaign instrumentation.** The `odoo.approval.<target>` log targets, the span/ledger helpers and `CALL_TRACES`, the table of entry points wrapped at registry load by `models.py`'s `_register_hook`. Quiet unless a target is named on the command line; removed when the campaign ends. Reference: conventions.md, "Campaign Instrumentation" |
| `ir_attachment.py` | extends `ir.attachment` | Blocks deletion of attachments on finalized requests |
| `mail_activity.py` | extends `mail.activity` | Stores `approver_id`, the approver row an approval activity asks, and derives `approval_request_id` from it; an approval activity marked done by its row's effective approver approves, on the request or on the document |
| `mail_activity_type.py` | extends `mail.activity.type` | Registers approval activity type metadata |
| `models.py` | extends `base` | `get_views` flags every related model that has a Block or Request binding (`has_approval_bindings`) |
| `res_groups.py` | extends `res.groups` | Drops the escalation-manager memo when group membership moves from the GROUP side |
| `res_users.py` | extends `res.users` | `_is_approval_manager` seam, archive handover (SM-7), memo invalidation |

### Wizards (`wizards/`)

| File | Model | Purpose |
|------|-------|---------|
| `approval_decision_wizard.py` | `approval.decision.wizard` | Refuse (structured reason + note) or request a change (field + required note). Approving is 1-click and never opens the wizard |
| `approval_delegate_wizard.py` | `approval.delegate.wizard` | Delegate pending approvals to another user for a date range |

### Reports (`reports/`)

| File | Model | Type | Purpose |
|------|-------|------|---------|
| `approval_request_report.xml` | — | QWeb PDF | `action_report_approval_request` — printable request sheet, bound to `approval.request` as a report action. The template lives in `views/approval_request_template.xml`; the form's Print button gates on `state == "approved"` only (see `test_print_button.py`) |

### Tests (`tests/`)

| File | Coverage Area |
|------|---------------|
| `common.py` | `ApprovalCommon` base class (shared users/category/request fixtures) + product helpers |
| `test_activity_done.py` | An approval activity marked done: by its approver it approves, by anyone else or the system it only dismisses, and an approval that cannot be recorded leaves it open |
| `test_activity_link.py` | An approval activity stores its approver row: engine activities store it, an activity on the document approves when done and goes with its request, and a delegator's old activity decides nothing |
| `test_activity_target.py` | Where approvers are asked: a document-target category asks on the document, the default on the request, a request without a document on itself; a document activity approves when done and goes with a cancel; a step chooses the activity type; asking again and reminders do not duplicate |
| `test_approvals.py` | Core approval lifecycle, state transitions (`TestRequest`) |
| `test_approver_computation.py` | _sync_approvers, category changes, steps applying and ceasing to apply |
| `test_sequential_approval.py` | In-order steps: ordering, turns, refusal and withdrawal in a chain |
| `test_delegation.py` | Delegation lifecycle, effective approver |
| `test_decision_wizard.py` | Wizard refuse / request-change with reasons and notes |
| `test_bulk_operations.py` | Bulk approve/refuse from list view |
| `test_security.py` | Access control: write, unlink, approver CRUD, record-rule visibility |
| `test_deadline_escalation.py` | Smart escalation cron, priority-based reminders |
| `test_auto_expire.py` | Auto-cancel expired pending requests |
| `test_consent_approval.py` | Consent-based auto-approval after timeout |
| `test_auto_action_rules.py` | Auto-approve/auto-refuse conditional rules |
| `test_conditional_rules.py` | Rule evaluation through the steps that apply by it, live re-routing of a submitted request (`TestLiveRerouting`), routing-input lifecycle (`TestRoutingFieldLifecycle`) |
| `test_subject_conditions.py` | Source-document conditions: `domain` and `field_selection` matching; absent, deleted and other-model source documents; configuration-time path validation |
| `test_binding.py` | `approval.binding`: wrapping and unwrapping, one wrapper per method, Observe and Block, superuser vs `sudo()` elevation, the caller's elevation rather than the binding's, the kill switch, every configuration-time refusal; Request mode — no duplicate while pending, one replay as the requester, no replay after re-approval, no borrowing the approver's rights, no run once the snapshot moved, Block covered by a separately approved request; approve on invoke — an approver's call runs the operation exactly once, a non-approver's only raises the request, one step of two waits; run on approval off leaves the operation to the next call; the ORM-API and private-method refusals, and a stored refused binding left unapplied; a refusal that stands, who may reopen it, and withdrawing across steps |
| `test_binding_actions.py` | Action bindings: a blocked server action refused on the server — the call web_studio let through — request, replay as the requester and approve-on-invoke on a server action, a report refused and then rendered once covered, the PDF entry point gated too, `is_enforced`, and every constraint on what an action binding may be |
| `test_binding_client.py` | The approval button's questions: the `get_views` flag, an ungated button, who may decide each step before any call, a check that raises the request and runs nothing, decisions assigned to steps and withdrawn by a later step, a decision under one step leaving the user's other step open and withdrawn from that step alone, a step of another button refused, a refusal reopened by its refuser only, a record the caller cannot read, an action button |
| `test_binding_editor.py` | Studio's editor on the engine: the first step binds the button as Studio did, further steps join it up to order nine, an action button named by xmlid, the approvers list keeping delegations, the steps action, the steps opening as a kanban with a quick-create card, a button whose steps are all archived no longer gated |
| `test_binding_studio_parity.py` | What a Studio rule did, held by steps and bindings, each test naming its Studio test: a record no step applies to is not gated, an exclusive approval counts toward the exclusive step first, an archived step is ignored in any context, a group member decides but only listed members are asked, a step holding decisions is archived not deleted, a binding's target is fixed once it has requests |
| `test_engine_shape.py` | The engine ships no application: no root menu, no category records, its own menus only under Settings > Technical |
| `test_sla_tracking.py` | SLA status computation, compliance tracking |
| `test_lifecycle.py` | Cancelled state, reset-to-draft, forced-terminal paths, locked fields, delegation fan-in (19.0.1.0.7) |
| `test_request_change.py` | Approver-requested mid-flow edit (`pending_change_field`), and re-routing at re-submit (`TestRequestChangeReroutes`) |
| `test_pool_queue.py` | A group step is a queue: its members get rows and decide from To Review, nobody gets a personal activity, and a step may still ask every member (`asks_group_members`) |
| `test_print_button.py` | Print-button visibility on the request form arch |
| `test_dashboard.py` | Dashboard singleton, KPIs, bottleneck detection |
| `test_analytics_accuracy.py` | SQL view accuracy, metric calculations |
| `test_prediction_and_snapshot.py` | On-demand outcome prediction, category snapshots (+ batched-query regression) |
| `test_state_guards.py` | What each request state allows: submitted-request guards, locked fields, forged computed fields |
| `test_decision_log.py` | The ledger: a decision logged with its actor, a reset that erases the rows but not the history, a withdrawal as a fact, a delegate logged acting for the approver, an elevated decision saying so, grants and revocations, the log refusing change and deletion even by the superuser, and the history read through the request |
| `test_decision_attribution.py` | decision attribution under delegation, decision-funnel scoping, change-request close-out, manual-approver preservation, escalation lookup, document-requirement language, batched round-opening |
| `test_invariants.py` | invariants that must hold across the whole lifecycle (pending-review predicate, decision funnels) |
| `test_multi_company.py` | Multi-company isolation across every company_id-scoped model |
| `test_attachment_lock.py` | Attachments of a decided request are frozen: create, write, unlink, forged `res_field` |
| `test_category.py` | Category configuration: sequence-code derivation |
| `test_category_steps.py` | Steps: two one-of-two steps need one approval from each, per-step quorum, one row per user counting toward every step, exclusivity in both directions, group and expired members, step conditions, refusal, asking steps in order while deciding freely, notify lists, configuration that could never be met, and a category without steps untouched |
| `test_request_revocation.py` | Revoking an approved request from outside its decisions (`_revoke`): refused or cancelled, the rows keep their decisions and the request its approval date, only an approved request is revoked, the reason is recorded, a reset gives a clean draft, withdraw is refused afterwards |
| `test_routing_outcomes.py` | The routing contract: scripted readings of state, who could approve and who holds an activity after each decision, on categories built from steps -- required approvers, quorum, members in order, refusal, withdrawal, group queues, owner exclusion, conditions, approvers added by hand, delegation; every shipped category routing by steps and a configured category born with its pool step (`TestCategoriesRouteBySteps`) |
| `test_request_grant.py` | Approving a pending request from outside its decisions (`_approve_without_decision`): no row is named as deciding and none stays pending, an earlier decision stays as given, only a pending request is granted, withdrawal is refused, a grant can still be revoked and reset; the source document being told once is `test_approval/tests/test_source_document.py` |
| `test_step_decisions.py` | Decisions given for steps: a named step counts toward that step only, an unnamed decision takes every step of the row, a step decided once per user, a step outside the row refused, exclusivity in both directions, withdrawing one step keeps the other and re-asks, withdrawing the only step withdraws the decision, a step never decided cannot be withdrawn, a refusal naming a step, a reset clearing decided steps, the note naming where the decision counts, an approver whose step is met no longer asked |
| `test_step_source_approvers.py` | Steps whose approvers come from a field path on the source document (`subject_user_path`): each document names its own approver, only that user decides, members and the named user share the pool, confirm refuses a document naming nobody, the path must exist and end in `res.users` |
| `test_step_company.py` | A step's approvers are the users of the request's company: a group step holds only them, in the rows and the category snapshot; a document user or a listed member outside it is no approver, and a request left without one cannot be confirmed; a later-step member is one of the company |
| `test_campaign_instrumentation.py` | The campaign instrumentation's own invariants (TEMPORARY, goes with the campaign): a green flow logs no refusal, a refused call names its kind and its request, every `raise` of a user-facing error reports a refusal, no two sites share a kind, and every `CALL_TRACES` entry names a live method on a concrete model |
| `test_ui.py` | Tour-based UI tests; `approval_button_tour`: a gated partner button draws its approvals, is approved from the popover, and the request is approved on the server |

Former `test_audit_regressions.py` and `test_audit_round3_regressions.py`
(incident-named regression dumps, C1..M9 / A3-1..A3-19) were fully
dissolved: every test was relocated into its feature-area file above
(e.g. delegation
regressions into `test_delegation.py`) so a maintainer editing a model
finds ALL of its tests in one place instead of archaeology across
incident files. `test_fix_coverage.py` was dissolved the same way
(escalation-hook tests into `test_deadline_escalation.py`, the
action-locking test into `test_lifecycle.py`, activity-idempotency
into `test_approvals.py`).

### Data (`data/`)

| File | Content |
|------|---------|
| `ir_config_parameter_data.xml` | Sequence default `approval.sequence.` `manager` 9, the place approval_hr gives the requester's manager in an in-order step. A manually added approver row keeps the sequence it was given |
| `res_users_data.xml` | The administrator is an approval manager. The generic categories (General, Business Trip, etc.) are `approval_app`'s since 2.3 |
| `mail_activity_type_data.xml` | 2 activity types: approval + change request |
| `mail_message_subtype_data.xml` | Approval state change subtype |
| `ir_cron_data.xml` | 4 scheduled actions |
| `approval_refusal_reason_data.xml` | 12 refusal reasons, incl. system reasons `refusal_reason_parent_cancelled`, `refusal_reason_auto_rule`, `refusal_reason_data_migration` |

### Static (`static/src/`)

| File | Purpose |
|------|---------|
| `common/approval_trace.js` | **TEMPORARY campaign instrumentation, client half.** The `approval.<target>` console targets, off unless `?approval_trace=` or `localStorage["approval.trace"]` names one. Twin of `models/approval_trace.py`; removed with the campaign |
| `common/activity_model_patch.js` | Activity model patch for approval data |
| `common/approver_model.js` | Approver OWL model |
| `web/activity_patch.js` | Activity component patch for approve/refuse buttons |
| `web/activity_list_popover_item_patch.js` | Activity popover patch |
| `web/approval.js` | Approval form component |
| `views/kanban/approvals_category_kanban_controller.js` | Category kanban controller |
| `views/kanban/approvals_category_kanban_view.js` | Category kanban view registration |
| `views/view_button/approval_button_service.js` | Batches every gated button asked in one tick into one `approval.binding.get_button_approvals` call |
| `views/view_button/approval_button_hook.js` | One button's approval state: loads, and reloads through the model's `onRootLoaded` / `onRecordSaved` lifecycle subscriptions; check, decide, withdraw |
| `views/view_button/approval_button.js` | The avatars beside a gated button: decisions, and a placeholder while a step is short of its minimum |
| `views/view_button/approval_button_popover.js` | Steps, who decided and when; Approve / Refuse / Withdraw / Reopen exactly where the server says the caller may |
| `views/view_button/view_button_patch.js` | Gives gated object and action buttons the widget, and chains `beforeExecute` into the server check -- always for an action button, which nothing on the server can refuse, and for an object button while its loaded approvals say it is gated, so a stopped click warns and stays on the record; `_isApprovalGated()` is the override point, which Studio's form editor uses to draw every button's approvals |
| `views/view_button/form_controller_patch.js` | Reads `has_approval_bindings` from the view's related models |
| `scss/approval.scss` + `approval.dark.scss` | Approval styles |

### Security (`security/`)

| File | Content |
|------|---------|
| `res_groups.xml` | 2 groups — `group_approval_approver`, `group_approval_manager` — under one `res.groups.privilege` (`res_groups_privilege_approvals`) |
| `ir_rule.xml` | Record rules: multi-company, ownership, per-category `privacy_visibility` read audiences |
| `ir.model.access.csv` | ACL for every shipped model. The mixin's concrete test consumer is not one of them: `approval.test.document` lives in `test_approval`, which ships no ACL row for it |

## Directory Structure

```
approval/
+-- __manifest__.py
+-- __init__.py
+-- models/
|   +-- approval_category.py          # Category blueprint
|   +-- approval_category_step.py      # Steps and their members
|   +-- approval_request.py           # Core fields + CRUD + smart copy
|   +-- approval_request_access.py    # Who may do what (split by concern)
|   +-- approval_request_lifecycle.py # The transitions
|   +-- approval_request_routing.py   # Who approves
|   +-- approval_request_prediction.py# Outcome prediction
|   +-- approval_request_escalation.py # Escalation + reminders (split file)
|   +-- approval_approver.py          # Approver records
|   +-- mixin_approval_source.py      # Hooks every approval source answers
|   +-- mixin_approval.py             # Source document mixin (one request)
|   +-- mixin_approval_subjects.py    # One request per subject
|   +-- mixin_approval_access.py      # Access asked for through approval
|   +-- mixin_approval_lifecycle.py   # Confirmation gated by approval
|   +-- mixin_approval_state_sync.py  # Document state drives its request
|   +-- mixin_approval_threshold.py   # Currency-aware threshold base
|   +-- mixin_approval_domain.py      # Subject-domain parsing + path checks
|   +-- approval_refusal_reason.py    # Refusal reasons
|   +-- approval_rule.py              # Conditional rules
|   +-- approval_binding.py           # Method gates wrapped at registry load
|   +-- approval_observation.py        # Observed gated calls, both gates
|   +-- ir_actions_server.py          # Server actions consult bindings in run()
|   +-- ir_actions_report.py          # Report render entry points consult bindings
|   +-- approval_utils.py             # Module-level helpers (no model)
|   +-- approval_trace.py             # Campaign instrumentation (no model, TEMPORARY)
|   +-- ir_attachment.py              # Attachment protection
|   +-- mail_activity.py              # Activity extensions
|   +-- mail_activity_type.py         # Activity type metadata
|   +-- res_groups.py                 # Escalation-memo invalidation
|   +-- res_users.py                  # Manager seam + archive handover
+-- wizards/
|   +-- approval_decision_wizard.py   # Refuse / request-change
|   +-- approval_delegate_wizard.py   # Delegation setup
+-- reports/
|   +-- approval_request_report.xml   # QWeb PDF report action
+-- migrations/                       # 31 script directories (1.0.1 .. 2.10.2)
+-- tests/                            # 44 test modules + common.py
+-- views/                            # 10 XML view files
+-- data/                             # 6 XML data files
+-- security/                         # Groups, rules, ACL
+-- static/                           # JS, SCSS, images
```

## Key Statistics

| Metric | Count |
|--------|-------|
| Python files (non-test, incl. `__init__`/`__manifest__`) | 44 |
| Python test files | 44 (+ `common.py`) |
| XML files (non-static) | 28 |
| XML files (static templates) | 4 |
| JS files | 25 |
| SCSS files | 4 |
| ORM models (new) | 20 in `models/` + 2 wizards + 3 report models |
| ORM models (extended) | 8 (base, ir.actions.report, ir.actions.server, ir.attachment, mail.activity, mail.activity.type, res.groups, res.users) |
| Abstract models | 9 (mixin.approval.source, mixin.approval, mixin.approval.state.sync, mixin.approval.gate, mixin.approval.lifecycle, mixin.approval.subjects, mixin.approval.access, mixin.approval.threshold, mixin.approval.domain) |
| SQL view models | 2 |
| Transient models | 2 |
| Test-only models | 3 |
| Cron jobs | 4 |
| Migration script directories | 31 |

Re-measure rather than trusting these: `find . -name '*.py' -not -path './tests/*'
-not -path './migrations/*' -not -path '*__pycache__*' -not -path './machine_doc_v1/*'
| wc -l`, `ls tests/test_*.py | wc -l`, `ls migrations | wc -l`.

## Reading Order

1. **models.md** -- All models, fields, relationships, state machines
2. `approval_category.py` -- Category blueprint (understand config first)
3. `approval_request.py` -- Core fields and CRUD
4. `approval_request.py` -- State machine (`_compute_state`)
5. `approval_request_routing.py` -- `_sync_approvers` (who approves)
6. `approval_approver.py` -- Approver lifecycle and access control
7. `approval_request_lifecycle.py` -- The transitions (`_apply_decision` funnel, `_force_terminal`)
8. `approval_request_access.py` -- Security layer + locked fields
9. `approval_rule.py` -- Dynamic routing: adding, replacing, auto-deciding
10. `mixin_approval.py` -- Source document integration pattern

## Architecture Notes

### Split Model Pattern
`approval.request` is split across 7 files using `_inherit = "approval.request"`:
- `approval_request.py` -- Fields, CRUD, smart-copy defaults
- `approval_request_access.py` -- Access control + business rules
- `approval_request_lifecycle.py` -- Transitions, activities, locking
- `approval_request_routing.py` -- Approver sync, rules, snapshot
- `approval_request_prediction.py` -- Outcome prediction
- `approval_request_escalation.py` -- Escalation and reminders

### State Machine (since 19.0.1.0.7)
Request states: `new`, `pending`, `approved`, `refused`, `cancelled`.
`_TERMINAL_STATES = frozenset({"approved", "refused", "cancelled"})` (helper file).
`refused` = an approver said no; `cancelled` = retracted/expired, nobody decided.
That difference is a reporting contract, not just prose: the sibling
`_DECISION_STATES = frozenset({"approved", "refused"})` is what every
approval-RATE denominator divides by (`approval.metrics.approval_rate`,
`approval.dashboard.overall_approval_rate`, `_predict_outcomes`),
so a retraction never counts as a vote against a request.
All three terminals are recoverable via `action_reset_to_draft()` — the two
failure terminals by the owner or a manager, and `approved` by a manager only
(a guarded override for when the deciding approver is no longer available).
The former `revision`/`cancel` states are gone; mid-flow edits go through the
request-a-change flow (`pending_change_field`) which keeps the request `pending`.

### Decision Funnels
- Approver decisions (`action_approve`/`action_refuse`) funnel through
  `_apply_decision()` -- one shared sequence for lock, cache refresh,
  delegation-aware approver resolution, state write, chatter audit,
  chain advancement, activity cleanup and terminal notification.
- Non-decision terminations (owner cancel, auto-expire, parent cascade,
  auto-refuse rules use their own write path) funnel through
  `_force_terminal()`, which flips only NON-terminal approver rows and
  stamps refusal metadata.

### Approver Sync Engine
`_sync_approvers()` in `approval_request_routing.py` is the central approver
computation method. It is NOT a computed field (creates/updates related records).
Called from `create()`, `write()` (whenever a field in
`_get_fields_approver_sync_trigger()` is written — `category_id`,
`request_owner_id` and every routing input the rules declare),
`action_confirm()` and `action_reset_to_draft()`. The confirm-time call is
what makes the CATEGORY's current configuration authoritative: every other
trigger is a write to the request, so a draft that already existed when an
approver was added to (or removed from) the category would otherwise confirm
with the set computed at its creation. The pure "who should approve" decision step is
extracted to `_get_desired_approvers()` (unit-testable, no writes).
Sources: category approvers, conditional rules (adding or replacing), security groups,
HR manager (via extension hook).

### Security Design
Two-layer validation on all CRUD:
1. **Access control** (WHO): bypassed by sudo/manager
2. **Business rules** (WHAT state): sudo-proof, with one deliberate
   exception — `approval.approver._check_business_rules_write`, which the
   workflow's own sudo writes must pass through (see conventions.md).
   Includes the server-side locked-fields rule (`_check_locked_fields`),
   which freezes two sets once the request leaves draft (2026-07-03 audit):
   - `_LOCKED_FIELDS` — decision values + identity: `amount`,
     `currency_id`, `quantity`, the five date fields, `partner_id`,
     `reference`, `location`, `reason`, `request_owner_id`,
     `company_id`, and the source-document link `res_model`/`res_id`.
     Frozen for EVERYONE (sudo included). `date`/`reason` reopen via
     the request-a-change flow.
   - `_SYSTEM_LOCKED_FIELDS` — system-managed: `approval_minimum`
     (the threshold), `name`, `date_confirmed`, `category_snapshot`.
     Frozen against NON-sudo (user/RPC) writers only; the privileged
     writers are `action_confirm` (while still `new`), reset-to-draft
     (sudo), and the approver sync (sudo). Confirmation-time writes pass
     because state is still `new`.
   - `priority` is intentionally NOT frozen — a framework field, editable
     in every state.
   - A third, state-independent set: `_COMPUTE_ONLY_FIELDS` —
     `state`, `date_approval_granted`, `date_refused`, `date_cancelled`,
     `approval_deadline`, `res_model_id`. `_check_no_forged_computed_fields`
     rejects these in ANY state, draft included, because they are outputs
     of the workflow: writing `state` directly would forge a decision that
     no approver row backs, and the terminal-date stamps are what the
     analytics treat as proof one happened.

### Name / Numbering
The `name` column stays empty (language-neutral) until `action_confirm()`
assigns the category sequence consecutive; drafts display a translated
"New" placeholder via `display_name` only. Discarded drafts never burn
sequence numbers; reset-then-reconfirmed requests keep their number.

### Campaign Instrumentation (temporary)

`models/approval_trace.py` holds a debug-logging surface added for a code-quality /
maintainability / performance / lifecycle campaign, and it comes out when that
campaign ends. Two things make it invisible until asked for: the `odoo.approval`
logger root is levelled to `WARNING` at import unless the operator named it, and
the wrapped entry points (`CALL_TRACES`, applied by `models.py`'s `_register_hook`)
return the wrapped method's own result.

**The performance half has its own switch**, because a run with every target at DEBUG
is not a run whose timings mean anything: `APPROVAL_TRACE_SLOW_MS=25
APPROVAL_TRACE_NPLUSONE=1` with `--log-handler odoo.approval.perf:INFO` measures every
wrapped entry point and prints only the slow calls and the ones whose query count
reached their row count. Note that the wrapped layer does not exist during at-install
tests -- Odoo registers model hooks after that phase. Read conventions.md, "Campaign
Instrumentation", before extending or removing it -- it carries the target table,
the level discipline, the two switches and the removal recipe. **Do not treat it
as permanent architecture.**

### Quick Approve (removed)
The token/HMAC quick-approve feature was removed in 19.0.1.0.2 (replaced by
Telegram bot integration in separate `telegram_bot_*` modules). This module
ships no controllers and no post-init hook.

## Extension Points

- A step naming its approvers by a field path (`subject_model_id`, `subject_user_path`) -- e.g. approval_hr's requester manager
- `_get_escalation_manager(approver)` -- Supply the manager for escalation (approval_hr)
- `_check_withdraw_allowed()` / `_raise_withdraw_blocked()` -- Block withdrawal (e.g., linked invoices)
- `_check_reset_allowed()` -- Veto reset-to-draft (base blocks released source docs)
- `_can_consent_approve()` -- Veto consent auto-approval per request
- `_refuse_approval_request()` -- Cooperative rollback of documents created from the approval
- `_on_approval_state_changed()` -- React to approval decisions in source docs
- `_get_domain_approval_category()` -- Map document types to categories
- `_get_fields_locked()` -- Extend the post-submit frozen field set
- `_approval_rate_limit_exceeded()` -- Submission throttle on the mixin: "has this
  user filed more than N documents, or more than X in value, in the last H hours?"
  Multi-currency by construction — the caller's thresholds are in company currency
  and are converted per counterparty currency before comparison. Used by
  approval_purchase / approval_sale
- `_get_fields_approval_protected()` -- Fields on the SOURCE document that the mixin's
  `write()` freezes while an approval is in flight
- `approval_type` / `target_model` -- Selection fields extended by other modules
