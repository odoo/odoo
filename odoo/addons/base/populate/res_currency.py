from dateutil.relativedelta import relativedelta
from datetime import date

from odoo import models, Command
from odoo.tools import populate


class ResCurrencyRate(models.Model):
    _inherit = "res.currency.rate"

    _populate_sizes = {
        'small': 100,
        'medium': 1000,
        'large': 10000,
    }

    def _populate_factories(self):
        def get_rate(random, values, **kwargs):
            basis = sum(
                ord(c) for c in
                self.env['res.currency'].browse(values['currency_id']).name
            ) % 20
            return basis + random.uniform(-1, 1)

        def get_date(random, values, **kwargs):
            return date(2020, 1, 1) - relativedelta(days=kwargs['counter'])

        company_ids = self.env['res.company'].search([
            ('id', 'in', self.env.registry.populated_models['res.company']),
        ])
        return [
            ('currency_id', populate.randomize(self.env['res.currency'].search([('active', '=', True)]).ids)),
            ('company_id', populate.randomize(company_ids.root_id.ids)),
            ('name', populate.compute(get_date)),
            ('rate', populate.compute(get_rate)),
        ]
