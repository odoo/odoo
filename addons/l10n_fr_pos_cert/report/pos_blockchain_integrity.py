# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.tools import format_date


class ReportL10nFrPosBlockchainIntegrity(models.AbstractModel):
    _name = 'report.l10n_fr_pos_cert.report_l10n_fr_pos_blockchain_integrity'
    _inherit = 'report.blockchain.report_blockchain_integrity'
    _description = 'Get french pos blockchain integrity result as PDF.'

    @api.model
    def _check_blockchain_integrity(self):
        """Checks that all posted or invoiced pos orders have still the same data as when they were posted
        and raises an error with the result."""
        orders = self.env['pos.order'].search([
            ('state', 'in', ['paid', 'done', 'invoiced']),
            ('company_id', '=', self.env.company.id),
            ('blockchain_secure_sequence_number', '!=', 0),
        ])
        result = super()._check_blockchain_integrity(orders, 'date_order', self.env.company._is_accounting_unalterable())
        return {
            'results': [result],
            'printing_date': format_date(self.env, fields.Date.context_today(self))
        }
