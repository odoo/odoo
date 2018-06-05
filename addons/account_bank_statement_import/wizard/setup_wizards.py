# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SetupBarBankConfigWizard(models.TransientModel):
    _inherit = 'account.setup.bank.manual.config'

    def validate(self):
        """ Overridden so that we set the configured bank journal as using file
        import as it bank statements source.
        """
        super(SetupBarBankConfigWizard, self).validate()
        self.single_journal_id.bank_statements_source = 'file_import'