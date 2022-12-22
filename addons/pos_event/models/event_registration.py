# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import float_is_zero


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    pos_order_id = fields.Many2one(related='pos_order_line_id.order_id', string='PoS Order')
    pos_order_line_id = fields.Many2one('pos.order.line', string='PoS Order Line', ondelete='cascade', copy=False)

    # @api.depends('sale_order_id.currency_id', 'sale_order_line_id.price_total')
    # def _compute_payment_status(self):
    #     super()._compute_payment_status()

    def _is_free(self):
        po = self.pos_order_id
        po_line = self.pos_order_line_id
        return super()._is_free and (not po or float_is_zero(po_line.price_subtotal_incl, precision_digits=po.currency_id.rounding))
