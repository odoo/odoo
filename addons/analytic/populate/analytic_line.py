import logging

from odoo import models
from odoo.tools import populate
_logger = logging.getLogger(__name__)


class AnalyticLine(models.Model):
    _inherit = "account.analytic.line"
    _populate_sizes = {
        'small': 100,
        'medium': 1_000,
        'large': 10_000_000,
    }

    _populate_dependencies = ['account.analytic.account']

    def _populate_factories(self):
        accounts = self.env['account.analytic.account'].browse(self.env.registry.populated_models['account.analytic.account'])
        grouped_account = accounts.grouped('plan_id')
        return [
            ('amount', populate.randfloat(0, 1000)),
            *[(
                plan._column_name(),
                populate.randomize(grouped_account.get(plan, self.env['account.analytic.account'].browse([False]))._ids)
            ) for plan in sum(self.env['account.analytic.plan']._get_all_plans())],
            ('name', populate.constant("Line {counter}")),
        ]
