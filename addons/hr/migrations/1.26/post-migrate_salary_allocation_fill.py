r"""Post-migration: drain the rescued splits into hr.employee.bank.allocation.

`pre-migrate_salary_allocation_stash` copied the many2many rows and their jsonb
amounts into a scratch table, because the old storage is unreadable by `post`
and the new table does not exist in `pre`. This is the other half.

Written with raw SQL rather than `create()` on purpose. The model carries an
`@api.constrains` that the percentage allocations of one employee total exactly
100, and a database being upgraded is not guaranteed to satisfy it: the old
jsonb was maintained by a compute that could be bypassed by any code writing the
many2many directly, and `hr_payroll_account._set_bank_account` does exactly that.
Refusing to upgrade a database because data already in it breaks a constraint
this commit introduces would be a migration failing over a pre-existing
condition. The rows are moved as they are, and the totals are REPORTED so a
reader can find them, which is the same posture as `2.2`'s threshold report.
"""

import logging

from odoo.db.schema import table_exists

_logger = logging.getLogger(__name__)

SCRATCH = "hr_salary_allocation_migration"


def migrate(cr, version):
    if not version:
        return
    if not table_exists(cr, SCRATCH):
        _logger.info("no %s; nothing to drain.", SCRATCH)
        return
    if not table_exists(cr, "hr_employee_bank_allocation"):
        raise ValueError(
            "hr_employee_bank_allocation does not exist at post-migration time, "
            f"so the {SCRATCH} rows have nowhere to go. Refusing to drop them."
        )

    cr.execute(
        f"""
        INSERT INTO hr_employee_bank_allocation
            (employee_id, bank_account_id, company_id, sequence, amount,
             amount_is_percentage, create_uid, write_uid, create_date, write_date)
        SELECT s.employee_id, s.bank_account_id, s.company_id, s.sequence,
               s.amount, s.amount_is_percentage, 1, 1, now(), now()
          FROM {SCRATCH} s
         WHERE EXISTS (SELECT 1 FROM hr_employee e WHERE e.id = s.employee_id)
           AND EXISTS (SELECT 1 FROM res_partner_bank_account b
                        WHERE b.id = s.bank_account_id)
           AND NOT EXISTS (
                SELECT 1 FROM hr_employee_bank_allocation a
                 WHERE a.employee_id = s.employee_id
                   AND a.bank_account_id = s.bank_account_id
           )
        """
    )
    moved = cr.rowcount

    # An employee whose many2many was written past the compute has no jsonb
    # entry, so the rescue gave the row amount 0. Where that employee holds
    # exactly ONE percentage allocation, 100 is not a guess: `compute_salary_allocations`
    # short-circuits on `not has_multiple_bank_accounts` and pays the whole
    # remainder to the primary account, so "all of it to this account" is
    # already the behaviour. Recording it keeps the row editable, because the
    # new constraint would otherwise reject the next write to that employee.
    cr.execute(
        """
        UPDATE hr_employee_bank_allocation a
           SET amount = 100
         WHERE a.amount_is_percentage
           AND a.amount = 0
           AND (SELECT count(*) FROM hr_employee_bank_allocation b
                 WHERE b.employee_id = a.employee_id AND b.amount_is_percentage) = 1
        """
    )
    normalised = cr.rowcount
    if normalised:
        _logger.info(
            "set %d single-account allocation(s) to 100%%, which is what "
            "compute_salary_allocations already paid them.",
            normalised,
        )

    # Report rather than refuse: see the module docstring.
    cr.execute(
        """
        SELECT employee_id, round(sum(amount), 4)
          FROM hr_employee_bank_allocation
         WHERE amount_is_percentage
      GROUP BY employee_id
        HAVING round(sum(amount), 4) <> 100
      ORDER BY employee_id
        """
    )
    off = cr.fetchall()
    cr.execute(f"SELECT count(*) FROM {SCRATCH}")
    rescued = cr.fetchone()[0]
    cr.execute(f"DROP TABLE {SCRATCH}")

    _logger.info("moved %d of %d rescued allocation(s).", moved, rescued)
    if moved != rescued:
        _logger.warning(
            "%d rescued row(s) were dropped: their employee or bank account no "
            "longer exists, or the pair was already allocated.",
            rescued - moved,
        )
    if off:
        _logger.warning(
            "%d employee(s) carry percentage allocations that do not total 100, "
            "which the new constraint will reject on the next write to them: %s",
            len(off),
            ", ".join(f"employee {eid} at {total}%" for eid, total in off[:20]),
        )
