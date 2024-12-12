import uuid
import requests
import json

from odoo import _, api, fields, models
from requests.exceptions import Timeout, ConnectionError, HTTPError

DEMO_EFAKTURA_URL = 'https://demoefaktura.mfin.gov.rs/api/publicApi/sales-invoice/ubl'
EFAKTURA_URL = 'https://efakturadev.mfin.gov.rs/api/publicApi/sales-invoice/ubl'


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_rs_edi_uuid = fields.Char("Invoice UUID", copy=False, help="Unique Identifier for an invoice used as request id")

    l10n_rs_edi_is_eligible = fields.Boolean(
        compute="_compute_l10n_rs_edi_is_eligible",
        help="Serbia: technical field to determine if this invoice is eligible to be e-invoiced.",
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
            ('to_send', 'Sending'),
            ('sent', 'sent'),
            ('sending_failed', 'Error')
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
        default='3',
    )
    l10n_rs_edi_invoice_id = fields.Char("Invoice Id", copy=False)
    l10n_rs_edi_sales_invoice_id = fields.Char("Sales Invoice Id", copy=False)
    l10n_rs_edi_purchase_invoice_id = fields.Char("Purchase Invoice Id", copy=False)

    @api.depends('country_code', 'move_type')
    def _compute_show_delivery_date(self):
        # EXTENDS 'account'
        super()._compute_show_delivery_date()
        for move in self:
            if move.country_code == 'RS':
                move.show_delivery_date = move.is_sale_document()

    @api.depends("country_code", "move_type")
    def _compute_l10n_rs_edi_is_eligible(self):
        for move in self:
            move.l10n_rs_edi_is_eligible = move.country_code == 'RS' and move.is_sale_document()

    def _post(self, soft=True):
        posted = super()._post(soft)
        posted.l10n_rs_edi_state = 'to_send'
        return posted

    @api.depends('l10n_rs_edi_state')
    def _compute_show_reset_to_draft_button(self):
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            move.show_reset_to_draft_button = move.l10n_rs_edi_state != 'sent' and move.show_reset_to_draft_button

    def button_draft(self):
        # EXTENDS 'account'
        self.write(
            {
                "l10n_rs_edi_error": False,
                "l10n_rs_edi_attachment_file": False,
                "l10n_rs_edi_attachment_id": False,
            }
        )
        return super().button_draft()

    def _l10n_rs_edi_send(self, xml, sendToCir):
        self.ensure_one()
        params = {
            'requestId': self.l10n_rs_edi_uuid,
            'sendToCir': 'Yes' if sendToCir else 'No'
        }
        url = DEMO_EFAKTURA_URL if self.company_id.l10n_rs_edi_demo_env else EFAKTURA_URL
        headers = {
            'Content-Type': 'application/xml',
            'ApiKey': self.company_id.l10n_rs_edi_api_key,
        }
        try:
            response = requests.post(url=url, params=params, headers=headers, data=xml, timeout=30)
        except (Timeout, ConnectionError, HTTPError) as exception:
            self.l10n_rs_edi_state = 'sending_failed'
            error_message = _("There was a problem with the connection with eFaktura: %s", repr(exception))
            self.l10n_rs_edi_error = error_message
            self.message_post(body=error_message)
            return [self.l10n_rs_edi_error]
        if not response.ok:
            self.l10n_rs_edi_state = 'sending_failed'
            message = _("Sending Failed with Code: %s \n%s", response.status_code, json.loads(response.content.decode('utf-8')))
            self.l10n_rs_edi_error = message
            return [self.l10n_rs_edi_error]
        dict_response = json.loads(response.content.decode('utf-8'))
        self.l10n_rs_edi_state = 'sent'
        self.l10n_rs_edi_error = False
        self.l10n_rs_edi_invoice_id = dict_response.get('InvoiceId')
        self.l10n_rs_edi_purchase_invoice_id = dict_response.get('PurchaseInvoiceId')
        self.l10n_rs_edi_sales_invoice_id = dict_response.get('SalesInvoiceId')
        return []

    def _l10n_rs_edi_get_attachment_values(self, xml):
        return {
            'name': self._l10n_rs_edi_get_xml_attachment_name(),
            'mimetype': 'application/xml',
            'description': _('RS EDI e-move: %s', self.move_type),
            'company_id': self.company_id.id,
            'res_id': self.id,
            'res_model': self._name,
            'res_field': 'l10n_rs_edi_attachment_file',
            'raw': xml,
            'type': 'binary',
        }

    def _l10n_rs_edi_get_xml_attachment_name(self):
        return f"{self.name.replace('/', '_')}_edi.xml"

    @api.model_create_multi
    def create(self, vals):
        records = super().create(vals)
        for record in records:
            if record.l10n_rs_edi_is_eligible:
                record.l10n_rs_edi_uuid = uuid.uuid4()
        return records
