# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .models import (
    AccountChartTemplate, AccountFiscalPosition, AccountMove, AccountTax,
    L10n_It_Edi_DoiDeclaration_Of_Intent, ResCompany, ResPartner, SaleOrder,
)


def _l10n_it_edi_doi_post_init(env):
    for company in env['res.company'].search([('chart_template', '=', 'it')]):
        template = env['account.chart.template'].with_company(company)
        template._load_data({
            'account.tax': template._get_it_edi_doi_account_tax(),
            'account.fiscal.position': template._get_it_edi_doi_account_fiscal_position(),
            'res.company': template._get_it_edi_doi_res_company(),
        })
