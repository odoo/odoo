# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, fields
from odoo.tools import populate
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    _populate_dependencies = ['sale.temporal.recurrence', 'res.partner', 'res.company', 'res.users', 'product.pricelist']

    def _upsell(self, sample_size):
        random = populate.Random('renew')
        to_upsell = self.browse(random.choices(self.ids, k=int(len(self) * sample_size)))
        # We need to invoice before upselling
        # TODO add journal to company
        to_upsell._create_invoices()
        vals = []
        for so in to_upsell:
            vals += [so._prepare_upsell_renew_order_values('7_upsell')]
        self.create(vals)

    def _renew(self, sample_size):
        random = populate.Random('renew')
        to_renew_ids = set(random.choices(self.ids, k=int(len(self) * sample_size)))
        to_renew = self.browse(to_renew_ids)
        vals = []
        _logger.info("Renewing %d sale orders", len(to_renew))
        for so in to_renew:
            vals += [so._prepare_upsell_renew_order_values('2_renewal')]
        renewal = self.create(vals)
        to_confirm_ids = set(random.sample(renewal.ids, int(len(renewal.ids) * 0.8)))
        renewal_to_confirm = self.env['sale.order'].browse(to_confirm_ids)
        renewal_to_confirm.action_quotation_sent()
        # Don't confirm renewals as random data trigger random constraints
        # renewal_to_confirm.action_confirm()

    def _populate_factories(self):
        recurrence_id = self.env.registry.populated_models['sale.temporal.recurrence']
        num_rec = len(recurrence_id)

        def generate_random_timedelta(random):
            if random.random() < 0.5:
                return relativedelta(days=random.randint(-6, 3))
            else:
                return relativedelta(weeks=random.randint(-6, 3))

        def generate_start_date(iterator, field_name, model_name):
            random = populate.Random('start_date')
            today = fields.Date.today()
            for values in iterator:
                if values['recurrence_id']:
                    values[field_name] = today + generate_random_timedelta(random)
                else:
                    values[field_name] = False
                yield values

        def generate_next_invoice_date(iterator, field_name, model_name):
            random = populate.Random('next_invoice_date')
            for values in iterator:
                if values['start_date']:
                    recurrence = self.env['sale.temporal.recurrence'].browse(values['recurrence_id'])
                    values[field_name] = values['start_date'] + relativedelta(**{recurrence.unit+'s': random.randint(0, 3)*recurrence.duration})
                else:
                    values[field_name] = False
                yield values

        return super()._populate_factories() + [
            ('recurrence_id', populate.randomize([False] + recurrence_id, [num_rec] + [1]*num_rec)),
            ('start_date', generate_start_date),
            ('next_invoice_date', generate_next_invoice_date),
        ]
