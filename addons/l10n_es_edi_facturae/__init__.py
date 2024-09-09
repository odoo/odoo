# Part of Odoo. See LICENSE file for full copyright and licensing details.
import csv

from odoo.tools import file_open
from . import models
from . import wizard


def _l10n_es_edi_facturae_post_init_hook(env):
    """
    We need to replace the existing spanish taxes following the template so the new fields are set properly
    """
    concerned_companies = [
        company
        for company in env.companies
        if company.chart_template and company.chart_template.startswith('es_')
    ]
    for company in concerned_companies:
        Template = env['account.chart.template'].with_company(company)
        Template._load_data({
            'account.tax': Template._get_es_facturae_account_tax(),
        })
