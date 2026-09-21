from odoo import SUPERUSER_ID, api
from odoo.db.schema import column_exists

COLUMNS = ("expense_journal_id",)


def migrate(cr, version):
    if not version:
        return
    present = [column for column in COLUMNS if column_exists(cr, "res_company", column)]
    if not present:
        return
    # the rows through the ORM, so every default and required value is
    # applied; the values by SQL, straight from the company's columns
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env["res.company"].with_context(active_test=False).search([])
    env["hr_expense.config"]._for_each(companies)
    env.flush_all()
    assignments = ", ".join(f"{column} = c.{column}" for column in present)
    cr.execute(
        f"UPDATE hr_expense_config x SET {assignments} FROM res_company c WHERE c.id = x.company_id"
    )
    _move_allowed_payment_channels(env)
    env.invalidate_all()


def _move_allowed_payment_channels(env):
    """The many2many rows, from the company's relation table to the
    configuration's.

    Both table names are derived rather than written down: the ORM builds them
    from the two model tables, so a name spelled here would be a second copy of
    a rule that lives in many2many.__set_name__.
    """
    field = env["hr_expense.config"]._fields[
        "company_expense_allowed_payment_channel_ids"
    ]
    company_table = "_".join(
        sorted(["res_company", env[field.comodel_name]._table]) + ["rel"]
    )
    cr = env.cr
    cr.execute("SELECT to_regclass(%s)", [company_table])
    if not cr.fetchone()[0]:
        return
    cr.execute(
        f"""
        INSERT INTO {field.relation} ({field.column1}, {field.column2})
             SELECT config.id, old.{field.column2}
               FROM {company_table} old
               JOIN hr_expense_config config ON config.company_id = old.res_company_id
        ON CONFLICT DO NOTHING
        """
    )
