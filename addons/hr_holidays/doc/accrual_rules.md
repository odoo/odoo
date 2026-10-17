# Accrual Rules: Steps 1 and 2

## Employee Seniority

Use the existing stored `hr.employee.first_contract_date` in employee domains.
In this version it is computed by `_get_first_contract_date()` from the latest
consecutive employment versions, not necessarily the employee's earliest-ever
contract. Reuse that HR definition rather than introducing a second start date.

`hr.employee.seniority` is a non-stored, read-only display value computed using
calendar years, months and days. Missing or future contract starts have no
seniority; a contract starting today shows zero duration. The field has the same
HR access restriction as `first_contract_date` and is not searchable.

For the POC, build seniority conditions using `first_contract_date` with relative
date ranges. The accrual rule form uses a dedicated domain widget which exposes
the relative-range choice without enabling debug mode or its code editor. Odoo's
standard date-domain conversion and matched-record counter are reused.

The neighboring rule/domain model in this checkout is `hr.time.rule`, defined in
`hr_work_entry` and extended by `hr_attendance` and `hr_holidays`. Its
`employee_domain` field is the naming and UI reference. No execution or chatter
behavior is copied into the accrual skeleton.

## Rule and Allocation Model

`hr.leave.accrual.rule` owns the employee domain, country/company scope, time type,
frequency, amount, period anchor and validity configuration. The allocation unit
is read-only and comes from `hr.work.entry.type.unit_of_measure`. Conditional
requirements are enforced both by the form and model constraints.

Managers configure rules under Time Off / Configuration / Accrual Rules. Officers
have read access; company restrictions apply to all operations.

`hr.leave.allocation.accrual_rule_id` records the originating rule. It is hidden
on allocation forms; a smart button opens the linked rule. Start dates stay
editable for officers after validation. Existing plan models and fields remain
available for the later migration.

## Deferred Work

Time Off administrators can use **Run Rule** to create validated, zero-balance
allocations for active employees matching the domain and company/country scope.
The action opens the linked allocations. Existing employee/rule pairs are reused;
rerunning never adds balance or overwrites adjustments. A database constraint
enforces the employee/rule identity. Employee matching runs with the caller's
access rights, without elevation or executable domain evaluation.

Saving a rule alone does not create allocations. Periodic execution, accrual
calculation, expiry application, caps, carry-over and migration remain deferred
to Steps 3 through 7. The manual action only creates allocation shells; it does
not yet apply the configured frequency, amount or expiry to those allocations.
Yearly renewal and rebasing after allocation start-date edits still require an
engine-level decision.
