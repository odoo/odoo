# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _, api
from odoo.tools import format_date


class ReportAccountBlockchainIntegrity(models.AbstractModel):
    _name = 'report.account.report_accounting_blockchain_integrity'
    _inherit = 'report.blockchain.report_blockchain_integrity'
    _description = 'Get blockchain integrity result as PDF.'

    @api.model
    def _check_blockchain_integrity(self):
        journals = self.env['account.journal'].search([('company_id', '=', self.env.company.id)])
        res = {
            'results': [],
            'printing_date': format_date(self.env, fields.Date.context_today(self))
        }
        for journal in journals:
            moves = self.env['account.move'].search([
                ('state', '=', 'posted'),
                ('company_id', '=', journal.company_id.id),
                ('journal_id', '=', journal.id),
                ('blockchain_secure_sequence_number', '!=', 0),
            ])
            journal_check = super()._check_blockchain_integrity(moves, 'date', journal.restrict_mode_hash_table)
            journal_check['journal_name'] = journal.name
            journal_check['journal_code'] = journal.code
            if not journal.restrict_mode_hash_table:
                journal_check['msg'] = _('This journal is not in strict mode.')
            res['results'].append(journal_check)
        return res
