from io import BytesIO
import logging

from odoo import _, api, models

_logger = logging.getLogger(__name__)


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_tr_nilvera_applicable(self, move):
        return move.l10n_tr_nilvera_send_status == 'not_sent' and move.is_invoice(include_receipts=True) and move.country_code == 'TR'

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({'tr_nilvera': {'label': _("Send E-Invoice to Nilvera"), 'is_applicable': self._is_tr_nilvera_applicable}})
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        alerts = super()._get_alerts(moves, moves_data)
        moves_to_check = moves.filtered(self._is_tr_nilvera_applicable)
        if tr_companies_missing_required_codes := moves_to_check.company_id.filtered(
            lambda c: c.country_code == 'TR' and not (c.partner_id.category_id.parent_id and self.env["res.partner.category"]._get_l10n_tr_official_mandatory_categories())
        ):
            alerts["tr_companies_missing_required_codes"] = {
                "message": _("Please ensure that your company contact has either the 'MERSISNO' or 'TICARETSICILNO' tag with a value assigned."),
                "action_text": _("View Company(s)"),
                "action": tr_companies_missing_required_codes.partner_id._get_records_action(name=_("Check tags on company(s)")),
                "level": "danger",
            }

        if tr_partners_missing_address := moves_to_check.filtered(
                lambda m: 'tr_nilvera' in moves_data[m]['extra_edis'] and (m.partner_id.country_code != 'TR' or not m.partner_id.city or not m.partner_id.state_id or not m.partner_id.street)
        ).partner_id:
            alerts["partner_data_missing"] = {
                "message": _("The following partner(s) are either not Turkish or are missing one of those fields: city, state and street."),
                "action_text": _("View Partner(s)"),
                "action": tr_partners_missing_address._get_records_action(name=_("Check data on Partner(s)")),
            }

        if tr_invalid_subscription_dates := moves_to_check.filtered(
            lambda move: move._l10n_tr_nilvera_einvoice_check_invalid_subscription_dates()
        ):
            alerts["critical_invalid_subscription_dates"] = {
                "message": _("The following invoice(s) need to have the same Start Date and End Date on all their respective Invoice Lines."),
                "action_text": _("View Invoice(s)"),
                "action": tr_invalid_subscription_dates._get_records_action(
                    name=_("Check data on Invoice(s)"),
                ),
                "level": "danger",
            }

        if tr_einvoice_partners_missing_ref := moves_to_check.partner_id.filtered(
            lambda p: p.l10n_tr_nilvera_customer_status == "einvoice" and not p.ref
        ):
            alerts["critical_partner_data_missing"] = {
                "message": _("The following partner(s) are either not Turkish or are missing one of those fields: city, state and street."),
                "action_text": _("View Partner(s)"),
                "action": tr_einvoice_partners_missing_ref._get_records_action(name=_("Check reference on Partner(s)")),
                "level": "danger",
            }

        if invalid_negative_lines := moves_to_check.filtered(
            lambda move: move._l10n_tr_nilvera_einvoice_check_negative_lines(),
        ):
            alerts["critical_invalid_negative_lines"] = {
                "message": _("Nilvera portal cannot process negative quantity nor negative price on invoice lines"),
                "action_text": _("View Invoice(s)"),
                "action": invalid_negative_lines._get_records_action(name=_("Check data on Invoice(s)")),
                "level": "danger",
            }

        return alerts

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------
    def _link_invoice_documents(self, invoices_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoices_data)
        # The move needs to be put as sent only if sent by Nilvera
        for invoice, invoice_data in invoices_data.items():
            if invoice.company_id.country_code == 'TR':
                invoice.is_move_sent = invoice.l10n_tr_nilvera_send_status == 'sent'


    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            if 'tr_nilvera' in invoice_data['extra_edis']:
                if attachment_values := invoice_data.get('ubl_cii_xml_attachment_values'):
                    xml_file = BytesIO(attachment_values.get('raw'))
                    xml_file.name = attachment_values['name']
                else:
                    xml_file = BytesIO(invoice.ubl_cii_xml_id.raw or b'')
                    xml_file.name = invoice.ubl_cii_xml_id.name or ''

                if not invoice.partner_id.l10n_tr_nilvera_customer_alias_id:
                    # If no alias is saved, the user is either an E-Archive user or we haven't checked before. Check again
                    # just in case.
                    invoice.partner_id.check_nilvera_customer()
                customer_alias = invoice.partner_id.l10n_tr_nilvera_customer_alias_id.name
                if customer_alias:  # E-Invoice
                    invoice._l10n_tr_nilvera_submit_einvoice(xml_file, customer_alias)
                else:   # E-Archive
                    invoice._l10n_tr_nilvera_submit_earchive(xml_file)
