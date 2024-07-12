from odoo import api, models


class L10nPtStockReportHashIntegrity(models.AbstractModel):
    _name = 'report.l10n_pt_stock.report_hash_integrity'
    _description = 'Get hash integrity result as PDF.'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'res.company',
            'data': {**(data or {}), **self.env.company._l10n_pt_stock_check_hash_integrity()},
            'docs': self.env.company,
        }
