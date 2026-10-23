import stdnum.pt.nif
from odoo import _, api, models
from odoo.exceptions import RedirectWarning, UserError


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

    @api.model
    def _generate_and_send_invoices(self, moves, from_cron=False, allow_raising=True, allow_fallback_pdf=False, **custom_settings):
        # EXTENDS account
        # Sending an invoice generates it: it is issued before any of its documents is made (the
        # e-invoice XML is built before the PDF), along with the invoices before it in its series that
        # are not issued yet. From the cron it is issued as the user who asked for the sending; one
        # that cannot be issued is not sent, with the reason in its chatter.
        to_issue = moves.filtered(lambda m: m._l10n_pt_country_ok() and not m.l10n_pt_document_number)
        if to_issue and (from_cron or not allow_raising):
            moves -= self._l10n_pt_issue_or_log(to_issue)
        else:
            to_issue._l10n_pt_issue_with_predecessors()
        return super()._generate_and_send_invoices(
            moves, from_cron=from_cron, allow_raising=allow_raising, allow_fallback_pdf=allow_fallback_pdf, **custom_settings,
        )

    @api.model
    def _l10n_pt_issue_or_log(self, moves):
        """Issue ``moves``, in one go if possible, and return those that could not be, after logging why."""
        def issue(moves_to_issue):
            for author_id, author_moves in moves_to_issue.grouped(lambda m: (m.sending_data or {}).get('author_user_id')).items():
                author_moves.with_context(l10n_pt_issue_user_id=author_id)._l10n_pt_issue_with_predecessors()

        try:
            with self.env.cr.savepoint():
                issue(moves)
            return moves.browse()
        except (UserError, RedirectWarning):
            pass
        failed = moves.browse()
        # One by one, in the order of their numbers, so that each is issued if it can be.
        for move in moves.sorted('sequence_number'):
            try:
                with self.env.cr.savepoint():
                    issue(move)
            except (UserError, RedirectWarning) as error:
                failed |= move
                move.sending_data = False
                move.message_post(body=_("This invoice could not be issued, so it was not sent: %s", error.args[0]))
        return failed

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
