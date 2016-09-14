# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.one
    def _create_check_sequence(self):
        """ Create a check sequence for the journal """
        self.check_sequence_id = self.env['ir.sequence'].sudo().create({
            'name': self.name + _(" : Check Number Sequence"),
            'implementation': 'no_gap',
            'padding': 5,
            'number_increment': 1,
            'company_id': self.company_id.id,
        })

    @api.model
    def _enable_electronic_payment_on_bank_journals(self):
        """ Enables electronic payment method and add a check sequence on bank journals.
            Called upon module installation via data file.
        """
        electronic = self.env.ref('payment.account_payment_method_electronic')
        bank_journals = self.search([('type', '=', 'bank')])
        for bank_journal in bank_journals:
            bank_journal.write({
                'inbound_payment_method_ids': [(4, electronic.id, None)],
            })