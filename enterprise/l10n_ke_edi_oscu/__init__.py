# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from . import models
from . import wizard


_logger = logging.getLogger(__name__)


def _post_init_hook(env):
    # UNSPSC category codes can be used in Kenya.
    env['product.unspsc.code'].flush_model()
    env.cr.execute('''
        UPDATE product_unspsc_code
           SET active = 'true'
         WHERE code ILIKE '%00'
    ''')
    env['product.unspsc.code'].invalidate_model()

    # Load eTIMS type on the tax
    for company in env['res.company'].search([('chart_template', '=', 'ke')], order="parent_path"):
        _logger.info("Company %s already has the Kenyan localization installed, updating...", company.name)
        ChartTemplate = env['account.chart.template'].with_company(company)
        tax_types_to_load = {
            tax_xmlid: values
            for tax_xmlid, values in ChartTemplate._get_ke_account_tax_etims_type().items()
            if ChartTemplate.ref(tax_xmlid, raise_if_not_found=False)
        }
        ChartTemplate._load_data({
            'account.tax': tax_types_to_load,
        })

    # Change all OSCU codes ir.model.data to noupdate, so it only gets updated through the cron
    xmls = env['ir.model.data'].search([('model', '=', 'l10n_ke_edi_oscu.code')])
    xmls.write({'noupdate': True})
