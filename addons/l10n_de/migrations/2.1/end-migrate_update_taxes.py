# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    tags_77 = env['account.account.tag']._get_tax_tags('77', env.ref('base.de').id)
    for chart_template in ('de_skr03', 'de_skr04'):
        for company in env['res.company'].search([('chart_template', '=', chart_template)], order="parent_path"):
            env['account.chart.template'].try_loading(chart_template, company, force_create=False)

            # Reloading the taxes doesn't remove tax grids, so remove Kz 77 (deliveries to other
            # member states) from the domestic agriculture/forestry taxes explicitly.
            for xmlid in ('tax_ust_55_farmer', 'tax_ust_107_farmer'):
                tax = env.ref(f'account.{company.id}_{xmlid}_{chart_template[3:]}', raise_if_not_found=False)
                if tax:
                    tax.repartition_line_ids.tag_ids -= tags_77

    # The OSS taxes of l10n_eu_oss had no tax grid, add Kz 45 (other non-taxable turnover) to the
    # base of the existing ones.
    oss_tag = env.ref('l10n_eu_oss.tag_oss', raise_if_not_found=False)
    if oss_tag:
        tags_45 = env['account.account.tag']._get_tax_tags('45_BASE', env.ref('base.de').id)
        oss_lines = env['account.tax.repartition.line'].search([
            ('tag_ids', 'in', oss_tag.ids),
            ('repartition_type', '=', 'base'),
            ('tax_id.country_id', '=', env.ref('base.de').id),
        ])
        for line in oss_lines:
            line.tag_ids |= tags_45.filtered(lambda tag: tag.tax_negate == (line.document_type == 'refund'))
