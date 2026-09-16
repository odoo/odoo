# Approval Conventions & Gotchas

## Security Model

### Three-Layer Defense in Depth

| Layer | What It Checks | Bypass |
|-------|---------------|--------|
| 1. `ir.rule` (SQL) | Row-level filtering (read/write/create/unlink domains) | Sudo bypasses |
| 2. Python CRUD access (`_check_access_*`) | WHO can perform the operation | Sudo or managers (the sync engine runs under sudo). Non-manager approvers may write only delegation and decision-note fields on their own row — never `state`/`sequence`/`required` |
| 3. Python business rules (`_check_business_rules_*`, `_check_locked_fields`) | WHAT states allow the operation | Sudo-proof on the request: `_check_locked_fields` (`_LOCKED_FIELDS` half) and `_check_no_forged_computed_fields` bind everyone. On `approval.approver`, create and unlink are equally sudo-proof — their only exemption is `env.su` **plus** the `approver_ids_computation` context — but `_check_business_rules_write` returns early on `env.su` alone, because the workflow itself writes `flow_state` and the decision stamps under sudo |

### Groups

| Group | XML ID | Implies | Permissions |
|-------|--------|---------|-------------|
| Approver | `group_approval_approver` | `base.group_user` | Shows the "My Approvals" menu. It is **not** what grants the right to decide — that comes from being assigned on the request, group or no group. No configuration access |
| Administrator | `group_approval_manager` | `group_approval_approver` | Full CRUD on all models, configuration access |

Both sit under the `res_groups_privilege_approvals` privilege
(`security/res_groups.xml`).

### ACL Summary (ir.model.access.csv)

| Model | Internal User (group_user) | Manager (group_approval_manager) |
|-------|---------------------------|----------------------------------|
| `approval.category` | read | full CRUD |
| `approval.request` | full CRUD | (inherits from user) |
| `approval.approver` | full CRUD (ACL level) | (inherits from user) |
| `approval.refusal.reason` | read | full CRUD |
| `approval.template` | read | full CRUD *(`approval_app`)* |
| `approval.rule` | read | full CRUD |
| `approval.document.requirement` | read | full CRUD *(`approval_app`)* |
| `approval.dashboard` | **none** (0,0,0,0) | full CRUD |
| `approval.metrics` | **none** (0,0,0,0) | full CRUD |
| `approver.performance` | **none** (0,0,0,0) | full CRUD |
| Wizards (decision, delegate) | full CRUD | (inherits from user) |

**The three analytics models are manager-only.** Their `base.group_user`
row exists but grants nothing — it is there to make the intent explicit
rather than to leave the model unlisted. A plain internal user opening a
dashboard action gets an access error, by design: the dashboard and both
SQL views aggregate across every requester, which is exactly what
`privacy_visibility` restricts on the request itself.

**Important:** `approval.approver` has full CRUD at the ACL level for all users, but
Python CRUD methods (`_check_access_create/write/unlink`) block manual operations.
Only the sync engine (via `approver_ids_computation` context) or sudo/manager can
create/delete approvers — and even then **only while the request is `new`**
(business rule, tightened in 19.0.1.0.13), except during a sync. Refused and
cancelled requests are NOT re-openable this way: reset them to draft first.

### Record Rules

| Rule | Model | Scope | Domain |
|------|-------|-------|--------|
| Multi-company | category, category_approver, refusal_reason, rule, template | Global | `company_id in company_ids + [False]` — the `+ [False]` is what lets a company-less rule apply everywhere (`mixin.approval.threshold.company_id`) |
| Multi-company | request, approver, metrics, performance | Global | `company_id in company_ids` |
| User read | request | group_user | Owner OR approver OR delegate |
| User read | approver | group_user | Own request's owner OR self OR delegate OR **co-approver on the same request** (`request_id.approver_ids.user_id`/`.delegate_id`) — approvers can see who else is on the chain, which is what makes the sequential position legible |
| Visibility read (additive) | request, approver | group_user | `category_id.privacy_visibility` audiences: `restricted_users` (in `allowed_user_ids`), `restricted_groups` (in `allowed_group_ids.all_user_ids`), `employees` (everyone). `private` adds no extra audience. Read-only; same-group rules OR together so these only WIDEN visibility |
| User write | request | group_user | Owner OR approver OR delegate |
| User write | approver | group_user | Self OR delegate |
| User create | request | group_user | Owner = current user |
| User unlink | request | group_user | Owner = current user AND state = new |
| Manager read | request, approver | group_approval_manager | All |
| Manager write/create | request, approver | group_approval_manager | All |
| Manager unlink | request | group_approval_manager | state = new only (submitted/terminal requests are audit trail) |
| Manager unlink | approver | group_approval_manager | All — the single `approval_approver_manager_write` rule carries `perm_unlink`. The row-level gate is open here on purpose: the state gate is the Python business rule (`_check_business_rules_unlink`, draft only), which no rule and no sudo bypasses |

---

## How to Extend Approval for a New Domain

### Step 1: Extend category selection fields

```python
# In your module's model that extends approval.category:
class ApprovalCategory(models.Model):
    _inherit = "approval.category"

    approval_type = fields.Selection(
        selection_add=[("purchase", "Purchase Order")],
    )
    target_model = fields.Selection(
        selection_add=[("purchase.order", "Purchase Order")],
    )
```

### Step 2: Inherit the mixin in your model

```python
class PurchaseOrder(models.Model):
    _inherit = ["purchase.order", "mixin.approval"]

    def _get_domain_approval_category(self):
        return [("approval_type", "=", "purchase")]

    def _get_approval_required_fields(self):
        return ["partner_id", "order_line"]

    def _get_approval_reason_html(self):
        return f"<p>Purchase order {escape(self.name)}</p>"

    def _prepare_approval_request_values(self, category):
        vals = super()._prepare_approval_request_values(category)
        vals["amount"] = self.amount_total
        vals["partner_id"] = self.partner_id.id
        return vals

    # Override the PER-TRANSITION hooks, never the dispatcher.
    def _on_approval_approved(self):
        self.button_confirm()

    def _on_approval_refused(self):
        self.state = "rejected"
```

**Do not override `_on_approval_state_changed`.** It is the dispatcher;
overriding it and calling `super()` was how every satellite ended up
posting two chatter messages for one decision — the base dispatches to
`_on_approval_approved`, which posts a generic "Approval granted", and
the satellite's richer message then landed on top of it. Override the
per-transition hook instead (`_on_approval_approved`,
`_on_approval_refused`, `_on_approval_cancelled`, `_on_approval_revoked`,
`_on_approval_reset`) and omit `super()` when your message replaces the
generic one.

**Do not override `_get_approval_category` either.** The mixin owns the
whole selection algorithm — search the candidate domain, narrowed to the
document's own company plus company-less categories, in `sequence, id`
order, and return the first category whose `_is_applicable_for` accepts
the document. An EMPTY domain short-circuits to `False` without calling
`_raise_approval_category_not_configured()`: "this document type has no
approval configured" is not the same failure as "it does, and nothing
matched". Supply only the parts that vary:

| Seam | Supply when |
|------|-------------|
| `_get_domain_approval_category()` | always — which categories are candidates |
| `approval.category._is_applicable_for(document)` | your categories carry matching criteria (amount, partner, product…). Fall through to `super()` for documents you do not own, and be **fail-closed**: a category with no criteria configured must match nothing |
| `_get_approval_category_fallback(categories)` | approval can be triggered by a flag *outside* the category criteria and needs a generic category to route to |
| `_raise_approval_category_not_configured()` | "no category exists" is a configuration error worth naming, not "no approval needed" |
| `_raise_approval_category_not_matched(categories)` | same, for "categories exist but none matched this document" |

Both `_raise_*` hooks are no-ops in the base, so the documented contract
of `_get_approval_category` — return False, don't raise — still holds for
consumers that do not opt in.

**Anything that runs inside `_on_approval_*` runs inside the approver's
`action_approve` transaction**, and the core deliberately does not
swallow exceptions from it. If your hook advances the document
(`action_confirm`, `action_post`, `button_validate`), put it inside
`_approval_side_effect()`, which supplies the savepoint, the
`UserError`/`ValidationError` catch and the chatter note:

```python
def _on_approval_approved(self):
    ...
    with self._approval_side_effect(
        self.env._(
            "Approval was granted but the order could not be auto-confirmed: %(error)s"
        ),
    ):
        self.action_confirm()
```

Do not hand-roll the savepoint. Without it a failure leaves the
document's partial writes in the transaction, or poisons it so your own
warning `message_post` fails and propagates — killing the approval with
an error addressed to the wrong person. approval_stock shipped exactly
that bug (a failed auto-validate committing half-applied stock moves)
because the guard was a convention each satellite re-implemented rather
than something the mixin provided.

`_approval_decider_names(state)` is the matching helper for the other
line every hook repeats — the filter-and-join over `approver_ids` that
opens the decision message. Pass the state you mean (`"approved"`,
`"refused"`).

### Step 3: Add views for the approval button

```xml
<record id="purchase_order_form_inherit_approval" model="ir.ui.view">
    <field name="name">purchase.order.form.approval</field>
    <field name="model">purchase.order</field>
    <field name="inherit_id" ref="purchase.purchase_order_form"/>
    <field name="arch" type="xml">
        <xpath expr="//button[@name='button_confirm']" position="before">
            <button name="action_create_approval_request"
                    string="Request Approval"
                    type="object"
                    invisible="not can_request_approval"/>
            <button name="action_view_approval_request"
                    string="View Approval"
                    type="object"
                    invisible="not approval_request_id"/>
        </xpath>
    </field>
</record>
```

### Step 4 (optional): Block withdrawal when documents are linked

```python
class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    def _check_withdraw_allowed(self):
        super()._check_withdraw_allowed()
        if self.res_model == "purchase.order" and self.res_id:
            po = self.env["purchase.order"].browse(self.res_id)
            # Shared message/count formatting for all satellites:
            self._raise_withdraw_blocked(po.invoice_ids, "invoice/bill")
```

### Step 5 (optional): Ask a user a path names

A step asks whoever a field path on the request or its document names, with
`subject_model_id` and `subject_user_path`. approval_hr asks the requester's
manager through `approval.request.requester_manager_user_id`:

```python
class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    requester_manager_user_id = fields.Many2one(
        comodel_name="res.users",
        compute="_compute_requester_manager_user_id",
    )
```

### Step 6 (optional): Freeze additional value fields after submit

```python
class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    def _get_fields_locked(self):
        return super()._get_fields_locked() | {"bank_account_id"}
```

---

## Common Pitfalls

### 1. Writing approver state directly without the decision funnel

**Wrong:**
```python
approver.write({"state": "approved"})
```

This raises for every caller: `state` is projected from the decision
ledger. **Right:** use `request.action_approve()` / `action_refuse()` (or,
for non-decision terminations, `request._force_terminal(...)`). The funnel
`_apply_decision()` handles locking (`_lock_for_approval_action`), cache
invalidation, delegation resolution, chain advancement, activity
cleanup and the source-document notification. A decision taken outside
those actions -- an import of history -- is `approver._record_decision(...)`.
Routing in custom code writes `flow_state`, after locking, and calls
`_refresh_turn_states()` / `_notify_if_terminal_transition()` yourself.

### 2. Creating/deleting approvers without context

**Wrong:**
```python
self.env["approval.approver"].create({"request_id": request.id, "user_id": user.id})
```

This will be blocked by `_check_access_create()` — for regular users
unconditionally (H9), and by `_check_business_rules_create()` on any request
that is not `new` — managers and sudo included (only `env.su` **plus** the
`approver_ids_computation` context is exempt). Approvers are managed by
`_sync_approvers()`.

**Right:** Configure the category's steps: members, a group, or a path to the user to ask.

### 3. Editing value fields after submission

`amount`, `currency_id`, `quantity`, `date*`, `partner_id`, `reference`,
`location`, `reason`, `request_owner_id`, `company_id` and the source
link `res_model`/`res_id` are frozen once the request leaves draft —
enforced server-side by `_check_locked_fields()` (never bypassed, sudo
included), not just by form readonly. `currency_id` is in the set for the
same reason `amount` is: every rule threshold was evaluated
against the amount converted FROM it, so moving it after submit would
silently re-price the decision. The only sanctioned reopening is
the request-a-change flow: while `pending_change_field` is set, exactly
the flagged field (date fields or reason) is writable again — and only
for the REQUESTER (owner, manager or sudo), never for an approver, who
would otherwise be able to move a value their co-approvers already
signed. Applying the change resets those earlier approvals: `action_
resubmit()` reopens a fresh decision round (see architecture.md). To
change anything else, reset a refused/cancelled request to draft.

### 4. Forgetting to cancel activities on terminal states

When a request reaches a terminal state (approved, refused, cancelled), leftover
activities for other pending approvers must be cleaned up. `_apply_decision()`
and `_force_terminal()` handle this; if you write custom state transitions,
call `_cancel_activities()`.

### 5. Modifying category after confirmation

Category changes are blocked after `action_confirm()` by both a constraint
(`_check_category_change`, form saves) and a guard in `write()` (direct ORM
writes) — both raise via the shared `_raise_category_change_blocked()`.
The block applies to any state other than `new`: to change the category,
either create a new request, or (for refused/cancelled requests) use
`action_reset_to_draft()` — back in draft the category is editable again.

### 6. Assuming request owner can modify approvers

Request owners **cannot** add, remove, or modify approver records. All approver
management flows through `_sync_approvers()`. The owner's role is limited to:
- Creating the request
- Filling in fields (draft only — see locked fields)
- Confirming (action_confirm)
- Re-submitting after a requested change (action_resubmit)
- Cancelling a pending request (action_cancel)
- Reopening a refused/cancelled request (action_reset_to_draft)

### 7. Ignoring delegation when checking approvers

**Wrong:**
```python
approver = request.approver_ids.filtered(lambda a: a.user_id == current_user)
```

**Right:**
```python
approver = request._get_current_pending_approver()  # pending rows for env.user
# or, for arbitrary states:
approver = request.approver_ids.filtered(
    lambda a: a._get_effective_approver() == current_user
)
```

`_get_current_pending_approver()` is the single delegation-aware resolution
helper used by the header buttons, bulk actions and wizard defaults.

### 8. Not handling the `approver_ids_computation` context

When `_sync_approvers()` creates/deletes approvers via `Command.create()`/`Command.delete()`,
it runs the write under **`sudo()`** and sets `context(approver_ids_computation=True)`.
The context key alone is NOT a bypass — RPC clients control the context dict, so a
context-only escape hatch let any internal user forge approver rows. `_skip_check_access()`
therefore keys only on `env.su`/manager; the business rules (`_check_business_rules_create/unlink`
and `_check_approver_ids_business_rules`) require **both** `env.su` AND the context key.
If you add custom access/business checks on `approval.approver`, gate any
`approver_ids_computation` exemption on `self.env.su` too.

### 9. Expecting the compute to notify source documents

`_compute_state()` has NO side effects. The `_on_approval_state_changed()`
hook fires from the transitioning action via
`_notify_if_terminal_transition(old_state)`. If you add a new code path
that drives a request into a terminal state, you own the notification.

---

## Test Commands

Run from the **workspace root** (`~/Odoo`), with the venv interpreter —
the paths and the config file are the ones described in the root
`CLAUDE.md`. `<db>` should be named so it says whose it is; several
sessions share these checkouts.

```bash
# Fresh database + install + full approval suite.
# Create it THROUGH Odoo, not createdb: p314o19m.conf sets
# db_template = tpl_p314o19marin, which already carries pg_trgm,
# unaccent, vector and postgis.
p314o19m/bin/python odoo/odoo-bin -c p314o19m.conf -d <db> \
    -i approval --test-tags '/approval' --stop-after-init

# Re-run on an existing database
p314o19m/bin/python odoo/odoo-bin -c p314o19m.conf -d <db> \
    -u approval --test-tags '/approval' --stop-after-init

# Specific class / method
... --test-tags '/approval:TestCancelFlow' --stop-after-init
... --test-tags '/approval:TestCancelFlow.test_owner_can_cancel_pending' --stop-after-init

# Port 8069 is shared. Either pass --http-port <n> or, as above,
# --stop-after-init so nothing binds. Redirect to a log to grep:
... > /tmp/approval.log 2>&1
grep "tests when loading" /tmp/approval.log
grep -E "ERROR|FAIL:" /tmp/approval.log | tail -20

# Teardown
psql -U marin -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='<db>';"
dropdb -U marin <db>
```

Baseline: **506 tests, 0 failed, 0 errors** across the 28 test modules
(re-measured 2026-08-12 on a fresh install, ~90s).

JS tests use the warm HOOT runner, not `odoo-bin`. Suite ids are
`@approval/<basename without .test.js>`:

```bash
cd odoo/tooling/hoot
./hoot '@approval/category_kanban'       # or @approval/activity_patch
./hoot --affected ../../addons/approval/static/tests/<file>.test.js
```

Name the files explicitly — a bare `--affected` picks up whatever other
sessions have left in the shared worktree.

New test files should inherit `tests.common.ApprovalCommon` (shared
owner/approver/manager users + `_make_category` / `_make_request`
factories) instead of rebuilding user fixtures.

---

## "When Modifying X, Also Update Y"

| When You Modify... | Also Update... |
|---------------------|---------------|
| `approval.category.step` members, groups, conditions | PENDING requests reroute only when a step arrives or departs (`_reroute_steps_live`), so a member added to a step already applying is not asked mid-flight; DRAFTS pick the change up at `action_confirm()`, which re-syncs against the current steps |
| `approval.category` fields (has_* from `approval_app`, approval_minimum) | Existing drafts are not rewritten on the spot, but `approval_minimum` is re-derived from the category at `action_confirm()`; `has_*` are related fields, so they follow immediately |
| `_compute_state()` logic | The action methods that call `_notify_if_terminal_transition()` -- the compute itself must stay side-effect free |
| `_compute_sla_status()` logic | `_search_sla_status()` -- its SQL CASE mirrors the compute exactly; update both together |
| `_sync_approvers()` / `_get_desired_approvers()` sources | `_merge_approver_to_staging()` merge rules (required OR, sequence MIN); rows always stage 'new' (sync is draft-only) |
| `ESCALATION_RULES` constant (`approval_request.py`) | `_get_escalation_rules()` overlays `approval.escalation.<priority>.<kind>` system parameters on top of it -- do not restate the numbers elsewhere |
| `action_confirm()` validation | `_check_confirm()`, which calls `_check_enough_approvers()`; `approval_app` extends it with `_check_has_document_has_attachment()` and `_check_category_required_fields()` |
| `_LOCKED_FIELDS` / `_get_fields_locked()` | `_PENDING_CHANGE_EDITABLE` (fields reopened by the change flow) and the form view `readonly` attrs |
| `approval_type` / `target_model` selection | Both are on `approval.category` with `selection_add` -- extend there, not on request (request uses related) |
| Approver CRUD access checks | `approval_approver.py` (`_check_access_create/write/unlink`, `_check_business_rules_*`) — every o2m command on `approver_ids` reaches the row model, so the request has no second copy |
| `_check_withdraw_allowed()` override | Use `_raise_withdraw_blocked()` for the canonical message; provide clear reasons why withdrawal is blocked |
| New category fields for validation | Extend `_get_category_required_field_mapping()` in `approval_app/models/approval_request.py` |
| Terminal transitions added in new code | Route through `_apply_decision()` (decisions) or `_force_terminal()` (non-decisions) so metadata, activities and notifications stay consistent |
| SQL views (`approval_metrics`, `approver_performance`) | Both are `_auto = False` + `mixin.sql.report`, which builds the statement at query time from `_get_fields_select()` / `_get_from_tables()` / `_get_where_conditions()` / `_get_fields_group_by()`. A new field needs its own SELECT entry — the field list and the query are not linked |
| `approval.request.amount` or any threshold | `amount` is **Monetary** in `currency_id`. Never compare it to a rule threshold directly — go through `mixin.approval.threshold._convert_request_amount()`, which converts into the rule's own currency |
| Cron schedule or logic | Update `data/ir_cron_data.xml` AND the Python method (3 crons; the file is `noupdate="1"`, removals need a migration -- see 19.0.1.0.7) |
| Stored columns removed/de-stored | Add a migration (cf. 19.0.1.0.7: dropped `approver_compute_ms`, stale `sla_status` column, cleared stored draft-name placeholders) |

---

## Context Keys

| Key | Set By | Effect |
|-----|--------|--------|
| `approver_ids_computation` | `_sync_approvers()` (under `sudo()`) | Together with `env.su`, relaxes the state business-rules on `approval.approver` CRUD. Ignored without `env.su` — the key is client-forgeable via RPC context, so it is never a bypass on its own |
| `skip_wizard` | Bulk operations, crons, mixin, tests | Bypasses decision wizard, performs action directly |
| `requested_change_field` | Decision wizard (`action_confirm_change`) | Field name ('date'/'reason') consumed by `action_request_change()` inline path |
| `default_category_id` | Category kanban "New Request" | Pre-fills category on request form |
| `default_approver_id` / `default_decision_type` | `_get_decision_wizard_action()` | Pre-fills the decision wizard (decision_type: 'refuse' or 'change'). Only these two — the wizard's `request_id` is a precomputed stored compute off `approver_id`, so there is no `default_request_id` |
| `approval_acting_user_id` | `_notify_source_document_state_change()` | Carries the deciding user's id into the source document's `_on_approval_*` hook, which runs under `sudo()`. Read it to attribute a satellite's own chatter message to the approver rather than to OdooBot |
| `approval_reset_from` | `_force_draft()` | The decided state a reset to draft left (`approved`, `refused` or `cancelled`), carried into the source document's `_on_approval_reset`. The base hook words its chatter note from it |

---

## Split Model Pattern

`approval.request` is split across 7 files for maintainability. All use `_inherit = "approval.request"`:

| File | Responsibility | Method Prefix |
|------|---------------|---------------|
| `approval_request.py` | Fields, CRUD, smart-copy, `ESCALATION_RULES` | `create`, `write`, `unlink`, `copy` |
| `approval_request.py` | Fields, CRUD, copy, the state machine and the small computes, `_TERMINAL_STATES` / `_DECISION_STATES` | `_compute_*`, `create`/`write` |
| `approval_request_access.py` | Who may write, unlink, decide, re-route, reopen a refusal, withdraw another's decision; locked and compute-only fields | `_check_access_*`, `_check_locked_fields`, `_check_reset_actor`, `_check_withdraw_actor`, `_is_later_step_member` |
| `approval_request_lifecycle.py` | Every transition and what it touches: decisions, withdraw, cancel, reset, change requests, `_force_terminal`, activities, row locks | `action_*`, `_apply_decision`, `_force_terminal` |
| `approval_request_routing.py` | Who approves: `_sync_approvers`, `_get_desired_approvers` from the applicable steps, live rerouting, auto-action rules, list adoption, category snapshot | `_sync_*`, `_get_applicable_steps`, `_reroute_steps_live` |
| `approval_request_escalation.py` | When: deadline, overdue, SLA compute and search, the three crons, reminders and escalation | `cron_*`, `_compute_sla_*`, `_send_reminder` |
| `approval_request_prediction.py` | On-demand outcome prediction | `_predict_*` |

When adding a new method, place it in the file matching its responsibility.

---

## Campaign Instrumentation (TEMPORARY)

`models/approval_trace.py` and every `trace.*` call site in this module are
**scaffolding for one campaign** -- code quality, maintainability, performance
and lifecycle work on `approval` -- and are removed when it ends. Nothing in the
engine's behaviour depends on them: rendering never reads a field, the wrappers
return what they wrapped, and no target emits above INFO. A real warning belongs
on the module logger of the file that found it, not on a campaign target that a
future session deletes.

### The two switches

Every logger is `odoo.approval.<target>`, and the root `odoo.approval` is set to
`WARNING` at import unless the operator already named it, so **an ordinary server
or test run prints nothing, `--log-level=debug` included**. Ask for what you want:

```bash
# everything, at one decision per line
... odoo-bin -c p314o19m.conf -d <db> --log-handler odoo.approval:DEBUG

# one axis
... --log-handler odoo.approval.routing:DEBUG --log-handler odoo.approval.steps:DEBUG

# lifecycle only, no per-decision noise
... --log-handler odoo.approval:INFO

# everything except one target's per-item flood
... --log-handler odoo.approval:DEBUG --log-handler odoo.approval.routing.items:INFO
```

The second switch is the `odoo.approval.<target>.items` child, which a parent at
DEBUG enables too: it carries the per-item lines (one per staged approver, one per
created activity) that are useful on one request and unreadable over a batch.

### Level discipline

| Level | Call | What belongs there |
|-------|------|--------------------|
| INFO | `trace.X.note()` | One line per externally visible event: a request confirmed, decided, forced terminal, granted, reset; a cron's totals; a binding raising a request |
| DEBUG | `trace.X.event()` | One line per decision this code took, with the inputs that decided it |
| DEBUG on `<target>.items` | `trace.X.items()` | One line per item of a batch |
| DEBUG | `trace.X.span()` | Wraps a block: `ms`, `d` (call depth), `r` (`ok` / `raised:<Error>`) |

### Targets

One per concern, so a session enables the axis it is working on. `_BY_NAME` in
`approval_trace.py` is the authoritative list; this table says what each covers.

| Target | Covers |
|--------|--------|
| `access` | The guard questions and their answers: `_can_decide_step`, `_is_later_step_member`, `_get_rows_decidable_by` (who may decide right now, which the button and the state sync both ask) |
| `activity` | Activities created, not created, marked done, retired, cancelled |
| `attachment` | `ir.attachment` locking on decided requests |
| `binding` | Gating: the guard's front door (entered, or skipped for the kill switch or for no binding), selection, coverage, observation, requests raised, replay, coverage reset, checkpoints, the one-shot invoke stamp |
| `button` | What the approval button asks and does (`approval_binding_client.py`) |
| `compute` | Compute fields worth a look for cost or correctness (`_compute_state`, the kanban dashboard, minimum validity) |
| `cron` | The three crons' envelopes: batch contents, caps, totals |
| `crud` | `create` / `write` / `unlink` on the engine's own models, and which write triggered a re-route |
| `decision` | The decision funnel: actor resolution, fan-in, which steps an approval naming none is given for (the exclusivity rule), how the chain advanced, withdrawals |
| `degraded` | The third class: not a refusal and not a question -- the engine gave up on something and carried on (an unparseable subject domain, a `res_model` that left the registry). INFO, because a session debugging "why did nothing happen?" cannot find these from either of the other two |
| `delegation` | Effective approver, delegation set, superseded, handover on archive |
| `document` | The confirm-time document check: which requirements a request had, which its attachments satisfied, and which were missing -- the PASS as well as the refusal |
| `editor` | Studio's editor calls (`approval_binding_editor.py`) |
| `escalation` | Reminder/escalation triage, targets, consent approval, delegation activity reconciliation |
| `lifecycle` | State transitions of `approval.request`, round opening, bulk decisions, cascades |
| `mixin` | `mixin.approval` adopters: request raised, category matched, rate limits, hooks told |
| `perf` | The span ledger (`dump_perf_ledger()`), nothing else |
| `prediction` | `_predict_outcomes` inputs and verdicts |
| `refusal` | **Only actual refusals**: every `raise` a guard reaches, with the inputs that refused it |
| `registry` | Load-time wrapping: this campaign's own, and the bindings' |
| `report` | Dashboard and SQL-report queries |
| `routing` | `_sync_approvers`: the desired set, the plan, where each staged approver came from |
| `rules` | `approval.rule` evaluation, step conditions, auto-approve/refuse, currency conversion |
| `search` | The search helpers behind the non-stored fields, and which branch `boolean_search_domain` took for an operator |
| `snapshot` | The category snapshot taken at confirm |
| `steps` | Applicability, pools, quorum assignment, open steps |
| `subjects` | `mixin.approval.subjects` (one request per subject) |
| `sync` | `mixin.approval.state.sync`: a document's state driving its request, and back |
| `template` | `approval.template` defaults |
| `wizard` | The two wizards |

**The `refusal` invariant: a call that succeeds logs zero refusals.** A guard that
answers a question rather than declining one logs to `access`, not `refusal`. So
```bash
grep 'odoo.approval.refusal' run.log | sed 's/.*refusal: //' | cut -d' ' -f1 | sort | uniq -c | sort -rn
```
over a corpus is the ranked list of what the engine actually turns away -- and a
refusal line on a successful flow is a bug in the code or in the instrumentation.

Six things keep that list worth reading, and `tests/test_campaign_instrumentation.py`
holds each one so it stays true -- and each one was broken on purpose once to check the
test sees it (a raise with no event, two sites sharing a kind, a silent `except`, a
refusal emitted on a green path, a `CALL_TRACES` entry naming a method that does not
exist: five for five read `1 failed`):

1. **The null control.** A green flow -- confirm, two approvals, a withdrawal, a
   re-approval, a reset, a re-confirm -- runs inside `assertNoLogs` on
   `odoo.approval.refusal`. A neighbouring project's refusal census read 5,726 over
   a sweep of which 4,700 were the engine asking itself questions through the
   refusing form, and the top two rows of its ranked work list were noise. Check the
   null hypothesis the way you would check a test: on a corpus you know is handled,
   the count is zero or the census is measuring something else.
2. **Completeness.** Every `raise UserError/ValidationError/AccessError` in
   `models/`, `wizards/` and `reports/` reports a refusal first -- 145 sites, checked
   by walking the sources. A census of the sites somebody remembered is a biased
   sample, and it biases toward whatever was easy to instrument. Add a guard, add its
   event.
3. **One kind per site.** No two sites share a kind, also checked, because a shared
   raise reached by several callers silently merges several causes into one row. The
   one method that IS shared -- `_raise_not_assigned_approver`, four callers, four
   reasons -- carries no event of its own: each caller reports its own kind
   (`decision_without_a_row`, `change_request_without_a_row`, `wizard_without_a_row`)
   and the method is named in `REPORTED_BY_ITS_CALLERS` so the completeness check
   knows why it is bare.
4. **No handler swallows a failure without a word.** This is the class neither of the
   other three can see, and no refusal census can: an `except` that neither re-raises
   nor says anything. Three of the addon's twenty handlers were silent when the check
   was written. Two now report on `degraded`; the third
   (`approval.binding._get_snapshot`, where an unparseable domain empties the snapshot
   and thereby stops a binding's coverage from ever being invalidated) got a PERMANENT
   `_logger.warning` instead, because that one is a defect the campaign happens to have
   found rather than something to instrument and remove. The exemption list holds one
   entry: the renderer, whose `<unrenderable>` marker IS its report.
5. **Only refusals on the `refusal` target.** Every line on it sits in a method that
   raises, directly or through a `_raise_*` helper -- three sites use the helper so that
   several callers each report their own kind. Written after two lines were found on it
   that refuse nothing: a `_compute_usage_count` on `approval.refusal.reason` (the MODEL
   is about refusal reasons; the TARGET is about refusals) and `_parse_domain_or_warn`,
   where an unparseable domain is treated as matching nothing and the flow carries on.
   The first moved to `compute`; the second was deleted, because `_parse_domain` already
   reports it on `degraded`. Either one would have put a line on the one target whose
   whole value is that a green flow leaves it empty.
6. **No campaign line is the only statement of a body.** The campaign is DELETED at the
   end, so such a body becomes a syntax error the moment it is -- see the placement rules
   below. The check names the two hooks that are empty by omission rather than by design
   and may therefore be all line.

**Coverage, so the next pass knows where to look.** 363 of the addon's 523 methods
(69%) carry a hand-placed line or a wrapper, and the 827 lines of body that do not are
mostly `view_*` action builders, one-line getters and the two methods that ARE the
pre-campaign logging (`_log_sync_plan`, `_log_cycle`). Re-measure rather than trusting
this, and say what you counted: walk `models/`, `wizards/` and `reports/` with `ast`,
**excluding `models/approval_trace.py`** -- the kernel is the instrument, not a subject --
and count a method covered when its body holds `trace.` or its name is a key in
`CALL_TRACES`. **`CALL_TRACES` is an annotated assignment**, so a walk that matches only
`ast.Assign` finds zero wrapped methods and reads 261 of 523 instead of 332: it silently
drops the 155 names the declarative half covers, which is most of the campaign. The
worst-covered files are where the next pass should start:

```
30/48  models/approval_request.py          19/28  models/approval_request_routing.py
20/36  models/mixin_approval.py            16/29  models/approval_category.py
15/30  models/mixin_approval_state_sync.py 10/15  models/approval_binding_client.py
37/50  models/approval_binding.py          20/25  models/approval_request_escalation.py
50/62  models/approval_request_lifecycle.py 18/23  models/approval_rule.py
```

Every target fires on one suite run except `perf`, which by design speaks only on the
measurement switch.

**`migrations/` is deliberately outside the campaign.** Those files already log what they
did, on their own module logger, at INFO and WARNING -- and that logging is PERMANENT: a
migration runs once, on somebody's upgrade, and the campaign's lines are deleted before
most of them will ever run again. A campaign target there would be either deleted before
it reported anything or kept by accident. When a migration statement is silently a no-op
(`1.0.26` reports its `UPDATE` rowcount and says nothing about the three `DELETE`s that
follow), the fix is a permanent `_logger` line in that file, not a `trace.` call.

**Two placement rules the sites here follow, both learned by breaking them.**

1. **An empty extension hook cannot carry a campaign line.** `_check_approval_sync_policy`
   is `def ...: return` on purpose -- the adopter's veto point, vetoing nothing by default.
   Putting the only statement of a body on a line the campaign deletes leaves a syntax
   error behind, and ruff refuses the shape anyway (`PLR1711`, a useless `return` under a
   statement). Instrument the **call site**, which survives the deletion:
   `_apply_approval_outcome` reports `sync_policy checked=<bool>` and the hook stays bare.
   The same applies to `_raise_approval_category_not_configured` and
   `_raise_approval_category_not_matched` -- except that those two are not empty by design
   but empty by omission, so there the line belongs in the body and says so
   (`category_not_configured_unraised` on `degraded`).
2. **A line on a hot path stays silent even when the target is off.** `ViewButton.setup`
   runs for every button of every row, and its first branch is the ungated common case.
   An event there costs a dictionary literal and a second `_isApprovalGated()` call on
   every one of them, since the payload is built before `trace.event` asks whether anyone
   is listening. Instrument the branch a reader is asking about (`gating`,
   `kind_not_gated`) and leave the majority path bare, with a comment saying it is bare on
   purpose so the next pass does not "complete" it.

**The two kinds of check are not interchangeable.** The null control has a natural
oracle -- zero -- so it can be measured. Completeness has none: 62 of 145 sites reading
41 kinds is a perfectly plausible number with nothing to contradict it, which is why
these three have to enumerate the tree and name every offending site in the failure
message rather than compare a total.

### The wrapped entry points

`approval_trace.CALL_TRACES` maps model -> method -> target, and
`base._register_hook` (`models/models.py`) wraps each one at registry load, so the
engine's own files carry **no line** for any of it. One span per call:

```
odoo.approval.routing: approval.request._sync_approvers n=1 uid=2 sql=7 ms=5.595 d=1 r=ok
odoo.approval.lifecycle: approval.request.action_confirm n=1 uid=2 sql=2 ms=1.157 d=0 r=raised:UserError
```

`n` is the batch size (the `vals_list` for `create`, `self` otherwise), `sql` the
query-count delta, `d` the call depth (so the nesting reconstructs the call tree),
`r` the outcome. **Only concrete models belong in that table**: an adopter of
`mixin.approval` inherits the mixin's Python class, not its registry class, so
wrapping an abstract model reaches nobody -- the mixins are instrumented by hand.
A method named there and since renamed prints one `stale_call_traces` line on the
`registry` target at load; nothing else breaks.

### The client half

`static/src/common/approval_trace.js` is the same idea for the browser, and the same
`target event key=value` grammar, so one grep reads a flow across both halves:

```
approval.service flushed specs=3 ms=41.180 results=3
approval.button  loaded model=res.partner res_id=7 gated=true approved=false
```

It is **off unless asked for**, by either switch, because a console line costs a user
nothing and a reader everything:

```js
?approval_trace=button,service          // one page load
localStorage["approval.trace"] = "all"  // until you clear it
```

`1`, `*`, `all` or `true` mean every target. Four targets: `button` (the widget, the
hook's load/reload lifecycle, the decide/withdraw calls, the gated-model set a form
reads), `service` (the batching service -- how many specs one tick coalesced and what
the round trip cost), `activity` (approve/refuse from an activity) and `popover`
(reserved, no call site).

Mechanics worth knowing before adding a site:
- **`browser.console`, never `console`.** `addons/approval` is not in ESLint's
  `COMMUNITY_MODULES`, so `globals.browser` is not declared for it and a bare `console`
  is a `no-undef` error -- and ESLint is a repo-wide HARD ZERO. `browser.console.debug`
  also lets a test patch it, which is how `static/tests/campaign_trace.test.js` asserts
  the default silence.
- **The file carries `// @ts-check`.** `js_ts_check.py` counts client files WITHOUT it,
  so a new untyped file raises that gate by one; typed and clean, it costs nothing.
  `npx tsc --project tsconfig.json --noEmit` reports no diagnostic in `approval/static`.
- The switch is memoised on first use; `trace.forget()` drops it, which only the tests
  need.
- `view_button_patch.js` now carries the client's gating decision (`gating`,
  `kind_not_gated`, `server_gates_it`), and the kanban controller carries the one
  navigation it owns. `approval_button.js` stays uninstrumented: it is a template plus
  two delegations to the hook, which reports both. Both files were held by another session
  during an ESM `.js`-extension migration when the client half first landed, which is why
  they came late -- §12, not a judgement about their content.
- Four more carry no line because they hold no decision: `activity_model_patch.js`,
  `approver_model.js`, `activity_patch.js` and `approvals_category_kanban_view.js` are
  declarations and registrations.

### The performance switch, which is not one of the printing ones

A run with every target at DEBUG is not the run whose timings anybody wants: writing
102,333 lines dominates what it measures. So measurement has its own switch, and it
works with the targets shut:

```bash
# the whole performance run: two variables and ONE handler
APPROVAL_TRACE_SLOW_MS=25 APPROVAL_TRACE_NPLUSONE=1 \
    odoo-bin -c p314o19m.conf -d <db> --log-handler odoo.approval.perf:INFO ...
```

| Variable | Effect |
|----------|--------|
| `APPROVAL_TRACE_SLOW_MS=N` | time every wrapped entry point; report the calls at or over N ms as `slow` |
| `APPROVAL_TRACE_NPLUSONE=1` | report any call whose query count reached its row count as `n_plus_one` (implied by `SLOW_MS`) |

Both land on `odoo.approval.perf` at INFO and nothing else speaks, so the output of
such a run is the finding rather than a log to grep. Setting either also fills the
ledger. `trace.accounting()` is the predicate the wrappers and `span` consult, and it
is deliberately separate from `Target.on()`: **a test that asserts silence with
`assertNoLogs` on `odoo.approval` sets that logger to DEBUG and so makes the span it
was checking for print.** Ask `Target.on()` instead; `tests/test_campaign_instrumentation.py`
says so where it would otherwise be rediscovered.

What one such run says, on the sixteen-flow corpus behind the null control:

```
n_plus_one call=approval.category.create n=4  sql=19 per_row=4.75 ms=18.5
slow       call=approval.request.action_confirm  ms=60.3 n=1 sql=43
slow       call=approval.request.cron_consent_approval ms=26.6 n=1 sql=95
ledger call=approval.approver._create_activity calls=37 total_ms=222 worst_ms=56.9
       rows=22 sql=373 sql_per_call=10.1 sql_per_row=16.95
```

Read `n_plus_one` as a CANDIDATE list, not a verdict: a `create` legitimately issues
several statements per record, so the flags worth working are on read paths, and
`sql_per_row` is the column that separates them. A parent span's `sql` also includes
its children's, so compare siblings rather than summing the column.

### `annotate`: the batch is not always the work

A wrapped entry point knows `n`, its batch size, and nothing else -- and `_sync_approvers`
is called with ONE request and writes a plan of forty rows. The query count has to be
read against the forty, so a method that knows its own work unit says so:

```python
trace.annotate(work=len(rows_to_delete) + len(rows_to_create) + updates)
```

`work=` is reserved: the ledger and the N+1 check prefer it over `n`. Eleven sites use
it -- the sync plan, the live rows, an opening round, the three crons, the reminder
fan-out, the activity fan-out and the prediction corpus. Outside a span it is a no-op,
and it costs one thread-local read when nothing is measuring.

### The perf ledger

Every span accumulates calls, total and worst ms, rows and queries per event whenever
the performance switch is set or `perf` is at DEBUG. From a shell:

```python
from odoo.addons.approval.models import approval_trace as trace
...exercise the flow...
trace.dump_perf_ledger(top=14)    # logs the table to odoo.approval.perf at INFO
trace.perf_ledger()               # or read it as LedgerRow tuples
trace.forget_perf_ledger()        # measure one flow rather than the process
```

`LedgerRow` carries `ms_per_call`, `sql_per_call` and `sql_per_row` derived, because
those are the three numbers a reader actually ranks by.

### The wrapped layer does not exist during at-install tests

Odoo calls `register_model_hooks()` -- and so `base._register_hook`, and so
`approval_trace.instrument` -- only after every module has loaded, which is after the
at-install phase has run. **An at-install test sees the hand-placed events and no spans
at all.** The two campaign test classes that depend on wrapping are therefore
`@tagged("post_install", "-at_install")`, and a measurement that reports no spans may
be reporting the phase rather than the code.

### Adding a call site

- Keyword arguments are evaluated **before** the level check, so pass only cheap
  values (ids, counts, states). Anything that allocates or queries goes behind
  `if trace.X.on():`, and a per-item payload goes to `items()` as a lambda.
- Never `_()` a campaign message: these lines are for maintainers, and a
  translated log line breaks `grep`.
- **Pass the record, not its `_name`.** `record=self` renders `approval.request#42`
  and `records=rows` renders `approval.approver#[7,9]`, which is what you wanted
  anyway -- and that read is a site the metadata fan-in census counts
  (`tooling/architecture/mixin_coupling_check.py` greps it over `addons/`), so reading
  it here moves a figure in a CORE docstring that would have to move back when the
  campaign is removed. **This rule is a ratchet**
  (`test_no_call_site_reads_the_model_name_attribute`, ceiling 7) because writing it
  down was not enough: it was broken twice, sixteen reads the first time and five the
  second, and each time the resulting figure was misattributed to somebody else --
  once into CLAUDE.md §4 as an ORM defect that did not exist. **The census scans
  `tests/` too**, so the guard BUILDS the token instead of spelling it; a guard that
  names what it counts adds three to the count, which is how the second
  misattribution happened.
- Never log above INFO, and never make behaviour depend on a target being on.

### What it costs

Measured 2026-09-11 on this machine, 200 create -> confirm -> approve cycles per
sample after 20 warm-up cycles, against a detached worktree at the same base as
the control:

| Tree | p50 | p90 |
|------|-----|-----|
| control (HEAD, no campaign) | 54.8 ms / 30.7 ms | 59.5 ms / 41.1 ms |
| instrumented, every target quiet | 54.2 ms / 31.1 ms | 59.1 ms / 40.8 ms |
| instrumented, `odoo.approval:DEBUG` | 41.7 ms / 33.3 ms | 59.0 ms / 41.1 ms |

Two interleaved pairs, because the machine is shared and the absolute figures
move by 40% between runs: the control/instrumented pairs differ by -1.0% and
+1.3%, i.e. **the cost with the targets quiet is below this machine's noise**, and
with every target at DEBUG it is a few percent plus the cost of writing the lines
(102,333 of them over the 819-test suite).

The debt it does add is length, measured with the gates' own runners:

```
py_class_length.py    --addon approval --count   4423 -> 5796  (+1373)
py_function_length.py --addon approval --count    159 ->  269   (+110)
```

Neither floor was moved: `pyclasslen_addons` and `pyfunclen_addons` are already
over their floors at HEAD for reasons that predate this work, and a scaffolding
campaign is the wrong thing to bank a floor against. **Removing the campaign
returns both numbers**, which is the point of writing them down here.
`c901` (approval: 1), the AST lint rules (`py_lint.py`, 0 in approval) and
`ruff`/`ruff format` are unchanged.

### Removing the campaign

```bash
grep -rn 'approval_trace\|trace\.[A-Z]' odoo/addons/approval --include='*.py'
grep -rn 'approval_trace\|trace\.\(on\|event\|note\|span\)' \
    odoo/addons/approval --include='*.js'
```
is the whole surface (the second line is the client half, plus
`static/tests/campaign_trace.test.js` and `tests/test_campaign_instrumentation.py`,
which are tests OF the campaign and go with it).

Delete `models/approval_trace.py` and its entry in `models/__init__.py`, the two
`_register_hook` / `_unregister_hook` overrides in `models/models.py`,
`static/src/common/approval_trace.js`, both test files, and every `trace.*` call. Some
calls sit in a small restructuring -- a `matches` / `pool` / `wanted` local introduced
so the value could be logged once; inline it back or keep it, it reads the same either
way. **Two things stay behind on purpose**, because the campaign found defects rather
than instrumenting them: the `_logger.warning` in `approval.binding._get_snapshot` (an
unparseable domain empties the snapshot and stops a binding's coverage from ever being
invalidated) and the `browser.console.warn` in `useApprovalButton`'s `load` (a gate
that cannot be read shows the button ungated, which used to happen in silence).

**What predates the campaign and stays**: the module loggers
(`_logger = logging.getLogger(__name__)`) in `approval_request.py`,
`approval_request_routing.py`, `approval_request_lifecycle.py`,
`approval_request_escalation.py`, `approval_binding.py`, `approval_rule.py`,
`mixin_approval_domain.py` and `res_users.py`, together with
`_log_sync_plan` / `_SYNC_LOG_PREFIX`, `_log_cycle` / `_CYCLE_LOG_PREFIX`, and
every `_logger.warning` / `.info` / `.exception` in the module. Those are the
engine's own diagnostics and they are not this campaign's to remove.
