from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    in_company_ids = env["res.company"].search([("account_fiscal_country_id.code", "=", "IN")]).ids
    cr.execute(
        """
        UPDATE account_move_line aml
           SET l10n_in_gstr_section = 'purchase_composition_supplies'
          FROM account_move am
          JOIN res_partner rp
            ON am.commercial_partner_id = rp.id
         WHERE am.id = aml.move_id
           AND aml.l10n_in_gstr_section = 'purchase_out_of_scope'
           AND aml.tax_line_id IS NULL
           AND am.l10n_in_gst_treatment = 'composition'
           AND am.l10n_in_state_id = rp.state_id
           AND am.company_id = ANY(%s)
        """,
        [in_company_ids],
    )

    cr.execute(
        """
        UPDATE account_move_line aml
           SET l10n_in_gstr_section = 'purchase_out_of_scope'
          FROM account_move am
         WHERE am.id = aml.move_id
           AND am.l10n_in_gst_treatment = 'composition'
           AND aml.l10n_in_gstr_section IN ('purchase_b2b_rcm', 'purchase_b2b_regular', 'purchase_cdnr_rcm', 'purchase_cdnr_regular')
           AND am.company_id = ANY(%s)
        """,
        [in_company_ids],
    )
