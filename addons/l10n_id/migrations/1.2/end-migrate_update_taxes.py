# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Tax groups to create in format of [(xml_id, name)]
    tax_group_info = [
        ("l10n_id_tax_group_non_luxury_goods", "Non-luxury Good Taxes"),
        ("l10n_id_tax_group_0", "Zero-rated Taxes"),
        ("l10n_id_tax_group_exempt", "Tax Exempted"),
    ]

    for xmlid, name in tax_group_info:
        if not env.ref(f"l10n_id.{xmlid}", raise_if_not_found=False):
            env['ir.model.data'].create({
                "name": xmlid,
                "module": "l10n_id",
                "model": "account.tax.group",
                "res_id": env['account.tax.group'].create({'name': name, 'country_id': env.ref('base.id').id}).id,
                'noupdate': True
            })

    # For all taxes linked to the tax_ST1 and tax_PT1, set the tax group to non-luxury goods
    # if no changes to amount and tax group yet
    tax_group_id = env.ref("l10n_id.l10n_id_tax_group_non_luxury_goods")
    default_group = env['account.tax']._default_tax_group()
    id_chart = env.ref("l10n_id.l10n_id_chart", raise_if_not_found=False)

    if not id_chart:
        return

    companies = env['res.company'].search([('chart_template_id', 'child_of', id_chart.id)])
    for company in companies:
        tax_xml_ids = [
            f"l10n_id.{company.id}_tax_ST1",
            f"l10n_id.{company.id}_tax_PT1",
        ]
        for tax_xml_id in tax_xml_ids:
            tax = env.ref(tax_xml_id, raise_if_not_found=False)
            if tax and tax.amount == 11.0 and tax.tax_group_id == default_group:
                tax.update({"tax_group_id": tax_group_id.id, "description": "12%"})
