# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api
from odoo.tools import float_is_zero


class EventRegistration(models.Model):
    _inherit = ['event.registration']
    _name = 'event.registration'

    @api.depends('pos_order_id.state')
    def _compute_registration_status(self):
        super()._compute_registration_status()
        for record in self.filtered("pos_order_id.id"):
            if record.pos_order_id.state in ['paid', 'done', 'invoiced']:
                record.sale_status = 'sold'
                record.state = 'open'
            elif float_is_zero(record.pos_order_id.amount_total, precision_rounding=record.pos_order_id.currency_id.rounding):
                record.sale_status = 'free'
                record.state = 'open'
            else:
                record.sale_status = 'to_pay'
                record.state = 'draft'
