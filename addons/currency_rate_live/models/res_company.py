# -*- coding: utf-8 -*-
import datetime
from dateutil.relativedelta import relativedelta
from openerp import api, fields, models


class Company(models.Model):
    _inherit = "res.company"

    currency_interval_unit = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')],
        string='Interval Unit')
    currency_provider_ids = fields.One2many('currency.rate.provider', 'company_id')
    currency_next_execution_date = fields.Date(string="Next Execution Date")

    @api.multi
    def button_currency_update(self):
        providers = self.env['currency.rate.provider'].search([('company_id', 'in', self.ids)])
        for provider in providers:
            provider.server_action_id.with_context(active_id=provider.id, active_model=provider._name).run()
        companies = self.search([('currency_next_execution_date', '<=', fields.Date.today())])
        for company in companies:
            if not company.currency_interval_unit:
                continue
            elif company.currency_interval_unit == 'daily':
                next_update = relativedelta(days=+1)
            elif company.currency_interval_unit == 'weekly':
                next_update = relativedelta(weeks=+1)
            elif company.currency_interval_unit == 'monthly':
                next_update = relativedelta(months=+1)
            company.currency_next_execution_date = datetime.datetime.now() + next_update

    @api.multi
    def run_currency_update(self):
        companies = self.search([('currency_next_execution_date', '<=', fields.Date.today())])
        companies.with_context(cron=True).button_currency_update()
