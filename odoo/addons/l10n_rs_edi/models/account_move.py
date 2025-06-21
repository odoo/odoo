import uuid
import requests

from odoo import _, api, fields, models
from requests.exceptions import Timeout, ConnectionError, HTTPError

DEMO_EFAKTURA_URL = 'https://demoefaktura.mfin.gov.rs/api/publicApi/sales-invoice/ubl'
EFAKTURA_URL = 'https://efakturadev.mfin.gov.rs/api/publicApi/sales-invoice/ubl'


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_rs_edi_uuid = fields.Char(
        string="RS Invoice UUID",
        compute="_compute_l10n_rs_edi_uuid",
        copy=False,
        store=True,
        help="Unique Identifier for an invoice used as request id",
    )

    l10n_rs_edi_is_eligible = fields.Boolean(
        compute="_compute_l10n_rs_edi_is_eligible",
        store=True,
        help="Technical field to determine if this invoice is eligible to be e-invoiced.",
    )

    l10n_rs_edi_attachment_file = fields.Binary(
        string="Serbian E-Invoice XML File",
        copy=False,
        attachment=True,
        help="Serbia: technical field holding the e-invoice XML data.",
    )

    l10n_rs_edi_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="eFaktura XML Attachment",
        compute=lambda self: self._compute_linked_attachment_id('l10n_rs_edi_attachment_id', 'l10n_rs_edi_attachment_file'),
        depends=['l10n_rs_edi_attachment_file'],
    )

    l10n_rs_edi_state = fields.Selection(
        string="Serbia E-Invoice state",
        selection=[
            ('sent', 'Sent'),
            ('sending_failed', 'Error'),
        ],
        tracking=True,
        readonly=True,
        copy=False,
    )

    l10n_rs_edi_error = fields.Text(
        string="Serbia E-Invoice error",
        copy=False,
        readonly=True,
    )

    l10n_rs_tax_date_obligations_code = fields.Selection(
        string="Tax Date Obligations",
        selection=[
            ('35', 'By Delivery Date'),
            ('3', 'By Issuance Date'),
            ('432', 'By Billing System'),
        ],
        store=True,
        readonly=False,
        compute='_compute_l10n_rs_tax_date_obligations_code',
    )
    l10n_rs_edi_invoice = fields.Char(string="Invoice Id", copy=False)
    l10n_rs_edi_sales_invoice = fields.Char(string="Sales Invoice Id", copy=False)
    l10n_rs_edi_purchase_invoice = fields.Char(string="Purchase Invoice Id", copy=False)

    @api.depends('country_code', 'move_type')
    def _compute_show_delivery_date(self):
        # EXTENDS 'account'
        super()._compute_show_delivery_date()
        for move in self:
            if move.l10n_rs_edi_is_eligible:
                move.show_delivery_date = True

    @api.depends("country_code", "move_type")
    def _compute_l10n_rs_edi_is_eligible(self):
        for move in self:
            move.l10n_rs_edi_is_eligible = move.country_code == 'RS' and move.is_sale_document() and move.l10n_rs_edi_state in (False, 'sending_failed')

    @api.depends('country_code')
    def _compute_l10n_rs_tax_date_obligations_code(self):
        for move in self:
            if move.country_code == 'RS':
                move.l10n_rs_tax_date_obligations_code = '3'

    @api.depends('l10n_rs_edi_state')
    def _compute_show_reset_to_draft_button(self):
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.show_reset_to_draft_button and move.l10n_rs_edi_state == 'sent':
                move.show_reset_to_draft_button = False

    @api.depends('l10n_rs_edi_is_eligible')
    def _compute_l10n_rs_edi_uuid(self):
        for move in self:
            if move.l10n_rs_edi_is_eligible and not move.l10n_rs_edi_uuid:
                move.l10n_rs_edi_uuid = uuid.uuid4()

    def button_draft(self):
        # EXTENDS 'account'
        self.write({
            "l10n_rs_edi_error": False,
            "l10n_rs_edi_state": False,
        })
        return super().button_draft()

    def _l10n_rs_edi_send(self, sendToCir):
        self.ensure_one()
        self.env['res.company']._with_locked_records(self)
        xml, errors = self.env['account.edi.xml.ubl.rs']._export_invoice(self)
        if errors:
            return xml, errors
        params = {
            'requestId': self.l10n_rs_edi_uuid,
            'sendToCir': 'Yes' if sendToCir else 'No'
        }
        url = DEMO_EFAKTURA_URL if self.company_id.l10n_rs_edi_demo_env else EFAKTURA_URL
        headers = {
            'Content-Type': 'application/xml',
            'ApiKey': self.company_id.l10n_rs_edi_api_key,
        }
        error_message = False
        try:
            response = requests.post(url=url, params=params, headers=headers, data=xml, timeout=30)
            response.raise_for_status()
        except (Timeout, ConnectionError, HTTPError) as exception:
            error_message = _("There was a problem with the connection with eFaktura: %s", exception)
            self.message_post(body=error_message)
            return xml, error_message
        dict_response = {}
        try:
            dict_response = response.json()
        except requests.exceptions.JSONDecodeError as e:
            error_message = _("Invalid response from eFaktura: %s", str(e))
        self.l10n_rs_edi_state = 'sending_failed' if error_message else 'sent'
        self.l10n_rs_edi_error = error_message
        self.l10n_rs_edi_invoice = dict_response.get('InvoiceId')
        self.l10n_rs_edi_purchase_invoice = dict_response.get('PurchaseInvoiceId')
        self.l10n_rs_edi_sales_invoice = dict_response.get('SalesInvoiceId')
        return xml, error_message

    def _l10n_rs_edi_get_attachment_values(self, xml):
        self.ensure_one()
        return {
            'name': self._l10n_rs_edi_get_xml_attachment_name(),
            'mimetype': 'application/xml',
            'description': _('RS E-Invoice: %s', self.move_type),
            'company_id': self.company_id.id,
            'res_id': self.id,
            'res_model': self._name,
            'res_field': 'l10n_rs_edi_attachment_file',
            'raw': xml,
            'type': 'binary',
        }

    def _l10n_rs_edi_get_xml_attachment_name(self):
        return f"{self.name.replace('/', '_')}_edi.xml"
