from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import format_date


class ReportL10nPtStockHashIntegrity(models.AbstractModel):
    _name = 'report.l10n_pt_stock.report_stock_blockchain_integrity'
    _inherit = 'report.blockchain.report_blockchain_integrity'
    _description = 'Get Portuguese stock blockchain integrity result as PDF.'

    @api.model
    def _check_blockchain_integrity(self):
        if self.env.company.country_id.code != 'PT':
            return super()._check_blockchain_integrity()
        if self.env['ir.config_parameter'].sudo().get_param('l10n_pt.iap_endpoint', 'demo') != 'demo':
            raise UserError(_('This feature is only available in the demo environment for test purposes'))
        self.env['stock.picking'].l10n_pt_compute_missing_hashes(self.env.company.id)
        stock_pickings = self.env['stock.picking'].search([
            ('state', '=', 'done'),
            ('company_id', '=', self.env.company.id),
            ('blockchain_secure_sequence_number', '!=', 0),
        ])
        result = super()._check_blockchain_integrity(stock_pickings, 'date_done')
        return {
            'results': [result],
            'printing_date': format_date(self.env, fields.Date.context_today(self))
        }
