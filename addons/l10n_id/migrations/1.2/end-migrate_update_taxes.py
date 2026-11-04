# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Load the new tax groups if it doesn't exist yet
    ChartTemplate = env["account.chart.template"]
    companies = env['res.company'].search([('chart_template', '=', 'id')], order="parent_path")

    new_tax_groups = ["l10n_id_tax_group_non_luxury_goods", "l10n_id_tax_group_0", "l10n_id_tax_group_exempt"]

    tax_group_data = {
        xmlid: data
        for xmlid, data in ChartTemplate._get_account_tax_group('id').items()
        if xmlid in new_tax_groups
    }

    # For taxes: tax_ST1 and tax_PT1 which are non-luxury tax, if the amount and tax group
    # has not been changed yet by user, we update the tax group and description
    for company in companies:
        ChartTemplate.with_company(company)._load_data({
            "account.tax.group": tax_group_data,
        })
        tax_ST1 = ChartTemplate.with_company(company).ref("tax_ST1", raise_if_not_found=False)
        tax_PT1 = ChartTemplate.with_company(company).ref("tax_PT1", raise_if_not_found=False)

        old_group = ChartTemplate.with_company(company).ref("default_tax_group", raise_if_not_found=False)
        new_group = ChartTemplate.with_company(company).ref("l10n_id_tax_group_non_luxury_goods")

        if not old_group:
            continue

        for tax in [tax_ST1, tax_PT1]:
            if tax and tax.amount == 11.0 and tax.tax_group_id == old_group:
                tax.write({
                    "tax_group_id": new_group.id,
                    "description": "12%",
                })
