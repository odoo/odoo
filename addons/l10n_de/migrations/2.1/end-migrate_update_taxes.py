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
