# -*- coding: utf-8 -*-
from odoo.addons import account
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountPayment(models.Model, account.AccountPayment):

    is_donation = fields.Boolean(string="Is Donation", related="payment_transaction_id.is_donation")
