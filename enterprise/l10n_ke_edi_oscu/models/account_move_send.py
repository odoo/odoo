# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, models
from markupsafe import Markup


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_oscu_applicable(self, move):
        return move.company_id.l10n_ke_oscu_is_active and not move.l10n_ke_oscu_receipt_number

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({'ke_oscu': {'label': _("Send to eTIMS"), 'is_applicable': self._is_oscu_applicable}})
        return res

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            if 'ke_oscu' in invoice_data['extra_edis']:
                validation_messages = (invoice.l10n_ke_validation_message or {}).values()
                if (blocking := [msg for msg in validation_messages if msg.get('blocking')]):
                    invoice_data['error'] = {
                        'error_title': _("Can't send to eTIMS"),
                        'errors': [msg['message'] for msg in blocking],
                    }
                    continue
                _content, error = invoice._l10n_ke_oscu_send_customer_invoice()

                if error:
                    invoice_data['error'] = {
                        'error_title': _("Error when sending to the KRA:"),
                        'errors': [error['message']],
                    }
                    # To help support diagnose issues, log timeouts in the chatter
                    if error['code'] == 'TIM':
                        invoice.message_post(body=Markup('<p>%s</p>') % error['message'])

                if self._can_commit():
                    self._cr.commit()
