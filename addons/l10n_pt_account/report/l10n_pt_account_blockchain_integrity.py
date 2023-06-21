# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import format_date


class ReportL10nPtAccountBlockchainIntegrity(models.AbstractModel):
    _inherit = 'report.account.report_accounting_blockchain_integrity'
    _description = 'Get blockchain integrity result as PDF.'

    @api.model
    def _check_blockchain_integrity(self):
        if self.env.company.country_id.code != 'PT':
            return super()._check_blockchain_integrity()
        if self.env['ir.config_parameter'].sudo().get_param('l10n_pt.iap_endpoint', 'demo') != 'demo':
            raise UserError(_('This feature is only available in the demo environment for test purposes'))
        res = {
            'results': [],
            'printing_date': format_date(self.env, fields.Date.context_today(self))
        }
        self.env['account.move'].l10n_pt_compute_missing_hashes(self.env.company.id)
        for move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
            moves = self.env['account.move'].search([
                ('state', '=', 'posted'),
                ('move_type', '=', move_type),
                ('company_id', '=', self.env.company.id)
            ])
            integrity_check = self.env['report.blockchain.report_blockchain_integrity']._check_blockchain_integrity(moves, 'date')
            integrity_check['journal_name'] = dict(moves._fields['move_type'].selection)[move_type]
            integrity_check['journal_code'] = move_type
            res['results'].append(integrity_check)
        return res
