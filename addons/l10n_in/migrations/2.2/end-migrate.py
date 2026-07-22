from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    in_company_ids = env["res.company"].search([("account_fiscal_country_id.code", "=", "IN")]).ids

    tax_types = ["igst", "cess"]
    regular_base_tax_tags = {tax_type: env.ref(f"l10n_in.tax_tag_base_{tax_type}").id for tax_type in tax_types}
    regular_tax_tags = {tax_type: env.ref(f"l10n_in.tax_tag_{tax_type}").id for tax_type in tax_types}

    cr.execute(
        """
        UPDATE account_move_line aml
           SET l10n_in_gstr_section = 'purchase_imp_services'
          FROM account_move am,
               account_account_tag_account_move_line_rel tag_rel
         WHERE aml.move_id = am.id
           AND aml.id = tag_rel.account_move_line_id
           AND tag_rel.account_account_tag_id IN %s
           AND aml.l10n_in_gstr_section = 'purchase_out_of_scope'
           AND am.l10n_in_gst_treatment = 'overseas'
           AND am.company_id = ANY(%s)
           AND (
                am.move_type = 'in_refund'
                OR (
                    am.move_type = 'in_invoice'
                    AND am.debit_origin_id IS NOT NULL
                )
           )
           AND EXISTS (
                SELECT 1
                  FROM account_tax tax
                 WHERE tax.l10n_in_reverse_charge IS TRUE
                   AND (
                       (
                          aml.display_type = 'tax'
                          AND
                          tax.id = aml.tax_line_id
                       )
                       OR (
                            aml.display_type = 'product'
                            AND EXISTS (
                                  SELECT 1
                                    FROM account_move_line_account_tax_rel aml_tax_rel
                                   WHERE aml_tax_rel.account_move_line_id = aml.id
                                     AND aml_tax_rel.account_tax_id = tax.id
                            )
                       )
                   )
           )
        """,
        [tuple(regular_base_tax_tags.values()) + tuple(regular_tax_tags.values()), in_company_ids]
    )

    cr.execute(
        """
        UPDATE account_move_line aml
           SET l10n_in_gstr_section = 'purchase_out_of_scope'
          FROM account_move am
         WHERE aml.move_id = am.id
           AND aml.l10n_in_gstr_section = 'purchase_imp_services'
           AND am.company_id = ANY(%s)
           AND NOT EXISTS (
                SELECT 1
                  FROM account_tax tax
                 WHERE tax.l10n_in_reverse_charge IS TRUE
                   AND (
                       (
                          aml.display_type = 'tax'
                          AND
                          tax.id = aml.tax_line_id
                       )
                       OR (
                            aml.display_type = 'product'
                            AND EXISTS (
                                  SELECT 1
                                    FROM account_move_line_account_tax_rel aml_tax_rel
                                   WHERE aml_tax_rel.account_move_line_id = aml.id
                                     AND aml_tax_rel.account_tax_id = tax.id
                            )
                       )
                   )
           )
        """,
        [in_company_ids]
    )

    cr.execute(
        """
        UPDATE account_move_line aml
           SET l10n_in_gstr_section = 'purchase_out_of_scope'
         WHERE aml.l10n_in_gstr_section = 'purchase_cdnur_regular'
        """
    )
