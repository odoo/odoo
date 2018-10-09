# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountBankStatementImportJounalCreation(models.TransientModel):
    _name = 'account.bank.statement.import.journal.creation'
    _description = 'Journal Creation on Bank Statement Import'

    journal_id = fields.Many2one('account.journal', delegate=True, required=True, ondelete='cascade')

    @api.multi
    def create_journal(self):
        """ Create the journal (the record is automatically created in the process of calling this method) and reprocess the statement """
        statement_import_transient = self.env['account.bank.statement.import'].browse(self.env.context['statement_import_transient_id'])
        return statement_import_transient.with_context(journal_id=self.journal_id.id).import_file()
