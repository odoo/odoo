# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AppointmentType(models.Model):
    _inherit = "appointment.type"

    has_payment_step = fields.Boolean("Up-front Payment", help="Require visitors to pay to confirm their booking")
    product_id = fields.Many2one(
        'product.product', string="Product",
        compute="_compute_product_id",
        domain=[('detailed_type', '=', 'booking_fees')],
        readonly=False, store=True)

    _sql_constraints = [
        ('check_product_and_payment_step',
         'CHECK(has_payment_step IS NULL OR NOT has_payment_step OR product_id IS NOT NULL)',
         'Activating the payment step requires a product')
    ]

    @api.depends('has_payment_step')
    def _compute_product_id(self):
        """ When checking has_payment_step, if there is only a single 'booking_fees' product,
            set it as a product on the appointment type. When unchecking it, set False instead."""
        self.filtered(lambda apt: not apt.has_payment_step).product_id = False
        todo = self.filtered(lambda apt: apt.has_payment_step and not apt.product_id)
        product_booking_fees = self.env['product.product'].search(
            [('detailed_type', '=', 'booking_fees')], limit=2
        ) if todo else self.env['product.product']
        if len(product_booking_fees) == 1:
            todo.product_id = product_booking_fees[0]
