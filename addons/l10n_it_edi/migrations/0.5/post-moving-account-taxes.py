# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Updates already created taxes from l10n_it with new fields in l10n_it_edi."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    ChartTemplate = env['account.chart.template']
    edi_taxes_data = ChartTemplate._parse_csv('it', 'account.tax', module='l10n_it_edi')
    ChartTemplate._deref_account_tags('it', edi_taxes_data)
    companies = env['res.company'].search([('chart_template', '=', 'it'), ('parent_id', '=', False)])

    for company in companies:
        CompanyChartTemplate = ChartTemplate.with_company(company)
        taxes_to_update = {
            xml_id: data
            for xml_id, data in edi_taxes_data.items()
            if CompanyChartTemplate.ref(xml_id, raise_if_not_found=False)
        }

        if taxes_to_update:
            CompanyChartTemplate._load_data({'account.tax': taxes_to_update})
