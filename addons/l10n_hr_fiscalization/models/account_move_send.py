from odoo import api, models
from odoo.exceptions import UserError


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_fiscalization_applicable(self, move):
        return (
            move.move_type in ('out_invoice', 'out_refund')
            and move.company_id.country_code == 'HR'
            and move.company_id.l10n_hr_fiscalization_certificate
            and not move.partner_id.commercial_partner_id.is_company
        )

    def _get_all_extra_edis(self):
        res = super()._get_all_extra_edis()
        res.update({
            'fiscalization': {
                'label': self.env._("Fiscalization"),
                'is_applicable': self._is_fiscalization_applicable
            }
        })
        return res

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            if (
                self._is_fiscalization_applicable(invoice)
                and 'fiscalization' in invoice_data['extra_edis']
            ):
                try:
                    invoice.l10n_hr_fiscalize_invoice()
                except UserError as e:
                    invoice_data['error'] = str(e)
                    raise
                if invoice.invoice_pdf_report_file:
                    # force it to regenerate
                    invoice.write({'invoice_pdf_report_file': False})
