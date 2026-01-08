# Part of Odoo. See LICENSE file for full copyright and licensing details.


def _add_mod130_tax_tags(env):
    taxes_repartition_lines = env['account.tax.repartition.line'].search([
        ('tax_id', 'any', [
            ('l10n_es_type', '=', 'retencion'),
            ('country_code', '=', 'ES'),
            ('type_tax_use', '=', 'sale'),
        ]),
        ('repartition_type', '=', 'tax'),
    ])
    invoice_mod130_tax_tag = env['account.account.tag'].search([('name', '=', '-mod130[06]')])
    refund_mod130_tax_tag = env['account.account.tag'].search([('name', '=', '+mod130[06]')])

    for line in taxes_repartition_lines:
        if line.document_type == 'invoice':
            line.tag_ids += invoice_mod130_tax_tag
        else:
            line.tag_ids += refund_mod130_tax_tag
