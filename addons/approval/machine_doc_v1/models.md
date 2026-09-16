# Approval Models

`approval.template` and `approval.document.requirement` belong to `approval_app`
since 19.0.2.6.0, together with the request form's fields marked below: the
engine routes and decides a request, the application is how a person raises one.

## Model Relationship Diagram

```
approval.category                       [inherits mixin.mail.thread, mixin.catalog]
    +-- rule_ids ---------> approval.rule      [inherits mixin.approval.threshold, mixin.approval.domain]
    |                           +-- currency_id -> res.currency
    |                           +-- subject_model_id -> ir.model
    +-- step_ids ---------> approval.category.step   [inherits mixin.approval.threshold, mixin.approval.domain]
    |                           +-- member_ids -> approval.category.step.member
    |                           |                   +-- user_id / delegated_by_id -> res.users
    |                           +-- group_id -> res.groups
    |                           +-- notify_user_ids -> res.users (m2m)
    +-- document_requirement_ids -> approval.document.requirement   (approval_app)
    +-- template_count ----> approval.template (o2m via category_id)   (approval_app)
    +-- allowed_user_ids --> res.users (m2m)
    +-- allowed_group_ids -> res.groups (m2m)
    +-- escalation_user_id -> res.users
    +-- automation_id ----> automation.rule   (approval_automation)
    +-- sequence_id ------> ir.sequence

approval.request
    +-- category_id -------> approval.category
    +-- request_owner_id --> res.users
    +-- partner_id --------> res.partner
    +-- company_id --------> res.company
    +-- currency_id -------> res.currency   (amount is Monetary in THIS currency;
    |                           rules convert into their own before
    |                           comparing — mixin.approval.threshold)
    +-- approver_ids ------> approval.approver (o2m)
    |                           +-- user_id -----> res.users
    |                           +-- delegate_id -> res.users
    |                           +-- decided_by_user_id -> res.users
    |                           +-- source_rule_id -> approval.rule
    |                           +-- refusal_reason_id -> approval.refusal.reason
    +-- refusal_reason_id -> approval.refusal.reason (canonical, request-level)
    +-- template_id -------> approval.template   (approval_app)
    +-- applied_rule_ids --> approval.rule (m2m)
    +-- res_model/res_id --> Any model (Many2oneReference)
    +-- attachment_ids ----> ir.attachment (o2m)
    +-- automation_runtime_id -> automation.runtime   (approval_automation)

mixin.approval.threshold (Abstract)   — base of approval.rule
    +-- company_id --------> res.company   (empty = applies to every company)
    +-- currency_id -------> res.currency  (required; thresholds are in it)

mixin.approval.domain (Abstract)      — base of approval.rule, approval.binding
    (no fields; parses and path-checks a subject domain)

approval.binding                        [inherits mixin.approval.domain]
    +-- model_id ----------> ir.model
    +-- category_id -------> approval.category
    +-- observation_ids ---> approval.observation (o2m)
                                +-- user_id -----> res.users

mixin.approval.source (Abstract)
    (no fields; the pool and activity hooks every approval source answers)

mixin.approval (Abstract)              [inherits mixin.approval.source]
    +-- approval_request_id -> approval.request
    +-- approval_state (related)
    +-- pending_approver_ids (related)

mixin.approval.state.sync (Abstract)   [inherits mixin.approval]
    +-- the document's own state field (declared per adopter) drives approval_request_id

mixin.approval.lifecycle (Abstract)    [inherits mixin.approval, mixin.lifecycle]
    +-- action_confirm asks for approval where a category applies

mixin.approval.subjects (Abstract)     [inherits mixin.approval.source]
mixin.approval.access (Abstract)       [inherits mixin.approval.subjects]
    +-- approval_request_ids -> approval.request (o2m on res_id, one live per subject_key)

approval.refusal.reason
    +-- category_ids ------> approval.category (m2m)

mail.activity (extended)
    +-- approval_request_id -> approval.request (computed from approver_id)
    +-- approver_id -------> approval.approver (stored)
```

**Product lines are NOT part of this module.** `approval.request.line`,
`approval.category.product_ids` and `has_product` moved to the separate
`approval_product` module; migration `19.0.1.0.12` hands the records over
and drops the field/view/ACL definitions here.

---

## approval.category

| Key | Value |
|-----|-------|
| Model | `approval.category` |
| File | `models/approval_category.py` |
| Type | Model |
| Inherits | `mixin.mail.thread`, `mixin.catalog` |
| Order | `sequence, id` |
| Multi-company | Yes (`_check_company_auto`) |

`mixin.catalog` (`odoo/odoo/addons/base/models/mixin_catalog.py`) is where
`name` (Char, required, `translate=True`) and `active` come from, along
with a unique-name index that is on by DEFAULT. This model redeclares it
scoped to the company (`_name_src_uniq = name_uniq_index("company_id")`),
so category names are unique per company, archived rows included.

### Fields

| Field | Type | Stored | Required | Key Attributes |
|-------|------|--------|----------|----------------|
| `company_id` | Many2one(`res.company`) | Yes | No | default=env.company, tracking, index |
| `company_currency_id` | Many2one(`res.currency`) | No | No | related=company_id.currency_id |
| `name` | Char | Yes | Yes | translate (from `mixin.catalog`), unique per company |
| `active` | Boolean | Yes | No | default=True (from `mixin.catalog`), tracking |
| `sequence` | Integer | Yes | No | |
| `sequence_code` | Char | Yes | Yes | unique per company (`_sequence_code_uniq`, nulls not distinct) |
| `sequence_id` | Many2one(`ir.sequence`) | Yes | No | check_company |
| `image` | Binary | Yes | No | default=Folder.png |
| `description` | Char | Yes | No | translate |
| `has_date` | Selection(required/optional/no) | Yes | Yes | default="no", tracking *(added by `approval_app`)* |
| `has_date_deadline` | Selection | Yes | Yes | default="no", tracking *(added by `approval_app`)* |
| `has_date_planned` | Selection | Yes | Yes | default="no", tracking *(added by `approval_app`)* |
| `has_date_range` | Selection | Yes | Yes | default="no", tracking *(added by `approval_app`)* |
| `has_partner` | Selection | Yes | Yes | default="no", tracking *(added by `approval_app`)* |
| `has_automation` | Selection | Yes | Yes | default="no", tracking *(added by `approval_automation`)* |
| `has_quantity` | Selection | Yes | Yes | default="no", tracking *(added by `approval_app`)* |
| `has_amount` | Selection | Yes | Yes | default="no", tracking *(added by `approval_app`)* |
| `has_reference` | Selection | Yes | Yes | default="no", tracking *(added by `approval_app`)* |
| `has_location` | Selection | Yes | Yes | default="no", tracking *(added by `approval_app`)* |
| `has_document` | Selection(required/optional) | Yes | Yes | default="optional", tracking *(added by `approval_app`)* |
| `allow_self_approval` | Boolean | No | Yes | Whether the request owner may also decide; off, no step stages them. Off by default; categories existing at 19.0.2.1.0 were migrated to on |
| `allowed_user_ids` | Many2many(`res.users`) | Yes | No | Gate request creation; also the `restricted_users` read audience |
| `allowed_group_ids` | Many2many(`res.groups`) | Yes | No | Gate request creation; also the `restricted_groups` read audience |
| `privacy_visibility` | Selection(private/restricted_users/restricted_groups/employees) | Yes | Yes | **default="private"**, tracking. Additive READ audience (ir.rule based) — the default adds NO audience beyond requester/approvers/delegates/managers |
| `approval_minimum` | Integer | Yes | Yes | default=1, tracking. A request's minimum when none of the category's steps applies, and the minimum of a pool step `_add_approver` creates |
| `approval_type` | Selection([general]) | Yes | No | tracking, extensible |
| `target_model` | Selection([]) | Yes | No | tracking, extensible |
| `document_requirement_ids` | One2many(`approval.document.requirement`) | Yes | No | *(added by `approval_app`)* |
| `rule_ids` | One2many(`approval.rule`) | Yes | No | |
| `rule_count` | Integer | No | No | compute |
| `template_count` | Integer | No | No | compute *(added by `approval_app`)* |
| `count_request_to_validate` | Integer | No | No | compute |
| `color` | Integer | Yes | No | |
| `kanban_dashboard` | Text | No | No | compute (JSON) |
| `show_on_dashboard` | Boolean | Yes | No | default=True |
| `approval_deadline_hours` | Integer | Yes | No | default=48, tracking |
| `escalate_overdue` | Boolean | Yes | No | default=False, tracking (legacy flag; the dedicated overdue cron was removed, escalation runs via `cron_smart_escalation`) |
| `escalation_user_id` | Many2one(`res.users`) | Yes | No | tracking |
| `auto_expire_hours` | Integer | Yes | No | default=0, tracking |
| `sla_target_hours` | Integer | Yes | No | default=0, tracking |
| `sla_warning_pct` | Integer | Yes | No | default=80, tracking |
| `consent_approval_hours` | Integer | Yes | No | default=0, tracking |
| `automation_id` | Many2one(`automation.rule`) | Yes | No | *(added by `approval_automation`)* |
| `step_ids` | One2many(`approval.category.step`) | — | No | Every request routes by the steps whose condition it meets. A category created where the context carries `approval_category_routes_by_steps` starts with an "Approvers" step counting approvers added by hand (`default_get`) |
| `notify_sequentially` | Boolean | Yes | No | Step mode only. Every step may be decided at any time, but an approver is only asked — given an activity — once every earlier step is met. It orders the asking, not the deciding |
| `activity_target` | Selection | Yes | No | string="Ask Approvers On", default `request`. `document` asks each approver on the request's source document, when it has one that holds activities; the activity still decides the request when done (it carries `approver_id`) |

### Key Methods

| Method | Purpose |
|--------|---------|
| `create()` | Always auto-creates the ir.sequence from sequence_code |
| `write()` | Syncs sequence_code and company_id to ir.sequence |
| `_compute_kanban_dashboard()` | Batched _read_group for dashboard JSON |
| `create_request()` | Opens new request form with defaults |
| `_get_view_request()` | Base helper for all dashboard view actions |
| `_add_approver(user, required, sequence)` | Adds `user` as a member of the category's pool step, the first counting approvers added by hand, creating that step when the category has none |

### Constraints

| Method | Rule |
|--------|------|
| `_constrains_approval_minimum` | minimum >= 1 |
| `_constrains_consent_sequential` | Consent auto-approval cannot be combined with a step whose members decide in order |

### SQL constraints

| Name | Rule |
|------|------|
| `_name_src_uniq` | `name` unique per `company_id` (redeclares `mixin.catalog`'s default whole-table index with a company scope; archived rows keep their name reserved) |
| `_sequence_code_uniq` | `unique nulls not distinct (sequence_code, company_id)` |

---

## approval.request

| Key | Value |
|-----|-------|
| Model | `approval.request` |
| Files | `approval_request.py` (fields, CRUD, state machine), `approval_request_access.py` (who may), `approval_request_lifecycle.py` (transitions), `approval_request_routing.py` (who approves), `approval_request_escalation.py` (when), `approval_request_prediction.py` |
| Type | Model |
| Inherits | `mixin.mail.thread.main.attachment`, `mixin.mail.activity` |
| Chatter access | `_mail_post_access = "read"` — read rights are enough to post, so an approver who can see a request can comment on it without holding write |
| Order | `create_date desc, id desc` |
| Multi-company | Yes (`_check_company_auto`) |

### Fields

| Field | Type | Stored | Required | Key Attributes |
|-------|------|--------|----------|----------------|
| `company_id` | Many2one(`res.company`) | Yes | No | default=env.company, index |
| `category_id` | Many2one(`approval.category`) | Yes | Yes | index, allowed-user/group domain |
| `category_image` | Binary | No | No | related |
| `request_owner_id` | Many2one(`res.users`) | Yes | Yes | default=env.user, check_company, index |
| `partner_id` | Many2one(`res.partner`) | Yes | No | check_company, index=btree_not_null |
| `name` | Char | Yes | No | tracking, copy=False. **Empty until `action_confirm` assigns the sequence consecutive**; drafts show a translated "New" placeholder via `display_name` only |
| `priority` | Selection(0-3) | Yes | Yes | default="1", tracking, index (the escalation cron filters on `(state, priority)` every 4 hours) |
| `last_reminder_date` | Datetime | Yes | No | readonly, copy=False |
| `reminder_count` | Integer | Yes | No | default=0, readonly, copy=False |
| `escalated_to_manager` | Boolean | Yes | No | default=False, readonly, copy=False |
| `date` | Datetime | Yes | No | |
| `date_start` | Datetime | Yes | No | |
| `date_end` | Datetime | Yes | No | |
| `date_deadline` | Datetime | Yes | No | *(added by `approval_app`)* |
| `date_planned` | Datetime | Yes | No | *(added by `approval_app`)* |
| `date_confirmed` | Datetime | Yes | No | index (cleared by reset-to-draft) |
| `date_approval_granted` | Datetime | Yes | No | compute, store, index, copy=False; cleared whenever the request leaves `approved`, except on a revoked request (`revoked_state`), which keeps the date its approval was granted |
| `date_refused` | Datetime | Yes | No | compute, store, index, copy=False, cleared whenever the request is not in the state it records |
| `date_cancelled` | Datetime | Yes | No | compute, store, index, copy=False, cleared whenever the request is not in the state it records |
| `revoked_state` | Selection | Yes | No | refused / cancelled, readonly, copy=False. Set by `_revoke()` when an approved request is overturned from outside its decisions; `_compute_state` reads it before the approver rows, whose decisions stay as given. Cleared by `_force_draft()` |
| `revoked_by_user_id` | Many2one(`res.users`) | Yes | No | readonly, copy=False. Who revoked the approval |
| `date_revoked` | Datetime | Yes | No | readonly, copy=False. When the approval was revoked |
| `granted_by_user_id` | Many2one(`res.users`) | Yes | No | readonly, copy=False. Set by `_approve_without_decision()` when a pending request is approved from outside its decisions; `_compute_state` reads it after `revoked_state` and before the approver rows. Cleared by `_force_draft()`; a request carrying it refuses withdrawal |
| `refusal_reason_id` | Many2one(`approval.refusal.reason`) | Yes | No | readonly, copy=False, tracking. Canonical reason of the terminal refusal (wizard, cascade or auto-rule) |
| `refusal_note` | Text | Yes | No | readonly, copy=False, tracking |
| `pending_change_field` | Selection(date/reason) | Yes | No | readonly, copy=False. Field the requester must update before approval can resume. `_get_pending_change_candidates()` offers `reason` always and `date` once the request carries a date or a period; `approval_app` offers `date` by what the category's form exposes instead |
| `location` | Char | Yes | No | *(added by `approval_app`)* |
| `reference` | Char | Yes | No | *(added by `approval_app`)* |
| `reason` | Html | Yes | No | |
| `quantity` | Float | Yes | No | |
| `amount` | **Monetary** | Yes | No | Expressed in `currency_id`, NOT company currency |
| `currency_id` | Many2one(`res.currency`) | Yes | **Yes** | default=env.company.currency_id. The unit of `amount`; rules convert into their OWN currency before comparing (`mixin.approval.threshold._convert_request_amount`), and it is in `_LOCKED_FIELDS` — changing it after submit would move every threshold the decision was made against |
| `approver_ids` | One2many(`approval.approver`) | Yes | No | check_company |
| `user_ids` | Many2many(`res.users`) | No | No | compute |
| `state` | Selection(new/pending/approved/refused/cancelled) | Yes | No | compute, store, default="new", tracking, group_expand, index |
| `user_approver_state` | Selection(new/pending/waiting/approved/refused/cancelled) | No | No | compute (context=uid) — mirrors the six `approval.approver` states |
| `is_terminal` | Boolean | No | No | compute. True once the request reaches approved, refused or cancelled — exists so views can say "this is over" BY NAME instead of spelling `_TERMINAL_STATES` out as a literal triple in four `invisible` expressions |
| `is_pending_my_review` | Boolean | No | No | compute (context=uid), search (via `boolean_search_domain`). Delegation-aware "is this in my queue right now" — backs the review inbox |
| `can_change_request_owner` | Boolean | No | No | compute |
| `has_*` | Selection | No | No | 10 related fields from category *(added by `approval_app`)* (there is no `has_product` — see `approval_product`, and no `has_payment_method` since 19.0.1.0.26) |
| `approval_minimum` | Integer | Yes | No | default=1, readonly, copy=True. Effective minimum (an approver-replacing rule's override, or the category default) |
| `allow_self_approval` | Boolean | No | No | related to the category |
| `decision_log_ids` | One2many(`approval.decision.log`) | No | No | compute_sudo; the decision history |
| `approval_type` | Selection | Yes | No | related, store |
| `target_model` | Selection | Yes | No | related, store |
| `approval_progress` | Float | No | No | compute |
| `pending_approver_ids` | Many2many(`res.users`) | No | No | compute |
| `approval_deadline` | Datetime | Yes | No | compute, store, index. Reads `approval_deadline_hours` from `category_snapshot` via `_get_snapshot_config` (live category fallback) |
| `is_overdue` | Boolean | No | No | compute, search |
| `sla_status` | Selection(on_track/at_risk/breached/met/no_sla) | **No** | No | compute, search=`_search_sla_status` (SQL). Non-stored: value tracks the wall clock |
| `sla_elapsed_hours` | Float | No | No | compute |
| `sla_remaining_hours` | Float | No | No | compute |
| `can_withdraw` | Boolean | No | No | compute (context=uid) |
| `template_id` | Many2one(`approval.template`) | Yes | No | readonly, copy=False, index=btree_not_null *(added by `approval_app`)* |
| `applied_rule_ids` | Many2many(`approval.rule`) | Yes | No | readonly, copy=False (cleared by reset-to-draft) |
| `category_snapshot` | Json | Yes | No | readonly, copy=False (built at confirm; cleared by reset-to-draft) |
| `res_model` | Char | Yes | No | readonly, index |
| `res_id` | Many2oneReference | Yes | No | model_field=res_model, readonly |
| `res_model_id` | Many2one(`ir.model`) | Yes | No | compute, store |
| `res_name` | Char | No | No | compute (batched per model) |
| `attachment_ids` | One2many(`ir.attachment`) | Yes | No | domain=[res_model=approval.request] |
| `count_attachment` | Integer | No | No | compute |
| `automation_id` | Many2one | No | No | related *(added by `approval_automation`)* |
| `automation_runtime_id` | Many2one(`automation.runtime`) | Yes | No | index=btree_not_null *(added by `approval_automation`)* |
| `binding_id` | Many2one(`approval.binding`) | Yes | No | readonly, copy=False, ondelete=set null. Set when an `approval.binding` in Request mode raised the request; approving it runs that binding's method once, as `request_owner_id` |
| `binding_snapshot` | Json | Yes | No | readonly, copy=False. The values the binding's condition read from the source document when the request was raised. The approval covers the record only while they still match |
| `subject_key` | Char | Yes | No | readonly, copy=False, indexed. What the request asks about when its record holds one request per subject (`mixin.approval.subjects`): `access:<partner>` on a course, `stage:<stage>` on an engineering change. Only a request carrying one reaches such a record |
| `date_binding_replayed` | Datetime | Yes | No | readonly, copy=False. When the gated operation ran after approval. Set once, so a withdrawal and a second approval do not run it again |
| `operation` | Char | Yes | No | readonly, copy=False, index=btree_not_null. The gated operation a document's own `mixin.approval.gate` raised this request for. A grant clears that operation and no other |
| `operation_snapshot` | Json | Yes | No | "Approved Subject": what the document looked like when the request was raised, as its `_get_approval_snapshot` describes it. The grant covers that version and no other |
| `date_operation_run` | Datetime | Yes | No | readonly, copy=False. When the grant ran that operation, so it runs once |
| `binding_replay_error` | Text | Yes | No | readonly, copy=False. Why the gated operation did not run. The approval itself stands |

Removed in 19.0.1.0.7 (or earlier): `revision_count`, `cloned_from_id`,
`approver_compute_ms`, the quick-approve token/QR fields, the stored
`sla_status` column (migration drops it). Removed in 19.0.1.0.12:
`line_ids` and `has_product` — product lines are now `approval_product`.

### State Machine

```
new --(action_confirm)--> pending --> approved            (terminal)
                             |   \--> refused             (terminal)
                             \-----> cancelled            (terminal)

refused / cancelled --(action_reset_to_draft: owner or manager)--> new
approved            --(action_reset_to_draft: manager only)------> new
```

State is a **stored computed field** based on `approver_ids.state`
(`_compute_state`, priority order):
- No approvers => `new`
- Any approver `refused` => `refused`
- Any approver `cancelled` => `cancelled`
- Any approver `new` => `new`
- approved_count >= `approval_minimum` (NOT clamped to len(approvers)) AND all required approved => `approved`
- Otherwise => `pending`

`refused` outranks `cancelled` so a real decision is never masked.
`_TERMINAL_STATES = frozenset({"approved", "refused", "cancelled"})`
(class attribute in `approval_request.py`). The source-document
notification is NOT fired from the compute; the transitioning action
calls `_notify_if_terminal_transition()` explicitly.

An approver's request-a-change keeps the state `pending` and sets
`pending_change_field`; approve/refuse/consent are blocked until the
requester re-submits (`action_resubmit`).

### Key Methods (across all split files)

| Method | File | Purpose |
|--------|------|---------|
| `create()` | request.py | Approval minimum from category, subscribe owner, sync approvers (no name assignment — deferred to confirm) |
| `write()` | request.py | Access check, forged-compute and locked-fields business rules, category-change guard, owner re-subscription, sync approvers when a field in `_get_fields_approver_sync_trigger()` is written |
| `copy()` | request.py | Duplicate with a "Duplicated from" log; `approval_app` overrides `copy_data()` to seed smart defaults from the owner's history (`_smart_clone_defaults`) |
| `unlink()` | request.py | Two-layer validation (access + business rules: draft only) |
| `_compute_display_name()` | request.py | Translated "New" placeholder for unnumbered drafts |
| `_compute_state()` | request.py | Core state machine (no side effects) |
| `_compute_sla_status()` / `_search_sla_status()` | compute.py | Non-stored SLA status + SQL search (CASE mirrors the compute) |
| `_compute_approval_deadline()` / `_get_snapshot_config()` | compute.py | Deadline from config frozen at confirm |
| `_compute_date_approval_granted/refused/cancelled()` | request.py | Append-only terminal-date stamps (cleared on state=`new`) |
| `_predict_outcomes()` / `action_predict_outcome()` | compute.py | On-demand outcome prediction from comparable decided requests (batched, memoised per category+partner). A button, not a field: computing it on every form read cost a bucket search per load and depended on the reader's record rules |
| `action_confirm()` | lifecycle.py | Draft only: validate, assign sequence name, snapshot, stamp date_confirmed, auto-rules, start workflow |
| `action_approve(approver, steps)` | lifecycle.py | Guard pending-change, then `_apply_decision("approve", approver, steps)`; `steps` is the step the approval button decides |
| `action_refuse(approver, steps)` | lifecycle.py | Header path opens decision wizard; inline path, or a named step, `_apply_decision("refuse", approver, steps)` |
| `_apply_decision()` | lifecycle.py | **Single decision funnel**: lock, cache refresh, delegation-aware resolution, state write, chatter, chain advance, activity cleanup, terminal notify, refusal rollback hook. Records the steps each row decided: the ones named, or `_get_steps_for_decision`; a named step may join an approved row's decided steps |
| `_get_current_pending_approver()` | request.py | Delegation-aware pending-approver resolution (single source for header/bulk/wizard) |
| `action_cancel()` | lifecycle.py | Owner/manager, pending only → `_force_terminal("cancelled")` |
| `action_reset_to_draft()` | lifecycle.py | any terminal state → new; clears decision metadata, date_confirmed, snapshot, escalation counters, applied rules; re-syncs approvers; keeps name. refused/cancelled: owner or manager. approved: **manager only** + `_check_withdraw_allowed()` (descendant-document guard) + notifies source document of the exit. The effects are `_force_draft`, without the guard, which an approval binding's coverage reset also runs on a waiting request that holds decisions |
| `_check_owner_or_manager()` | access.py | Access layer (WHO) for owner-side lifecycle actions |
| `action_request_change()` / `action_resubmit()` | action.py | Request-a-change flow (set/clear `pending_change_field`) |
| `action_withdraw()` | lifecycle.py | Withdraw approval (approved row → pending; explicit exit-from-approved notification); clears the row's decided steps |
| `action_withdraw_approver(approver_id, step_id)` | lifecycle.py | Withdraw another's (or one's own) decision after `_check_withdraw_actor`; with `step_id`, only that step: a row decided for others too keeps them (`_withdraw_decided_steps`), otherwise the whole decision goes |
| `_withdraw_decided_steps(approver, steps)` | lifecycle.py | Takes a decision back from some of its steps. The row stays approved for the rest; a request that falls back to pending re-asks its parked rows |
| `_refuse_cascade()` | lifecycle.py | Parent-document cancellation → `_force_terminal("refused")` with `refusal_reason_parent_cancelled` |
| `action_approve_bulk()` / `action_refuse_bulk()` | action.py | Bulk decisions via `_action_bulk_decision` (delegation-aware, skip_wizard) |
| `action_view_to_review()` | request.py | Pending-review inbox, includes requests delegated TO the user |
| `_refuse_approval_request()` | lifecycle.py | No-op anchor for cooperative document rollback (account/purchase/sale override) |
| `_sync_approvers()` | routing.py | **Core engine**: reconcile approver rows from all sources (write step) |
| `_get_desired_approvers()` | routing.py | Pure decision step of the sync (no writes, unit-testable); returns a `DesiredApprovers` dataclass |
| `_force_terminal()` | lifecycle.py | Non-decision termination funnel (cancel/expire/cascade); preserves terminal approver rows, stamps refusal metadata |
| `_revoke(new_state, body, ...)` | lifecycle.py | Overturns an **approved** request into `refused` or `cancelled` from outside its decisions (a validated leave refused by an officer): writes `revoked_state`, stamps the refusal metadata, cancels activities, notifies the source document once, runs `_refuse_approval_request()` for a refusal. Every approver row keeps its decision. A non-approved request raises `UserError`; `approved` as the target raises `ValueError` |
| `_approve_without_decision(body, ...)` | lifecycle.py | Approves a **pending** request from outside its decisions (a leave the system validates): writes `granted_by_user_id`, turns pending rows to `waiting`, cancels activities, notifies the source document once. No row is recorded as deciding, and one decided before keeps its decision. A non-pending request raises `UserError` |
| `_check_moved_from_source_document()` | lifecycle.py | Refuses withdraw, reset to draft, cancel and change requests on a request whose source model sets `_approval_request_follows_document` (`mixin.approval.state.sync`): such a request is decided here and moved otherwise from its document |
| `_get_approval_activities(user=None)` | lifecycle.py | The approval activities asking this request's approvers, found through `mail.activity.approver_id` wherever they live. `_cancel_activities`, `_retire_unasked_approval_activities` and `_get_user_approval_activities` all read it |
| `_notify_if_terminal_transition()` | lifecycle.py | Fire source-doc hook once on entering a terminal state |
| `_get_notifiable_source_document()` | lifecycle.py | The adopting document to tell, or None: registry, `mixin.approval` and two-way-link checks; returned under `sudo()` with `approval_acting_user_id` |
| `_notify_source_document_progress()` | lifecycle.py | Calls the document's `_on_approval_progress()` after an approval that met a step while the request stays pending |
| `_lock_for_approval_action()` | lifecycle.py | SELECT FOR UPDATE to prevent race conditions |
| `_check_auto_action_rules()` | routing.py | Auto-approve/refuse rules; auto-refuse stamps `refusal_reason_auto_rule` metadata |
| `_get_desired_approvers()` | routing.py | Every request takes its approvers from its applicable steps alone, each row staged with its member's `required` and `sequence`, and hands back the steps' `when_rule_ids` as the matched rules `applied_rule_ids` records. The rules steps read are evaluated once per request per sync (`_get_step_rule_matches`, remembered in the `approval_rule_matches` context) |
| `_reroute_steps_live(desired)` | routing.py | A pending request its steps route, after a routing field changed: rows join the steps that now apply (an approval given for a step that stopped applying carries to the step that replaced it), a user only an arriving step names gets a row, and nothing happens when no step arrived or departed, so a member added to a step already applying is not asked mid-flight |
| `_get_escalation_rules()` | escalation.py | `ESCALATION_RULES` defaults + `approval.escalation.<priority>.<kind>` ir.config_parameter overrides |
| `_get_escalation_manager()` | escalation.py | Hook: manager to escalate to (base returns empty; approval_hr overrides) |
| `_prepare_category_snapshot()` | routing.py | Audit snapshot of the category's configuration, its applicable steps and the `effective_*` keys |
| `_notify_source_document_state_change()` | lifecycle.py | Calls mixin hook on source doc (registry isinstance check) |
| `_check_access_write()` | access.py | Owner OR assigned approver write access |
| `_check_locked_fields()` | access.py | **Business rule, never bypassed**: value fields frozen outside draft; `pending_change_field` selectively reopens date/reason, and only for the requester (owner/manager/sudo) |
| `_check_no_forged_computed_fields()` | access.py | Rejects direct writes to `_COMPUTE_ONLY_FIELDS` (`state`, the three terminal-date stamps, `approval_deadline`, `res_model_id`) in **every** state, draft included — these are workflow outputs, not inputs |
| `_check_routing_fields_after_submit()` | access.py | Once submitted, the live routing inputs (`priority`) are the requester's: an approver may not re-route or re-time the request they decide |
| `_check_confirm()` | lifecycle.py | Pre-confirm: approvers, documents (distinct-match), required fields |
| `_check_reset_allowed()` | lifecycle.py | Hook: veto reset-to-draft (base blocks released source-doc links) |
| `cron_smart_escalation()` | escalation.py | Priority-based reminder schedule (batched, limit 500/priority; skips requests with `pending_change_field` set; per-request savepoint) |
| `_reconcile_delegation_activities()` | escalation.py | Runs first on every escalation tick: repoints an approval To-Do at the effective approver when a delegation was set (or lifted) after the round had already opened, closing the duplicate. Without it the activity stays in the principal's inbox for the life of the delegation |
| `cron_auto_expire()` | escalation.py | **Cancel** (not refuse) requests past `auto_expire_hours` via `_force_terminal` |
| `cron_consent_approval()` | escalation.py | Auto-approve after consent window; skips sequential categories, refused approvers, `pending_change_field`, `_can_consent_approve()` vetoes |
| `_replay_bound_operation()` | Called from `_notify_if_terminal_transition` when a request becomes `approved`, AFTER `_notify_source_document_state_change`, so an adopter sees itself approved before the operation it gated runs. Hands off to `approval.binding._replay`; does nothing once `date_binding_replayed` is set, when the binding's `run_on_approval` is off, or while an invoking call is recording its own approval |
| `_get_applicable_steps()` | The category's steps whose condition this request meets, in order. Routing stages one row per user over them |
| `_is_quorum_met(state_counts, threshold)` | When any row carries steps: every applicable step meets its quorum. Otherwise (rows added by hand where no step applies) the request's `approval_minimum` |
| `_get_step_counts()` / `_get_step_assignment()` | Approvals per step. An approved row counts toward every step its decision was given for (`decided_step_ids`). Only a row approved for several steps one of which is exclusive -- consent, an automatic rule -- is resolved here, toward the lowest step still short |
| `_get_steps_for_decision(approver)` | The steps an approval naming none is given for: every undecided step of the row, or, beside an exclusive step, the first still short of its quorum (exclusive first within a sequence). Decided when taken, so who decided which step stays fixed as later approvals come in |
| `_check_steps_decidable(approvers, steps)` | Studio's exclusivity for decisions that name steps: a step already decided by the row, or a second step beside an exclusive decided one, raises |
| `_get_rows_decidable_by(user)` | The user's rows an approval naming no step decides -- pending rows, and approved rows with a step still open to the user (their decided step was archived, or the button decided only some of their steps). `approval.binding._approve_on_invoke` decides these, so a click after an archive decides the rest, as Studio's click did |
| `_get_unmet_steps()` / `_get_open_steps()` | The steps still short of their quorum, and the lowest-sequence ones among them, which are the ones being asked |
| `_check_steps_can_be_met(steps)` | At confirmation, refuses a step whose pool is smaller than its quorum, rather than leaving a request that could never be approved |
| `_notify_step_decision(approvers, acting_user, decision, steps)` | Posts an internal note to the notify list of every step the decision counts toward -- the named steps, or the decided ones, narrowed on approval to where the assignment put them |

### Constraints

| Method | Rule |
|--------|------|
| `_check_date_consistency` | date_end > date_start |
| `_check_approver_ids` | No duplicate approvers per request (id-set based). Fires only when writing through `request.approver_ids`; the real guarantee is the `approval_approver_request_user_uniq` SQL constraint |
| `_check_category_access` | Owner must be allowed by category |
| `_check_category_change` | No category change after confirmation (form saves; direct writes guarded in `write()` via `_raise_category_change_blocked`) |

### Escalation Rules (constant `ESCALATION_RULES`, `approval_request.py`)

Defaults; each value overridable via ir.config_parameter
`approval.escalation.<priority>.<first_reminder|escalation>` (hours),
resolved by `_get_escalation_rules()`:

| Priority | First Reminder | Escalation |
|----------|---------------|------------|
| Urgent (3) | 4 hours | 8 hours |
| High (2) | 24 hours | 48 hours |
| Normal (1) | 48 hours | 96 hours |
| Low (0) | 72 hours | 168 hours |

---

## approval.approver

| Key | Value |
|-----|-------|
| Model | `approval.approver` |
| File | `models/approval_approver.py` |
| Type | Model |
| Order | `sequence, id` |
| Multi-company | Yes (`_check_company_auto`) |

### Fields

| Field | Type | Stored | Required | Key Attributes |
|-------|------|--------|----------|----------------|
| `request_id` | Many2one(`approval.request`) | Yes | Yes | ondelete=cascade, check_company, index |
| `company_id` | Many2one(`res.company`) | Yes | No | related, store, index |
| `user_id` | Many2one(`res.users`) | Yes | Yes | check_company, index |
| `sequence` | Integer | Yes | No | default=10 |
| `state` | Selection(new/pending/waiting/approved/refused/cancelled) | Yes | No | compute (`_compute_state`), store, readonly, index. A projection of the decision ledger over `flow_state`: the row's standing fact since the request's last `reset` -- `approved`, or `withdrawn` with steps still decided, reads approved; `refused` reads refused -- else `flow_state`. `create`/`write` naming it raise for every caller, `sudo()` included (`_raise_state_is_derived`) |
| `flow_state` | Selection(new/pending/waiting/refused/cancelled) | Yes | No | required, default="new", readonly. Where routing has put the row: whose turn it is, and the rows a refusal or a cancellation closed. Never a decision; every funnel that moves a turn writes this, never `state`. `_stamp_pending_since` keys on it |
| `decision_log_ids` | One2many(`approval.decision.log`, `approver_id`) | No | No | readonly. The facts `state` is projected from |
| `required` | Boolean | Yes | No | default=False, readonly |
| `pending_since` | Datetime | Yes | No | readonly, copy=False, index=btree_not_null. Stamped by `_stamp_pending_since` (from `create`/`write`, so all five promotion paths are covered) when the row ENTERS `pending`; cleared by reset-to-draft. With `decision_date` it gives each approver's OWN turnaround instead of the request's age since `date_confirmed` |
| `source_synced` | Boolean | Yes | No | readonly, copy=False. Exact sync provenance since 19.0.1.0.13: set on every row `_sync_approvers` creates. A synced row whose source stopped producing it is DELETED on re-sync rather than kept as a phantom manual approver |
| `source_rule_id` | Many2one(`approval.rule`) | Yes | No | readonly, copy=False, index=btree_not_null. Which rule injected this row, on rows staged before 19.0.2.8.0; the sync still reads it as an automated source |
| `decision_date` | Datetime | Yes | No | readonly, copy=False, index. Stamped by `_apply_decision` on a GENUINE approve/refuse; cleared on withdraw/reset. NULL for non-decision flips. Drives the performance analytics |
| `decided_by_user_id` | Many2one(`res.users`) | Yes | No | readonly, copy=False, index. WHO exercised the slot (`user_id` is WHOSE it is) — the delegate inside an active delegation window. Stamped and cleared beside `decision_date`; both analytics consumers key on `COALESCE(decided_by_user_id, user_id)` |
| `delegate_id` | Many2one(`res.users`) | Yes | No | check_company, copy=False |
| `delegate_start_date` | Date | Yes | No | copy=False |
| `delegate_end_date` | Date | Yes | No | copy=False |
| `is_delegated` | Boolean | **No** | No | compute, search=`_search_is_delegated`, copy=False. Non-stored: "today" is resolved in the SLOT OWNER's timezone (`user_id.tz`, `@api.depends` includes it), not the server's. The compute buckets the recordset by tz (`_delegation_today_by_tz`); the search inverts that into one OR-branch per distinct `res.users.tz` value, built by `_delegation_date_buckets()` and memoised in `env.cr.cache` under `approval_delegation_tz_buckets` (dropped by `res.users.write` on a `tz` change) |
| `note` | Text | Yes | No | Decision note (approve/refuse context) |
| `refusal_reason_id` | Many2one(`approval.refusal.reason`) | Yes | No | |
| `step_ids` | Many2many(`approval.category.step`) | Yes | No | readonly, copy=False. The steps this row may decide. Rows stay `unique(request_id, user_id)`, so a user in the pools of two steps is one row carrying both |
| `decided_step_ids` | Many2many(`approval.category.step`) | Yes | No | readonly, copy=False, `active_test`. The steps the row's decision was given for, and so what the quorum counts it toward. The approval button decides the step it is drawn under; every other decision takes `_get_steps_for_decision`. Cleared on withdraw, reset and a requested change; migration 1.8 fills it for rows decided before |

### Key Methods

| Method | Purpose |
|--------|---------|
| `action_approve()` | 1-click approve — delegates to `request_id.action_approve(self)`, never opens the wizard |
| `action_refuse()` | Opens decision wizard (or direct refuse with skip_wizard context) |
| `_get_effective_approver()` | Returns delegate if delegation window active, else user_id |
| `_create_activity()` | Schedule mail activity for approver to-do, assigned to the **effective approver** (delegate when active); idempotent per effective-user+request |
| `_get_activity_target()` / `_get_activity_type()` | Where the row's approver is asked -- the request, or its source document when the category's `activity_target` is `document` and the document holds activities -- and with which type: the first of the row's steps that names one, else the approval activity. `_create_activity`, escalation reminders and the delegation wizard all use both |
| `_check_access_create/write/unlink()` | Access control layer. Write is field-scoped for non-managers: delegation fields by the original `user_id` only; decision-note fields (`refusal_reason_id`, `note`) by the effective approver; `flow_state`/`sequence`/`required`/`request_id` are workflow-managed (manager/sudo only); `state` is derived and writable by no one |
| `_check_business_rules_create/unlink()` | Business rules layer: DRAFT only since 19.0.1.0.13 (relaxed only by `env.su` + `approver_ids_computation` sync context) — rows on decided requests are state-transition vehicles and are re-cycled via reset-to-draft |
| `_check_delegation_dates` (constraint) | Delegation requires both dates, end >= start |
| `_check_delegate_identity` (constraint) | Delegate must not be the approver themselves, the request owner, or a co-approver on the same request |
| `_filtered_notifiable()` | The rows whose approver should be asked now. Every activity goes through `_create_activity`, which applies this first, so it orders the asking for all six callers: a row on a `notify_sequentially` category is asked only once one of its steps is among the lowest unmet ones. Only a row whose user is listed for one of its steps is asked, and, when the category requests its steps in order, once a step they are listed for opens, not one they may decide through its group. A listed approver is asked only while one of their steps is still short of its quorum; after a decision or a withdrawal, `_retire_unasked_approval_activities` unlinks the approval activities of rows this stops asking |
| `_approve_for_every_step()` | Approves rows nobody decided -- consent approval, an auto-approve rule -- for all their steps, so they count as those paths always counted |

---

## mixin.approval.threshold (Abstract)

| Key | Value |
|-----|-------|
| Model | `mixin.approval.threshold` |
| File | `models/mixin_approval_threshold.py` |
| Type | AbstractModel |
| Inherited by | `approval.rule` |

The currency layer for every numeric threshold in the module. Both routing
models compare a request's `amount` against a configured number, and both
may live on a category shared across companies with different currencies —
so the comparison is never raw.

### Fields

| Field | Type | Stored | Required | Key Attributes |
|-------|------|--------|----------|----------------|
| `company_id` | Many2one(`res.company`) | Yes | No | default=env.company, index. **Empty means "applies to every company"** — that is how a shared category carries global rules (see `approval.request._rule_applies_to_company`) |
| `currency_id` | Many2one(`res.currency`) | Yes | **Yes** | default=env.company.currency_id. The currency the record's thresholds are expressed in |

### Key Methods

| Method | Purpose |
|--------|---------|
| `_convert_request_amount(request)` | Converts `request.amount` from `request.currency_id` into this record's `currency_id` before any threshold comparison. Rate date is `request.date` → `request.date_confirmed` → today; rate company is `request.company_id` → the record's → `env.company`. Identity short-circuit when the currencies match |
| `_intervals_overlap(bounds_a, bounds_b)` (static) | Half-open/closed-aware interval overlap, used by `approval.rule._check_auto_action_conflict` |

---

## mixin.approval.source (Abstract)

| Key | Value |
|-----|-------|
| Model | `mixin.approval.source` |
| File | `models/mixin_approval_source.py` |
| Type | AbstractModel, inherited by `mixin.approval` and `mixin.approval.subjects` |

What the engine asks of any record a request is raised for, whichever adopter shape it takes. The step pool and the approver's activity check `isinstance(record, mixin.approval.source)`, so a subject record narrows its steps and chooses its activity exactly as a document does.

### Hooks

| Method | Purpose |
|--------|---------|
| `_filter_approval_step_user_ids(step, user_ids)` | **Override**: of the users a step would let decide this document, the ones its own policy lets decide it; the default keeps them all. Staging, the snapshot, the quorum check at confirmation, the later-step check and the approval button all read the narrowed pool, so a user the document would veto holds no row |
| `_get_approval_activity_type(approver, step_type)` | **Override**: the activity type `approver` is asked with on this document; the step's by default. `approval.approver._get_activity_type()` asks it for every activity the engine creates and every escalation reminder; activities are found, retired and reassigned by `approver_id`, never by type. hr_holidays answers from its state |
| `_get_approval_activity_values(approver)` | **Override**: values of the record's own for the activity asking `approver`, merged in by `approval.approver._get_source_activity_values()` when the category asks on the record; nothing reaches an activity kept on the request. website_slides puts the requesting partner there, so its Grant / Refuse buttons keep rendering |

---

## mixin.approval (Abstract)

| Key | Value |
|-----|-------|
| Model | `mixin.approval` |
| File | `models/mixin_approval.py` |
| Type | AbstractModel |

### Fields

| Field | Type | Stored | Required | Key Attributes |
|-------|------|--------|----------|----------------|
| `approval_request_id` | Many2one(`approval.request`) | Yes | No | copy=False, readonly, index, tracking |
| `approval_state` | Selection | Yes | No | related, store (new/pending/approved/refused/cancelled) |
| `date_approval_granted` | Datetime | Yes | No | related, store, tracking |
| `approval_progress` | Float | No | No | related |
| `pending_approver_ids` | Many2many(`res.users`) | No | No | related |
| `date_approval_requested` | Datetime | Yes | No | related (=date_confirmed), store, tracking |
| `approval_user_ids` | Many2many(`res.users`) | No | No | related |
| `approval_required` | Boolean | No | No | compute (memoised per domain+company) |
| `can_request_approval` | Boolean | No | No | compute |

### Key Methods (Override Points)

| Method | Purpose |
|--------|---------|
| `action_create_approval_request()` | Create + submit approval request, link bidirectionally |
| `action_refuse_approval()` | Reverse cascade: parent cancelled → `_refuse_cascade()` on the linked request |
| `action_view_approval_request()` | Open the linked request form |
| `_clear_refused_approval_link()` | Release a refused/cancelled link so a reopened document can request a fresh approval |
| `_get_domain_approval_category()` | **Override**: domain to find category |
| `_get_fields_approval_required()` | **Override**: required fields before approval |
| `_get_approval_request_name()` | **Override**: customize request name |
| `_prepare_approval_request_values()` | **Override**: customize request creation values. Honours `approval_binding_for` = (model, id, binding) in context, only when it names this record, so a binding-raised request knows its operation and a nested document cannot inherit the link |
| `_on_approval_state_changed()` | **Dispatcher — do NOT override.** Routes to `_on_approval_approved` / `_on_approval_refused` / `_on_approval_cancelled` / `_on_approval_revoked` / `_on_approval_reset`. Base posts a chatter note per state; for the `pending` revocation it also schedules a To-Do for the responsible user on activity-enabled models. See conventions.md |
| `_find_approval_category()` | The lookup that never raises: candidates by domain + company, first `_is_applicable_for`, then the fallback. What `_compute_approval_required` reads |
| `_get_approval_category()` | Find matching category (uses domain + company). Owns the whole selection algorithm; supply `_get_domain_approval_category()`, `approval.category._is_applicable_for()`, `_get_approval_category_fallback()` and the two `_raise_*` hooks instead of overriding it |
| `_approval_side_effect(failure_note)` | Context manager wrapping any document-advancing call made from a hook: savepoint + `UserError`/`ValidationError` catch + chatter note. Hooks run inside the approver's transaction — do not hand-roll this |
| `_approval_decider_names(state)` | The filter-and-join over `approver_ids` that opens a decision message |
| `write()` / `_get_fields_approval_protected()` | Freezes the listed source-document fields while an approval is in flight |
| `unlink()` | Blocks deleting a document with a live approval |
| `_check_can_request_approval()` / `_compute_can_request_approval()` | Gate on the "Request Approval" button |
| `_before_approval_request_submit(approval)` | Hook between request creation and auto-confirm |
| `_get_approval_submitted_action()` / `_get_approval_request_view_action()` | Client actions returned after submit / when opening the request |

### Submission Rate Limiting

`_approval_rate_limit_exceeded(*, hours, max_count, max_amount,
under_threshold_amount, excluded_states=("cancel",))` answers "has this
document's creator filed too many, or too much, in the last `hours`?" —
a satellite calls it from its own approval-required predicate
(approval_purchase, approval_sale).

It is **multi-currency by construction**: the caller's thresholds are
expressed in company currency, and the method converts
`under_threshold_amount` into each counterparty currency present in the
window before comparing, rather than summing mixed-currency totals. The
window is scoped to `(company_id, create_uid, create_date >= now - hours,
state not in excluded_states)` and excludes the record itself. Rate date
comes from `_approval_rate_limit_rate_date()` (override to pin it).
Covered by `test_approval/tests/test_rate_limit.py`.

---

## mixin.approval.state.sync (Abstract)

| Attribute | Value |
|---|---|
| Model | `mixin.approval.state.sync` |
| File | `models/mixin_approval_state_sync.py` |
| Inherits | `mixin.approval` |
| Class attribute | `_approval_request_follows_document = True`, read by `approval.request._check_moved_from_source_document()` |

For a document that keeps its own lifecycle and lets the engine record who decided which step. The opposite
pattern, a document the engine moves through `_on_approval_approved` and friends, stays plain `mixin.approval`.

### Adopter hooks

| Hook | Contract |
|---|---|
| `_get_approval_sync_state_field()` | The document's state field. Default `state` |
| `_get_approval_sync_kinds()` | Each value of that field mapped to a kind: `pending`, `progress` (a first step approved), `approved`, `refused`, `cancelled` or `draft`. Required |
| `_check_approval_sync_policy(kind)` | The document's own authority, run as the acting user before a request-side decision is applied. Raises to veto |
| `_apply_approval_sync_outcome(kind)` | Moves the document for a kind, through the document's overridable methods. Required |
| `_get_approval_category_xmlid()` | Optional: the category the document's requests belong to |
| `_is_approval_request_required()` | Whether a pending document raises a request: its state is `pending` and `_can_raise_approval_request()` holds |
| `_can_raise_approval_request()` | Whether the document may hold a request at all, whatever its state: none yet, and a category applies. Adopters add their own exclusions here, so they reach a backfilled document in progress too |
| `_get_legacy_approval_activity_xmlids()` | The review activities the document scheduled itself before adopting the engine, which a backfilled request replaces. Default none |
| `_get_approval_backfill_decider()` | Who decided the first step of a document in progress before its request existed. Default nobody |

### Behaviour

| Method | What it does |
|---|---|
| `create()` / `_create_approval_requests()` | Raises a request for a document created in a `pending` state. The superuser uid and `import_file` raise none; a user's `sudo()` keeps their uid and still does |
| `write()` | When the state field moves: a document without a request that enters `pending` raises one; one with a request is brought in line by `_sync_approval_request()`, unless its request is already being synced (`approval_state_sync` context) |
| `_sync_approval_request()` | `pending` restarts the request (reset + confirm). `draft` resets it. `progress` records the acting user's decision on the open step. `approved` records their decision when they hold a decidable row, else `_approve_without_decision`. `refused` / `cancelled` revoke an approved request, record a pending refusal as the user's decision when they hold a pending row, else force the terminal state. A refusal hands the request the `approval_refusal_note` context value as its `refusal_note`, whichever of the three it takes; a cancellation carries none |
| `_on_approval_progress/approved/refused/cancelled()` | A decision taken on the request itself: checks `_check_approval_sync_policy` (skipped for the superuser, and for an engine cancellation, which is not a decision), then applies the outcome under the sync context. Skipped when the document is already in that kind |
| `_on_approval_reset/revoked()` | Silent while syncing, otherwise `mixin.approval`'s messages |
| `unlink()` | Cancels a pending request before the document goes |
| `_backfill_approval_requests()` | For an upgrade, run as the superuser whom `_create_approval_requests` skips. Each document whose state is `pending` or `progress`, that may raise a request and can request approval, first loses its legacy review activities, which `approval.approver._create_activity` would not count as asking the same approver, then gets its request. A document in progress then has its decider's approval recorded for the open step alone, under the sync context, or, when the decider holds no row, keeps the step open with a note. Returns the documents backfilled |

Covered by `test_approval/tests/test_state_sync.py` against `approval.test.synced.document`, and by the
hr_holidays engine tests; the backfill by `test_approval/tests/test_state_sync_backfill.py` and hr_holidays' 1.9 post-migrate tests.

---

## approval.refusal.reason

| Key | Value |
|-----|-------|
| Model | `approval.refusal.reason` |
| File | `models/approval_refusal_reason.py` |
| Type | Model |
| Inherits | `mixin.catalog` (`name` required+translate, `active`); `_name_src_uniq` rescoped to `company_id` |
| Order | `sequence, name` |
| Multi-company | Yes (`_check_company_auto`) |

### Fields

| Field | Type | Stored | Required | Key Attributes |
|-------|------|--------|----------|----------------|
| `company_id` | Many2one(`res.company`) | Yes | No | default=False, index |
| `name` | Char | Yes | Yes | translate |
| `active` | Boolean | Yes | No | default=True |
| `sequence` | Integer | Yes | No | default=10 |
| `description` | Text | Yes | No | translate |
| `category_ids` | Many2many(`approval.category`) | Yes | No | check_company |
| `usage_count` | Integer | No | No | compute |

System reasons shipped in data: `refusal_reason_parent_cancelled` (cascade
refusals), `refusal_reason_auto_rule` (auto-refuse rules),
`refusal_reason_data_migration`.

---

## approval.rule

| Key | Value |
|-----|-------|
| Model | `approval.rule` |
| File | `models/approval_rule.py` |
| Type | Model |
| Inherits | `mixin.approval.threshold` (supplies `company_id` + `currency_id`), `mixin.approval.domain` (parses and path-checks `subject_domain`) |
| Order | `category_id, sequence, id` |

### Fields

| Field | Type | Stored | Required | Key Attributes |
|-------|------|--------|----------|----------------|
| `name` | Char | Yes | Yes | |
| `active` | Boolean | Yes | No | default=True |
| `sequence` | Integer | Yes | No | default=10 |
| `company_id` | Many2one(`res.company`) | Yes | No | from `mixin.approval.threshold`; empty = every company |
| `currency_id` | Many2one(`res.currency`) | Yes | **Yes** | from `mixin.approval.threshold`; `threshold` is expressed in it |
| `category_id` | Many2one(`approval.category`) | Yes | Yes | ondelete=cascade, index |
| `condition_type` | Selection(threshold/domain/field_selection) | Yes | **Yes** | default="threshold". `threshold` compares a normalized figure on the request; `domain` and `field_selection` read the SOURCE DOCUMENT through `request.get_source_document()`, so a request with no source document, a deleted one, or one of another model never matches them |
| `condition_field` | Selection(amount/quantity/date_range_days/priority) | Yes | No | required by `_check_condition_shape` for `threshold` rules only |
| `operator` | Selection(gt/gte/lt/lte/eq/neq/between) | Yes | No | string="Comparison"; required for `threshold` rules only |
| `threshold` | Float | Yes | No | `threshold` rules only. The lower bound (inclusive) when `operator` is `between`; for `priority`, 0=Low 1=Normal 2=High 3=Urgent |
| `threshold_max` | Float | Yes | No | `between` only: the upper bound, EXCLUSIVE. 0 means unlimited |
| `subject_model_id` | Many2one(`ir.model`) | Yes | No | ondelete=cascade. Required for `domain` and `field_selection`: the model the condition reads |
| `subject_model_name` | Char | No | No | related `subject_model_id.model`. The domain editor in the form reads its fields from it: the widget takes a model name, and handed the many2one it crashed the form |
| `subject_domain` | Char | Yes | No | `domain` rules: evaluated with `filtered_domain` against the source document; every dotted path is walked against the registry at save time |
| `subject_field` | Char | Yes | No | `field_selection` rules: the field on the source model |
| `subject_value` | Char | Yes | No | `field_selection` rules: compared as text against the raw value — a Selection's key, a Many2one's id |
| `action_type` | Selection(auto_approve/auto_refuse/condition) | Yes | Yes | default="condition". `condition` does nothing by itself: steps apply by it (`when_rule_ids`, `unless_rule_ids`), and while one does the rule can be neither archived, deleted nor given another action (`_check_no_step_reads_it`). Rules that added or replaced approvers were retired in 19.0.2.8.0: a step names the approvers and applies by a condition |

### Constraints

- `_name_category_uniq`: unique nulls not distinct (name, category_id, company_id)
- `_check_range_bounds`: `threshold` rules with `between` only — the upper bound exceeds the lower one, or is 0 for unlimited
- `_check_threshold`: `threshold` rules only — a `priority` threshold is one of 0, 1, 2, 3
- `_check_condition_shape`: a `threshold` rule needs `condition_field` and `operator`; any other type needs `subject_model_id`, and every path its `subject_domain` or `subject_field` names must exist on that model. Refused at save time because a rule that never matches reads as "approval was not required"

### Key Methods

| Method | Purpose |
|--------|---------|
| `_evaluate(request)` | Dispatches on `condition_type` and is the only entry point |
| `_get_subject(request)` | The source document, or False when it is absent, deleted, or not of `subject_model_id` |
| `_evaluate_domain(request)` / `_evaluate_field_selection(request)` | The two source-document condition types |
| `_get_field_value(request)` | Extract numeric value using match/case; `amount` goes through `_convert_request_amount()` so the comparison happens in the rule's currency |
| `_compare(value, threshold)` | Apply operator |

---

## mixin.approval.subjects (Abstract)

| Key | Value |
|-----|-------|
| Model | `mixin.approval.subjects` |
| File | `models/mixin_approval_subjects.py` |
| Inherits | `mixin.approval.source` |

For a record that holds one request per subject rather than one in all: a course takes access requests from many partners, an engineering change raises one for each stage it passes. The request carries its subject in `subject_key`; only one request per subject is waiting at a time.

### Fields

| Field | Type | Stored | Required | Key Attributes |
|-------|------|--------|----------|----------------|
| `approval_request_ids` | One2many(`approval.request`) | No | No | inverse `res_id`, domain `res_model` = the record's model and `subject_key` set; readonly |

### Adopter hooks

| Hook | Contract |
|------|----------|
| `_get_approval_subject_category(subject_key)` | The category a request for that subject belongs to. Required |
| `_prepare_approval_subject_request_values(subject_key, category)` | The request's values: name, category, owner (the current user), `res_model`/`res_id`, `subject_key`, the record's company |
| `_on_approval_subject_state_changed(request, new_state)` | A subject's request reached a terminal state, or was reset or revoked; the request says which subject |
| `_on_approval_subject_progress(request)` | A decision met a step of a subject's request, which is still pending |

### Behaviour

| Method | What it does |
|--------|--------------|
| `_raise_approval_request(subject_key)` | Raises and submits the request as the current user (the request is created under `sudo`, keeping the uid). Refused while a request for that subject is new or pending |
| `_get_approval_request(subject_key)` / `_get_live_approval_request(subject_key)` | The latest request for the subject, and that request only while it is new or pending |

`approval.request._get_notifiable_source_document()` tells such a record only about a request that carries a `subject_key`; a request pointed at the record without one reaches nothing, as a `mixin.approval` document is told only about the request it references. Covered by `test_approval/tests/test_approval_subjects.py` against `approval.test.subject.document`.

---

## mixin.approval.gate (Abstract)

| Key | Value |
|-----|-------|
| Model | `mixin.approval.gate` |
| File | `models/mixin_approval_gate.py` |
| Inherits | `mixin.approval` |

For a document that gates its own terminal transitions — confirming, posting, validating — without owning a `mixin.lifecycle` state machine. The adopter declares `_approval_operations` (the gated methods) and, through the registry's `_operation_checkpoints`, where each one's validations live.

| Method | What it does |
|--------|--------------|
| `_run_through_approval(operation, run)` | Splits the records, calls `run(ready)` on what needs no approval or already holds it, raises a request for the rest (one record: returns that request's action), and carries the run's own action as the notification's `next` |
| `_split_for_approval(operation)` | ready / needs-approval. A waiting request always refuses; a refused or cancelled one refuses while the document still requires approval; an approved one is checked by `_check_approval_covers` |
| `_approval_request_gates(operation)` | Whether the linked request was raised for this operation. A grant clears the operation it was asked for and no other |
| `_check_approval_covers(operation)` | Hook: raises when the grant no longer covers what the operation would do |
| `_check_approval_admits(operation)` | Called from the operation's checkpoint, so a caller that did not come through the gate is caught. Records an `approval.observation` and refuses only once `approval.gate_enforced` is set |
| `_is_operation_run_on_approval(operation)` / `_run_operation_on_approval()` | Whether a grant re-enters the transition, and the re-entry itself: once, as superuser, through the gated method so its validations run again |
| `_refuse_pending_approval()` | Refuses a waiting request, for an adopter's cancel path |

Adopted by `mixin.approval.lifecycle`. Covered by `test_approval/tests/test_gate.py` against `approval.test.gated`.

---

## mixin.approval.lifecycle (Abstract)

| Key | Value |
|-----|-------|
| Model | `mixin.approval.lifecycle` |
| File | `models/mixin_approval_lifecycle.py` |
| Inherits | `mixin.approval.gate`, `mixin.lifecycle` |

For a document with a declared lifecycle whose confirmation is the approval gate. It is `mixin.approval.gate` with `_approval_operations = ("action_confirm",)`, so the split, the coverage check and the re-entry are the gate's; only the lifecycle's own wiring lives here. The adopter supplies `_get_domain_approval_category`; with no category matching, confirming is the plain lifecycle.

| Method | What it does |
|--------|--------------|
| `action_confirm` | Runs the confirm checks, then `_run_through_approval("action_confirm", ...)` |
| `_is_operation_run_on_approval` | A grant re-enters `action_confirm` while the document is still a draft |
| `action_cancel` | Cancels, then `_refuse_pending_approval`, so an adopter whose refusal callback cancels meets an already cancelled document |
| `action_draft` | Clears a refused or cancelled request's link, so confirming asks again |

An adopter that gains the mixin after its model's own `action_confirm` (sale and purchase orders in `approval_product`) sits below that method in the MRO. It overrides `action_confirm` to call `_run_through_approval` with its own `super()`, so nothing the order does on confirmation runs before the gate.

Adopted by `maintenance.order` and agromarin's `mixin.approval.document`. Covered by `maintenance`'s `TestMaintenanceOrderApproval`.

---

## mixin.approval.access (Abstract)

| Key | Value |
|-----|-------|
| Model | `mixin.approval.access` |
| File | `models/mixin_approval_access.py` |
| Inherits | `mixin.approval.subjects` |

For a record whose access a partner asks for: a course on invitation, a shared document or folder, a knowledge article. Each ask is a subject, `access:<partner>` or `access:<partner>:<role>`, so a view request and an edit request wait separately. The grant row stays the domain's (a course membership, a `document.access`, a `knowledge.article.member`); the decision is the engine's. There is no shared grant-row mixin, because the rows disagree on roles, expiry and what a row without a role means.

### Adopter hooks

| Hook | Contract |
|------|----------|
| `_access_approval_category` | Class attribute: the xmlid of the shipped category. Or override `_get_approval_subject_category` |
| `_has_access(partner, role)` | Whether the partner already holds the role. Required |
| `_grant_access(partner, role)` | Writes the grant when a request is approved. Required |
| `_get_access_request_name(partner, role)` | The request's name; "Access to <record> for <partner>" by default |

### Behaviour

| Method | What it does |
|--------|--------------|
| `_get_access_subject_key(partner, role)` / `_get_access_subject(subject_key)` | Encode and decode the subject; a key of another kind decodes to no partner |
| `_request_access(partner, role)` | Raises the request, refused when `_has_access` already holds or a request for that subject is waiting |
| `_get_live_access_request(partner, role)` | The waiting request for that subject, read under `sudo` |
| `_decide_access_request(partner, role, approve)` | A caller who can decide the request records a decision. Otherwise, a caller who may write the record approves without a decision or refuses by force. Anyone else gets an `AccessError`. Returns False when nothing is waiting |

`_on_approval_subject_state_changed` grants on `approved` and nothing else. Covered by `test_approval/tests/test_approval_access.py` against `approval.test.access.document`, and by `website_slides`' `TestCourseAccessRequest`.

---

## mixin.approval.domain (Abstract)

| Key | Value |
|-----|-------|
| Model | `mixin.approval.domain` |
| File | `models/mixin_approval_domain.py` |
| Type | AbstractModel |
| Inherited by | `approval.rule`, `approval.binding`, `approval.category.step` |

Parsing and configuration-time checking of a domain evaluated against a
source document rather than the request. Both inheritors let a user type such
a domain. One naming a field nobody has never matches, and a rule or binding
that never matches reads as "approval was not required" rather than as a
broken configuration — so the paths are walked when the record is saved, not
when a decision depends on them.

### Key Methods

| Method | Purpose |
|--------|---------|
| `_domain_source_field()` | Abstract: the Char field holding the domain (`subject_domain` on both inheritors) |
| `_parse_domain(field_name=None)` / `_parse_domain_or_warn(field_name=None)` | `ast.literal_eval` into a `Domain`, or None; the second logs the unparseable value. `field_name` defaults to `_domain_source_field()`, and a binding passes `reset_domain` |
| `_check_domain_against_model(model, field_name=None)` | Raises unless the domain parses and every path in it exists |
| `_check_field_path(model, path)` | Walks a dotted path across relational fields |

---

## approval.binding

| Key | Value |
|-----|-------|
| Model | `approval.binding` |
| File | `models/approval_binding.py` |
| Type | Model |
| Inherits | `mixin.approval.domain` |
| Order | `model_name, method, sequence, id` |

Gates a method on an approval — the opposite direction to `mixin.approval`,
which waits for the document to ask. The operation is intercepted and the
approval consulted before it runs, for every caller rather than only the user
interface. `_register_hook` wraps each gated method ONCE per (model, method),
and the wrapper resolves every binding on it at call time. It is the mechanism
`web_studio`'s approval rules use, without their two defects: an unconditional
`sudo()` bypass, and patches that do not compose.

Kill switch: `ir.config_parameter` `approval.binding_enabled`.

### Fields

| Field | Type | Stored | Required | Key Attributes |
|-------|------|--------|----------|----------------|
| `name` | Char | Yes | No | computed from model, method and mode |
| `sequence` | Integer | Yes | No | default=10 |
| `active` | Boolean | Yes | No | default=True |
| `model_id` | Many2one(`ir.model`) | Yes | **Yes** | ondelete=cascade, index |
| `model_name` | Char | Yes | No | related `model_id.model`, index — the lookup key |
| `method` | Char | Yes | **Yes** | refused if `automation` claims it, if it is the ORM's own API, if it is private outside module data, if it does not exist, or if it is the binding machinery |
| `category_id` | Many2one(`approval.category`) | Yes | No | ondelete=cascade. Required for `block` and `request` |
| `subject_domain` | Char | Yes | No | string="Applies When"; empty means every record |
| `mode` | Selection(advise/block/request) | Yes | **Yes** | default="advise". `advise` (labelled Observe) runs the operation and records it; `block` refuses unless an approved request covers the record; `request` raises the approval instead of running — and, with `run_on_approval`, runs the operation exactly once when it is approved, as the person who called it |
| `sudo_policy` | Selection(enforce/superuser/bypass) | Yes | **Yes** | default="superuser". Who the gate does NOT apply to. `sudo()` flips `su` and keeps `uid`, so the real superuser and an ordinary user elevated by `sudo()` are separate risks and separate settings |
| `observation_ids` | One2many(`approval.observation`) | — | No | |
| `observation_count` | Count | — | No | |
| `elevated_count` | Integer | No | No | computed by one grouped read over observations |
| `self_elevated_count` | Integer | No | No | same read; callers elevated by `sudo()`, not the superuser |
| `approve_on_invoke` | Boolean | Yes | No | `request` mode only. When somebody who may approve a pending step calls the operation, the call records their approval — the way a Studio approval button works — and the operation runs if nothing is left; otherwise the remaining approvers are asked and the call waits |
| `run_on_approval` | Boolean | Yes | No | default=True, `request` mode only. Run the operation once, as the requester, when the request is approved. Off, approval only clears the gate and the operation runs on the next call — how Studio approvals behave. Off also lifts the zero-argument limit, since there is no replay to feed |
| `action_id` | Many2one(`ir.actions.actions`) | Yes | No | ondelete=cascade. The action to gate instead of a method; a binding gates exactly one of the two |
| `is_enforced` | Boolean | No | No | computed. True for a method, a server action or a report; False for a window or client action, which only opens a view — nothing the server can intercept, so only the client's check stands in the way |
| `reset_domain` | Char | Yes | No | string="Reset When". Domain on the gated model; when a covered record comes to match it, the approval that covered it is reset to draft. Fires on the transition INTO the condition only *(added by `approval_automation`)* |
| `reset_automation_id` | Many2one(`automation.rule`) | Yes | No | readonly, copy=False, ondelete=set null. The managed rule that keeps Reset When in effect *(added by `approval_automation`)* |

### Constraints

- `_model_method_domain_uniq`: unique nulls not distinct (model_id, method, subject_domain)
- `_check_binding`: the model is in the registry; the method passes `_check_method_available`; the domain passes `_check_domain_against_model`; `block` and `request` have a category; `request` passes `_check_method_replayable`
- `_check_method_available`: refuses `AUTOMATION_CLAIMED_METHODS` — `create`, `write`, `unlink`, `_compute_field_value`, `_onchange_methods__`, `message_post`. `automation._unregister_hook` does `delattr(Model, name)` for each across the whole registry without checking who installed it, so a gate there would disappear silently rather than fail
- `_check_method_replayable`: with `run_on_approval` on, `request` mode only gates a method taking nothing but `self`. The signature is read with `annotationlib.Format.FORWARDREF`: nine `res.partner` methods annotate with names their module never imports, and the default reading raises `NameError` on 3.14. Replaying stored arguments would have to guess at stale recordsets and closures, so the limit is enforced up front; with it off nothing is replayed and any method may be gated
- `_get_method_refusal(method)`: refuses every name `BaseModel` defines, dunders included, except the lifecycle actions in `ORM_LIFECYCLE_ACTIONS` (`action_archive`, `action_unarchive`, `toggle_active`). The gate calls the ORM's API itself (`browse`, `filtered_domain`, `sudo`), so wrapping one recurses or breaks the model; an Observe binding on `__setattr__` broke building any partner in the process.
- `_check_private_method_from_module_data` (fires on `model_id` and `method` only): a private method is accepted only with `install_module` in the context, which is to say from module data. Editing any other field of such a binding from the interface is unaffected.
- `approve_on_invoke` needs `request` mode: Block mode raises no request for the caller to approve
- A binding gates exactly one of `method` and `action_id`; the uniqueness constraint covers (model_id, method, action_id, subject_domain), so two actions on one model can each be bound
- With `run_on_approval` in `request` mode, only a method or a server action can be run again; a window, client or report action needs it off
- `reset_domain`, when set, must name paths that exist on the gated model *(added by `approval_automation`)*

### Key Methods

| Method | Purpose |
|--------|---------|
| `_register_hook()` / `_unregister_hook()` | Wrap each gated (model, method) once, skipping and logging a stored binding `_get_method_refusal` refuses; unwrap only attributes carrying the `approval_binding_origin` marker |
| `_get_guarded_method(model, method)` | The method wrapper. Resolves the bindings on (model, method) and hands the call to `_gate` |
| `_gate(records, bindings, label, call)` | The one routine behind a wrapped method, a gated server action and a gated report. Measures the CALLER's elevation once, applies every binding whose domain selects the record, and inserts every observation in one statement. Records that need no approval — or that an invoking caller's own approval just covered — are passed to `call` and stamped; the rest wait, and the requests action is returned |
| `_bindings_for_action(action_id)` / `_get_action_binding_ids(action_id)` | The bindings on one action, `ormcache`d with `active_test` forced, like the method lookup |
| `_check_action_available()` | A server action must run on the binding's model, and a report must print it; a report cannot be in `request` mode, because refusing to render rolls back the request that would have asked |
| `_run_action_on(records)` | Replays a server action on `records`, in their environment, with `active_model` / `active_ids` set — through `run()`, so the gate still applies |
| `_get_selected(records)` | The records the binding's domain selects, in one `filtered_domain` over the whole recordset |
| `_get_covered_ids(records)` | The records an approval already stands for, in one pass. An adopter's own approved request is taken as it is — the mixin protects the fields approvers decide on and owns withdrawal. Any other record is covered by an approved request pointing at it in the binding's category, and, when this binding raised it, only while `binding_snapshot` still matches |
| `_get_snapshot(record)` | The values the domain's paths read from the record now. No domain reads nothing, so its approval covers the operation whatever the record's state |
| `_enforce(record, elevation, observations, covered_ids)` | One binding on one record. `elevation` is passed in rather than read from `self.env`: the binding is read through `sudo()`, so its own env reports every caller as elevated — which, under `bypass`, let an ordinary user straight through a Block gate |
| `_elevation()` | `none`, `superuser` (uid is SUPERUSER_ID) or `self_elevated` |
| `_bindings_for(model, method)` / `_get_binding_ids(model, method)` | `ormcache`d per (model, method). Runs under sudo with `active_test` forced, because neither uid nor context is part of the key |
| `_apply_to_registry()` | On create and write. Clears the lookup cache, which is signalled to every worker; only a binding on a method nothing wraps yet re-registers and invalidates the registry |
| `_raise_requests_for(records)` | `request` mode, per binding; returns the requests, and the wrapper builds the action. An adopter asks through its own `action_create_approval_request` with `approval_binding_for` in context; anything else gets a request pointed at it by `res_model`/`res_id`, carrying `binding_snapshot`. A request still open for the record is reused, never raised twice — and one reset to draft is confirmed again, with a fresh snapshot |
| `_approve_on_invoke(requests)` | Records the caller's approval on every pending step they may decide. Runs with `approval_binding_invoking` in context, so a request this completes is NOT replayed: the call already running performs the operation, and a replay would perform it a second time. A refused approval leaves the request pending with its approvers asked |
| `_mark_invoked_run(records)` | Stamps `date_binding_replayed` on the approved requests an invoking call just ran, so a later withdrawal and re-approval cannot run the operation again |
| `_replay(request)` | Runs the method once after approval, as `request_owner_id` — never the approver, never under sudo, so an approval cannot lend the approver's rights (the superuser account keeps its `su`). Re-checks coverage first, so a record whose snapshot moved is not run. A `UserError` (including access, validation and missing-record errors) is recorded in `binding_replay_error` and the approval stands; anything else propagates. Runs with `approval_binding_replay` in context, under which the wrapper refuses rather than raising a new request |
| `_sync_reset_automation()` | One managed `on_create_or_write` rule per binding with a Reset When. Its pre-update filter is the condition inverted, so it fires on the transition into it. After creation only the name, the two filters and the trigger fields are written: never `trigger`, whose change makes `_compute_filter_pre_domain` clear the pre-update filter, and never `model_id`, whose write recomputes `trigger` to nothing. A changed model gets a new rule *(added by `approval_automation`)* |
| `_reset_coverage(records)` | Resets to draft every request `_get_requests_holding_decisions` returns: an approved one through `action_reset_to_draft`, so an adopter hears it through `_on_approval_reset`; a waiting one, locked first, through `_force_draft`, so a decision given for the document's earlier state does not survive. Clears the one-shot stamp so the next cycle runs on approval again |
| `_get_covering_requests(records)` / `_get_reset_field_ids(domain)` *(added by `approval_automation`)* | The approved requests that could be covering the records; the fields the condition reads, which become the rule's trigger fields |
| `_get_requests_holding_decisions(records)` | What a reset clears: the covering approved requests, and the binding's waiting requests some approver has already decided in part |
| `get_button_approvals(specs)` | For each `{model, res_id, method, action_id}`: `{gated, approved, request, steps}`. Each step carries who may decide it (`approval.request._can_decide_step`: neither decided by the caller nor excluded by an exclusive step they decided) and its decisions, assigned by `approval.request._get_step_assignment`, so what the button draws is what the quorum counts. A category without steps is one step with `id` false. Read access on the record is checked first |
| `check_button_approval(model, res_id, method, action_id)` | `_gate` with a no-op operation: `{approved, request_id}`. It raises or reuses the request and marks the one-shot, because the browser runs the action next |
| `action_decide_approval(..., approve, step_id)` / `action_withdraw_decision(..., approver_id, step_id)` | Decide as the caller, for the step the button drew the control under (`_get_button_decision_steps` refuses a step of another button), or withdraw through `action_withdraw_approver` (a refusal through `action_reset_to_draft`); the rights are `_can_withdraw_approver` / `_can_reopen_refusal`, the same predicates the checks raise from, judged against the withdrawn step |
| `_get_checkpoint_guard(model, checkpoint, operations)` / `_enforce_at_checkpoint(records, bindings, operation)` | Operation checkpoints. A model that declares `_operation_checkpoints = {operation: private_hook}` (`account.move`: `action_post` -> `_post_check_business_rules`) has the hook wrapped too, so a binding on the operation holds on every path that crosses it. The paths that never reach the operation's own wrapper get Block semantics: a checkpoint can neither ask for an approval nor keep a request, so a record Block or Request mode would stop is refused there |
| `_admit(records, operation)` / `_get_admitted_ids(records, operation)` | The operation's wrapper marks the records it lets through, as (model, operation, ids) in `approval_binding_admitted`; their checkpoint does not check them again. Records the admitted call touches on its own (a reversal a posting creates) are still checked |
| `create_step_for_button(model, method, action_id)` | Adds a step to a button; the first one binds the button in Studio's shape (Request, approve-on-invoke, run-on-approval off, a category that requests its steps in order). A step starts with the Internal User group and the gated model as subject model; its sequence is the last plus one, capped at 9 |
| `action_open_button_steps(model, method, action_id)` | A button's steps as a kanban (then list and form), with a quick-create card -- the card Studio's rule kanban showed: name, exclusivity, group, order, approvers |
| `_has_anyone_to_ask()` | False when the category has no active step, no approver and no routing rule; `_get_selected` then selects nothing outside Observe mode, so a button whose steps are all archived is no longer gated |
| `_get_selected(records)` | The records a call is gated on: the binding's subject domain, then — outside Observe mode — only records some active step of the category applies to, so a record no step applies to runs ungated (Studio's `test_03`) |
| `_check_target_unchanged_once_requested(vals)` | `write` refuses to change `model_id`, `method` or `action_id` once the binding has requests: the decisions on them were given for that target |

---

## approval.observation

| Key | Value |
|-----|-------|
| Model | `approval.observation` |
| File | `models/approval_observation.py` |
| Type | Model |
| Order | `id desc` |

One row per gated call let through while its gate was only watching: written by
an Observe binding, by any binding whose `sudo_policy` let an elevated caller
pass, and by `mixin.approval.gate` when a call reaches a terminal transition by
a path the gate does not own and `approval.gate_enforced` is not set.
Append-only on purpose: a counter on the binding would contend for one row lock
on every gated call, and the question the table answers needs the breakdown
rather than a total.

**Reading it is the point.** Both gates are meant to be sized before they are
switched on, so the table has its own screen: *Settings > Technical > Approvals
> Watched Calls* (`action_approval_observation`), which opens filtered to
`would_block` and grouped by model and operation. Those rows are what
enforcement would begin refusing. Rows with no `binding_id` come from a code
gate and are switched on through `approval.gate` rather than a binding's mode;
the search view separates the two.

### Fields

| Field | Type | Stored | Required | Key Attributes |
|-------|------|--------|----------|----------------|
| `binding_id` | Many2one(`approval.binding`) | Yes | No | ondelete=cascade, index=btree_not_null. Empty for a gate a model declares in code |
| `model_name` | Char | Yes | **Yes** | index. The gated model |
| `operation` | Char | Yes | **Yes** | index. The gated method the call was reaching |
| `res_id` | Integer | Yes | No | index |
| `user_id` | Many2one(`res.users`) | Yes | No | the caller's uid, which `sudo()` preserves |
| `elevation` | Selection(none/superuser/self_elevated) | Yes | **Yes** | index |
| `would_block` | Boolean | Yes | No | whether Block would have refused this call — the number that sizes switching a binding on |
| `date` | Datetime | Yes | No | default=now, index |

---

## approval.gate

| Key | Value |
|-----|-------|
| Model | `approval.gate` |
| File | `models/approval_gate.py` |
| Type | Model |
| Order | `model_name, operation` |

One row per terminal transition a model gates in its own code -- the configured
twin of `approval.binding`. A binding exists because a person decided to gate a
method; a gate exists because a model declares `_approval_operations`, so
**nobody creates these**. `_register_hook` calls `_sync_declared_gates`, which
walks the registry, adds a row for each declared operation and deletes any row
whose operation the model no longer declares. A new adopter therefore appears
the next time the registry is built, without a data file.

An operation earns a row only where the model also names it in
`_operation_checkpoints`. `_check_approval_admits` is called from that checkpoint
and nowhere else, so without one enforcement has no path to close: the toggle
would govern nothing and the count beside it could never leave zero.
`mixin.approval.lifecycle` is the standing case -- it declares `action_confirm`
for every order-like document and names no checkpoint, so `sale.order`,
`purchase.order`, `maintenance.order` and `rma.order` have no row. The pairs left
out are named on `trace.REGISTRY` at each sync.

The only field a person may write is `enforced`, and that is the point: the row
is a place to put the decision the counts beside it inform. Enforcement is **per
operation**, so a gate whose watched calls cost nothing can be switched on while
an expensive one keeps watching. `mixin.approval.gate._is_approval_gate_enforced`
asks `_is_enforced`, which reads an `ormcache`d set cleared on every write here.

Supersedes `approval.gate_enforced`, the single system parameter 19.0.2.9.0
shipped with. `_adopt_legacy_enforcement` carries a `1` there onto every row and
deletes the parameter, so a database that was enforcing keeps enforcing. It runs
from the sync rather than from a migration because **no migration phase runs late
enough**: the gates cannot be discovered until every adopter is in the registry,
which is `_register_hook`, and end migrations run before that.

A document holds **one** `approval_request_id` at a time, so a model may declare
several gated operations but cannot have two of them waiting at once.

### Fields

| Field | Type | Stored | Required | Key Attributes |
|-------|------|--------|----------|----------------|
| `model_name` | Char | Yes | **Yes** | index, readonly. The gated model |
| `operation` | Char | Yes | **Yes** | index, readonly. The method the model declares as terminal |
| `model_id` | Many2one(`ir.model`) | No | No | compute, for display |
| `enforced` | Boolean | Yes | No | the one writable field: whether this operation refuses a bypassing caller yet |
| `would_block_count` | Integer | No | No | compute: the calls enforcement would refuse -- the cost of switching it on, and the only count a code gate can honestly offer, since it records a call it would have refused and no other |

Constraint: UNIQUE `(model_name, operation)`.

---

## approval.category.step

| Key | Value |
|-----|-------|
| Model | `approval.category.step` |
| File | `models/approval_category_step.py` |
| Type | Model |
| Inherits | `mixin.approval.threshold` (a numeric condition on the request's own figures), `mixin.approval.domain` (parses and path-checks `subject_domain` and `subject_user_path`) |
| Order | `category_id, sequence, id` |

One step of a category's approval: a pool of users, and how many of them must
approve. One approver list and one request-wide minimum cannot tell two steps that
each need one of two people from one step that needs two: a minimum of 2 accepts
both approvals from the first. That is exactly what a Studio approval rule is, and
since 19.0.2.8.0 every category routes by steps.

### Fields

| Field | Type | Stored | Required | Key Attributes |
|-------|------|--------|----------|----------------|
| `category_id` | Many2one(`approval.category`) | Yes | **Yes** | ondelete=cascade, index |
| `company_id` | Many2one(`res.company`) | Yes | No | related `category_id.company_id`; scopes the multi-company rule |
| `sequence` | Integer | Yes | No | default=10. The step's place in the order `notify_sequentially` asks in |
| `name` | Char | Yes | **Yes** | translate |
| `active` | Boolean | Yes | No | default=True |
| `minimum` | Integer | Yes | No | string="Approvals Needed", default=1. The step's quorum |
| `member_ids` | One2many(`approval.category.step.member`) | — | No | the step's named users |
| `group_id` | Many2one(`res.groups`) | Yes | No | its members join the pool too — the union Studio's `approver_ids` / `approval_group_id` pair expresses |
| `exclusive` | Boolean | Yes | No | an approval counting toward this step counts toward no other step of the request, and the other way round |
| `asks_group_members` | Boolean | Yes | No | Every user of `group_id` is asked (`_is_notifiable`). Off, the group is a queue and only listed members are asked |
| `counts_added_approvers` | Boolean | Yes | No | Approvers added by hand to a request (rows routing did not stage, `source_synced` False) join the step at sync: they are asked (`_is_notifiable`), may decide it, count toward its quorum, and count into its pool at confirm (`_check_steps_can_be_met`). Migration 2.8 set it on every step it built from an approver list, since the list counted them toward the minimum |
| `in_order` | Boolean | Yes | No | string="Members Decide in Order". Only the member whose turn it is (`approval.request._get_step_turn_row`: the first, by member `sequence`, whose row has not approved the step) is asked and may decide; `_check_step_turn` refuses the others and `_get_steps_for_decision` leaves the step out of their decision. The step's quorum ends the chain. Rows are ordered by member `sequence`, and an added approver by its own row `sequence`, as the approver list ordered them. A step is also unmet while a member marked `required` (`approval.category.step.member.required`) has not approved it (`_get_step_required_rows_pending`). The users an approver path names stand at `subject_user_sequence` in the order, and `subject_user_required` makes the step wait for them; `_check_in_order_pool` refuses a group on such a step, whose users have no place in the order |
| `advisory` | Boolean | Yes | No | The step's approvers are asked (its unmet advisory steps are open beside the lowest blocking step) and their decisions recorded, but it decides nothing: `_is_quorum_met` reads `_get_blocking_unmet_steps()`, a row refused only for advisory steps (`approval.approver._is_advisory_only()`) is no deciding refusal (`_get_deciding_refusals()`) and flips no other row, progress is reported for blocking steps only, and confirmation does not need an advisory step's pool. The ECO's optional and comment roles |
| `notify_user_ids` | Many2many(`res.users`) | Yes | No | posted an internal note when an approver of this step decides |
| `subject_model_id` | Many2one(`ir.model`) | Yes | No | the model the condition and the approver path read; required when `subject_domain` or `subject_user_path` is set. **`approval.request` means the request itself** (`_get_subject`): its domain and path read the request, so a request raised with no source document can still name approvers, as approval_hr names the requester's manager through `requester_manager_user_id`. The document's own approver policy still filters the pool |
| `subject_model_name` | Char | No | No | related `subject_model_id.model`. The domain editor in the form reads its fields from it: the widget takes a model name, and handed the many2one it crashed the form |
| `subject_domain` | Char | Yes | No | string="Applies When". The step applies only to requests whose source document matches |
| `condition_field` / `operator` / `threshold` / `threshold_max` / `currency_id` | Selection / Selection / Float / Float / Many2one | Yes | No | from `mixin.approval.threshold`. The step applies only when the request's amount (converted into `currency_id`), quantity, date range in days or priority compares true. Unlike `subject_domain` it needs no source document, which is what lets a threshold rule or a replacement band be written as a step |
| `when_rule_ids` / `unless_rule_ids` | Many2many(`approval.rule`) | Yes | No | The step applies only when every `when` rule matches and no `unless` rule does, as `approval.rule._evaluate` and the rule's company decide (`_matches_request_rules`). The conversion writes them for rule sets figure conditions cannot express |
| `subject_user_path` | Char | Yes | No | string="Approvers From". A field path on the source document ending in `res.users` (e.g. `employee_id.leave_manager_id`): each document names its own approvers, who join the step's members. What a time off manager is, and neither a listed member nor a group can say |
| `activity_type_id` | Many2one(`mail.activity.type`) | Yes | No | The activity this step's asked approvers get; empty uses `approval.mail_activity_data_approval` |
| `user_ids` | Many2many(`res.users`) | No | No | compute + inverse: the current members as an editable list; the inverse syncs plain members and leaves delegation rows (`delegated_by_id`) alone |
| `_get_member_user_ids(document, company)` / `_get_pool_user_ids(document, company)` | Listed members within their term plus the users the document names, who are asked; the pool adds the group's users, who may decide but are not asked. Given a company, both keep only users allowed in it (`_filter_company_user_ids`), since an approver row belongs to its request's company. Every caller passes the request's source document and company, or on the approval button the gated record and the company its request is (or would be) raised in. Past the company, the pool asks a record adopting `mixin.approval.source` to narrow it through `_filter_approval_step_user_ids` (`_filter_document_user_ids`), so no one holds a row the document's own policy would refuse. `_get_managed_approver_user_ids` alone reads `_get_candidate_user_ids(document)`, every user the step names before either narrowing, so a row whose user lost the company or the document's favour is still recognised as routing's own |
| `_unlink_except_step_holding_decisions()` | A step some approver row decided under cannot be deleted; archive it |
| `_check_pool()` | Fires on `user_ids` too, so an approvers list given without a group is checked after its inverse has created the members |

### Constraints

- `_check_pool`: a quorum of at least one, and members, a group or an approver path to give it
- `_check_source_user_path`: an approver path names its source model, every part of it exists there, and it ends in a field whose comodel is `res.users`
- `_check_condition`: a condition names its source model, and every path it reads exists there
- `_check_in_order_without_consent`: consent auto-approval approves every member at once, so a step whose members decide in order refuses it (and `approval.category._constrains_consent_sequential` refuses it from the category's side)
- `_check_in_order_pool`: a step whose members decide in order has no group
- `_check_figure_condition`: a figure condition has a comparison, and a `between` band's upper bound is above its lower one (or 0 for none)
- `_check_category_not_sequential`: the same refusal as `approval.category._constrains_steps_not_sequential`, from the step's side, since creating a step does not write the category

### Key Methods

| Method | Purpose |
|--------|---------|
| `_get_pool_user_ids(document, company)` | Who may approve today: members whose `date_end` has not passed, the active users `subject_user_path` resolves to on the document (read under `sudo`), plus the group's users -- of those, the ones whose `company_ids` include `company` when one is given, and whom the document keeps |
| `_get_candidate_user_ids(document)` | Members, path users and group users with neither the company nor the document narrowing them: the set routing owns rows for |
| `_filter_document_user_ids(user_ids, document)` | Hands the pool to `document._filter_approval_step_user_ids(step, user_ids)` (under `sudo`) when the record adopts `mixin.approval.source` (`mixin.approval` or `mixin.approval.subjects`); any other record, such as one gated by a binding button, keeps its pool |
| `_get_source_user_ids(document)` | The users the path names on this document; empty for another model, no document, or no path. Confirm refuses a step whose document names nobody through `_check_steps_can_be_met` |
| `_is_applicable_to_request(request)` | The figure condition first (`_matches_request_figure`), then the document condition: no document condition means every request; otherwise the request's source document must be of `subject_model_id` and match |

---

## approval.category.step.member

| Key | Value |
|-----|-------|
| Model | `approval.category.step.member` |
| File | `models/approval_category_step.py` |
| Type | Model |
| Order | `step_id, id` |

### Fields

| Field | Type | Stored | Required | Key Attributes |
|-------|------|--------|----------|----------------|
| `step_id` | Many2one(`approval.category.step`) | Yes | **Yes** | ondelete=cascade, index |
| `company_id` | Many2one(`res.company`) | Yes | No | related `step_id.company_id` |
| `user_id` | Many2one(`res.users`) | Yes | **Yes** | ondelete=cascade, index |
| `date_end` | Date | Yes | No | string="Valid Until". Empty means no end, so a delegation until a date is a membership with an end date |
| `delegated_by_id` | Many2one(`res.users`) | Yes | No | who handed over the right, when the membership is a delegation |

### SQL constraints

- `_step_user_uniq`: unique(step_id, user_id)

---

## approval.decision.wizard (Transient)

| Key | Value |
|-----|-------|
| Model | `approval.decision.wizard` |
| File | `wizards/approval_decision_wizard.py` |
| Type | TransientModel |

Captures the approver's input when **refusing** or **requesting a change**.
Approving is a 1-click action that never opens this wizard.

### Fields

| Field | Type | Key Attributes |
|-------|------|----------------|
| `approver_id` | Many2one(`approval.approver`) | required, readonly |
| `request_id` | Many2one(`approval.request`) | compute from approver_id, precompute, store, readonly, required |
| `user_id` | Many2one(`res.users`) | related |
| `decision_type` | Selection(refuse/change) | required, readonly |
| `refusal_reason_id` | Many2one(`approval.refusal.reason`) | required for refuse (validated in action) |
| `refusal_reason_description` | Text | related (read-only guidance banner) |
| `change_field` | Selection(date/reason) | field the requester must update |
| `note` | Text | optional on refuse; required on change |
| `request_name` | Char | related |
| `request_owner_id` | Many2one | related |
| `category_id` | Many2one | related |

### Key Methods

| Method | Purpose |
|--------|---------|
| `_stamp_refusal()` | Persist reason+note on the deciding approver row AND the request (canonical `refusal_reason_id`/`refusal_note`); the actor and state checks live in `_apply_decision` |
| `action_confirm_refuse()` | Require reason; single mode stamps and refuses `approver_id`'s request, batch mode (`request_ids`, from `action_refuse_bulk`) stamps and refuses each request under its own savepoint |
| `action_confirm_change()` | Require field+note; `action_request_change` sets `pending_change_field` and schedules the requester's change-request To-Do itself |
| `action_cancel()` | Close the wizard (no decision) |

---

## approval.delegate.wizard (Transient)

| Key | Value |
|-----|-------|
| Model | `approval.delegate.wizard` |
| File | `wizards/approval_delegate_wizard.py` |
| Type | TransientModel |

### Fields

| Field | Type | Key Attributes |
|-------|------|----------------|
| `user_id` | Many2one(`res.users`) | required, readonly, default=env.user |
| `delegate_id` | Many2one(`res.users`) | required |
| `start_date` | Date | required, default=today |
| `end_date` | Date | required |
| `apply_to` | Selection(pending/all_future) | required, default="pending" |
| `allowed_company_ids` | Many2many(`res.company`) | default=`env.companies`. The wizard's own copy of the active company set, so `delegate_id`'s domain can reference it. `approval.approver.delegate_id` is `check_company=True` and would reject a foreign delegate anyway — this leaf turns that into a filtered dropdown instead of a raw constraint error |
| `pending_count` | Integer | compute |
| `waiting_count` | Integer | compute |

### Key Methods

| Method | Purpose |
|--------|---------|
| `action_confirm()` | Apply delegation to matching approvers, notify delegate |

---

## The reporting models moved out at 19.0.2.0.0

`approval.metrics`, `approver.performance` and `approval.dashboard` now live in
`approval_analytics`, and `approval.binding.reset_domain` /
`reset_automation_id` in `approval_automation`. Both auto-install, so a database
that had them keeps them; the split exists so that a module adopting
`mixin.approval` does not take `mixin_report_sql` and the whole `automation`
closure with it. Read their fields in those modules.

---

## approval.decision.log

| Key | Value |
|-----|-------|
| Model | `approval.decision.log` |
| File | `models/approval_decision_log.py` |
| Order | `date desc, id desc` |
| Access | Approval managers read the model directly; everyone else reads a request's history through `approval.request.decision_log_ids` (`compute_sudo`), so whoever may read the request may read what was decided about it |

| Field | Type | Notes |
|-------|------|-------|
| `request_id` | Many2one(`approval.request`) | required, cascade |
| `approver_id` | Many2one(`approval.approver`) | the row the fact is about, if any |
| `step_ids` | Many2many(`approval.category.step`) | the steps a decision was given for, or withdrawn from |
| `verdict` | Selection | approved, refused, withdrawn, granted, revoked, cancelled, reset |
| `state_after` | Char | the request's state once the fact was applied |
| `user_id` | Many2one(`res.users`) | who acted |
| `principal_id` | Many2one(`res.users`) | the approver a delegate acted for |
| `elevation` | Selection | none, superuser, self_elevated |
| `refusal_reason_id` / `note` | | as given |
| `date` | Datetime | |

**Invariants.** Created only by `_append_decision_log`, which every funnel calls: `_apply_decision`, `action_withdraw`, `_withdraw_decided_steps`, `_force_draft` (before it clears the rows), `_force_terminal`, `_revoke`, `_approve_without_decision`, `_approve_for_every_step`, `_record_decision`, and the change-request resubmission. `write` and `unlink` raise for every caller, except a write to an empty recordset, which changes nothing.

**An approver's status is the ledger's, not the row's (19.0.2.7.0).** `approval.approver.state` is computed from the row's facts, so a row reads approved or refused only when a fact says so, and no write -- a server action, an import, adopter code, `sudo()` -- can make it read otherwise. Deciding without the approve/refuse actions goes through `_record_decision(verdict, actor, steps, date, note)`, which stamps the decision fields and appends the fact in one call: mrp_plm's import of a stage's history uses it, and tests that need a decided row without deciding it use `tests/common.record_approval`, which calls it. `_approve_for_every_step` (consent, automatic rules) appends its fact under the superuser with the rule or the consent window as the note, and a requested change applied to an approved request appends `withdrawn` for the rows it undoes. `state_after` is stamped once the facts' rows are flushed, so it reads the state they produced. Migration 2.7 filled `flow_state` from the old column and appended the facts the ledger never saw: an approved row, or a refused row carrying a `decision_date`, with no standing fact since its request's last reset.

**Separation of duties (19.0.2.1.0).** `approval.category.allow_self_approval`, mirrored on the request: when false, `_get_desired_approvers` never stages the request owner, on any routing path, and `_check_not_deciding_own_request` refuses a decision on a row whose effective approver is the owner -- checked before `_check_decision_actor`'s superuser return, so `sudo()` does not reopen it. Categories existing at the upgrade were migrated to allowing. The Studio editor's categories allow it by design: a button's approval restricts who may press, and the presser is the approver.

**Subject integrity (19.0.2.2.0).** After approval, a write that actually changes a field of `_get_fields_approval_protected()` -- compared value by value, x2many commands included -- sends the request back to draft through `_force_draft`, logged as a `reset` naming the fields, unless `_is_approval_invalidated_by_changes(fields)` says the document re-checks those fields itself. Applies to every caller; a request whose `_check_reset_allowed` refuses makes the write refuse instead. Context key `approval_keep_on_subject_change` skips it.

**Coverage integrity (19.0.2.1.0).** `mixin.approval` refuses writes to `approval_state`, `date_approval_granted` and `date_approval_requested` for every caller, and accepts an `approval_request_id` only for a request about the record itself, a subject-less request still in `new`, which the write binds to the record, or a request whose category's `target_model` is the record's model linking what it produced. The last is written inside `approval.request._link_produced_documents` (or its `_producing_documents` window), which is kept on the cursor so that no RPC caller can open it: pointing an order at an approved request that produces orders is refused. Re-writing the link a record already has is not checked.

---

## Extended Models

### ir.attachment (extended)

| File | `models/ir_attachment.py` |
|------|--------------------------|
| Hook | `_unlink_approved_approval_request()` via `@api.ondelete` |
| Rule | Blocks deletion of attachments on finalized requests |

### base (extended)

| | |
|------|--------------------------|
| File | `models/models.py` |
| Method | `get_views()` sets `has_approval_bindings` on each related model with an active Block or Request binding, read from `approval.binding._get_names_of_gated_models` (ormcache, cleared with every binding write) |

### mail.activity (extended)

| File | `models/mail_activity.py` |
|------|--------------------------|
| Fields | `approver_id` (stored Many2one, indexed, ondelete cascade: the row the activity asks, written by `approval.approver._create_activity`, the delegation wizard and escalation reminders), `approval_request_id` (compute from `approver_id`, searched through it) |
| Method | `_to_store_defaults()` adds approver state to Store |

`_action_done` asks `_get_answering_approvers` which rows the activities approve: an approval activity -- one with an `approver_id`, wherever it lives, on the request or on the document -- marked done by the user it was asked of approves that row through `approval.approver.action_approve`, provided that user is still the row's effective approver: after a delegation the delegator's old activity decides nothing. Anyone else, the system included, only dismisses it. The done runs first and the approval after it, both inside one savepoint: the feedback given with the activity is posted (approving first let the decision close the activity without it), and a decision that cannot be recorded raises and rolls the done back, so the activity stays open.

### mail.activity.type (extended)

| File | `models/mail_activity_type.py` |
|------|-------------------------------|
| Method | `_get_model_info_by_xmlid()` registers approval activity type |

### res.groups (extended)

| File | `models/res_groups.py` |
|------|------------------------|
| Method | `write()` — when `user_ids`, `implied_ids` or `all_user_ids` move, calls `approval.request._invalidate_escalation_manager_cache()` |
| Why | The default escalation manager is memoised per (transaction, company) by group membership. Membership can change from the GROUP side, which no `res.users` hook sees, and the memo would then hand escalations to someone who no longer holds the privilege |

### res.users (extended)

| File | `models/res_users.py` |
|------|-----------------------|
| Methods | `_is_approval_manager()` — the manager seam every access check goes through (`approval_utils.is_approval_manager`); `write()` — drops the delegation tz-bucket memo on a `tz` change, the escalation-manager memo on `group_ids`/`active`, and triggers the archive handover; `_approval_handover_on_archive()` — SM-7, reassigns the archived user's live `pending`/`waiting` rows (see architecture.md, *Departure Handover*) |
