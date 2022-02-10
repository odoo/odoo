# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import datetime, float_repr, format_date


class AccountMove(models.Model):
    _inherit = 'account.move'

    system_entry_date = fields.Datetime(
        string='System Entry Date',
        readonly=True,
        invisible=True,
        copy=False,
        store=True)
    digital_signature = fields.Char(
        string='Digital signature',
        readonly=True,
        invisible=True,
        copy=False,
        store=True)

    def init_system_entry_date(self):
        """Initialize the System Entry Date"""
        self.system_entry_date = datetime.now()

    def create_hash(self):
        """Initialize the hash of the invoice, once."""

        def get_previous_hash():
            self._cr.execute("SELECT * from account_move WHERE type = 'out_invoice' ORDER BY system_entry_date DESC LIMIT 1")
            result = self._cr.fetchall()[0]
            print(result)
            print(type(result))
            if result is not None:
                return result.digital_signature
            return ""

        self.init_system_entry_date()
        invoice_date = self.invoice_date.strftime('%Y-%m-%d')
        system_entry_date = self.system_entry_date.strftime("%Y-%m-%dT%H:%M:%S")
        invoice_no = self.type + ' ' + self.name
        gross_total = float_repr(self.amount_total, 2)
        previous_hash = get_previous_hash()
        message = f"{invoice_date};{system_entry_date};{invoice_no};{gross_total};{previous_hash}"
        # TODO: self.digital_signature = rsa(message)
        self.digital_signature = message

    def action_post(self):
        super().action_post()
        self.create_hash()
        for move in self:
            print(move.system_entry_date)
            print(move.digital_signature)

    def button_draft(self):
        raise UserError(_("Sorry, you cannot reset to draft a posted invoice"))
