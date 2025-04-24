from odoo import models


class L10nPtReprintReason(models.TransientModel):
    """
    Wizard prompting user to enter reason why document is printed more than once.
    """
    _inherit = 'l10n_pt.reprint.reason'

    def _l10n_pt_reprint_models(self):
        return super()._l10n_pt_reprint_models() | {'sale.order'}

    def _get_report_action(self, model, documents, action=None):
        if model == 'sale.order':
            return documents.with_context(has_reprint_reason=True).action_quotation_send()
        return super()._get_report_action(model, documents, action)
