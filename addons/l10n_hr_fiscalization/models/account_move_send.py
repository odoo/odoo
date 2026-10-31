import zoneinfo

from odoo import api, fields, models
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

    @api.model
    def _generate_and_send_invoices(self, moves, from_cron=False, allow_raising=True, allow_fallback_pdf=False, **custom_settings):
        for move in moves:
            if self._is_fiscalization_applicable(move) and not move.l10n_hr_edi_addendum_id:
                move.l10n_hr_edi_addendum_id = self.env['l10n_hr_edi.addendum'].create({
                    'move_id': move.id,
                    'payment_method_type': move.l10n_hr_payment_method_type,
                    'fiscalization_number': move._get_l10n_hr_fiscalization_number(move.name),
                    'invoice_sending_time': fields.Datetime.now(zoneinfo.ZoneInfo('Europe/Zagreb')),
                })
        return super()._generate_and_send_invoices(moves, from_cron=from_cron, allow_raising=allow_raising, allow_fallback_pdf=allow_fallback_pdf, **custom_settings)

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
                    raise e
                if invoice.invoice_pdf_report_id:
                    # force it to regenerate
                    invoice.write({'invoice_pdf_report_file': False})
                if self._can_commit():
                    self.env.cr.commit()
