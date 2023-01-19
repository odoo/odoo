# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountCommonJournalReport(models.TransientModel):
    _name = 'account.common.journal.report'
    _description = 'Common Journal Report'
    _inherit = "account.common.report"

    amount_currency = fields.Boolean('With Currency', help="Print Report with the currency column if the currency differs from the company currency.")

    def pre_print_report(self, data):
        data['form'].update({'amount_currency': self.amount_currency})
        return data
