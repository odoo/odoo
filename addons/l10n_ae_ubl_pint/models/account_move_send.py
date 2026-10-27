from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _generate_and_send_invoices(self, moves, from_cron=False, allow_raising=True, allow_fallback_pdf=False, **custom_settings):
        """ Verify the buyers' Peppol status, when their Peppol identifier is set, before the
        documents are built: it decides their endpoint, their own or a predefined one (see
        account.move._l10n_ae_get_predefined_buyer_endpoint). Also for a company not sending on
        Peppol itself (e.g. through ClearTax), unlike account_peppol's own verification.
        """
        # EXTENDS 'account_peppol'
        uae_sales = moves.filtered(lambda move: move.l10n_ae_company_country_code == 'AE' and move.is_sale_document())
        for partner, company in uae_sales.grouped(lambda move: (move.commercial_partner_id, move.company_id)):
            if partner.with_company(company).peppol_verification_state != 'valid':
                partner.button_account_peppol_check_partner_endpoint(company=company)
        return super()._generate_and_send_invoices(moves, from_cron, allow_raising, allow_fallback_pdf, **custom_settings)

    def _is_applicable_to_move(self, method, move, **move_data):
        # EXTENDS 'account_peppol'
        if method == 'peppol' and not move._l10n_ae_is_sent_by_peppol():
            return False
        return super()._is_applicable_to_move(method, move, **move_data)

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        alerts.update(self._l10n_ae_pint_get_moves_alerts(
            moves.filtered(lambda m: moves_data[m]['invoice_edi_format'] == 'pint_ae'),
        ))
        return alerts

    @api.model
    def _l10n_ae_pint_get_moves_alerts(self, moves):
        """ The alerts for the PINT AE rules these moves, their partners and their lines break. """
        if not moves:
            return {}
        partners = moves.commercial_partner_id | moves.company_id.partner_id
        return {
            **self._l10n_ae_pint_get_alerts(moves, self.env._("View Invoice(s)")),
            **self._l10n_ae_pint_get_alerts(partners, self.env._("View Partner(s)")),
            **self._l10n_ae_pint_get_alerts(
                moves.invoice_line_ids, self.env._("View Invoice(s)"), get_action_records=lambda lines: lines.move_id,
            ),
        }

    @api.model
    def _l10n_ae_pint_get_alerts(self, records, action_text, get_action_records=None):
        """ The alerts for the PINT AE rules these records break, one per rule.

        Each model gives the rule a record breaks with `_l10n_ae_pint_group_by_error_code`.

        :param records: invoices, partners or invoice lines.
        :param action_text: label of the alert's button.
        :param get_action_records: the records the button opens for the offending ones, these by default.
        """
        alert_vals = {}
        for error_tuple, invalid_records in records.grouped(lambda r: r._l10n_ae_pint_group_by_error_code()).items():
            if not error_tuple:
                continue
            error_vals = dict(error_tuple)
            action_records = get_action_records(invalid_records) if get_action_records else invalid_records
            alert_vals[error_vals['error_code']] = {
                'message': error_vals['message'],
                'level': error_vals['level'],
                'action': action_records._get_records_action(),
                'action_text': action_text,
            }
        return alert_vals
