# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PosConfig(models.Model):
    _inherit = 'pos.config'

    self_order_pay_after = fields.Selection([
        ('each', 'Each Order'),
        ('meal', 'Meal')
        ],
        string='Pay After:', default='each', 
        help="Choose when the customer will pay")

    @api.constrains('self_order_location', 'self_order_allow_open_tabs')
    def _check_required_fields(self):
        if self.module_pos_self_order and not self.self_order_location:
            raise ValidationError(_('Please select the order location for self order'))
        if self.self_order_location == 'table' and not self.self_order_allow_open_tabs:
            raise ValidationError(_('Please select a value for "Pay After"'))

    def self_order_allow_view_menu(self):
        self.ensure_one()
        return self.self_order_view_mode or self.self_order_kiosk_mode

    def self_order_allow_order(self):
        self.ensure_one()
        return self.compute_self_order_location != 'none'

    def self_order_allow_ongoing_orders(self):
        """
        Returns True if ongoing orders are allowed.
        Ongoing orders means that a customer can order multiple times and pay at the end of the meal,
        instead of paying after each order.
        """
        self.ensure_one()
        return self.self_order_pay_after == 'meal'

    def compute_self_order_location(self):
        self.ensure_one()
        if self.self_order_kiosk_mode:
            return 'kiosk'
        elif self.self_order_phone_mode:
            return 'table'
        else:
            return 'none'
