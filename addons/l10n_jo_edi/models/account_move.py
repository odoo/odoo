import base64
import requests
import uuid
from werkzeug.urls import url_encode

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

JOFOTARA_URL = "https://backend.jofotara.gov.jo/core/invoices/"


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_jo_edi_uuid = fields.Char(string="Invoice UUID", copy=False, compute="_compute_l10n_jo_edi_uuid", store=True)
    l10n_jo_edi_qr = fields.Char(string="QR", copy=False)

    l10n_jo_edi_is_needed = fields.Boolean(
        compute="_compute_l10n_jo_edi_is_needed",
        help="Jordan: technical field to determine if this invoice is eligible to be e-invoiced.",
    )
    l10n_jo_edi_state = fields.Selection(
        selection=[('to_send', 'To Send'), ('sent', 'Sent')],
        string="JoFotara State",
        tracking=True,
        copy=False)
    l10n_jo_edi_error = fields.Text(
        string="JoFotara Error",
        copy=False,
        readonly=True,
        help="Jordan: Error details.",
    )
    l10n_jo_edi_computed_xml = fields.Binary(
        string="Jordan E-Invoice computed XML File",
        compute="_compute_l10n_jo_edi_computed_xml",
        help="Jordan: technical field computing e-invoice XML data, useful at submission failure scenarios.",
    )
    l10n_jo_edi_xml_attachment_file = fields.Binary(
        string="Jordan E-Invoice XML File",
        copy=False,
        attachment=True,
        help="Jordan: technical field holding the e-invoice XML data.",
    )
    l10n_jo_edi_xml_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Jordan E-Invoice XML",
        compute=lambda self: self._compute_linked_attachment_id(
            "l10n_jo_edi_xml_attachment_id", "l10n_jo_edi_xml_attachment_file"
        ),
        depends=["l10n_jo_edi_xml_attachment_file"],
        help="Jordan: e-invoice XML.",
    )
    reversed_entry_id = fields.Many2one(tracking=True)

    @api.depends("country_code", "move_type")
    def _compute_l10n_jo_edi_is_needed(self):
        for move in self:
            move.l10n_jo_edi_is_needed = (
                move.country_code == "JO"
                and move.move_type in ("out_invoice", "out_refund")
            )

    @api.depends("l10n_jo_edi_state")
    def _compute_show_reset_to_draft_button(self):
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        self.filtered(lambda move: move.l10n_jo_edi_state == 'sent').show_reset_to_draft_button = False

    @api.depends("l10n_jo_edi_is_needed")
    def _compute_l10n_jo_edi_uuid(self):
        for invoice in self:
            if invoice.l10n_jo_edi_is_needed and not invoice.l10n_jo_edi_uuid:
                invoice.l10n_jo_edi_uuid = uuid.uuid4()

    @api.depends("state", "l10n_jo_edi_is_needed")
    def _compute_l10n_jo_edi_computed_xml(self):
        for invoice in self:
            if invoice.state == 'posted' and invoice.l10n_jo_edi_is_needed:
                xml_content = self.env['account.edi.xml.ubl_21.jo']._export_invoice(invoice)[0]
                invoice.l10n_jo_edi_computed_xml = base64.b64encode(xml_content)
            else:
                invoice.l10n_jo_edi_computed_xml = False

    def download_l10n_jo_edi_computed_xml(self):
        if error_message := self._l10n_jo_validate_config() or self._l10n_jo_validate_fields():
            raise ValidationError(_("The following errors have to be fixed in order to create an XML:\n") + error_message)
        params = url_encode({
            'model': self._name,
            'id': self.id,
            'field': 'l10n_jo_edi_computed_xml',
            'filename': self._l10n_jo_edi_get_xml_attachment_name(),
            'mimetype': 'application/xml',
            'download': 'true',
        })
        return {'type': 'ir.actions.act_url', 'url': '/web/content/?' + params, 'target': 'new'}

    def _l10n_jo_qr_code_src(self):
        self.ensure_one()
        encoded_params = url_encode({
            'barcode_type': 'QR',
            'value': self.l10n_jo_edi_qr,
            'width': 200,
            'height': 200,
        })
        return f'/report/barcode/?{encoded_params}'

    def _is_sales_refund(self):
        self.ensure_one()
        return self.company_id.l10n_jo_edi_taxpayer_type == 'sales' and self.move_type == 'out_refund'

    def _get_invoice_scope_code(self):
        "Invoices in this module are always local invoices"
        return '0'

    def _get_invoice_payment_method_code(self):
        "Invoices in this module are always receivable invoices"
        return '2'

    def _get_invoice_tax_payer_type_code(self):
        return {
            'income': '1',
            'sales': '2',
            'special': '3',
        }.get(self.company_id.l10n_jo_edi_taxpayer_type, '1')

    def button_draft(self):
        # EXTENDS 'account'
        self.write(
            {
                "l10n_jo_edi_error": False,
                "l10n_jo_edi_state": False,
                "l10n_jo_edi_qr": False,
            }
        )
        return super().button_draft()

    def _get_fields_to_detach(self):
        # EXTENDS account
        fields_list = super()._get_fields_to_detach()
        fields_list.append('l10n_jo_edi_xml_attachment_file')
        return fields_list

    def _post(self, soft=True):
        # EXTENDS 'account'
        for invoice in self.filtered('l10n_jo_edi_is_needed'):
            invoice.l10n_jo_edi_state = 'to_send'
        return super()._post(soft)

    def _get_name_invoice_report(self):
        # EXTENDS account
        self.ensure_one()
        if self.l10n_jo_edi_state in self._l10n_jo_edi_state_sent_options() and self.l10n_jo_edi_xml_attachment_id:
            return 'l10n_jo_edi.report_invoice_document'
        return super()._get_name_invoice_report()

    def _l10n_jo_build_jofotara_headers(self):
        self.ensure_one()
        return {
            'Client-Id': self.sudo().company_id.l10n_jo_edi_client_identifier,
            'Secret-Key': self.sudo().company_id.l10n_jo_edi_secret_key,
        }

    def _send_l10n_jo_edi_request(self, params, headers):
        try:
            response = requests.post(JOFOTARA_URL, json=params, headers=headers, timeout=50)
        except requests.exceptions.Timeout:
            return {'error': _("Request timeout! Please try again.")}
        except requests.exceptions.RequestException as e:
            return {'error': _("Invalid request: %s", e)}

        if not response.ok:
            content = response.content.decode()
            if response.status_code == 403:
                content = _("Access forbidden. Please verify your JoFotara credentials.")
            return {'error': _("Request failed: %s", content)}
        dict_response = response.json()
        return dict_response

    def _submit_to_jofotara(self):
        self.ensure_one()
        headers = self._l10n_jo_build_jofotara_headers()
        xml_invoice = self.env['account.edi.xml.ubl_21.jo']._export_invoice(self)[0]
        params = {'invoice': base64.b64encode(xml_invoice).decode()}
        dict_response = self._send_l10n_jo_edi_request(params, headers)
        if 'error' in dict_response and len(dict_response) == 1:
            return dict_response['error']
        self.l10n_jo_edi_qr = str(dict_response.get('EINV_QR', ''))
        self.invoice_pdf_report_id.res_field = False
        self.env["ir.attachment"].create(
            {
                "res_model": "account.move",
                "res_id": self.id,
                "res_field": "l10n_jo_edi_xml_attachment_file",
                "name": self._l10n_jo_edi_get_xml_attachment_name(),
                "raw": xml_invoice,
            }
        )

    def _l10n_jo_edi_get_xml_attachment_name(self):
        return f"{self.name.replace('/', '_')}_edi.xml"

    def _l10n_jo_validate_config(self):
        error_msgs = []
        if not self.sudo().company_id.l10n_jo_edi_client_identifier:
            error_msgs.append(_("Client ID is missing."))
        if not self.sudo().company_id.l10n_jo_edi_secret_key:
            error_msgs.append(_("Secret key is missing."))
        if not self.company_id.l10n_jo_edi_taxpayer_type:
            error_msgs.append(_("Taxpayer type is missing."))
        if not self.company_id.l10n_jo_edi_sequence_income_source:
            error_msgs.append(_("Activity number (Sequence of income source) is missing."))

        if error_msgs:
            return _("%s \nTo set: Configuration > Settings > Electronic Invoicing (Jordan)", "\n".join(error_msgs))

    def _l10n_jo_validate_fields(self):
        def has_non_digit_vat(partner, partner_type, error_msgs):
            if partner.vat and not partner.vat.isdigit():
                error_msgs.append(_("JoFotara portal cannot process %s VAT with non-digit characters in it", partner_type))

        error_msgs = []

        customer = self.partner_id
        has_non_digit_vat(customer, 'customer', error_msgs)

        supplier = self.company_id.partner_id.commercial_partner_id
        has_non_digit_vat(supplier, 'supplier', error_msgs)

        if self.move_type == 'out_refund':
            if not self.reversed_entry_id:
                error_msgs.append(_('Please use "Reversal of" to link this credit note with an Invoice'))
            elif self.currency_id != self.reversed_entry_id.currency_id:
                error_msgs.append(_("Please make sure the currency of the credit note is the same as the related invoice"))

            if not self.ref:
                error_msgs.append(_('Please make sure the "Customer Reference" contains the reason for the return'))

        if any(
            line.display_type not in ('line_note', 'line_section')
            and (line.quantity < 0 or line.price_unit < 0)
            for line in self.invoice_line_ids
        ):
            error_msgs.append(_("JoFotara portal cannot process negative quantity nor negative price on invoice lines"))

        for line in self.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_note', 'line_section')):
            if self.company_id.l10n_jo_edi_taxpayer_type == 'income' and len(line.tax_ids) != 0:
                error_msgs.append(_("No taxes are allowed on invoice lines for taxpayers unregistered in the sales tax"))
            elif self.company_id.l10n_jo_edi_taxpayer_type == 'sales' and len(line.tax_ids) != 1:
                error_msgs.append(_("One general tax per invoice line is expected for taxpayers registered in the sales tax"))
            elif self.company_id.l10n_jo_edi_taxpayer_type == 'special' and len(line.tax_ids) != 2:
                error_msgs.append(_("One special and one general tax per invoice line is expected for taxpayers registered in the special tax"))

        return "\n".join(error_msgs)

    def _l10n_jo_edi_state_sent_options(self):
        return ['sent']

    def _mark_sent_jo_edi(self):
        self.l10n_jo_edi_error = False
        self.l10n_jo_edi_state = 'sent'

    def _l10n_jo_edi_send(self):
        self.ensure_one()
        if not self.env['res.company']._with_locked_records(records=self, allow_raising=False):
            return
        if error_message := self._l10n_jo_validate_config() or self._l10n_jo_validate_fields() or self._submit_to_jofotara():
            self.l10n_jo_edi_error = error_message
            return error_message
        else:
            self._mark_sent_jo_edi()
            self.with_context(no_new_invoice=True).message_post(
                body=_("E-invoice (JoFotara) submitted successfully."),
                attachment_ids=self.l10n_jo_edi_xml_attachment_id.ids,
            )
