# hr_attendance — machine doc v1

Attendance recording: an employee checks in and out, the module prices what
they worked against the schedule they were on, and files the excess as overtime
lines a manager can approve or correct.

Read this first, then [architecture.md](architecture.md) for how the pieces
fit, [models.md](models.md) for the data, and
[conventions.md](conventions.md) for the contracts a change must not break.

Every figure below is derived by `factcheck.sh` from the tree and asserted
against this document. None of them is typed by hand here or there.

## Key Statistics

| | |
|---|---|
| Version | 2.4 |
| Application | yes |
| License | LGPL-3 |
| Dependencies | `hr`, `barcodes`, `geocoding` |
| ORM models (new) | 4 in `models/` |
| Models extended | `hr.employee`, `hr.version`, `ir.http`, `res.company`, `res.config.settings`, `res.users` |
| Python model files | 10 |
| Python test files | 21 |
| HTTP routes | 13 |
| Cron jobs | 2 |
| Security groups | 5 |
| JavaScript source files | 14 |
| Migration script directories | 4 |

## What it owns

| Model | Role |
|---|---|
| `hr.attendance` | one check-in/check-out span, and everything derived from it |
| `hr.attendance.overtime.line` | one priced piece of overtime, attached to an attendance |
| `hr.attendance.overtime.rule` | one rule for pricing it |
| `hr.attendance.overtime.ruleset` | the set of rules a version is subject to |

`hr.version` is both declared and extended here: the module adds `ruleset_id`
to it, which is what binds an employee's schedule period to a set of overtime
rules.

## The two entry points that are not a form

**The kiosk** is a public page at `/hr_attendance/<token>`, where `<token>` is
`res.company.attendance_kiosk_key`. The token is the whole of the
authentication: every kiosk route is `auth="public"` and gated only by it.
See *The kiosk surface* in [architecture.md](architecture.md).

**The systray** is `/hr_attendance/systray_check_in_out`, `auth="user"`, which
acts for `request.env.user.employee_id` and nobody else.

## Crons

| XML id | What it does |
|---|---|
| `hr_attendance_check_out_cron` | closes attendances of employees who never checked out, at their day's budget |
| `hr_attendance_absence_cron` | files a technical attendance for an employee who was expected and left no record |

Both are swept in `models/hr_attendance.py`. The auto-check-out one uses the
overtime deferral; the absence one deliberately does not, for a reason
[conventions.md](conventions.md) records.

## The test files

| File | Asks |
|---|---|
| `test_hr_attendance_process.py` | the check-in/check-out flow end to end |
| `test_hr_attendance_constraints.py` | overlap, ordering and the future check-in |
| `test_hr_attendance_derived_fields.py` | an attendance follows its overtime lines |
| `test_hr_attendance_derived_freshness.py` | the hour totals follow the attendances, and `expected_hours` ignores a manager's correction |
| `test_hr_attendance_schedule_zone.py` | one attendance, one zone — lunch, `date`, the version fixed point, flexible resources |
| `test_hr_attendance_timezone.py` | which day an overtime line is filed under, and schedule zone beating personal zone |
| `test_hr_attendance_night_window.py` | a timing rule whose window wraps midnight |
| `test_hr_attendance_deferral.py` | the overtime deferral prices once and prices the same |
| `test_hr_attendance_overtime.py` | the rule engine's quantity and timing arithmetic |
| `test_hr_attendance_rulesets.py` | rate combination, regeneration and the ruleset's reach |
| `test_hr_attendance_undertime.py` | the shortfall side of the same engine |
| `test_hr_attendance_expected_hours_hook.py` | the extension point a downstream module overrides |
| `test_hr_attendance_presence.py` | the evidence/inference asymmetry |
| `test_hr_attendance_manager.py` | who may approve, and what approving does |
| `test_hr_attendance_security.py` | an employee sees their own overtime lines and no others |
| `test_hr_attendance_kiosk.py` | the kiosk routes, their authorisation, and the settings route |
| `test_hr_attendance_pin.py` | the PIN throttle, at the model and at the route |
| `test_hr_attendance_domain_translation.py` | the controller's domain allowlist |
| `test_hr_attendance_audit.py` | the regressions this module's audit pinned, each named for its defect |
| `test_load_scenario.py` | `data/scenarios` loads |
| `test_performance.py` | the sweep's query count and batch cost |

## Migrations

| Version | What it does |
|---|---|
| `2.1` | back-fills `hr.attendance.overtime.line.attendance_id`, the column that made the line-to-attendance join real instead of a `(employee_id, check_in)` match |
| `2.2` | reports any company that had set one of the removed overtime thresholds, before the ORM drops the columns |
| `2.3` | fills a kiosk key for any company that had none, before the column becomes `required` and unique |
| `2.4` | drops `hr_employee.last_check_in` and `last_check_out`: both are read off `last_attendance_id` now, and the ORM never drops the column of a field that stops being stored |

Neither drops a column it did not create. `ir.model.fields._drop_columns()`
removes the column of a field a module stopped declaring, during the upgrade
that removes the field record — which is why `2.2` runs in `pre` and not in
`post`: by `post` the column is gone and there is nothing left to read.

## Extension Points

Methods other modules override or are expected to. Each is asserted to exist by
`factcheck.sh`, so advertising one that has been renamed fails the gate.

- `_get_employee_calendar()` — which schedule prices this attendance.
  `enterprise/hr_work_entry_attendance` overrides it to prefer a contract's.
- `_schedule_version()` — which `hr.version` that schedule comes from.
- `_worked_hours_between()` — hours worked in a span, breaks deducted.
- `_lunch_intervals()` — the breaks that span deducts.
- `_scheduled_hours_on()` — worked hours the schedule places on a local day.
- `_update_overtime()` — regenerate the overtime of a period.
- `_deferring_overtime()` — do several of the above and price once.
- `_attendance_action_change()` — check the employee in, or out if they are in.
- `_get_attendance_systray_data()` — what the systray and kiosk show.

## Instrumentation

`tools/debug_log.py` holds four loggers under `odoo.addons.hr_attendance.debug`,
on the pattern hr, project, stock, point_of_sale and web also carry.

| Logger | Answers |
|---|---|
| `logic` | which branch a decision took, and on what |
| `performance` | how long a sweep took and over how many records |
| `pipeline` | which schedule, version and zone priced an attendance |
| `lifecycle` | a record created, closed, regenerated or deleted |

Arm the family, not one logger:

```
--log-handler odoo.addons.hr_attendance.debug:DEBUG
```

Every call site imports the module as `dbg`, so `grep -rn 'dbg\.' addons/hr_attendance`
is the whole of it.

## Running the tests

```
odoo-bin -c <conf> -d <db> -u hr_attendance --test-enable \
    --test-tags '/hr_attendance' --stop-after-init --http-port <yours>
```

`--no-http` skips 5 `HttpCase` classes as `INFRASTRUCTURE UNAVAILABLE` and
reports them as errors, not as failures: `TestHrAttendanceKiosk`,
`TestKioskRouteAuthorisation`, `TestKioskSettingsModeIsNotSelfServe`,
`TestKioskPinRouteThrottle` and `TestHrAttendanceOvertime`. A `--no-http` run
says nothing about them either way — the lane reports a clean number over the
tests it did run, and an error count is not a failure count.

The JS tests are not in the default HOOT lane. `WebSuite.test_ui` runs
`@web/ui` alone, so this module's suites need naming:

```
--test-tags '/web:WebSuite.test_ui[@hr_attendance/attendance_list_view]'
```
