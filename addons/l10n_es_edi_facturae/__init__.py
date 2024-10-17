# Part of Odoo. See LICENSE file for full copyright and licensing details.
import csv

from odoo.tools import file_open
from . import models
from . import wizard
from .models.account_move import AccountMove
from .models.account_move_send import AccountMoveSend
from .models.account_tax import AccountTax
from .models.certificate import CertificateCertificate
from .models.res_company import ResCompany
from .models.res_partner import L10n_Es_Edi_FacturaeAc_Role_Type, ResPartner
from .models.uom_uom import UomUom
from .wizard.account_move_reversal import AccountMoveReversal


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
