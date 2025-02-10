import stdnum.pt.nif
from odoo import models, _
from odoo.exceptions import RedirectWarning


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
        if invoice.country_code == 'PT':
            # Hashing the invoice triggers the creation of the QR code to be displayed on the generated PDF attachment
            if not invoice.company_id.vat or not stdnum.pt.nif.is_valid(invoice.company_id.vat):
                action = self.env.ref('base.action_res_company_form')
                raise RedirectWarning(_('Please define the VAT on your company (e.g. PT123456789)'),
                                      action.id,
                                      _('Company Settings'))
            invoice.button_hash()

    def _get_alerts(self, moves, moves_data):
        """
        Add date format alert, when partner's date format does not match Portugal's required format. According to
        the Portuguese tax authorities, printed documents must have the date in format 'YYYY-MM-DD' or 'DD-MM-YYYY'.
        """
        alerts = super()._get_alerts(moves, moves_data)
        if pt_moves := moves.filtered(lambda m: m.country_code == 'PT'):
            languages_with_diff_date_format = self.env['res.lang']
            formats = ["%Y-%m-%d", "%d-%m-%Y"]
            partners = pt_moves.mapped('partner_id')
            lang_codes = partners.mapped('lang')
            langs = self.env['res.lang'].search([('code', 'in', lang_codes)])
            for lang in langs:
                if lang.date_format not in formats:
                    languages_with_diff_date_format += lang
            if languages_with_diff_date_format:
                alerts['l10n_pt_configure_partner_language'] = {
                    'message': _("The language of some partners has a date format that does not match Portugal's requirements (either 'YYYY-MM-DD' or 'DD-MM-YYYY'). "
                                 "Please configure the date format in these languages."),
                    'level': 'info',
                    'action_text': _("View Language(s)"),
                    'action': languages_with_diff_date_format._get_records_action(),
                }
        return alerts
