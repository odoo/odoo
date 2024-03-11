# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.models.chart_template import update_taxes_from_templates
from odoo import api, SUPERUSER_ID

import psycopg2
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    account_templates = {account_code: env.ref(f'l10n_it.{account_code}') for account_code in ['2607', '2608']}
    companies = env['res.company'].search([('chart_template_id', '=', env.ref('l10n_it.l10n_it_chart_template_generic').id)])
    for company in companies:
        try:
            for account_code, account_template in account_templates.items():
                template_vals = [(account_template, company.chart_template_id._get_account_vals(company, account_template, account_code + '00', {}))]
                company.chart_template_id._create_records_with_xmlid('account.account', template_vals, company)
                _logger.info("Created split payment accounts for company: %s(%s).", company.name, company.id)
        except psycopg2.errors.UniqueViolation:
            _logger.error("Split payment accounts already exist for company: %s(%s).", company.name, company.id)

    update_taxes_from_templates(cr, 'l10n_it.l10n_it_chart_template_generic')
