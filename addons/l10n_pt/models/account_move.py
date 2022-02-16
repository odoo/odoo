# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from hashlib import sha256

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

    def _get_new_hash(self, secure_seq_number):
        """ Returns the hash to write on journal entries when they get posted"""
        self.ensure_one()
        #get the only one exact previous move in the securisation sequence
        prev_move = self.search([('state', '=', 'posted'),
                                 ('type', '=', self.type),
                                 ('company_id', '=', self.company_id.id),
                                 ('journal_id', '=', self.journal_id.id),
                                 ('secure_sequence_number', '!=', 0),
                                 ('secure_sequence_number', '=', int(secure_seq_number) - 1)])
        if prev_move and len(prev_move) != 1:
            raise UserError(
               _('An error occured when computing the inalterability. Impossible to get the unique previous posted journal entry.'))

        self.system_entry_date = datetime.now()
        invoice_date = self.invoice_date.strftime('%Y-%m-%d')
        system_entry_date = self.system_entry_date.strftime("%Y-%m-%dT%H:%M:%S")
        invoice_no = self.type + ' ' + self.name
        gross_total = float_repr(self.amount_total, 2)
        previous_hash = prev_move.inalterable_hash if prev_move else ""
        message = f"{invoice_date};{system_entry_date};{invoice_no};{gross_total};{previous_hash}"
        return self._compute_hash(message)

    def _compute_hash(self, message):
        self.ensure_one()
        # This is only temporary
        hash_string = sha256(message.encode()).hexdigest()
        return hash_string

    def button_draft(self):
        raise UserError(_("Sorry, you cannot reset to draft a posted invoice"))
