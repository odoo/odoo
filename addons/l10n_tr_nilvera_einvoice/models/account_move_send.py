from io import BytesIO
import logging
import re

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
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        # Add the Nilvera PDF to the mail attachments.
        attachments = super()._get_invoice_extra_attachments(move)
        if move.l10n_tr_nilvera_send_status == 'succeed' and move.message_main_attachment_id.id != move.invoice_pdf_report_id.id:
            attachments += move.message_main_attachment_id
        return attachments

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        def _is_valid_nilvera_name(move):
            _, parts = move._get_sequence_format_param(move.name)

            return (
                parts['year'] != 0
                and parts['year_length'] == 4
                and parts['seq'] != 0
                and re.match(r'^[A-Za-z0-9]{3}[^A-Za-z0-9]?$', parts['prefix1'])
            )

        alerts = super()._get_alerts(moves, moves_data)

        # Filter for moves that have 'tr_nilvera' in their EDI data
        tr_nilvera_moves = moves.filtered(lambda m: 'tr_nilvera' in moves_data[m]['extra_edis'])

        # Show alert if the current company is in Türkiye and test mode is enabled for Nilvera
        if self.env.company.account_fiscal_country_id.code == 'TR' and self.env.company.l10n_tr_nilvera_use_test_env:
            alerts['l10n_tr_nilvera_einvoice_test_mode'] = {
                'level': 'info',
                'message': _("Testing mode is enabled."),
            }

        if tr_companies_missing_required_codes := tr_nilvera_moves.company_id.filtered(lambda c: c.country_code == 'TR' and not (c.partner_id.category_id.parent_id and self.env["res.partner.category"]._get_l10n_tr_official_mandatory_categories())):
            alerts["tr_companies_missing_required_codes"] = {
                "message": _("Please ensure that your company contact has either the 'MERSISNO' or 'TICARETSICILNO' tag with a value assigned."),
                "action_text": _("View Company(s)"),
                "action": tr_companies_missing_required_codes.partner_id._get_records_action(name=_("Check tags on company(s)")),
                "level": "danger",
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
        if tr_partners_missing_required_fields := self._get_l10n_tr_tax_partner_address_alert(tr_nilvera_moves):
            alerts["tr_partners_missing_required_fields"] = tr_partners_missing_required_fields

        # Alert if partner is missing required tax office
        if tr_partners_missing_tax_office := self._get_l10n_tr_tax_partner_tax_office_alert(tr_nilvera_moves):
            alerts["tr_partners_missing_tax_office"] = tr_partners_missing_tax_office

        # Alert if TR company is missing required tax office
        if tr_companies_missing_tax_office := self._get_l10n_tr_tax_company_tax_office_alert(tr_nilvera_moves):
            alerts["tr_companies_missing_tax_office"] = tr_companies_missing_tax_office

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

        if invalid_negative_lines := tr_nilvera_moves.filtered(
            lambda move: move._l10n_tr_nilvera_einvoice_check_negative_lines(),
        ):
            alerts["critical_invalid_negative_lines"] = {
                "level": "danger",
                "message": _("Nilvera portal cannot process negative quantity nor negative price on invoice lines"),
                "action_text": _("View Invoice(s)"),
                "action": invalid_negative_lines._get_records_action(name=_("Check data on Invoice(s)")),
            }

        if moves_with_invalid_name := tr_nilvera_moves.filtered(lambda move: not _is_valid_nilvera_name(move)):
            alerts['tr_moves_with_invalid_name'] = {
                'level': 'danger',
                'message': _(
                    "The invoice name must follow the format when sending to Nilvera: 3 alphanumeric characters, "
                    "followed by the year, and then a sequential number. Example: INV/2025/000001",
                ),
                'action_text': _("View Invoice(s)"),
                'action': moves_with_invalid_name._get_records_action(name=_("Check name on Invoice(s)")),
            }

        return alerts

    def _get_l10n_tr_tax_partner_address_alert(self, moves):
        # Extended in l10n_tr_nilvera_einvoice_extended to remove error based on l10n_tr_is_export_invoice
        if tr_partners_missing_required_fields := moves.filtered(
            lambda m: (
                not m.partner_id.vat
                or not m.partner_id.street
                or not m.partner_id.city
                or not m.partner_id.state_id
                or not m.partner_id.country_id
            ),
        ).partner_id:
            return {
                "message": _("The following partner(s) are missing at least one of these fields: Tax ID, Street, City, State or Country"),
                "action_text": _("View Partner(s)"),
                "action": tr_partners_missing_required_fields._get_records_action(name=_("Check Tax ID, City, Street, State, and Country or Partner(s)")),
                "level": "danger",
            }
        return {}

    def _get_l10n_tr_tax_partner_tax_office_alert(self, moves):
        # Overriden in l10n_tr_nilvera_einvoice_extended to give error based on l10n_tax_office field
        if tr_einvoice_partners_missing_ref := moves.partner_id.filtered(lambda p: p.l10n_tr_nilvera_customer_status == "einvoice" and not p.ref and p.country_code == "TR"):
            return {
                "message": _("The following E-Invoice partner(s) must have the reference field set to the tax office name."),
                "action_text": _("View Partner(s)"),
                "action": tr_einvoice_partners_missing_ref._get_records_action(name=_("Check reference on Partner(s)")),
                "level": "danger",
            }

        return {}

    def _get_l10n_tr_tax_company_tax_office_alert(self, moves):
        # Overriden in l10n_tr_nilvera_einvoice_extended to give error based on l10n_tax_office field
        if tr_companies_missing_tax_office := moves.company_id.partner_id.filtered(lambda p: not p.reference and p.country_code == "TR"):
            return {
                "message": _("The following TR Company(s) must have the reference field set to the tax office name."),
                "action_text": _("View Company(s)"),
                "action": tr_companies_missing_tax_office._get_records_action(name=_("TR Company(s)")),
                "level": "danger",
            }
        return {}

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
                customer_alias = invoice._get_partner_l10n_tr_nilvera_customer_alias_name()
                if customer_alias:  # E-Invoice
                    invoice._l10n_tr_nilvera_submit_einvoice(xml_file, customer_alias)
                else:   # E-Archive
                    invoice._l10n_tr_nilvera_submit_earchive(xml_file)

    @api.model
    def _postprocess_invoice_ubl_xml(self, invoice, invoice_data):
        # EXTENDS account_edi_ubl_cii
        # Nilvera rejects XMLs with the PDF attachment.

        if invoice_data['invoice_edi_format'] == 'ubl_tr':
            return

        return super()._postprocess_invoice_ubl_xml(invoice, invoice_data)
