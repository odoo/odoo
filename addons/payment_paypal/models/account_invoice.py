# -*- coding: utf-8 -*-

from openerp import models, fields

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    paypal_url = fields.Char('Paypal Url', store=False)     # dummy field
