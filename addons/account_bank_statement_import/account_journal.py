# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_bank_statements_available_import_formats(self):
        """ Returns a list of strings representing the supported import formats.
        """
        return []

    def _get_bank_statements_available_sources(self):
        rslt = super(AccountJournal, self)._get_bank_statements_available_sources()

        formats_list = self._get_bank_statements_available_import_formats()
        if formats_list:
            formats_list.sort()
            import_formats_str = ', '.join(formats_list)
            rslt.append(("file_import", _("Import") + "(" + import_formats_str + ")"))

        return rslt

    bank_statements_source = fields.Selection(selection=_get_bank_statements_available_sources) # Necessary to have the ORM understand we override the selection function ...

    @api.multi
    def import_statement(self):
        """return action to import bank/cash statements. This button should be called only on journals with type =='bank'"""
        action_name = 'action_account_bank_statement_import'
        [action] = self.env.ref('account_bank_statement_import.%s' % action_name).read()
        # Note: this drops action['context'], which is a dict stored as a string, which is not easy to update
        action.update({'context': (u"{'journal_id': " + str(self.id) + u"}")})
        return action

    def get_journal_dashboard_datas(self):
        """ Overridden to change the conditions for 'create' to appear so that
        it always comes with 'import'.
        """
        rslt = super(AccountJournal, self).get_journal_dashboard_datas()

        rslt['allow_statements_creation'] = self.type == 'bank' and self.bank_statements_source == 'file_import'

        return rslt
