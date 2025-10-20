# Part of Odoo. See LICENSE file for full copyright and licensing details.
import csv

from odoo.tools import file_open
from . import models
from . import wizard


def _l10n_es_edi_facturae_post_init_hook(env):
    """
    We need to replace the existing spanish taxes following the template so the new fields are set properly
    """
    for company in env['res.company'].search([('chart_template', 'like', r'es\_%'), ('parent_id', '=', False)]):
        Template = env['account.chart.template'].with_company(company)
        if company.chart_template.startswith("es_canary"):
            tax_data = {
                **Template._get_es_facturae_account_tax_es_common(),
                **Template._get_es_facturae_account_tax_es_canary_common(),
            }
        else:
            tax_data = {
                **Template._get_es_facturae_account_tax_es_common(),
                **Template._get_es_facturae_account_tax_es_common_mainland(),
            }
        # Filter out data for non-existing taxes; else this function will raise.
        # In case of data for a non-existing tax we would try to create that tax.
        # This would fail because we don't supply enough information in this module (just `l10n_es_edi_facturae_tax_type`).
        tax_data = {
            xmlid: value
            for xmlid, value in tax_data.items()
            if Template.ref(xmlid, raise_if_not_found=False)
        }
        Template._load_data({
            'account.tax': tax_data,
        })


def uninstall_hook(env):
    env["res.partner"]._clear_removed_edi_formats("es_facturae")
