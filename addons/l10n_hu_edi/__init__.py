# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import psycopg2.errors

from odoo import _

from . import models
from . import wizard

from .models.account_move import AccountMove, AccountMoveLine
from .models.account_move_send import AccountMoveSend
from .models.account_tax import AccountTax
from .models.product import ProductTemplate
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.res_partner import ResPartner
from .models.template_hu import AccountChartTemplate
from .models.uom_uom import UomUom
from .wizard.account_move_reversal import AccountMoveReversal
from .wizard.l10n_hu_edi_cancellation import L10n_Hu_EdiCancellation
from .wizard.l10n_hu_edi_tax_audit_export import L10n_Hu_EdiTax_Audit_Export

_logger = logging.getLogger(__name__)


def post_init(env):
    for company in env['res.company'].search([('chart_template', '=', 'hu')]):
        # Apply default cash rounding configuration
        company._l10n_hu_edi_configure_company()

        # Set Hungarian fields on taxes
        sql_logger = logging.getLogger('odoo.sql_db')
        previous_level = sql_logger.level
        sql_logger.setLevel(logging.CRITICAL)
        try:
            with env.cr.savepoint():
                env['account.chart.template'].with_company(company)._load_data({
                    'account.tax': env['account.chart.template']._get_hu_account_tax()
                })
        except psycopg2.errors.NotNullViolation:
            _logger.warning(_(
                'Could not set NAV tax types on taxes because some taxes from l10n_hu are missing.\n'
                'You should set the type manually or reload the CoA before sending invoices to NAV.'
            ))
        finally:
            sql_logger.setLevel(previous_level)
