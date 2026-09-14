# hr_attendance — architecture

## The shape of it

An attendance is a span. Everything else in the module is derived from that
span and from the schedule the employee was on when they worked it.

```
  check in ──────────────────────────► check out
      │                                     │
      │  _schedule_version()  ── which hr.version was in force
      │        │
      │        ├── _schedule_tz()            the zone it is written in
      │        └── _get_employee_calendar()  the schedule itself
      │
      ├── date            the local day it is filed under
      ├── worked_hours    the span, minus the schedule's breaks
      └── create/write/unlink
              └── _update_overtime()
                      ├── _overtime_windows()               which periods moved
                      ├── _attendances_in_overtime_windows() close them over neighbours
                      ├── delete the lines of those periods
                      └── rule_ids._generate_overtime_vals() price them again
```

## One attendance, one zone

The single most load-bearing rule in the module, and the one it did not used to
follow. Three different zones were in use at once — the employee's current
schedule, the resource's own zone, and the version's — and they disagree for
anyone whose personal zone or schedule is not the one their work contact
carries.

`_schedule_version()` is now the only answer, and everything reads it:

| Reader | Uses |
|---|---|
| `date` | `_schedule_tz()` |
| `worked_hours` | `_schedule_tz()` and `_lunch_intervals()` |
| the overtime day | `_get_localized_times()`, which is `_schedule_tz()` |
| the auto-check-out day | `_local_check_in()`, which is `_schedule_tz()` |

**Which day the version is chosen by is itself circular** — the local day needs
the zone, the zone comes from the version. `_schedule_version()` resolves it as
a bounded fixed point: pick by the UTC date, localise in that version's zone,
re-pick by the local day, stop when it stops moving. A zone offset is less than
a day, so it settles in one step. Two versions whose zones each push the day
onto the other have no fixed point; the bound is what makes that stop rather
than loop.

It is resolved once per span and handed down, because `_worked_hours_between()`
otherwise asks for it four times over.

## The overtime pipeline

`_update_overtime(windows=None)` is the whole of it. It runs on every create,
write that touches `employee_id`/`check_in`/`check_out`, and unlink.

1. **Which periods moved.** `_overtime_windows()` returns
   `{employee: (first_local_date, last_local_date)}` for the closed attendances
   of `self`. `windows` carries periods `self` no longer describes — the day an
   attendance moved away from, the day a deleted one stood on.
   `_round_overtime_window()` widens each to whole weeks where any rule the
   employee has ever had is weekly, because a weekly rule sums a whole week.

2. **Close them.** `_attendances_in_overtime_windows()` grows each window until
   it contains every attendance that shares a day or week with one already in
   it, then returns the window and those attendances. It is a fixpoint loop for
   the same reason: adding an attendance can widen the window, which can admit
   another.

3. **Delete and re-price.** Every line in those periods is deleted and rebuilt.
   A manager's approval or manual correction survives if the rebuilt line is
   identical in attendance, day, rules and computed amount —
   `_regeneration_key()` is that identity. A real change drops the line back to
   its default.

4. **Rules.** Attendances are grouped by the ruleset of the version that covers
   them, and each ruleset's `rule_ids._generate_overtime_vals()` produces the
   line values.

### Deferral

A sweep that changes many attendances pays for step 3 once per change, over
periods that mostly overlap. `_deferring_overtime()` is a block those
operations record into instead, priced once on the way out. `_cron_auto_check_out`
uses it.

**Inside the block the fields the regeneration produces hold stale values** —
`overtime_hours`, `validated_overtime_hours`, `overtime_status`,
`linked_overtime_ids`. A caller that reads them between two deferred operations
reads what they held before the block. That is why `_cron_absence_detection`
does not use it: it drops a marker whose `overtime_hours` came out zero, and
deferred, every marker is zero.

## The rules

Two kinds, and they are not variants of each other.

**Quantity** (`base_off = "quantity"`) asks *how much*: hours beyond
`expected_hours`, or beyond what the contract's schedule holds, per `day` or
per `week`. The period is summed across every attendance in it, which is why
the window has to close over neighbours before anything is priced.

**Timing** (`base_off = "timing"`) asks *when*: hours falling inside a window,
on working days, non-working days, during a leave, or outside a named
schedule. A window whose `timing_start` is greater than its `timing_stop`
wraps midnight — 22:00 to 06:00 — and is built as the complement of
[06:00, 22:00] inverted within the day, then reassembled per day, so a shift
crossing midnight earns on both sides and each side is filed under its own day.

Where several rules cover the same hour, `_record_overlap_intervals()` splits
the span at every boundary so each piece carries exactly the set of rules that
apply to it, and `_extra_overtime_vals()` combines their rates by the ruleset's
`rate_combination_mode` — the highest, or the sum of the excesses over 1.0.

## Undertime

A quantity rule whose period came out *short* produces a negative line, but
only where the company has `absence_management` on and the shortfall exceeds
`employee_tolerance`. Where several rules each report a shortfall for one day,
the smallest is the one owed.

`_cron_absence_detection` is the other half: an employee who was expected and
left no attendance at all gets a one-second technical attendance at their local
midnight, so the rules have something to price. If it prices to nothing, the
marker is deleted again.

## The kiosk surface

`/hr_attendance/<token>` renders a page whose entire authentication is the
token. Every route it calls is `auth="public"`:

| Route | Does | Runs as |
|---|---|---|
| `employees_infos` | lists employees for manual selection | superuser |
| `attendance_employee_data` | that employee's day | superuser |
| `manual_selection` | checks in/out, PIN-gated | superuser |
| `attendance_barcode_scanned` | checks in/out by badge | superuser |
| `set_settings` | changes the kiosk mode | the caller |
| `create_employee`, `set_badge`, `get_employees_without_badge` | setup, trial mode only | the caller |

The first four are deliberately superuser: a visitor at the kiosk is not a
user. The last three are deliberately not, so a public visitor is refused by
the ORM and the route turns that refusal into a message.

**Every route answers a refusal the same way**, `{"status": "error"}` with an
optional `message`. Four shapes were in use for one situation before that, one
of which was an uncaught `AccessError` reaching the client as an HTTP 500.

`employees_infos` takes a domain from the client and runs it as superuser, so
its allowlist — `name` and `department_id`, `=` and `ilike` — is the whole of
the access control on that call. Anything it does not positively recognise is
refused.

## The PIN

`_check_attendance_pin()` is what stands between a four-digit PIN and anyone
holding the kiosk URL, because the keypad's own back-off runs in the caller's
browser. It counts failures, doubles the delay past three of them, and caps at
a minute. Attempts made while throttled still count, so a caller that retries
on a timer escalates rather than pinning the delay at whatever first triggered
it.
