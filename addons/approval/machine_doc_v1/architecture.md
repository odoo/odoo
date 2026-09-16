# Approval Architecture

## Subsystem Overview

```
+----------------------------------------------------------------------+
|                        approval.category                             |
|  Blueprint: field visibility, approval minimums, escalation, SLA,    |
|  privacy visibility (read audience)                                  |
|  approver_ids  rule_ids  step_ids                                    |
+----+----------------+-----------+------------------------------------+
     |                |           |
     v                v           v
+----------+  +-----------+  +-----------+
| category.|  | approval. |  | approval. |
| approver |  | rule      |  | template  |
| (user,   |  | (amount/  |  | (condition|
|  seq,    |  |  quantity |  |  + action)|
|  required|  |  ranges)  |  |           |
+----------+  +-----+-----+  +-----+-----+
     |              |              |
     |              +------+-------+
     |                     v
     |         +------------------------+
     |         | approval.threshold.    |
     |         |   mixin (Abstract)     |
     |         | company_id (empty =    |
     |         |   every company)       |
     |         | currency_id (required) |
     |         | _convert_request_      |
     |         |   amount()             |
     |         +------------------------+
     |                     |
     +-----+---------------+
           |
           v
+----------------------------------------------------------------------+
|                        approval.request                              |
|  Split across 7 files: fields, compute, action, validation,         |
|  helper (_sync_approvers, _force_terminal), escalation, cron        |
|  state = stored compute from approver_ids.state                     |
|  amount is Monetary in currency_id; rules convert into their own    |
|  their own currency before comparing                                |
|  decisions funnel through _apply_decision(); non-decision           |
|  terminations funnel through _force_terminal()                      |
+----+---------------------+------------------------------------------+
     |                     |
     v                     v
+-------------+  +------------+   +-------------------+
| approval.   |  | ir.        |   | mixin.approval    |
| approver    |  | attachment |   | (Abstract)        |
| (user,      |  | (protect   |   | Source doc link   |
|  state,     |  |  on final  |   | via res_model/id  |
|  seq,       |  |  states)   |   |                   |
|  delegate,  |  +------------+   | _on_approval_     |
|  pending_   |                   |  state_changed()  |
|  since,     |                   | _approval_rate_   |
|  source_*)  |                   |  limit_exceeded() |
+---------+---+                   +-------------------+
     |
     v
+---------+    +---------+
| decision|    | delegate|
| wizard  |    | wizard  |
| (refuse |    | (date   |
|  or     |    |  range, |
|  change)|    |  scope) |
+---------+    +---------+
     |
     v
+---------------+
| SQL Views     |
| approval.     |
|  metrics      |
| approver.     |
|  performance  |
| approval.     |
|  dashboard    |
+---------------+
```

---

## Approval Request Lifecycle

```
1. User selects category, fills fields, adds attachments
   create() -> _sync_approvers() -> approvers populated
   State: new  (name column stays EMPTY; display_name shows "New")

2. action_confirm()  (draft state only — re-confirm raises)
   +-- _sync_approvers() — ONCE for the whole recordset, before the
   |       per-request loop: reconciles approver set + approval_minimum
   |       against the CURRENT category configuration before freezing
   |       it. The only trigger that is not a write to the request, so
   |       it is what stops an old draft confirming with a stale set
   +-- _check_confirm()
   |   +-- _check_enough_approvers()
   |   +-- approval_app: _check_has_document_has_attachment()  (each
   |   |       required doc type must match a DISTINCT attachment)
   |   +-- approval_app: _check_category_required_fields()
   +-- name = category sequence consecutive (deferred numbering; a
   |       reset-then-reconfirmed request keeps its original number)
   +-- _build_category_snapshot() -> category_snapshot (JSON audit,
   |       incl. effective_* keys + the matched replacing rule)
   +-- date_confirmed = fields.Datetime.now()  (stamped BEFORE auto
   |       rules so granted >= confirmed on auto-approved requests)
   +-- _check_auto_action_rules() -> may auto-approve/auto-refuse
   |       (auto-refuse stamps refusal_reason_auto_rule metadata;
   |        terminal transition notified via _notify_if_terminal_transition)
   +-- [after the loop] _open_approval_round(rows still 'new')
   |       [shared with action_resubmit; takes a MULTI-request set]
   |   +-- If sequential: sort by (sequence, id), first -> pending, rest -> waiting
   |   +-- If parallel: all -> pending
   |   +-- _create_activity() on the rows entering the round
   |       Layout is per request; the three writes it resolves to are
   |       batched across the whole recordset, so a bulk confirm issues
   |       ONE mail.activity.create instead of one per request
   |       (3506 -> 1692 queries for 50 requests x 3 approvers).
   +-- _log_cycle("confirm") — after the round opens, since that line
   |       records the state the transition LANDS in
   State: pending

3. Approver decisions (action_approve / action_refuse)
   +-- _check_no_pending_change() (blocked while pending_change_field set)
   +-- action_refuse without skip_wizard opens the decision wizard
   |       (captures refusal_reason_id + note -> persisted on approver
   |        row AND request-level refusal_reason_id/refusal_note)
   +-- _apply_decision(decision, approver) — the single funnel:
       +-- _lock_for_approval_action() -> SELECT FOR UPDATE
       +-- invalidate_recordset(["state"]) (guard vs stale ORM cache)
       +-- _get_current_pending_approver() (delegation-aware) unless a
       |       resolved approver was passed (re-filtered to still-pending)
       +-- stamp decision_date, decided_by_user_id (the EFFECTIVE approver)
       |       and decided_step_ids, then _append_decision_log(approved/
       |       refused): approver.state projects from that fact
       +-- Chatter audit entry attributed to the acting (effective) user
       +-- refuse (unless every deciding row is advisory only):
       |       _flip_unsettled_approvers("refused") -- every remaining
       |       non-terminal row is refused
       +-- approve, request still pending: _refresh_turn_states() hands an
       |       in-order step's turn on, then asks whoever it reaches
       +-- action_feedback() on acting user's activity
       +-- _cancel_activities() if request reached terminal state
       +-- request reached 'approved': leftover pending rows are parked
       |       as 'waiting' — the decision window CLOSES at approval
       |       (no unbounded late veto; SM-6). action_withdraw reopens
       |       parked rows only when it actually pulls the request out
       |       of 'approved'; a surplus approval (count above the
       |       minimum) withdraws into 'waiting' and leaves the request,
       |       and its siblings, closed.
       +-- _notify_if_terminal_transition(old_state)
       +-- refuse into terminal: _refuse_approval_request() rollback hook

4. Owner-side exits
   +-- action_cancel()          pending -> cancelled (owner/manager,
   |       via _force_terminal; closes any open change request)
   +-- action_reset_to_draft()  any terminal -> new (refused/cancelled:
           owner/manager, except a standing refusal -- a refused binding
           request on a record with no approval of its own -- which only
           its refuser, a manager or a later step's member may reopen
           (_check_reset_actor); approved: manager only + _check_withdraw_allowed).
           Every one notifies the source document ('new', with
           approval_reset_from in context). _check_reset_allowed hook;
           clears decision metadata, date_confirmed, snapshot, escalation
           counters, applied rules; re-syncs approvers; keeps name/number)
```

---

## State Machine: approval.request

State is a **stored computed field** (`_compute_state`). It is never written directly.
It recomputes whenever `approver_ids.state`, `approver_ids.required`, or `approval_minimum` change.

Request states: `new`, `pending`, `approved`, `refused`, `cancelled`.
Approver states: `new`, `pending`, `waiting`, `approved`, `refused`, `cancelled`. On a request its steps route, `waiting` is a row whose every undecided step decides in order and is not at its turn (`approval.request._refresh_turn_states`, run when a round opens, after an approval or a withdrawal, and after a reroute or an adoption); a waiting row reaches the decision funnel only to be refused as out of turn. A row written straight to `approved` decides every step it is on.
Each row stamps `pending_since` when it ENTERS `pending` and
`decision_date` when a genuine approve/refuse takes it out again (both
cleared by reset-to-draft, both in `_WORKFLOW_MANAGED_FIELDS`). The pair
is what lets the approver analytics time each approver's OWN turnaround
— `decision_date - pending_since` — rather than the whole request's age
from `date_confirmed`, which in a sequential chain billed every approver
for the delays of everyone ahead of them and made the dashboard's
"Slowest Approver" name whoever sat last. Stamping lives in
`approval.approver._stamp_pending_since`, applied from `create`/`write`,
so all five promotion paths are covered by construction.
`_TERMINAL_STATES = frozenset({"approved", "refused", "cancelled"})`
(`approval_request_routing.py`).

```
                    +-------+
                    |  new  |  (no approvers, or any approver state="new")
                    +---+---+
                        |
                  action_confirm()
                        |
                    +---v---+
                    |pending|<---- (request-a-change keeps the state
                    +---+---+       pending; pending_change_field set)
                        |
              +---------+---------+
              |         |         |
              A         R         C
              |         |         |
              v         v         v
         +--------+ +-------+ +---------+
         |approved| |refused| |cancelled|
         +--------+ +---+---+ +----+----+
                        |          |
                        +----+-----+
                             |
                  action_reset_to_draft()
                             |
                         +---v---+
                         |  new  |
                         +-------+

    Legend:
    A = approved_count >= approval_minimum AND all required approved
    R = any approver refused (real decision — outranks cancelled)
    C = any approver cancelled (owner cancel / auto-expire / nobody decided)
```

### State Priority (checked in `_compute_state` order)

| Priority | Approver Condition | Request State |
|----------|-------------------|---------------|
| 0 | No approver rows | `new` |
| 1 | Any approver `refused` | `refused` |
| 2 | Any approver `cancelled` | `cancelled` |
| 3 | Any approver `new` | `new` |
| 4 | approved_count >= `approval_minimum` (hard contract, NOT clamped to len(approvers)) AND all required approved | `approved` |
| 5 | Otherwise | `pending` |

### Departure Handover (SM-7)

Archiving a user (``approval.res_users.write``) hands their live
``pending``/``waiting`` rows on pending requests UP: the successor comes
from ``_get_escalation_manager()`` (approval_hr walks the management
chain past archived managers; base falls back to the category
escalation contact, then — SM-8, 2026-07-14 — to an active
``approval.group_approval_manager`` member in the request's company —
matched on ``all_group_ids``, so a manager holding the privilege through
a group that IMPLIES it counts, exactly as ``_is_approval_manager()``
(``has_group``) already did; the earlier direct-only ``group_ids`` search
made the fallback silently find nobody —
so non-HR satellites with an unconfigured category no longer end up
with only an admin To-Do) and the row's ``user_id`` is REASSIGNED (not
delegated — delegation windows expire and would revert to the archived
user). Rows with an active delegation to a live user are left alone.
Illegal targets (owner, co-approver, wrong company, none found) become
a To-Do for the archiving admin. Categories still listing the archived
user get a chatter note. Backstop: the escalation cron escalates
immediately (at reminder time) when a pending row's effective approver
is inactive, and ``_send_reminder`` never targets archived inboxes.

### Approver-Row Integrity (since 19.0.1.0.13)

Approver rows may be manually created/deleted in DRAFT only (never
bypassed, sudo included, except the `_sync_approvers` exemption). The
request state is a stored compute over its rows, so a hand edit on a
decided request was a hidden state transition that skipped every funnel
(deleting the refusing row of a refused request silently flipped it to
approved; deleting all rows returned it to draft bypassing
`action_reset_to_draft`). Decided requests are re-cycled exclusively via
reset-to-draft. Sync provenance is exact via
`approval.approver.source_synced` (stamped on every sync-created row):
a row whose automated source stopped producing it is deleted on
re-sync, never preserved as a phantom "manual" approver.

### Who Can Trigger Each Transition

| Action | Who | Method | Preconditions |
|--------|-----|--------|---------------|
| Confirm | Request owner | `action_confirm()` | state=new only, enough approvers, required fields/documents |
| Approve | Assigned/delegated approver | `action_approve()` | state=pending, approver state=pending, no pending change |
| Refuse | Assigned/delegated approver | `action_refuse()` (wizard unless skip_wizard) | state=pending, approver state=pending, no pending change |
| Request change | Assigned/delegated approver | `action_request_change()` (wizard) | state=pending, no change already pending |
| Re-submit after change | Owner, manager, or an approver (only the owner/manager may APPLY the change — see `_check_locked_fields`) | `action_resubmit()` | `pending_change_field` set; reopens a fresh round when approvals were already given |
| Cancel | Request owner or manager | `action_cancel()` | state=pending only (drafts are deleted, not cancelled) |
| Reset to draft | Owner or manager (refused/cancelled), except a standing refusal: its refuser (`decided_by_user_id`), a manager, or a pool member of a later step (`_check_refusal_reopener`); manager only (approved) | `action_reset_to_draft()` | state in `_TERMINAL_STATES` AND `_check_reset_allowed()`; approved also runs `_check_withdraw_allowed()` |
| Withdraw | Approver who approved; through `action_withdraw_approver(approver_id, step_id)` -- for one step of it, or all -- also a manager or a pool member of a later step (`_check_withdraw_actor`) | `action_withdraw()` / `action_withdraw_approver()` | approver state=approved (pending or approved request), `_check_withdraw_allowed()` |
| Bulk approve | Approver/delegate with pending rights | `action_approve_bulk()` | All selected state=pending, `_get_current_pending_approver()` non-empty |
| Bulk refuse | Approver/delegate with pending rights | `action_refuse_bulk()` | Validates the batch, then opens `approval.decision.wizard` in batch mode (`request_ids`) so a reason is captured on every request, exactly as a single refusal does |
| Cascade refuse | Parent document (mixin) | `action_refuse_approval()` → `_refuse_cascade()` | request not terminal and not draft |
| Auto-expire | Cron | `cron_auto_expire()` → `_force_terminal("cancelled")` | pending past `auto_expire_hours` |
| Consent approve | Cron | `cron_consent_approval()` | pending past window, parallel category, no refusal, no pending change, `_can_consent_approve()` |

---

## Ordered Approval

Every request routes by its category's steps, so order is a step's: `in_order`
asks a step's members one at a time by `(sequence, id)`, and
`_refresh_turn_states()` moves the turn after each decision or withdrawal.

**Sequence values by source:**

One `ir.config_parameter` key, seeded in `data/ir_config_parameter_data.xml`
and read through `_get_sequence_param(kind, default)` (which logs and falls
back to the default on an unparseable value):

| Source | Default Sequence | Where it comes from |
|--------|-----------------|---------------------|
| HR manager (approval_hr's step source) | 9 | `approval.sequence.manager` → `_get_sequence_manager()` |
| Step members | As defined | `approval.category.step.member.sequence`; a member a path names takes the step's `subject_user_sequence` in order, the step's `sequence` otherwise |
| Manual approvers | As given | The row's own `sequence`; a re-sync classifies a manual row but never rewrites it |

---

## Approver Sync Engine (`_sync_approvers`)

Called from `create()`, `write()` (when any routing input changes),
`action_confirm()` (reconciliation against the current category
configuration, before the snapshot freezes it) and
`action_reset_to_draft()`. Not a computed field -- creates/updates
related `approval.approver` records.

**Re-sync triggers (19.0.1.0.17).** `write()` no longer tests a
hardcoded field set. `_get_fields_approver_sync_trigger()` unions
`category_id`/`request_owner_id` with what `approval.rule` and
reports from `_get_fields_request_trigger()` — the
flattened values of their `_CONDITION_FIELD_DEPENDS` /
`_THRESHOLD_FIELD_DEPENDS` maps, today `amount`, `quantity`,
`currency_id`, `date`, `date_start`, `date_end`, `priority`. The previous literal
`{category_id, request_owner_id, amount, quantity}` had fallen behind
the models it was meant to mirror: a draft raised to Urgent never picked
up a `priority`-keyed rule, a date range never fired a
`date_range_days` rule, and switching a draft's currency crossed band
boundaries silently (amount comparisons convert through `currency_id`
at `date`). `action_confirm` then froze the stale set in and snapshotted
it as intended. A satellite adding a `condition_field` extends its own
model's mapping and is picked up here automatically.

**Purity (19.0.1.0.17).** `_get_desired_approvers()` is write-free:
`_sync_approvers` persists the `matched_rules` it returns on its
`DesiredApprovers` result, which are the applicable steps' `when_rule_ids`.

**Steps only (19.0.2.8.0).** A category has no approver list any more: no
`approval.category.approver`, no `approve_sequentially`, `group_approval` or
`approver_group_id`, and no rule that adds or replaces approvers. Migration 2.8's
end script converts what a database still holds (a list into one pool step,
sequential into `in_order`, a security group into a group step asking its members
when `notify_pool_members` did) and hands the pending list-routed requests to those
steps, refusing the upgrade on a rule that added or replaced approvers on a
category with no step. approval_hr's 19.0.1.1.4 re-syncs the requester-manager
steps after it, and telegram_bot_approval_request's 19.0.1.0.4 carries the
Telegram opt-in onto the members.

```
_sync_approvers()   [batch-level]
    |
    +-- Prefetch the batch's categories' steps in one query:
    |       category_id.fetch(["step_ids"])
    |
    +-- Per request: _get_desired_approvers()  [PURE — no writes]
    |   |
    |   +-- Map existing approvers {user_id: row}, mark duplicates
    |   +-- Rows always stage as 'new' — the sync is DRAFT-ONLY
    |   |       (state == 'new' filter; every trigger is a draft write
    |   |       or reset-to-draft; mid-flight staging removed, SM-5)
    |   +-- _get_applicable_steps() -> the steps whose condition holds
    |   +-- Each step's pool, members first in member order: a row per
    |   |       user, required when its member is (or when the step
    |   |       requires the user its path names), step_ids the steps
    |   |       that name it
    |   +-- Preserve truly manual approvers -> keep their sequence and
    |           flow_state, counted toward the steps that count added
    |           approvers; orphaned injections are left out (deleted by
    |           the caller). A row is an ORPHAN when source_synced is set,
    |           or it still carries a rule stamp from a list-routed past,
    |           or its user is a candidate of an applicable step
    |           (_get_managed_approver_user_ids(steps))
    |
    |   +-- Accumulate row ops for the WHOLE batch (not per request):
    |       rows_to_delete (duplicates + orphans), rows_to_create,
    |       rows_to_update keyed by value set (_stage_approver_update)
    |
    |   +-- Persist applied_rule_ids from _applied_rule_ids_after_sync()
    |           (the matched_rules the pure step returned)
    |
    +-- [after the loop] _build_sync_plan() -> _execute_sync_plan():
    |       ONE delete, ONE create, then one update PER DISTINCT VALUE SET
    |       (not three statements — rows_to_update is keyed by the value
    |       tuple, so N distinct shapes cost N writes). In this
    |       order — deletes, then creates, then updates. Order is
    |       load-bearing: a create before its duplicate is gone would
    |       transiently put two rows with the same user on one request,
    |       which the approval_approver_request_user_uniq SQL constraint
    |       rejects. Until 19.0.1.0.22 this note credited the
    |       _check_approver_ids Python constraint, which does NOT fire
    |       here: it is @api.constrains("approver_ids") on approval.request
    |       and the sync writes approval.approver rows directly, so a
    |       regression in this ordering produced silent duplicates — an
    |       extra vote toward approval_minimum — rather than an error.
    |       Each runs on approval.approver.sudo().with_context(
    |       approver_ids_computation=True) — sudo satisfies access; the
    |       context key relaxes the state business-rules only in
    |       combination with env.su.
    |       (Previously one update({"approver_ids": commands}) PER
    |        request, i.e. one INSERT per approver row on a bulk create.)
    +-- Collect effective approval_minimum (the applicable steps' minimums
    |       summed, or the category default when none applies) — flushed as
    |       batched UPDATEs grouped by value
    +-- Log-only timing: warn when the batch exceeds ~100ms/request
            (the old per-request approver_compute_ms column is gone)
```

### Approver Merge Logic (`_merge_approver_to_staging`)

When the same user appears from multiple sources:
- `required = True` takes precedence (OR merge)
- Lower `sequence` takes precedence (MIN merge)

---

## Forced Terminations (`_force_terminal`)

Single funnel for every termination that is NOT an approver decision:

`approved` is rejected outright (`ValueError`): a request only reaches it
through real approver rows, so consent auto-approval writes its own way.

| Caller | Terminal state | Refusal metadata |
|--------|---------------|------------------|
| `action_cancel()` (owner/manager) | `cancelled` | -- |
| `cron_auto_expire()` | `cancelled` | -- |
| `_refuse_cascade()` (parent document cancelled) | `_get_parent_cancel_state()`, `refused` in the base | `approval.refusal_reason_parent_cancelled` + note (refusals only) |

Shared side-effect sequence, in order: flip only **non-terminal** approver
rows (rows that already approved/refused keep their state — they are the
audit trail of who actually decided), persist `refusal_reason_id`/
`refusal_note` when provided and not already set, cancel open
activities, **retire any open request-a-change** (`_close_pending_change()`
— clears `pending_change_field` and closes the requester's change To-Do),
fire the source-document notification exactly once, post the chatter
trace, and run `_refuse_approval_request()` on refusals. The close-out
lived in `action_cancel` alone, so auto-expire and the parent cascade
left the requester a To-Do nothing ever closed — it then survived
reset-to-draft too (2026-08-11 audit). Auto-refuse rules terminate through their own write in
`_check_auto_action_rules()` but stamp the same canonical metadata
(`approval.refusal_reason_auto_rule`).

---


### Revoking an approval (`_revoke`)

`_force_terminal` skips a request that is already terminal, and `approved` is terminal, so it cannot
overturn an approval. `_revoke(new_state, body, refusal_reason=None, refusal_note=None, subtype_xmlid=None)`
does, for an approved request only: it records `revoked_state` (`refused` or `cancelled`),
`revoked_by_user_id` and `date_revoked`, which `_compute_state` reads before the approver rows. The rows keep
their decisions and `decided_by_user_id`, and the request keeps `date_approval_granted`. The source document
is notified once through `_notify_if_terminal_transition("approved")`; a refusal runs
`_refuse_approval_request()`. `_force_draft()` clears the three fields, and a revoked request can no longer be
withdrawn from, since it is neither pending nor approved. This is how an adopter whose own policy lets
someone overturn a finished approval -- time off refusing a validated leave -- keeps the engine's record true.

### Approving without a decision (`_approve_without_decision`)

A decision needs an approver row, and `_force_terminal` refuses `approved`, so the engine had no way to record
that an authority outside a request's decisions approved it. Time off needs one when the system validates a
leave whose request is still pending: the superuser's `action_approve`, or a leave validated again after its
public holidays changed. `_approve_without_decision(body, subtype_xmlid=None)` accepts a pending request only.
It records `granted_by_user_id`, which `_compute_state` reads after `revoked_state` and before the approver
rows; turns the rows still pending to `waiting`, as an approval does; cancels activities, closes a pending
change request, notifies the source document once and posts the body. No row is marked decided, so
`decided_by_user_id` names only people who decided, and a decision given before stays as given. The request
stamps `date_approval_granted` like any approval. `_revoke` can still overturn it, `_force_draft()` clears the
field, and withdrawing from it is refused, since no withdrawal could take back an approval nobody gave.

## Notification Flow

### Email / Activity Notifications

| Trigger | Recipients | Mechanism | Content |
|---------|-----------|-----------|---------|
| `action_confirm()` | Pending approvers | `activity_schedule()` | Approval to-do (idempotent per user+request) |
| `_apply_decision("approve")` | Request owner | `message_post()` with partner_ids, attributed to the acting user | "Request accepted" |
| `_apply_decision("refuse")` | Request owner | `message_post()` with partner_ids, attributed to the acting user | "Request refused" |
| Decision wizard (change) | Request owner | `activity_schedule()` change-request To-Do | Field to change + approver's note |
| `action_resubmit()` | Chatter | `message_post()`; change-request To-Do marked done | "Re-submitted after the requested change" |
| `action_withdraw()` | Chatter | `message_post()` attributed to the withdrawing user | "Withdrew approval" |
| `action_cancel()` | Chatter | `_force_terminal` message | "Request cancelled by X" |
| `action_reset_to_draft()` | Chatter | `message_post()` | "Reset to draft from 'state' by X" |
| `copy()` | Chatter (silent) | `_message_log()` | "Duplicated from ..." provenance trace |
| Smart escalation cron | Pending approvers | Activity update or create | Reminder with priority and duration |
| Escalation to manager | Approver's manager (`_get_escalation_manager` hook) | `message_post()` with partner_ids | Escalation notice; falls back to a reminder when no manager |
| Auto-expire cron | Chatter | `_force_terminal` message (mt_note) | "Automatically cancelled after X hours" |
| Consent approval cron | Chatter | `message_post()` (mt_note) | "Auto-approved by consent" |

There are 2 activity types (`data/mail_activity_type_data.xml`):
`mail_activity_data_approval` and `mail_activity_data_change_request`.

### Source Document Notification

The hook is **not** fired from `_compute_state` (running foreign-model
hooks inside a stored compute risks cache invalidation mid-batch).
Instead, every action that transitions a request into a terminal state
calls `_notify_if_terminal_transition(old_state)`, which:
1. Checks the state actually changed and is in `_TERMINAL_STATES`
2. Calls `_notify_source_document_state_change(new_state)`
3. Looks up the source document via `res_model` / `res_id` and verifies
   it with `isinstance(doc, env.registry["mixin.approval"])`
4. Verifies the link points BOTH ways — a document whose
   `approval_request_id` is not this request is logged as a warning and
   skipped, so a stale `res_id` cannot drive a foreign record's workflow
5. Calls `_on_approval_state_changed(new_state)` on the document,
   `sudo()` and with `approval_acting_user_id` in the context so a
   satellite can attribute its own messages to the deciding user

`action_withdraw()` additionally notifies `"pending"` explicitly when it
pulls a request OUT of `approved` (exits from terminal states are not
covered by `_notify_if_terminal_transition`). The base mixin reacts to
that revocation with a chatter alert plus a To-Do for the document's
responsible user (`user_id` fallback `create_uid`) on activity-enabled
models — satellites override for document-specific handling.

`_force_draft()` notifies `"new"` whenever it sends a decided request —
approved, refused or cancelled — back to draft, with `approval_reset_from`
in the context naming the state it left. A document that reacted to a
refusal learns its request is live again; the base `_on_approval_reset`
says the prior approval no longer holds only when that state was
`approved`, and otherwise that the request can be submitted again.

Between those outcomes the document also hears **progress**. After an approval that
meets at least one step and leaves the request `pending`, `_apply_decision` calls the
source document's `_on_approval_progress()` (a no-op on `mixin.approval`). It compares
the request's unmet steps before and after the decision, so a decision that meets no
step reports nothing, a refusal reports nothing, and the final approval reports its
outcome through the terminal notification instead. A double-validation leave uses it
to move to its intermediate state however the manager step was approved. Both
notifications find the document through `_get_notifiable_source_document()`, which
holds the registry, `mixin.approval` and two-way-link checks and returns it under
`sudo()` with `approval_acting_user_id`.

---

## Conditional Routing

### Conditional Rules (`approval.rule`)

Rules evaluate conditions and take actions:

| `action_type` | Effect |
|--------------|--------|
| `auto_approve` | Bypasses normal workflow, sets all approvers to approved |
| `auto_refuse` | Bypasses normal workflow, sets all approvers to refused AND stamps `refusal_reason_auto_rule` + note on the request |
| `condition` | Nothing by itself: a step applies when it matches (`when_rule_ids`) or unless it does (`unless_rule_ids`) |

**Rule evaluation** (`_evaluate`):
- Gets field value from request (amount, quantity, date_range_days, priority);
  `amount` is converted into the rule's `currency_id` first
- Applies operator (gt, gte, lt, lte, eq, neq) against threshold
  (float equality uses `_FLOAT_EQ_ABS_TOL` / `_FLOAT_EQ_REL_TOL`)
- `condition` rules a step reads evaluated once per request per sync (`_get_step_rule_matches`)
- `auto_approve`/`auto_refuse` rules evaluated in `_check_auto_action_rules()` (during `action_confirm`)

### Escalation Pipeline

```
Smart Escalation (cron_smart_escalation, every 4 hours, max 500
requests per priority bucket per tick):
    _reconcile_delegation_activities()   -- FIRST, before any bucket.
        Every pending row with a delegate whose To-Do still sits in the
        wrong inbox is repointed at the effective approver (or closed if
        the right one already exists). A delegation set AFTER the round
        opened does not move the activity by itself; this is what makes
        the queue converge.
    For each priority level in _get_escalation_rules():
        Find pending requests past reminder threshold (oldest first),
            EXCLUDING those with pending_change_field set — the ball is
            in the requester's court, not the approver's, so a request
            awaiting a change is never chased or escalated
        If past escalation threshold AND not yet escalated:
            _resolve_escalation_targets() -> {manager: approvers}, unescalated
            _escalate_to_manager() -> ONE message_post per MANAGER, naming
                every approver they are being asked to chase (it used to
                post once per approver; the base _get_escalation_manager
                ignores its argument, so a category with an escalation
                contact sent that person N identical copies). The cron
                reuses the same resolution for the reminder fallback
                instead of asking again per approver, and
                _get_default_escalation_manager is memoised per
                (transaction, company).
        Else:
            _send_reminder() -> update/create activity for pending approvers
        Batch-update last_reminder_date / reminder_count (grouped by
        prior count) only for requests where something actually went out
        Each request runs inside its own cr.savepoint(): a failure is
        logged and the request skipped, never a dead tick for the rest
```

**Escalation schedule**: defaults from the `ESCALATION_RULES` constant
(`approval_request.py`), each value overridable via ir.config_parameter
`approval.escalation.<priority>.<first_reminder|escalation>`; resolved
by `_get_escalation_rules()`:

| Priority | First Reminder | Escalation to Manager |
|----------|---------------|----------------------|
| Urgent (3) | 4 hours | 8 hours |
| High (2) | 24 hours | 48 hours |
| Normal (1) | 48 hours | 96 hours |
| Low (0) | 72 hours | 168 hours |

---

## Cron Jobs

4 scheduled actions (`data/ir_cron_data.xml`). The three on requests are batched via
`CRON_BATCH_LIMIT = 500`. The cap is per TICK for auto-expire and
consent — both build one OR-of-per-category-windows domain through
`_eligible_by_category_domain()` and issue a single capped, globally
oldest-first search. (It used to be per CATEGORY: the search sat inside
a `for category` loop with the limit on the inner query, so a
deployment's tick size scaled with how many categories it had
configured.) Smart escalation caps per PRIORITY BUCKET, so its
worst case is 4 x `CRON_BATCH_LIMIT` — deliberate, since each priority
carries its own thresholds:

| XML ID | Method | Schedule | Active | Purpose |
|--------|--------|----------|--------|---------|
| `ir_cron_smart_escalation` | `cron_smart_escalation()` | Every 4 hours | Yes | Priority-based reminders and manager escalation |
| `ir_cron_auto_expire` | `cron_auto_expire()` | Daily | Yes | **Cancel** (terminal `cancelled`, via `_force_terminal`) requests past `category.auto_expire_hours` |
| `ir_cron_consent_approval` | `cron_consent_approval()` | Every 4 hours | Yes | Auto-approve if no refusal within `consent_approval_hours`; skips sequential categories, requests with `pending_change_field`, and `_can_consent_approve()` vetoes |
| `ir_cron_hand_delegated_activities_over` | `approval.approver.cron_hand_delegated_activities_over()` | Daily | Yes | `is_delegated` is computed from today, so who may decide a delegated row changes when its window opens or closes. The approval activity is moved to that person (`_hand_activities_to_effective_approver`, also run by every write of the delegation fields). Unbatched: it reads only pending rows that carry a delegate |

Removed: the weekly `ir_cron_performance_report` (and its
`approver_compute_ms` column) — unlinked/dropped by the 19.0.1.0.7
migration; and the legacy `cron_escalate_overdue_approvals`.

---

## Concurrency Control

`_lock_for_approval_action()` acquires `SELECT FOR UPDATE` on `approval_request`
rows before any approval action (approve, refuse, withdraw). This prevents:
- Duplicate activity creation in sequential workflows
- Two approvers promoting the same "next" approver simultaneously
- State corruption from concurrent approve + refuse

The lock is blocking (no NOWAIT) -- concurrent requests wait rather than fail.
After acquiring the lock, `_apply_decision()` and `action_withdraw()`
invalidate the ORM cache for `state` (`invalidate_recordset`) so the
"still pending?" filter reads fresh DB values, and `_create_activity()`
is idempotent per (user, request) as a second guard.

---

## Debug Tracing

Two DEBUG streams, both greppable by prefix, cover the two levels at
which this module is hard to read from an ORM trace:

| Prefix | Emitter | Answers |
|--------|---------|---------|
| `approver-sync` | `_log_sync_plan()` (`approval_request_routing.py`) | "why did this request gain/lose an approver?" — the whole batch's flush plan, numbered in execution order |
| `approval-cycle` | `_log_cycle()` (same file) | "why is this request in this state?" — one line per transition with the resulting row layout |

`approval-cycle` is emitted by `action_confirm`, `_apply_decision`,
`action_withdraw`, `action_resubmit`, `action_reset_to_draft` and
`_force_terminal`, e.g.::

    approval-cycle decide request=42 (INT/00007) state=pending minimum=2
        rows=[alice=approved bob=pending] decision=approve actor=alice

The request's state is written by nobody — `_compute_state` derives it
from the approver rows — so the row layout is the part a trace of the
writes cannot show. Both helpers are guarded on `isEnabledFor(DEBUG)`;
nothing is rendered in production.

---

## Cross-Module Interactions

### Source Document Integration (`mixin.approval`)

Any model can inherit `mixin.approval` to integrate with the approval system:

```python
class PurchaseOrder(models.Model):
    _inherit = ["purchase.order", "mixin.approval"]

    def _get_domain_approval_category(self):
        return [("approval_type", "=", "purchase")]

    # Per-transition hook, NOT the _on_approval_state_changed dispatcher.
    def _on_approval_approved(self):
        self.action_confirm()
```

The mixin:
1. Creates `approval.request` with `res_model` / `res_id` back-reference
2. Auto-confirms the request (creates activities for approvers)
3. Owns category selection end to end (`_get_approval_category` searches
   the domain — scoped to the document's company plus company-less
   categories — in `sequence, id` order and returns the first category
   whose `approval.category._is_applicable_for` accepts the document);
   consumers supply the domain, the predicate, an optional fallback and
   the error wording, never the search
4. Dispatches state changes to per-transition hooks —
   `_on_approval_approved` / `_on_approval_refused` /
   `_on_approval_cancelled` / `_on_approval_revoked` / `_on_approval_reset`
   — via `_on_approval_state_changed()`, which consumers should not
   override (doing so and calling `super()` produces two chatter messages
   for one decision)
5. Provides related fields: `approval_state`, `approval_progress`, `pending_approver_ids`
6. Can force-refuse the linked request when the parent document is
   cancelled (`action_refuse_approval()` → `_refuse_cascade()`)
7. Releases failed links when the document reopens
   (`_clear_refused_approval_link()`), which also makes the old request
   non-resettable (`_check_reset_allowed`)

### A document that drives its request (`mixin.approval.state.sync`)

Some documents cannot hand their lifecycle to the engine. Time off is the case that forced this: five modules override
the leave's `action_refuse` alone, each post-processing after `super()`. A document the engine moves through its
callbacks would run that post-processing twice, once for the button and once for the callback. Such a document
inherits `mixin.approval.state.sync` instead, and the direction reverses:

- the document keeps its own state field and its buttons. A state change brings the request in line: the acting user's
  decision when they hold a decidable row, otherwise a grant (`_approve_without_decision`), a revocation (`_revoke`)
  or a forced terminal state;
- a decision taken on the request itself, in the approvals app or through an activity, reaches the document through
  `_check_approval_sync_policy`, the document's own authority run as the acting user, and then through the document's
  overridable methods. The engine's pools may be wider than the document's policy (a group step), and the policy
  decides;
- an `approval_state_sync` context of request ids keeps either side from reacting to the change the other just made;
- the request refuses being withdrawn, reset, cancelled or sent back for a change from the approvals app
  (`_check_moved_from_source_document`), since those moves belong to the document.

The adopter declares a state-to-kind map, a policy check and how to apply an outcome; everything else is the mixin's.

### Dependencies

The three declared in `__manifest__.py`:

| Module | Integration |
|--------|------------|
| `mail` | Activities, chatter, message_post, message_subscribe |
| `automation` | **Not a dependency since 19.0.2.0.0.** `approval_automation` carries `approval.category.automation_id`, `approval.request.automation_runtime_id` and a binding's Reset When |
| `mixin_report_sql` | **Not a dependency since 19.0.2.0.0.** `approval_analytics` carries `approval.metrics`, `approver.performance` and `approval.dashboard` |

**Not a dependency: `product`.** Product lines left this module in
19.0.1.0.12 — `approval.request.line`, `approval.category.product_ids`
and `has_product` now live in `approval_product`, which depends on
`approval` and on `product`. Nothing here imports or references them.

### Extension Points for Other Modules

| Hook | Purpose | Used By |
|------|---------|---------|
| `_get_escalation_manager(approver)` | Supply the manager for cron escalation | approval_hr |
| `_check_withdraw_allowed()` + `_raise_withdraw_blocked()` | Block withdrawal when linked documents exist | approval_account / sale / purchase / stock |
| `_check_reset_allowed()` | Veto reset-to-draft | Base only today (it blocks a request whose source-document link was released); no satellite overrides it |
| `_get_parent_cancel_state()` | Which terminal a parent-document cancellation drives the request into. Base returns `refused`; return `cancelled` where a parent's cancellation is not a verdict on the request | none today |
| `_can_consent_approve()` | Veto consent auto-approval | approval_account |
| `_refuse_approval_request()` | Cooperative rollback of documents created from the approval | account / purchase / sale satellites |
| `_on_approval_approved()` / `_on_approval_refused()` / `_on_approval_cancelled()` / `_on_approval_revoked()` / `_on_approval_reset()` | React to one transition in source documents. Omit `super()` when your message replaces the base's generic note. Put any document-advancing call inside `_approval_side_effect()` — the hook runs inside the approver's transaction and that helper carries the savepoint, catch and chatter note | account / sale / purchase / stock / rma / credit_management_approval |
| `_on_approval_progress()` | React to a step of the request being met while it stays pending -- the intermediate state of a multi-step document workflow. No-op on the mixin | hr_holidays (time off validate1) |
| `_on_approval_state_changed()` | The dispatcher. **Do not override** — it exists to route to the per-transition hooks above | Base only |
| `_get_domain_approval_category()` | Which categories are candidates for this document type | Any mixin consumer |
| `approval.category._is_applicable_for(document)` | Whether a candidate category matches this document. Fail-closed when criteria exist; fall through to `super()` for foreign documents | account / sale / purchase / stock / maintenance |
| `_get_approval_category_fallback(categories)` | Generic category for approval triggered by a flag outside the category criteria | account / stock |
| `_raise_approval_category_not_configured()` / `_raise_approval_category_not_matched(categories)` | Turn "no category" into a named configuration error instead of "no approval needed" | sale / purchase / maintenance / rma / credit_management_approval |
| `_get_approval_reason_html()` | Justification stored on the request; base returns the document display name | account / sale / purchase / stock / rma / credit_management_approval |
| `_get_category_required_field_mapping()` | Add required field validation, on `approval_app`, which owns the form fields it maps | Extensions adding custom fields (must also add the field — base no longer maps `payment_method_id`) |
| `_get_fields_locked()` | Extend the post-submit frozen field set | Extensions adding value fields |
| `_approval_rate_limit_exceeded(...)` | Submission throttle: too many, or too much in value, from this creator within a window. Multi-currency — thresholds are given in company currency and converted per counterparty currency before comparison | approval_purchase / approval_sale |
| `_approval_rate_limit_rate_date()` | Pin the conversion date used by the throttle | any consumer |
| `_get_fields_approval_protected()` | Fields on the SOURCE document frozen by the mixin's `write()` while an approval is in flight | any consumer |
| `_before_approval_request_submit(approval)` | Act between request creation and auto-confirm | any consumer |
| `_get_managed_approver_user_ids(steps)` | The user ids the applicable steps may stage, so a row whose step stopped applying is not kept as a phantom manual approver (legacy backstop; `source_synced` covers rows since 19.0.1.0.13) | none today |
| `approval_type` selection | Extend with new types (e.g., 'purchase', 'expense') | Domain-specific modules |
| `target_model` selection | Extend with new target models | Domain-specific modules |

---

## Category Snapshot (Audit Trail)

At `action_confirm()`, `_prepare_category_snapshot()` captures the category
configuration into a JSON field (`category_snapshot`). This preserves:

- Category name, approval_minimum, approval_type, `approval_deadline_hours`
- Active rules (name, condition_field, operator, threshold, action_type)
- The applicable steps: name, sequence, minimum, exclusivity, group, members,
  condition and source path
- **Effective resolved workflow**: `effective_approval_minimum` and
  `effective_approvers` (the rows actually staged)

Consumers read frozen values through `_get_snapshot_config(key)` (live
category fallback for legacy rows): `approval_deadline` is computed from
the snapshot so an admin editing the category neither moves in-flight
deadlines nor triggers an O(history) recompute storm. `sla_status`
deliberately reads the LIVE category config instead (reporting measure,
matches the `approval.metrics` SQL view). `action_reset_to_draft()`
clears the snapshot; the next confirm rebuilds it against the current
configuration.
