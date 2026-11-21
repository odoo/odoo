from odoo import models


class L10nPtReprintReason(models.TransientModel):
    _inherit = 'l10n_pt.reprint.reason'

    def _l10n_pt_reprint_models(self):
        return super()._l10n_pt_reprint_models() | {'stock.picking'}

    def _get_report_action(self, model, documents, action=None):
        if model == 'stock.picking':
            return self.env.ref('stock.action_report_delivery').report_action(documents)
        return super()._get_report_action(model, documents, action)
