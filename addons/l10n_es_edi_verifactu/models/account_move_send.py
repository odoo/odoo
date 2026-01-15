from odoo import _, api, models
from odoo.exceptions import RedirectWarning


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _l10n_es_edi_verifactu_get_move_info(self, moves):
        # We do not support sending a registration for already registered move or in case we are waiting to send a document already
        verifactu_moves = moves.filtered(lambda move: move.l10n_es_edi_verifactu_required)
        waiting_moves = verifactu_moves.filtered(lambda m: m.l10n_es_edi_verifactu_document_ids._filter_waiting())
        registered_moves = verifactu_moves.filtered(
            lambda m: m.l10n_es_edi_verifactu_state in ('registered_with_errors', 'accepted')
        )
        return {
            'verifactu_moves': verifactu_moves,
            'waiting_moves': waiting_moves,
            'registered_moves': registered_moves,
            'moves_to_send': verifactu_moves - waiting_moves - registered_moves,
        }

    @api.model
    def _is_es_verifactu_applicable(self, move):
        return bool(self._l10n_es_edi_verifactu_get_move_info(move)['verifactu_moves'])

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({'es_verifactu': {'label': _("Veri*Factu"), 'is_applicable': self._is_es_verifactu_applicable}})
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        verifactu_info = self._l10n_es_edi_verifactu_get_move_info(moves)
        if verifactu_info['waiting_moves']:
            alerts['l10n_es_edi_verifactu_warning_waiting_moves'] = {
                'message': _(
                    "The following entries wil be skipped. They are already waiting to send Veri*Factu records to the AEAT: %s.",
                    ', '.join(verifactu_info['waiting_moves'].mapped('name'))
                ),
                'action_text': _("View Invoice(s)"),
                'action': verifactu_info['waiting_moves']._get_records_action(name=_("Check Invoice(s)")),
            }
        if verifactu_info['registered_moves']:
            alerts['l10n_es_edi_verifactu_warning_registered_moves'] = {
                'message': _(
                    "The following entries wil be skipped. They are already registered with the AEAT: %s.",
                    ', '.join(verifactu_info['registered_moves'].mapped('name'))
                ),
                'action_text': _("View Invoice(s)"),
                'action': verifactu_info['registered_moves']._get_records_action(name=_("Check Invoice(s)")),
            }
        return alerts

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            if 'es_verifactu' not in invoice_data['extra_edis']:
                continue
            vals = invoice._l10n_es_edi_verifactu_get_record_values()
            action = msg = None

            if vals['verifactu_move_type'] == 'correction_substitution' and not vals['substituted_document']:
                substituted_move = invoice.l10n_es_edi_verifactu_substituted_entry_id
                msg = _("There is no Veri*Factu document for the substituted record.")
                action = invoice._l10n_es_edi_verifactu_action_go_to_journal_entry(substituted_move)
            elif vals['verifactu_move_type'] == 'correction_substitution' and not vals['substituted_document_reversal_document']:
                substituted_move = invoice.l10n_es_edi_verifactu_substituted_entry_id
                msg = _("There is no Veri*Factu document for the reversal of the substituted record.")
                action = invoice._l10n_es_edi_verifactu_action_go_to_journal_entry(substituted_move.reversal_move_ids)
            elif vals['verifactu_move_type'] in ('correction_incremental', 'reversal_for_substitution') and not vals['refunded_document']:
                reversed_move = invoice.reversed_entry_id
                msg = _("There is no Veri*Factu document for the refunded record.")
                action = invoice._l10n_es_edi_verifactu_action_go_to_journal_entry(reversed_move)

            if action and msg:
                invoice_data['error'] = {
                    'verifactu_redirect_action': action,
                    'error_title': _("Go to the journal entry"),
                    'errors': [msg],
                }

        checked_invoices = self.env['account.move'].browse([
            invoice.id for invoice, invoice_data in invoices_data.items()
            if 'es_verifactu' in invoice_data['extra_edis'] and not invoice_data.get('error', {}).get('verifactu_redirect_action')
        ])
        invoices_to_send = self._l10n_es_edi_verifactu_get_move_info(checked_invoices)['moves_to_send']

        created_document = invoices_to_send._l10n_es_edi_verifactu_mark_for_next_batch()

        for invoice in invoices_to_send:
            if not created_document[invoice].chain_index:
                invoices_data[invoice]['error'] = {
                    'error_title': _("The Veri*Factu document could not be created for all invoices."),
                    'errors': [_("See the 'Veri*Factu' tab for more information.")],
                }

        if created_document and self._can_commit():
            self.env.cr.commit()

    def _hook_if_errors(self, moves_data, allow_raising=True):
        # EXTENDS 'account'
        if allow_raising:
            for move, move_data in moves_data.items():
                error = move_data.get('error', {})
                if isinstance(error, dict) and error.get('verifactu_redirect_action'):
                    raise RedirectWarning('\n'.join(error['errors']), error['verifactu_redirect_action'], error['error_title'])
        super()._hook_if_errors(moves_data, allow_raising=allow_raising)
