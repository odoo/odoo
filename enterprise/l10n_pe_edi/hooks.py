# Part of Odoo. See LICENSE file for full copyright and licensing details.

def post_init_hook(env):
    # The `l10n_pe_edi_affectation_reason` field on `account.move.line` is created manually
    # to prevent "out of memory" (OOM) errors during module installation.
    # The field is populated here to ensure the values are filled after the related field
    # on `account.tax` has been computed.
    env.cr.execute("""
        WITH first_tax AS (
            SELECT DISTINCT ON (rel.account_move_line_id)
                   rel.account_move_line_id,
                   at.l10n_pe_edi_affectation_reason
            FROM account_move_line_account_tax_rel rel
            JOIN account_tax at ON at.id = rel.account_tax_id
            WHERE at.l10n_pe_edi_tax_code IS NOT NULL
            ORDER BY rel.account_move_line_id, at.sequence, at.id
        )
        UPDATE account_move_line aml
        SET l10n_pe_edi_affectation_reason = ft.l10n_pe_edi_affectation_reason
        FROM first_tax ft
        WHERE aml.id = ft.account_move_line_id
          AND aml.display_type NOT IN ('tax', 'payment_term');
    """)

    for company in env['res.company'].search([('chart_template', '=', 'pe'), ('parent_id', '=', False)]):
        ChartTemplate = env['account.chart.template'].with_company(company)
        tax_group_data = ChartTemplate._get_pe_edi_account_tax_group()
        existing_tax_groups = {xml_id: vals for xml_id, vals in tax_group_data.items() if ChartTemplate.ref(xml_id, raise_if_not_found=False)}
        ChartTemplate._load_data({'account.tax.group': existing_tax_groups})
