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
        res.update({'tr_nilvera': {'label': _("by Nilvera"), 'is_applicable': self._is_tr_nilvera_applicable}})
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        alerts = super()._get_alerts(moves, moves_data)

        # Filter for moves that have 'tr_nilvera' in their EDI data
        tr_nilvera_moves = moves.filtered(lambda m: 'tr_nilvera' in moves_data[m]['extra_edis'])

        # Show alert if the current company is in Türkiye and test mode is enabled for Nilvera
        if self.env.company.account_fiscal_country_id.code == 'TR' and self.env.company.l10n_tr_nilvera_use_test_env:
            alerts['l10n_tr_nilvera_einvoice_test_mode'] = {
                'level': 'info',
                'message': _("Testing mode is enabled."),
            }

        # Alert if company is missing required data (country = TR, and tax ID, city, state, street)
        if tr_companies_missing_required_fields := tr_nilvera_moves.filtered(
            lambda m: (
                not m.company_id.vat
                or not m.company_id.street
                or not m.company_id.city
                or not m.company_id.state_id
                or m.company_id.country_code != 'TR'
            )
        ).company_id:
            alerts["tr_companies_missing_required_fields"] = {
                'level': 'danger',
                "message": _(
                    "The following company(s) either do not have their country set as Türkiye "
                    "or are missing at least one of these fields: Tax ID, Street, City, or State"
                ),
                "action_text": _("View Company(s)"),
                "action": tr_companies_missing_required_fields._get_records_action(name=_(
                    "Check Tax ID, City, Street, State, and Country or Company(s)"
                )),
            }

        # Alert if partner is missing required data (tax ID, street, city, state, country)
        if tr_partners_missing_required_fields := tr_nilvera_moves.filtered(
            lambda m: (
                not m.partner_id.vat
                or not m.partner_id.street
                or not m.partner_id.city
                or not m.partner_id.state_id
                or not m.partner_id.country_id
            )
        ).partner_id:
            alerts["tr_partners_missing_required_fields"] = {
                'level': 'danger',
                "message": _(
                    "The following partner(s) are missing at least one of these fields: Tax ID, Street, City, State or Country"
                ),
                "action_text": _("View Partner(s)"),
                "action": tr_partners_missing_required_fields._get_records_action(name=_(
                    "Check Tax ID, City, Street, State, and Country or Partner(s)"
                )),
            }

        # Alert if partner has Street 2 filled, which is not allowed
        if tr_partners_with_street2 := tr_nilvera_moves.filtered(lambda m: (m.partner_id.street2)).partner_id:
            alerts["tr_partners_with_street2"] = {
                'level': 'danger',
                "message": _("The following partner(s) must have Street 2 empty"),
                "action_text": _("View Partner(s)"),
                "action": tr_partners_with_street2._get_records_action(name=_("Check Street 2 on Partner(s)")),
            }

        # Alert if partner does not use UBL TR e-invoice format or has not checked Nilvera status
        if tr_partners_invalid_edi_or_status := tr_nilvera_moves.filtered(
            lambda m: (
                m.partner_id.invoice_edi_format != 'ubl_tr'
                or m.partner_id.l10n_tr_nilvera_customer_status == 'not_checked'
            )
        ).partner_id:
            alerts["tr_partners_invalid_edi_or_status"] = {
                'level': 'danger',
                "message": _(
                    "The following partner(s) either do not have the e-invoice format UBL TR 1.2 "
                    "or have not checked their Nilvera Status"
                ),
                "action_text": _("View Partner(s)"),
                "action": tr_partners_invalid_edi_or_status._get_records_action(
                    name=_("Check e-Invoice Format or Nilvera Status on Partner(s)"
                )),
            }

        if tr_invalid_subscription_dates := moves.filtered(
            lambda move: move._l10n_tr_nilvera_einvoice_check_invalid_subscription_dates()
        ):
            alerts["tr_invalid_subscription_dates"] = {
                'level': 'danger',
                "message": _(
                    "The following invoice(s) need to have the same Start Date and End Date "
                    "on all their respective Invoice Lines."
                ),
                "action_text": _("View Invoice(s)"),
                "action": tr_invalid_subscription_dates._get_records_action(
                    name=_("Check data on Invoice(s)"),
                ),
            }

        # Alert if partner is missing Tax office name on reference field
        if tr_einvoice_partners_missing_ref := moves.partner_id.filtered(
            lambda p: p.l10n_tr_nilvera_customer_status == "einvoice" and not p.ref
        ):
            alerts["critical_partner_missing_reference_field"] = {
                "message": _(
                    "The following E-Invoice partner(s) must have the reference field set to the tax office name."
                ),
                "action_text": _("View Partner(s)"),
                "action": tr_einvoice_partners_missing_ref._get_records_action(
                    name=_("Check reference on Partner(s)")
                ),
                "level": "danger",
            }

        # Alert if company is missing Tax office name on reference field
        if (
            tr_companies_missing_required_fields
            := tr_nilvera_moves.company_id.partner_id.filtered(lambda p: not p.ref)
        ):
            alerts["tr_companies_missing_reference_field"] = {
                "level": "danger",
                "message": _(
                    "The following company(s) must have the reference field set to the tax office name."
                ),
                "action_text": _("View Company(s)"),
                "action": tr_companies_missing_required_fields._get_records_action(
                    name=_("Check reference on Company(s)")
                ),
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
                    invoice.partner_id._check_nilvera_customer()
                customer_alias = invoice.partner_id.l10n_tr_nilvera_customer_alias_id.name
                if customer_alias:  # E-Invoice
                    invoice._l10n_tr_nilvera_submit_einvoice(xml_file, customer_alias)
                else:   # E-Archive
                    invoice._l10n_tr_nilvera_submit_earchive(xml_file)
