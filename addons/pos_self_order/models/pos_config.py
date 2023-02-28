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

    def self_order_allow_view_menu(self):
        """
        Returns True if the menu can be viewed by customers on their phones, by scanning the QR code on the table and going to the provided URL.
        :return: True if the menu can be viewed, False otherwise
        :rtype: bool
        """
        self.ensure_one()
        return self.self_order_view_mode or self.self_order_kiosk_mode

    def self_order_allow_order(self):
        """
        Returns True if ordering is allowed.
        This is based on whether there is an active pos session and also and if self ordering is enabled.
        :return: True if ordering is allowed, False otherwise
        :rtype: bool
        """
        self.ensure_one()
        return self.has_active_session and self.compute_self_order_location != 'none'

    def self_order_allows_ongoing_orders(self):
        """
        Returns True if ongoing orders are allowed.
        Ongoing orders means that a customer can order multiple times and pay at the end of the meal,
        instead of paying after each order.
        :return: True if ongoing orders are allowed, False otherwise
        :rtype: bool
        """
        self.ensure_one()
        return self.self_order_pay_after == 'meal'

    def compute_self_order_location(self):
        """
        Returns the self order location.
        :return: 'none' if self ordering is disabled, 'table' if self_order_phone_mode is enabled, 'kiosk' if self_order_kiosk_mode is enabled
        :rtype: str
        """
        self.ensure_one()
        if self.self_order_kiosk_mode:
            return 'kiosk'
        if self.self_order_phone_mode:
            return 'table'
        return 'none'
