# automation — Architecture

## Core Mechanism: ORM Hook Patching

The trigger system works by **dynamically patching ORM methods at the model
class level** when the registry loads. This is the most powerful part of the
module: automations are completely transparent to business models.

### Patch Lifecycle

```
module load / automation CRUD
        ↓
_update_registry()
        ↓
_unregister_hook()   ← delattr: removes all previously patched methods
        ↓
_register_hook()     ← iterates all active automations, patches relevant models
        ↓
registry_invalidated = True  ← signals other workers to reload
```

### Methods Patched Per Model

| Patched Method | Trigger(s) | Factory Function |
|----------------|-----------|-----------------|
| `create` | CREATE_TRIGGERS | `make_create()` |
| `write` | WRITE_TRIGGERS | `make_write()` |
| `_compute_field_value` | WRITE_TRIGGERS | `make_compute_field_value()` |
| `unlink` | `on_unlink` | `make_unlink()` |
| `message_post` | `on_message_received`, `on_message_sent` | `make_message_post()` |
| `_onchange_methods[field]` | `on_change` | `make_onchange(rule_id)` |

`_get_actions()` is backed by `@ormcache` (`_get_automation_ids`). It runs on
every patched ORM call before we know whether a rule applies — measured at one
SELECT per call — so the result is cached and invalidated by
`automation.rule.create/write/unlink`, which clear it **unconditionally**: the
cache stores execution order as well as membership, so a bare `sequence` edit
changes the answer just as much as a `CRITICAL_FIELDS` one.

The factory-function pattern (closures) is **mandatory** — it prevents the
classic loop-closure bug where all patched methods end up sharing the last
iteration's `origin` variable.

### Patch Idempotency

`patched_models = defaultdict(set)` tracks which models have been patched for
each method name. A model is only patched once per method, regardless of how
many automation rules target it.

---

## Execution Flow by Trigger Type

### CREATE / WRITE Triggers

```
record.create(vals_list)          ← patched
    │
    ├─ _get_actions(records, CREATE_TRIGGERS)   → active automations (ormcache)
    ├─ create.origin(...)                        → call original method
    └─ for automation in automations:
           automation._process(
               automation._filter_post(records, feedback=True)
           )
```

```
record.write(vals)                ← patched
    │
    ├─ _get_actions(records, WRITE_TRIGGERS)
    ├─ pre = {a: a._filter_pre(records) for a in automations}  ← snapshot before
    ├─ old_values = {record.id: {field: value} ...}            ← snapshot values
    ├─ write.origin(...)                                         ← original write
    └─ for automation in automations:
           records, domain_post = automation._filter_post_export_domain(pre[a])
           automation._process(records, domain_post=domain_post)
```

### TIME Triggers (Cron)

```
ir.cron: "Automation Rules: check and execute"
    │
    _cron_process_time_based_actions()
    │
    for automation in active TIME_TRIGGER automations:
        records = automation._search_time_based_automation_records(until=now)
        for record in records:
            automation._process(record)
        automation.last_run = now
```

`_search_time_based_automation_records()` builds a time window domain:
`[last_run, until]` shifted by the configured delay (`trg_date_range`,
`trg_date_range_type`, `trg_date_range_mode`). Calendar-aware mode uses
`resource.calendar.plan_days()` and falls back to Python-level filtering.

### WEBHOOK Trigger

Not in this module. The automation_webhook bridge, which depends on automation
and integration and installs itself wherever both are present, adds the
on_webhook value, the POST /web/hook/<uuid> route, the inbound gate and the fields
they use, and runs the rule's `_process` on the record its getter returns.

### MAIL Triggers

```
record.message_post(...)          ← patched
    │
    message = _message_post.origin(...)
    │
    Skip if: __action_done in context, or message is internal/notification
    │
    mail_trigger = "on_message_received"  if author is customer/external
                   "on_message_sent"      if author is internal user
    │
    for automation in matching automations:
        automation._process(automation._filter_pre(self))
```

### MANUAL Trigger (on_hand) — Phase 1

```
automation.action_manual_trigger()
    │
    ├─ has_dag (any action has predecessor_ids):
    │      for record in filtered_records:
    │          runtime = automation.runtime.create(res_model, res_id)
    │          runtime.action_start()    ← creates runtime.line DAG from definition
    │          runtime.action_run_all()  ← runs all branches to completion
    │      return act_window → automation.runtime form/list
    │
    └─ no DAG (simple automation):
           records = env[active_model].browse(active_ids)
           _process(filtered_records)   ← direct execution, no runtime created
```

---

## _process() — Core Dispatch

```python
def _process(self, records, domain_post=None):
    # 1. Deduplicate: skip records already processed by this automation
    automation_done = context["__action_done"]
    records -= automation_done.get(self, recordset())

    # 2. Mark as done (prevents recursion)
    #    In __action_feedback mode: mutate dict in-place (allows re-check during filter)
    #    Normal mode: copy dict, attach to new context

    # 3. Field-level trigger filtering
    records = records.filtered(self._check_trigger_fields)

    # 4. Execute each server action on each record, in an order that
    #    satisfies predecessor_ids (sequence breaks ties). Plain
    #    sorted("sequence") ignored the declared graph entirely.
    for action in self.sudo().action_server_ids._sorted_by_dependency():
        for record in records:
            action.with_context(active_model, active_id, active_ids).run()
```

The `__action_done` context dict is the recursion guard. It maps
`automation → records_processed` and prevents the same automation from
running twice on the same record within one transaction.

---

## Cron Interval Calculation

`_get_cron_interval()` computes the optimal cron frequency:

```
delays = [trg_date_range * MINUTES_PER_DELAY_UNIT[type] for each time automation]
tolerance_interval = min(delays) * 0.10    # 10% of shortest delay
interval = clamp(tolerance_interval, MIN=1, MAX=240)   # minutes
```

If no time automations exist: `interval = 240 minutes` (4 hours).

The cron interval is only updated downward (if new automations need a faster
schedule). It is not automatically increased when short-delay automations are
removed — manual cron reset may be needed.

---

## Registry Invalidation Pattern

When an automation is created, modified, or deleted:

1. `_update_cron()` — adjusts cron frequency, activates/deactivates cron job
2. `_update_registry()` — calls `_unregister_hook()` then `_register_hook()`,
   sets `registry.registry_invalidated = True`
3. Other workers detect `registry_invalidated` and reload, picking up new patches

This means automation changes take effect **immediately** in the current
worker and **on next request** in other workers.
