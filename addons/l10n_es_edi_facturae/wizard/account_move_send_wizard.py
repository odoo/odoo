from odoo import models


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    def _compute_extra_edi_checkboxes(self):
        super()._compute_extra_edi_checkboxes()
        for wizard in self:
            checkboxes = wizard.extra_edi_checkboxes or {}
            if 'es_facturae' in checkboxes:
                # Set 'checked' status for the 'es_facturae' checkbox
                es_facturae_checkbox = checkboxes.get('es_facturae', {})
                es_facturae_checkbox['checked'] = (
                    wizard.move_id.partner_id.invoice_edi_format == 'es_facturae'
                    and not wizard.move_id.l10n_es_edi_facturae_xml_id
                )
                checkboxes['es_facturae'] = es_facturae_checkbox
                wizard.extra_edi_checkboxes = checkboxes

    def action_send_and_print(self, allow_fallback_pdf=False):
        action = super().action_send_and_print(allow_fallback_pdf)
        checkboxes = self.extra_edi_checkboxes or {}
        if 'es_facturae' in checkboxes and checkboxes['es_facturae']['checked']:
            # Set partner's invoice_edi_format to 'es_facturae' after sending
            partner = self.move_id.partner_id
            partner.invoice_edi_format = 'es_facturae'
        return action
