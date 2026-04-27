from odoo import models


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def action_get_pe_ple_reports(self):

        return {
            'res_model': 'l10n_pe.stock.ple.wizard',
            'views': [[False, 'form']],
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
