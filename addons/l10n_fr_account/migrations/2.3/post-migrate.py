from odoo.tools import SQL


def migrate(cr, version):

    changed_accounts_codes = ('110000', '119000', '120000', '129000')
    cr.execute(SQL(
        """
        UPDATE account_account acc
           SET account_type = 'equity_unaffected'
         WHERE EXISTS (
               SELECT 1
                 FROM jsonb_each_text(acc.code_store) AS elem
                WHERE elem.value IN %s
           )
           AND EXISTS (
               SELECT 1
                 FROM account_account_res_company_rel rel
                 JOIN res_company comp ON comp.id = rel.res_company_id
                 JOIN res_partner part ON part.id = comp.partner_id
                 JOIN res_country country ON country.id = part.country_id
                WHERE rel.account_account_id = acc.id
                  AND country.code = 'FR'
           )
        """,
            changed_accounts_codes))
