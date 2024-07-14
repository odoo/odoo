# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, fields
from odoo.tools import populate
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

class SaleOrderlog(models.Model):
    _inherit = 'sale.order.log'
    _populate_dependencies = ['sale.order']

    _populate_sizes = {
        'small': 1_000,
        'medium': 100_000,
        'large': 1_000_000,
    }

    def _populate_factories(self):
        order_ids = self.env.registry.populated_models['sale.order']

        def generate_random_timedelta(random):
            return relativedelta(days=random.randint(-1000, 0))

        def generate_event_date(iterator, field_name, model_name):
            random = populate.Random('event_date')
            today = fields.Date.today()
            for values in iterator:
                order_id = self.env['sale.order'].browse(values['order_id'])
                if not order_id.recurrence_id:
                    continue
                values[field_name] = today + generate_random_timedelta(random)
                yield values

        def generate_event_type(iterator, field_name, model_name):
            random = populate.Random('event_type')
            for values in iterator:
                order_id = self.env['sale.order'].browse(values['order_id'])
                if not order_id.recurrence_id:
                    continue
                r = random.random()
                if r < 0.1:
                    # creation
                    values['amount_signed'] = values['recurring_monthly']
                    values[field_name] = '0_creation'
                elif r < 0.2:
                    # sometimes we churn
                    values['amount_signed'] = - values['recurring_monthly']
                    values['recurring_monthly'] = 0
                    values[field_name] = '2_churn'
                elif values['amount_signed'] > 0:
                    values[field_name] = '1_expansion'
                else:
                    values[field_name] = '15_contraction'

                yield values

        def generate_currency_id(iterator, field_name, model_name):
            for values in iterator:
                order_id = self.env['sale.order'].browse(values['order_id'])
                if not order_id.recurrence_id:
                    continue
                values['currency_id'] = order_id.currency_id.id
                yield values

        def generate_subscription_state(iterator, field_name, model_name):
            for values in iterator:
                order_id = self.env['sale.order'].browse(values['order_id'])
                if not order_id.recurrence_id:
                    continue
                values['subscription_state'] = order_id.subscription_state
                yield values

        return super()._populate_factories() + [
            ('order_id', populate.randomize(order_ids)),
            ('amount_signed', populate.randfloat(-1000, 1000)),
            ('recurring_monthly', populate.randfloat(0, 10000)),
            ('event_date', generate_event_date),
            ('event_type', generate_event_type),
            ('currency_id', generate_currency_id),
            ('subscription_state', generate_subscription_state)
        ]
