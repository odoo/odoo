from odoo import api, models


class L10nPtStockReportAccountHashIntegrity(models.AbstractModel):
    _name = 'report.l10n_pt_stock.report_hash_integrity'
    _description = 'Get hash integrity result as PDF.'

    @api.model
    def _get_report_values(self, docids, data=None):
        if data:
            data.update(self.env.company._l10n_pt_stock_check_hash_integrity())
        else:
            data = self.env.company._l10n_pt_stock_check_hash_integrity()
        return {
            'doc_ids': docids,
            'doc_model': self.env['res.company'],
            'data': data,
            'docs': self.env['res.company'].browse(self.env.company.id),
        }
