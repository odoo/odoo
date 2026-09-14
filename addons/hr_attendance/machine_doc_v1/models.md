# hr_attendance — models

## Where the code is

| File | Declares |
|---|---|
| `models/hr_attendance.py` | `hr.attendance`, both crons, the schedule-zone helpers, the overtime deferral |
| `models/hr_attendance_overtime.py` | `hr.attendance.overtime.line` |
| `models/hr_attendance_overtime_rule.py` | `hr.attendance.overtime.rule` |
| `models/hr_attendance_overtime_ruleset.py` | `hr.attendance.overtime.ruleset` |
| `models/hr_employee.py` | the employee's attendance state, hour totals and presence |
| `models/hr_version.py` | `ruleset_id` on `hr.version` |
| `models/res_company.py` | the kiosk, cron and overtime switches |
| `models/res_config_settings.py` | their settings mirror |
| `models/res_users.py` | `_clean_attendance_officers()` |
| `models/ir_http.py` | `attendance_user_data` in the session |
| `controllers/main.py` | every HTTP route, kiosk and systray alike |
| `tools/debug_log.py` | the four debug loggers |
| `tools/demo.py` | the sample-data generation `demo/` calls |

Every field this module declares is named here; `factcheck.sh` asserts it, so a
field added without a line in this file fails the gate.

## hr.attendance

One check-in/check-out span. `_order = "check_in desc"`, and it carries
`mixin.mail.thread` so the crons can say why they touched it.

| Field | Type | Notes |
|---|---|---|
| `employee_id` | Many2one | required, `ondelete="cascade"`, group-expanded by `_read_group_employee_id` |
| `check_in` | Datetime | required, tracked |
| `check_out` | Datetime | tracked; empty means still there |
| `date` | Date | stored, **the employee's local day**, from `_schedule_tz()` |
| `worked_hours` | Float | stored; the span minus the schedule's breaks |
| `expected_hours` | Float | stored; `worked_hours` minus what the RULES computed, not minus a manager's correction |
| `overtime_hours` | Float | stored; sums `manual_duration`, so a correction moves it |
| `validated_overtime_hours` | Float | stored; the approved part only |
| `overtime_status` | Selection | to_approve / approved / refused, derived from the lines |
| `linked_overtime_ids` | One2many | the real relation the derived fields depend on |
| `color` | Integer | list-view decoration: stale open, over sixteen hours, technical |
| `is_manager` | Boolean | may the reader approve this one |
| `department_id`, `manager_id`, `attendance_manager_id` | Many2one | related, for filtering |
| `device_tracking_enabled` | Boolean | related to the company switch |
| `in_mode`, `out_mode` | Selection | kiosk / systray / manual / technical, and `auto_check_out` on the way out |
| `in_latitude`, `in_longitude`, `in_location`, `in_ip_address`, `in_browser` | | where the check-in came from |
| `out_latitude`, `out_longitude`, `out_location`, `out_ip_address`, `out_browser` | | and the check-out |

`copy()` raises: an attendance is a record of something that happened.

## hr.attendance.overtime.line

One priced piece of overtime. `_order = "time_start"`.

| Field | Type | Notes |
|---|---|---|
| `attendance_id` | Many2one | `ondelete="cascade"`; the real join, not a datetime match |
| `employee_id` | Many2one | required |
| `date` | Date | the local day it is filed under |
| `duration` | Float | **what the rules computed** |
| `manual_duration` | Float | what stands, defaulting to `duration`; a manager edits this |
| `status` | Selection | to_approve / approved / refused; defaults by the company's validation mode |
| `amount_rate` | Float | combined from the paid rules that applied |
| `rule_ids` | Many2many | which rules produced it |
| `time_start`, `time_stop` | Datetime | the attendance's own span, constrained stop > start |
| `company_id` | Many2one | related |
| `is_manager` | Boolean | the same verdict `hr.attendance.is_manager` gives |

`duration` and `manual_duration` are not interchangeable. `_regeneration_key()`
identifies a line across a regeneration by `duration`, so a correction to
`manual_duration` survives one; a change to `duration` is a different line.

## hr.attendance.overtime.rule

| Field | Type | Notes |
|---|---|---|
| `name` | Char | required |
| `description` | Html | |
| `base_off` | Selection | `quantity` (how much) or `timing` (when) |
| `quantity_period` | Selection | `day` or `week`, for a quantity rule |
| `expected_hours` | Float | the fixed threshold |
| `expected_hours_from_contract` | Boolean | take the threshold from the schedule instead |
| `timing_type` | Selection | work_days / non_work_days / leave / schedule |
| `timing_start`, `timing_stop` | Float | hours of the day; start > stop wraps midnight |
| `resource_calendar_id` | Many2one | the schedule a `timing_type="schedule"` rule is outside of |
| `employee_tolerance` | Float | shortfall forgiven before undertime is recorded |
| `employer_tolerance` | Float | excess forgiven before overtime is |
| `paid` | Boolean | does this rule pay |
| `amount_rate` | Float | at what rate |
| `sequence` | Integer | |
| `ruleset_id` | Many2one | required |
| `company_id` | Many2one | related to the ruleset's |
| `information_display` | Char | the one-line summary the form shows |

## hr.attendance.overtime.ruleset

| Field | Type | Notes |
|---|---|---|
| `name` | Char | required |
| `description` | Html | |
| `rule_ids` | One2many | |
| `rules_count` | Count | |
| `rate_combination_mode` | Selection | `max` or `sum` of the excesses over 1.0 |
| `company_id`, `country_id` | Many2one | |
| `active` | Boolean | |

`action_regenerate_overtimes()` re-prices every attendance of every employee on
a version subject to this ruleset, from the earliest such version's date.

## hr.version (extended)

| Field | Type | Notes |
|---|---|---|
| `ruleset_id` | Many2one | which rules apply during this version, `groups="hr.group_hr_manager"` |

This is the binding that makes overtime a property of the period an employee
worked rather than of the employee.

## hr.employee (extended)

| Field | Type | Notes |
|---|---|---|
| `attendance_ids` | One2many | officer-only |
| `last_attendance_id` | Many2one | stored, computed from the latest `check_in` |
| `last_check_in`, `last_check_out` | Datetime | related to it, stored |
| `attendance_state` | Selection | checked_in / checked_out |
| `hours_today`, `hours_previously_today`, `last_attendance_worked_hours` | Float | not stored; the systray's figures |
| `hours_this_month`, `hours_this_month_overtime`, `hours_this_month_display` | | not stored |
| `overtime_ids` | One2many | the employee's lines |
| `total_overtime` | Float | approved lines only, `compute_sudo` |
| `display_extra_hours` | Boolean | related to the company switch |
| `attendance_manager_id` | Many2one | the approver; setting it adds them to the officer group |
| `attendance_pin_failure_count`, `attendance_pin_retry_after` | | the kiosk PIN throttle |

The not-stored ones declare `@api.depends` on `attendance_ids` and `tz`. They
did not, and were computed once and held.

## res.company (extended)

`attendance_kiosk_key` and `attendance_kiosk_url` are the kiosk's address and
its only credential. `attendance_kiosk_mode`, `attendance_barcode_source`,
`attendance_kiosk_delay`, `attendance_kiosk_use_pin` configure the page;
`attendance_from_systray` and `attendance_device_tracking` the other entry
point and what it records. `auto_check_out` with `auto_check_out_tolerance`,
`absence_management`, `attendance_overtime_validation` and
`hr_attendance_display_overtime` drive the crons and the approval flow.

`res.config.settings` mirrors all of them except the kiosk key, which is a
credential and is regenerated rather than typed.

There is no company-level overtime tolerance. `overtime_company_threshold` and
`overtime_employee_threshold` were that, and the rule engine replaced them with
`employer_tolerance` and `employee_tolerance` on each
`hr.attendance.overtime.rule`, which is where a tolerance has to live once
different rules can price the same hour differently.

## res.users (extended)

`_clean_attendance_officers()` removes from the officer group any user who is
no longer the attendance manager of anybody.

## ir.http (extended)

`lazy_session_info()` adds `attendance_user_data` so the systray has the
employee's day without a second round trip.
