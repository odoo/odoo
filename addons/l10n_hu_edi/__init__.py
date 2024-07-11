# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import psycopg2.errors

from odoo import _

from . import models
from . import wizard

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
