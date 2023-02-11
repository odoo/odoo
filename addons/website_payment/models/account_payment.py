# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    is_donation = fields.Boolean(string="Is Donation", related="payment_transaction_id.is_donation", help="Is the payment a donation")
