# -*- coding: utf-8 -*-

from openerp import api, fields, models


class Bank(models.Model):
    _inherit = "res.partner.bank"

    journal_id = fields.Many2one('account.journal', string='Account Journal',
        help="This journal will be created automatically for this bank account when you save the record")

    @api.model
    def create(self, data):
        result = super(Bank, self).create(data)
        result.post_write()
        return result

    @api.multi
    def write(self, data):
        result = super(Bank, self).write(data)
        self.post_write()
        return result

    @api.model
    def _prepare_name(self, bank):
        "Return the name to use when creating a bank journal"
        name = bank.bank_name + ' ' if bank.bank_name else ''
        name += bank.acc_number
        return name

    @api.multi
    def post_write(self):
        JournalObj = self.env['account.journal']
        for bank in self:
            # Create a journal for the bank account if it belongs to the company.
            if bank.company_id and not bank.journal_id:
                journal_vals = JournalObj._prepare_bank_journal(bank.company_id, {'acc_name': self._prepare_name(bank), 'currency_id': bank.currency_id.id, 'account_type': 'bank'})
                journal = JournalObj.create(journal_vals)
                missing_vals = {'journal_id': journal.id}
                if not bank.partner_id:
                    missing_vals['partner_id'] = bank.company_id.partner_id.id
                if not bank.owner_name:
                    missing_vals['owner_name'] = bank.company_id.partner_id.name
                bank.write(missing_vals)
