# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import float_is_zero

class EventRegistration(models.Model):
    _inherit = 'event.registration'

    state = fields.Selection(default=None, compute="_compute_registration_state", store=True, readonly=False)
    sale_status = fields.Selection(string="Sale Status", default='free', selection=[
            ('to_pay', 'Not Sold'),
            ('sold', 'Sold'),
            ('free', 'Free'),
        ], compute="_compute_registration_status", store=True, readonly=False, compute_sudo=True)

    def _get_order_line(self):
        return False

    def _compute_registration_status(self):
        for record in self:
            order = record._get_order_line()
            if not order:
                record.sale_status = 'free'
            else:
                if float_is_zero(order._get_event_sale_total(), precision_digits=order.currency_id.rounding):
                    record.sale_status = 'free'
                else:
                    if order._get_event_sale_state():
                        record.sale_status = 'sold'
                    else:
                        record.sale_status = 'to_pay'

    @api.depends('sale_status')
    def _compute_registration_state(self):
        for record in self:
            if record._is_cancel():
                record.state = 'cancel'
            if record.sale_status == 'free':
                if record.state != 'cancel':
                    record.state = "open"
            else:
                if record.sale_status == 'sold':
                    record.state = "open"

    def _is_cancel(self):
        return False

    def _get_registration_summary(self):
        res = super(EventRegistration, self)._get_registration_summary()
        res.update({
            'sale_status': self.sale_status,
            'sale_status_value': dict(self._fields['sale_status']._description_selection(self.env))[self.sale_status],
            'has_to_pay': self.sale_status == 'to_pay',
        })
        return res
