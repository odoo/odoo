# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    use_in_payment = fields.Boolean("Use in payment", help="Display this bank account on messages in payment process.")
