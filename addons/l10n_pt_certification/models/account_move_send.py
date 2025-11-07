from itertools import groupby

from odoo import api, models
from odoo.exceptions import RedirectWarning, UserError

from odoo.addons.l10n_pt_certification.utils import hashing as pt_hash_utils


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _generate_and_send_invoices(self, moves, from_cron=False, allow_raising=True, allow_fallback_pdf=False, **custom_settings):
        # EXTENDS account
        # Sending an invoice generates it: it is issued before any of its documents is made (the
        # e-invoice XML is built before the PDF), along with the invoices before it in its series that
        # are not issued yet. From the cron it is issued as the user who asked for the sending; one
        # that cannot be issued is not sent, with the reason in its chatter.
        to_issue = moves.filtered(lambda m: m._l10n_pt_country_ok() and not m.l10n_pt_document_number)
        if to_issue and (from_cron or not allow_raising):
            moves -= (to_issue - self._l10n_pt_issue_or_log(to_issue))
        else:
            to_issue._l10n_pt_issue()
        return super()._generate_and_send_invoices(
            moves, from_cron=from_cron, allow_raising=allow_raising, allow_fallback_pdf=allow_fallback_pdf, **custom_settings,
        )

    @api.model
    def _l10n_pt_issue_or_log(self, moves):
        """
        Issue ``moves`` AT series by AT series, and return those that were issued.

        In a series, an invoice is issued with those before it (`account.move._l10n_pt_issue`), and
        what prevents issuing (a gap, the company's VAT or clock) holds for a whole series or company:
        the invoices of a series are issued, or not, together. Those not issued are not sent, with the
        reason in their chatter. While the signing service cannot be reached, no series can be: none is
        tried further.
        """
        def stop_sending(moves_not_issued, error):
            moves_not_issued.sending_data = False
            for move in moves_not_issued:
                move.message_post(body=self.env._("This invoice could not be issued, so it was not sent: %s", error.args[0]))

        issued = failed = moves.browse()
        for series_moves in moves.grouped('l10n_pt_at_series_id').values():
            try:
                with self.env.cr.savepoint():
                    # Each issued as the user who asked for its sending. In consecutive runs, not
                    # `grouped`: issuing a run also issues the earlier invoices, as the run's author.
                    for author_id, author_moves in groupby(
                        series_moves.sorted('sequence_number'),
                        key=lambda m: (m.sending_data or {}).get('author_user_id'),
                    ):
                        author_moves = self.env['account.move'].concat(*author_moves)
                        author_moves.with_context(l10n_pt_issue_user_id=author_id)._l10n_pt_issue()
            except pt_hash_utils.L10nPtSigningUnavailable as error:
                stop_sending(moves - issued - failed, error)
                break
            except (UserError, RedirectWarning) as error:
                stop_sending(series_moves, error)
                failed |= series_moves
            else:
                issued |= series_moves
        return issued

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
                    'message': self.env._("Some partners have a language with a date format that does not match Portugal's "
                                 "requirements (either 'YYYY-MM-DD' or 'DD-MM-YYYY'). "
                                 "Please configure the date format in these languages."),
                    'level': 'info',
                    'action_text': self.env._("View Language(s)"),
                    'action': langs._get_records_action(),
                }
        return alerts
