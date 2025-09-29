import base64
import uuid
from werkzeug.urls import url_encode

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_jo_edi_pos_enabled = fields.Boolean(related='company_id.l10n_jo_edi_pos_enabled')
    l10n_jo_edi_pos_uuid = fields.Char(string="Order UUID", copy=False, compute="_compute_l10n_jo_edi_pos_uuid", store=True)
    l10n_jo_edi_pos_qr = fields.Char(string="QR", copy=False)

    l10n_jo_edi_pos_state = fields.Selection(
        selection=[('to_send', 'To Send'), ('sent', 'Sent'), ('demo', 'Sent (Demo)')],
        string="JoFotara State",
        tracking=True,
        copy=False,
    )
    l10n_jo_edi_pos_error = fields.Text(
        string="JoFotara Error",
        copy=False,
        readonly=True,
    )

    l10n_jo_edi_pos_computed_xml = fields.Binary(
        string="Jordan E-Invoice computed XML File",
        compute="_compute_l10n_jo_edi_pos_computed_xml",
        help="Jordan: technical field computing e-invoice XML data, useful at submission failure scenarios.",
    )
    l10n_jo_edi_pos_xml_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="Jordan E-Invoice XML",
        help="Jordan: e-invoice XML.",
    )

    @api.depends('country_code')
    def _compute_l10n_jo_edi_pos_uuid(self):
        for order in self:
            if order.country_code == 'JO' and not order.l10n_jo_edi_pos_uuid:
                order.l10n_jo_edi_pos_uuid = uuid.uuid4()

    def _submit_to_jofotara(self):
        self.ensure_one()
        headers = self.company_id._l10n_jo_build_jofotara_headers()
        xml_order = self.env['pos.edi.xml.ubl_21.jo']._export_pos_order(self)[0]
        params = {'invoice': base64.b64encode(xml_order).decode()}
        dict_response = self.company_id._send_l10n_jo_edi_request(params, headers)
        if 'error' in dict_response and len(dict_response) == 1:
            return dict_response['error']
        self.l10n_jo_edi_pos_qr = str(dict_response.get('EINV_QR', ''))
        self.env['ir.attachment'].create(
            {
                'res_model': 'pos.order',
                'res_id': self.id,
                'name': self._l10n_jo_edi_pos_get_xml_attachment_name(),
                'raw': xml_order,
            }
        )

    def _l10n_jo_edi_pos_get_xml_attachment_name(self):
        return f"{self.name}_edi.xml"

    def _l10n_jo_validate_fields(self):
        return

    def _l10n_jo_edi_send(self):
        for order in self:
            if error_messages := order.company_id._l10n_jo_validate_config() or order._l10n_jo_validate_fields() or order._submit_to_jofotara():
                order.l10n_jo_edi_pos_state = False
                order.l10n_jo_edi_pos_error = error_messages
                return error_messages
            else:
                order.l10n_jo_edi_pos_state = 'demo' if self.env.company.l10n_jo_edi_demo_mode else 'sent'
                order.l10n_jo_edi_pos_error = False
                self._link_xml_and_qr_to_invoice(self.account_move)
                self.message_post(
                    body=self.env._("E-invoice (JoFotara) submitted successfully."),
                    attachment_ids=self.l10n_jo_edi_pos_xml_attachment_id.ids,
                )

    @api.model
    def sync_from_ui(self, orders):
        # EXTENDS 'point_of_sale'
        """Entrypoint for EDI through the POS. Launch EDI for all paid orders when they are received in the backend. Amend
        the response sent back to the POS after EDI to include fields needed for the receipt."""
        result = super().sync_from_ui(orders)

        # all orders in a single sync_from_ui call will belong to the same session
        if (
            len(orders) > 0
            and orders[0].get("session_id")
            and (orders_company := self.env["pos.session"].browse(orders[0]["session_id"]).company_id)
            and orders_company.country_code == 'JO'
            and orders_company.l10n_jo_edi_pos_enabled
        ):
            paid_orders = [order["id"] for order in result["pos.order"] if order["state"] == "paid"]
            self.env["pos.order"].browse(paid_orders)._l10n_jo_edi_send()

            for order in result["pos.order"]:
                extra_fields_needed_in_pos = [
                    "l10n_jo_edi_pos_state",
                    "l10n_jo_edi_pos_error",
                    "l10n_jo_edi_pos_qr",
                ]
                order_db = self.env["pos.order"].browse(order["id"])
                order.update(order_db.read(extra_fields_needed_in_pos)[0])

        return result

    def button_l10n_jo_edi_pos(self):
        if error_message := self._l10n_jo_edi_send():
            raise ValidationError(error_message)

    @api.depends('country_code', 'l10n_jo_edi_pos_error')
    def _compute_l10n_jo_edi_pos_computed_xml(self):
        for order in self:
            if order.country_code == 'JO' and order.l10n_jo_edi_pos_error:
                xml_content = self.env['pos.edi.xml.ubl_21.jo']._export_pos_order(self)[0]
                order.l10n_jo_edi_pos_computed_xml = base64.b64encode(xml_content)
            else:
                order.l10n_jo_edi_pos_computed_xml = False

    def download_l10n_jo_edi_pos_computed_xml(self):
        if error_message := self.company_id._l10n_jo_validate_config() or self._l10n_jo_validate_fields():
            raise ValidationError(self.env._("The following errors have to be fixed in order to create an XML:\n") + error_message)
        params = url_encode({
            'model': self._name,
            'id': self.id,
            'field': 'l10n_jo_edi_pos_computed_xml',
            'filename': self._l10n_jo_edi_pos_get_xml_attachment_name(),
            'mimetype': 'application/xml',
            'download': 'true',
        })
        return {'type': 'ir.actions.act_url', 'url': '/web/content/?' + params, 'target': 'new'}

    def _prepare_invoice_vals(self):
        # EXTENDS 'point_of_sale'
        vals = super()._prepare_invoice_vals()
        return {
            **vals,
            'l10n_jo_edi_uuid': self.l10n_jo_edi_pos_uuid,
            'l10n_jo_edi_state': self.l10n_jo_edi_pos_state,
            'l10n_jo_edi_error': self.l10n_jo_edi_pos_error,
            'l10n_jo_edi_invoice_type': 'local',  # pos order invoices are always of type local
            'preferred_payment_method_line_id': self.env['account.payment.method.line'].search([], limit=1).id,
        }

    def _create_invoice(self, move_vals):
        # EXTENDS 'point_of_sale'
        invoice = super()._create_invoice(move_vals)
        self._link_xml_and_qr_to_invoice(invoice)
        return invoice

    def _link_xml_and_qr_to_invoice(self, invoice):
        if invoice and self.l10n_jo_edi_pos_xml_attachment_id:
            self.env["ir.attachment"].create(
                {
                    "res_model": "account.move",
                    "res_id": invoice.id,
                    "res_field": "l10n_jo_edi_xml_attachment_file",
                    "name": f'{self.name}_edi.xml',
                    "datas": self.l10n_jo_edi_pos_xml_attachment_id.datas,
                }
            )
        if invoice and self.l10n_jo_edi_pos_qr:
            invoice.l10n_jo_edi_qr = self.l10n_jo_edi_pos_qr
