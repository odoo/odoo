# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import datetime, float_repr


class AccountMove(models.Model):
    _inherit = 'account.move'

    system_entry_date = fields.Datetime(
        string='System Entry Date',
        readonly=True,
        invisible=True,
        copy=False,
        store=True)
    digital_signature = fields.Char(
        string='Digital signature (hash)',
        readonly=True,
        invisible=True,
        copy=False,
        store=True)

    def create_hash(self):
        """Initialize the hash of the invoice, once."""

        def get_previous_hash(move_id, move_type):
            """Return the hash/digital signature of the previous invoice of the same type"""
            self._cr.execute("""
                SELECT *
                  FROM account_move
                 WHERE
                       type = %s AND
                       state = 'posted' AND
                       id != %s
              ORDER BY system_entry_date DESC
                 LIMIT 1
            """, [move_type, move_id])
            result = self._cr.fetchall()
            if result:
                result = result[0]  # Get first (and only) element
                previous_document = self.env['account.move'].browse(result[0])
                return previous_document.digital_signature
            return ""

        def compute_digital_signature(data):
            return "TODO"

        for move in self:
            move.system_entry_date = datetime.now()
            invoice_date = move.invoice_date.strftime('%Y-%m-%d')
            system_entry_date = move.system_entry_date.strftime("%Y-%m-%dT%H:%M:%S")
            invoice_no = move.type + ' ' + move.name
            gross_total = float_repr(move.amount_total, 2)
            previous_hash = get_previous_hash(move.id, move.type)
            message = f"{invoice_date};{system_entry_date};{invoice_no};{gross_total};{previous_hash}"
            move.digital_signature = compute_digital_signature(message)

    def action_post(self):
        super().action_post()
        self.create_hash()

    def button_draft(self):
        raise UserError(_("Sorry, you cannot reset to draft a posted invoice"))
