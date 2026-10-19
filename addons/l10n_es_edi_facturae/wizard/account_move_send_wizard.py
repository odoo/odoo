from odoo import models


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    def action_send_and_print(self, allow_fallback_pdf=False):
        checkboxes = self.extra_edi_checkboxes or {}
        action = super().action_send_and_print(allow_fallback_pdf)
        if 'es_facturae' in checkboxes and checkboxes['es_facturae']['checked']:
            # Set partner's invoice_edi_format to 'es_facturae' after sending
            partner = self.move_id.commercial_partner_id
            partner.invoice_edi_format = 'es_facturae'
        return action
