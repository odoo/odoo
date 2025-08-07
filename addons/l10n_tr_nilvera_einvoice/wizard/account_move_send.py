from io import BytesIO

from odoo import _, api, fields, models


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    l10n_tr_nilvera_einvoice_enable_xml = fields.Boolean(compute='_compute_l10n_tr_nilvera_einvoice_enable_xml')
    l10n_tr_nilvera_einvoice_checkbox_xml = fields.Boolean(
        string="Send E-Invoice to Nilvera",
        compute='_compute_l10n_tr_nilvera_einvoice_checkbox_xml',
        store=True,
        readonly=False,
    )
    l10n_tr_nilvera_warnings = fields.Json(compute='_compute_l10n_tr_nilvera_warnings')

    def _get_wizard_values(self):
        # EXTENDS 'account'
        values = super()._get_wizard_values()
        values['l10n_tr_nilvera_einvoice_xml'] = self.l10n_tr_nilvera_einvoice_checkbox_xml
        return values

    @api.model
    def _get_wizard_vals_restrict_to(self, only_options):
        # EXTENDS 'account'
        values = super()._get_wizard_vals_restrict_to(only_options)
        return {
            'l10n_tr_nilvera_einvoice_checkbox_xml': False,
            **values,
        }

    @api.model
    def _get_default_l10n_tr_nilvera_einvoice_enable_einvoice(self, move):
        return move.l10n_tr_nilvera_send_status == 'not_sent' and move.is_invoice(include_receipts=True) and move.country_code == 'TR'

    def _l10n_tr_nilvera_check_invoices(self):
        moves_to_check = self.move_ids.filtered(self._get_default_l10n_tr_nilvera_einvoice_enable_einvoice)

        warnings = {}

        if invalid_records := moves_to_check.partner_id.filtered(
            lambda p: p.country_code != "TR"
            or not p.city
            or not p.state_id
            or not p.street
        ):
            warnings["partner_data_missing"] = {
                "message": _(
                    "The following partner(s) are either not Turkish or are missing one of the following fields: city, state, or street."
                ),
                "action_text": _("View Partner(s)"),
                "action": invalid_records._get_records_action(
                    name=_("Check data on Partner(s)")
                ),
            }

        if critical_invalid_records := moves_to_check.partner_id.filtered(
            lambda p: p.l10n_tr_nilvera_customer_status == "einvoice" and not p.ref
        ):
            warnings["critical_partner_data_missing"] = {
                "message": _(
                    "The following E-Invoice partner(s) must have the reference field set to the tax office name."
                ),
                "action_text": _("View Partner(s)"),
                "action": critical_invalid_records._get_records_action(
                    name=_("Check reference on Partner(s)")
                ),
                "critical": True,
            }

        if invalid_subscription_dates := moves_to_check.filtered(
            lambda move: move._l10n_tr_nilvera_einvoice_check_invalid_subscription_dates()
        ):
            warnings["critical_invalid_subscription_dates"] = {
                "message": _("The following invoice(s) need to have the same Start Date and End Date on all their respective Invoice Lines."),
                "action_text": _("View Invoice(s)"),
                "action": invalid_subscription_dates._get_records_action(
                    name=_("Check data on Invoice(s)"),
                ),
                "critical": True,
            }

        if invalid_negative_lines := moves_to_check.filtered(
            lambda move: move._l10n_tr_nilvera_einvoice_check_negative_lines(),
        ):
            warnings["critical_invalid_negative_lines"] = {
                "message": _("Nilvera portal cannot process negative quantity nor negative price on invoice lines"),
                "action_text": _("View Invoice(s)"),
                "action": invalid_negative_lines._get_records_action(name=_("Check data on Invoice(s)")),
                "critical": True,
                "danger": True,
            }

        return warnings

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('l10n_tr_nilvera_einvoice_checkbox_xml')
    def _compute_checkbox_ubl_cii_xml(self):
        # EXTENDS 'account_edi_ubl_cii'
        super()._compute_checkbox_ubl_cii_xml()
        for wizard in self:
            if wizard.l10n_tr_nilvera_einvoice_checkbox_xml and wizard.enable_ubl_cii_xml and not wizard.checkbox_ubl_cii_xml:
                wizard.checkbox_ubl_cii_xml = True

    @api.depends('move_ids')
    def _compute_l10n_tr_nilvera_einvoice_enable_xml(self):
        for wizard in self:
            wizard.l10n_tr_nilvera_einvoice_enable_xml = any(self._get_default_l10n_tr_nilvera_einvoice_enable_einvoice(move) for move in wizard.move_ids)

    @api.depends('l10n_tr_nilvera_einvoice_enable_xml')
    def _compute_l10n_tr_nilvera_einvoice_checkbox_xml(self):
        for wizard in self:
            wizard.l10n_tr_nilvera_einvoice_checkbox_xml = wizard.l10n_tr_nilvera_einvoice_enable_xml

    @api.depends('l10n_tr_nilvera_einvoice_checkbox_xml')
    def _compute_mail_attachments_widget(self):
        # EXTENDS 'account' - add depends
        super()._compute_mail_attachments_widget()

    @api.depends('l10n_tr_nilvera_einvoice_checkbox_xml')
    def _compute_l10n_tr_nilvera_warnings(self):
        for wizard in self:
            if wizard.l10n_tr_nilvera_einvoice_checkbox_xml:
                wizard.l10n_tr_nilvera_warnings = wizard._l10n_tr_nilvera_check_invoices()
            else:
                wizard.l10n_tr_nilvera_warnings = False

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------
    def _link_invoice_documents(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoice, invoice_data)
        # The move needs to be put as sent only if sent by Nilvera
        if invoice.company_id.country_code == 'TR':
            invoice.is_move_sent = invoice.l10n_tr_nilvera_send_status == 'sent'

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            if invoice_data.get('l10n_tr_nilvera_einvoice_xml'):
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
