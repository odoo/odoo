import stdnum.pt.nif
from odoo import _, models
from odoo.exceptions import RedirectWarning


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
        if (
            invoice.country_code == 'PT'
            and (not invoice.company_id.vat or not stdnum.pt.nif.is_valid(invoice.company_id.vat))
        ):
            action = self.env.ref('base.action_res_company_form')
            raise RedirectWarning(_('Please define the VAT on your company (e.g. PT123456789)'),
                                  action.id,
                                  _('Company Settings'))

    def _get_alerts(self, moves, moves_data):
        """
        Add date format alert, when partner's date format does not match Portugal's required format. According to
        the Portuguese tax authorities, printed documents must have the date in format 'YYYY-MM-DD' or 'DD-MM-YYYY'.
        """
        alerts = super()._get_alerts(moves, moves_data)
        if pt_moves := moves.filtered(lambda m: m.country_code == 'PT'):
            lang_codes = pt_moves.mapped('partner_id.lang')
            langs = self.env['res.lang'].search([
                ('code', 'in', lang_codes),
                ('date_format', 'not in', ("%Y-%m-%d", "%d-%m-%Y"))
            ])
            if langs:
                alerts['l10n_pt_configure_partner_language'] = {
                    'message': _("Some partners have a language with a date format that does not match Portugal's"
                                 "requirements (either 'YYYY-MM-DD' or 'DD-MM-YYYY'). "
                                 "Please configure the date format in these languages."),
                    'level': 'info',
                    'action_text': _("View Language(s)"),
                    'action': langs._get_records_action(),
                }
        return alerts
