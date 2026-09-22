import logging

from odoo.db.schema import column_exists, table_exists

_logger = logging.getLogger(__name__)

SCRATCH = "hr_salary_allocation_migration"


def migrate(cr, version):
    if not version:
        return
    if not table_exists(cr, "employee_bank_account_rel"):
        _logger.info("no employee_bank_account_rel; nothing to rescue.")
        return

    has_json = column_exists(cr, "hr_employee", "salary_distribution")
    cr.execute(f"DROP TABLE IF EXISTS {SCRATCH}")
    cr.execute(
        f"""
        CREATE TABLE {SCRATCH} (
            employee_id          integer NOT NULL,
            bank_account_id      integer NOT NULL,
            company_id           integer,
            sequence             integer NOT NULL DEFAULT 10,
            amount               numeric NOT NULL DEFAULT 0,
            amount_is_percentage boolean NOT NULL DEFAULT true
        )
        """
    )

    entry = (
        """
        LEFT JOIN LATERAL jsonb_each(
            COALESCE(emp.salary_distribution, '{}'::jsonb)
        ) AS dist ON dist.key = rel.bank_account_id::text
        """
        if has_json
        else ""
    )
    amount = (
        """CASE WHEN jsonb_typeof(dist.value -> 'amount') = 'number'
                 THEN (dist.value ->> 'amount')::numeric ELSE 0 END"""
        if has_json
        else "0"
    )
    sequence = (
        """CASE WHEN jsonb_typeof(dist.value -> 'sequence') = 'number'
                 THEN (dist.value ->> 'sequence')::integer ELSE 10 END"""
        if has_json
        else "10"
    )
    is_pct = (
        """CASE WHEN jsonb_typeof(dist.value -> 'amount_is_percentage') = 'boolean'
                 THEN (dist.value ->> 'amount_is_percentage')::boolean ELSE true END"""
        if has_json
        else "true"
    )

    cr.execute(
        f"""
        INSERT INTO {SCRATCH}
            (employee_id, bank_account_id, company_id, sequence, amount,
             amount_is_percentage)
        SELECT rel.employee_id, rel.bank_account_id, emp.company_id,
               {sequence}, {amount}, {is_pct}
          FROM employee_bank_account_rel rel
          JOIN hr_employee emp ON emp.id = rel.employee_id
          {entry}
        """
    )
    rescued = cr.rowcount
    cr.execute(f"SELECT count(DISTINCT employee_id) FROM {SCRATCH}")
    employees = cr.fetchone()[0]
    _logger.info(
        "rescued %d salary allocation(s) for %d employee(s) into %s "
        "(salary_distribution column present: %s)",
        rescued,
        employees,
        SCRATCH,
        has_json,
    )
