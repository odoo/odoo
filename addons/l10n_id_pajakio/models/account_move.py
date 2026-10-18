from odoo import models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_id_pajakio_check_eligibility(self):
        """
        Check if invoice is eligible to be sent to Pajak.io. Raise errors if some conditions are violated
        """

        err_messages = self._check_efaktur_eligibility()

        if not self.company_id.city:
            err_messages.append(self.env._("Your company's city hasn't been configured yet."))

        if err_messages:
            raise UserError(
                self.env._('Unable to send to pajak.io for the following reasons(s):\n%(errors)s', errors='\n - '.join(err_messages)),
            )

    def _l10n_id_pajakio_prepare_invoice_payload(self):
        """ Prepare the JSON data that will be used when sending invoice data to Pajak.io """
        self.ensure_one()
        self._l10n_id_pajakio_check_eligibility()

        if not self.l10n_id_coretax_document:
            self.l10n_id_coretax_document = self.env['l10n_id_efaktur_coretax.document'].create({
                'invoice_ids': self.ids,
                'company_id': self.company_id.id,
                'document_type': 'pajakio',
            })

        return self.l10n_id_coretax_document._prepare_invoice_payload_pajakio()

    def button_request_cancel(self):
        # EXTENDS 'account'
        if self._need_cancel_request() and self.l10n_id_coretax_document.l10n_id_pajakio_status == 'approved':
            return {
                'name': self.env._('Cancel Pajak.io Invoice'),
                'type': 'ir.actions.act_window',
                'res_model': 'l10n_id_pajakio.invoice.cancel',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_invoice_id': self.id,
                },
            }
        return super().button_request_cancel()

    def _need_cancel_request(self):
        # EXTENDS 'account'
        return super()._need_cancel_request() or self.l10n_id_coretax_document.l10n_id_pajakio_status == 'approved'
