# -*- coding: utf-8 -*-
from odoo import models

import ast


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def action_open_bank_balance_in_gl(self):
        ''' Show the bank balance inside the General Ledger report.
        :return: An action opening the General Ledger.
        '''
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account_reports.action_account_report_general_ledger")

        action['context'] = dict(ast.literal_eval(action['context']), default_filter_accounts=self.default_account_id.code)

        return action
