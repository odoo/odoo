import base64
import json
import requests
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

JOFOTARA_URL = "https://backend.jofotara.gov.jo/core/invoices/"


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_jo_edi_uuid = fields.Char("Invoice UUID", copy=False)
    l10n_jo_edi_qr = fields.Char("QR", copy=False)

    l10n_jo_edi_is_needed = fields.Boolean(
        compute="_compute_l10n_jo_edi_is_needed",
        help="Jordan: technical field to determine if this invoice is eligible to be e-invoiced.",
    )
    l10n_jo_edi_state = fields.Selection(
        selection=[('to_send', 'To Send'), ('sent', 'Sent'), ('to_cancel', 'To Cancel'), ('cancelled', 'Cancelled')],
        string="JoFotara State",
        store=True,
        copy=False,
        compute='_compute_jo_edi_state')
    l10n_jo_edi_error = fields.Text(
        "JoFotara Error",
        copy=False,
        readonly=True,
        help="Jordan: Error details.",
    )
    l10n_jo_edi_xml_attachment_file = fields.Binary(
        string="Jordan E-Invoice XML File",
        copy=False,
        attachment=True,
        help="Jordan: technical field holding the e-invoice XML data.",
    )
    l10n_jo_edi_xml_attachment_id = fields.Many2one(
        "ir.attachment",
        string="Jordan E-Invoice XML",
        compute=lambda self: self._compute_linked_attachment_id(
            "l10n_jo_edi_xml_attachment_id", "l10n_jo_edi_xml_attachment_file"
        ),
        depends=["l10n_jo_edi_xml_attachment_file"],
        help="Jordan: e-invoice XML.",
    )

    @api.depends("country_code", "move_type")
    def _compute_l10n_jo_edi_is_needed(self):
        for move in self:
            move.l10n_jo_edi_is_needed = (
                move.country_code == "JO"
                and move.move_type in ("out_invoice", "out_refund")
            )

    @api.depends("l10n_jo_edi_is_needed", "state", "l10n_jo_edi_xml_attachment_id", "l10n_jo_edi_error", "reversal_move_ids", "payment_state")
    def _compute_jo_edi_state(self):
        jo_moves = self.filtered(lambda move: move.l10n_jo_edi_is_needed)
        for move in jo_moves:
            if move.state == 'posted':
                move.l10n_jo_edi_state = 'to_send'
            if move.l10n_jo_edi_xml_attachment_id and not move.l10n_jo_edi_error:
                move.l10n_jo_edi_state = 'sent'
            if move.reversal_move_ids and move.payment_state != 'partial':
                move.l10n_jo_edi_state = 'to_cancel'
            if move.state == 'cancel' or move.payment_state == 'reversed':
                move.l10n_jo_edi_state = 'cancelled'
            if move.state == 'draft':
                move.l10n_jo_edi_state = None

    @api.depends("l10n_jo_edi_xml_attachment_id", "l10n_jo_edi_error")
    def _compute_show_reset_to_draft_button(self):
        super()._compute_show_reset_to_draft_button()
        self.filtered(lambda move: move.l10n_jo_edi_xml_attachment_id and not move.l10n_jo_edi_error).show_reset_to_draft_button = False

    def button_draft(self):
        # EXTENDS 'account'
        self.write(
            {
                "l10n_jo_edi_error": False,
                "l10n_jo_edi_xml_attachment_file": False,
                "l10n_jo_edi_xml_attachment_id": False,
            }
        )
        return super().button_draft()

    def _build_jofotara_headers(self):
        if not self.company_id.l10n_jo_edi_client_id:
            raise ValidationError("Client ID is missing.\n To set it: Configuration > Settings > Electronic Invoicing (Jordan)")
        if not self.company_id.l10n_jo_edi_secret_key:
            raise ValidationError("Secret key is missing.\n To set it: Configuration > Settings > Electronic Invoicing (Jordan)")
        return {
            'Client-Id': self.company_id.l10n_jo_edi_client_id,
            'Secret-Key': self.company_id.l10n_jo_edi_secret_key,
            'Content-Type': 'application/json',
        }

    def submit_to_jofotara(self):
        self.ensure_one()
        headers = self._build_jofotara_headers()
        params = '{"invoice": "%s"}' % self.l10n_jo_edi_xml_attachment_id.datas.decode('ascii')

        try:
            response = requests.post(JOFOTARA_URL, data=str(params), headers=headers, timeout=50, verify=False)
        except (requests.exceptions.Timeout, requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
            raise UserError("Invalid request: %s" % e)

        response_text = response.content.decode('utf-8')
        if not response.ok:
            raise UserError("Request failed: %s" % response_text)
        dict_response = json.loads(response_text)
        self.l10n_jo_edi_qr = str(dict_response.get('EINV_QR', ''))

    def _l10n_jo_edi_get_xml_attachment_name(self):
        return f"{self.name.replace('/', '_')}_edi.xml"

    def _l10n_jo_edi_send(self):
        for invoice in self:
            invoice.l10n_jo_edi_xml_attachment_id.res_field = False
            invoice_xml = self.env["ir.attachment"].create(
                {
                    "res_model": "account.move",
                    "res_id": invoice.id,
                    "res_field": "l10n_jo_edi_xml_attachment_file",
                    "name": invoice._l10n_jo_edi_get_xml_attachment_name(),
                    "datas": base64.b64encode(invoice.env['account.edi.xml.ubl_21.jo']._export_invoice(invoice)),
                }
            )
            invoice.invalidate_recordset(
                fnames=[
                    "l10n_jo_edi_xml_attachment_id",
                    "l10n_jo_edi_xml_attachment_file",
                ]
            )

            try:
                invoice.submit_to_jofotara()
                invoice.l10n_jo_edi_error = False
                invoice.with_context(no_new_invoice=True).message_post(
                    body=_("E-invoice (JoFotara) submitted successfully."),
                    attachment_ids=invoice_xml.ids,
                )
            except (ValidationError, UserError) as error:
                invoice.l10n_jo_edi_error = error
                invoice.with_context(no_new_invoice=True).message_post(
                    body=_("E-invoice (JoFotara) submission failed. %s", error),
                    attachment_ids=invoice_xml.ids,
                )
                return error

    @api.model
    def create(self, vals):
        records = super().create(vals)
        for record in records:
            if record.l10n_jo_edi_is_needed:
                record.l10n_jo_edi_uuid = uuid.uuid4()
        return records
