# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_mx_edi_payment_method_id = fields.Many2one(
        comodel_name='l10n_mx_edi.payment.method',
        string="Payment Way",
        help="Indicates the way the payment was/will be received, where the options could be: "
             "Cash, Nominal Check, Credit Card, etc.")
