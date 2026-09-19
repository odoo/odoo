from odoo.db.schema import column_exists

COLUMNS = (
    "l10n_mx_income_return_discount_account_id",
    "l10n_mx_income_re_invoicing_account_id",
)


def migrate(cr, version):
    if not version or not column_exists(cr, "res_company", COLUMNS[0]):
        return
    present = [column for column in COLUMNS if column_exists(cr, "res_company", column)]
    cr.execute(
        f"""
        UPDATE account_config t
           SET {", ".join(f"{column} = c.{column}" for column in present)}
          FROM res_company c
         WHERE c.id = t.company_id
        """
    )
