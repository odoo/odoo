# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from .models.account_chart_template import AccountChartTemplate
from .models.account_fiscal_position import AccountFiscalPosition
from .models.account_move import AccountMove
from .models.account_tax import AccountTax
from .models.declaration_of_intent import L10n_It_Edi_DoiDeclaration_Of_Intent
from .models.res_company import ResCompany
from .models.res_partner import ResPartner
from .models.sale_order import SaleOrder


def _l10n_it_edi_doi_post_init(env):
    for company in env['res.company'].search([('chart_template', '=', 'it')]):
        template = env['account.chart.template'].with_company(company)
        template._load_data({
            'account.tax': template._get_it_edi_doi_account_tax(),
            'account.fiscal.position': template._get_it_edi_doi_account_fiscal_position(),
            'res.company': template._get_it_edi_doi_res_company(),
        })
