# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SnailmailConfirmInvoiceSend(models.TransientModel):
    _name = 'snailmail.confirm.invoice'
    _inherit = ['snailmail.confirm']
    _description = 'Snailmail Confirm Invoice'

    invoice_send_id = fields.Many2one('account.invoice.send')

    def _confirm(self):
        self.ensure_one()
        self.invoice_send_id._print_action()

    def _continue(self):
        self.ensure_one()
        return self.invoice_send_id.send_and_print()
