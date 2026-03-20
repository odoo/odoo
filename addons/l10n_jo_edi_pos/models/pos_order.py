import base64
import uuid
from urllib.parse import urlencode

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.sql import create_column, column_exists


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_jo_edi_pos_return_reason = fields.Char(string="Return Reason", help="Return Reason reported to JoFotara")
    l10n_jo_edi_pos_enabled = fields.Boolean(related='company_id.l10n_jo_edi_pos_enabled')
    l10n_jo_edi_pos_uuid = fields.Char(string="Order UUID", copy=False, compute='_compute_l10n_jo_edi_pos_uuid', store=True)
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
        compute='_compute_l10n_jo_edi_pos_computed_xml',
        help="Jordan: technical field computing e-invoice XML data, useful at submission failure scenarios.",
    )
    l10n_jo_edi_pos_xml_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="Jordan E-Invoice XML",
        help="Jordan: e-invoice XML.",
    )

    def _auto_init(self):
        if not column_exists(self.env.cr, 'pos_order', 'l10n_jo_edi_pos_uuid'):
            create_column(self.env.cr, 'pos_order', 'l10n_jo_edi_pos_uuid', 'char')
        return super()._auto_init()

    @api.depends('country_code')
    def _compute_l10n_jo_edi_pos_uuid(self):
        for order in self:
            if order.country_code == 'JO' and not order.l10n_jo_edi_pos_uuid:
                order.l10n_jo_edi_pos_uuid = uuid.uuid4()

    def _get_order_scope_code(self):
        return '0'

    def _get_order_payment_method_code(self):
        return '1' if any(self.payment_ids.payment_method_id.mapped('l10n_jo_edi_pos_is_cash')) else '2'

    def _get_order_tax_payer_type_code(self):
        return {
            'income': '1',
            'sales': '2',
            'special': '3',
        }.get(self.company_id.l10n_jo_edi_taxpayer_type, '1')

    def _submit_to_jofotara(self):
        self.ensure_one()
        headers = self.company_id._l10n_jo_build_jofotara_headers()
        xml_order = self.env['pos.edi.xml.ubl_21.jo']._export_pos_order(self)[0]
        params = {'invoice': base64.b64encode(xml_order).decode()}
        dict_response = self.company_id._send_l10n_jo_edi_request(params, headers)
        if 'error' in dict_response and len(dict_response) == 1:
            return dict_response['error']
        self.l10n_jo_edi_pos_qr = str(dict_response.get('EINV_QR', ''))
        self.l10n_jo_edi_pos_xml_attachment_id = self.env['ir.attachment'].create(
            {
                'res_model': 'pos.order',
                'res_id': self.id,
                'name': self._l10n_jo_edi_pos_get_xml_attachment_name(),
                'raw': xml_order,
            }
        )

    def _l10n_jo_edi_pos_get_xml_attachment_name(self):
        return f"{self.name.replace('/', '_')}_edi.xml"

    def _l10n_jo_validate_fields(self):
        error_msgs = []
        if self.refunded_order_id:
            if self.refunded_order_id.l10n_jo_edi_pos_state not in ['sent', 'demo']:
                error_msgs.append(self.env._("Refunded order was not sent to JoFotara. Please submit the original order to JoFotara first and try again."))
            if not self.l10n_jo_edi_pos_return_reason:
                error_msgs.append(self.env._("Refund order must have a return reason"))
        if any(line.price_unit < 0 for line in self.lines) or (not self.refunded_order_id and any(line.qty < 0 for line in self.lines)):
            error_msgs.append(self.env._("Downpayments, global discounts, and negative lines are not supported at the moment. To revert this order, please go to Orders > Select the Order > Refund or create a Return from the backend by going to Orders > Select the Order > Return"))
        if len(self.payment_ids.payment_method_id.mapped('l10n_jo_edi_pos_is_cash')) > 1:
            error_msgs.append(self.env._("Please select the payment methods that are consistent with the value set in 'JoFotara Cash'. If set, the payment method is Cash. If empty, then it is Receivable."))

        for line in self.lines:
            if self.company_id.l10n_jo_edi_taxpayer_type == 'income' and len(line.tax_ids) != 0:
                error_msgs.append(self.env._("No taxes are allowed on order lines for taxpayers unregistered in the sales tax"))
            elif self.company_id.l10n_jo_edi_taxpayer_type == 'sales' and len(line.tax_ids) != 1:
                error_msgs.append(self.env._("One general tax per order line is expected for taxpayers registered in the sales tax"))
            elif self.company_id.l10n_jo_edi_taxpayer_type == 'special' and len(line.tax_ids) != 2:
                error_msgs.append(self.env._("One special and one general tax per order line are expected for taxpayers registered in the special tax"))

        return "\n".join(error_msgs)

    def _l10n_jo_edi_send(self):
        for order in self:
            if error_messages := order.company_id._l10n_jo_validate_config() or order._l10n_jo_validate_fields() or order._submit_to_jofotara():
                order.l10n_jo_edi_pos_state = 'to_send'
                order.l10n_jo_edi_pos_error = error_messages
                # avoid creating an invoice in case of JoFotara sync failure
                order.to_invoice = False
                return error_messages
            else:
                order.l10n_jo_edi_pos_state = 'demo' if order.env.company.l10n_jo_edi_demo_mode else 'sent'
                order.l10n_jo_edi_pos_error = False
                order._link_xml_and_qr_to_invoice(order.account_move)
                order.message_post(
                    body=order.env._("E-invoice (JoFotara) submitted successfully."),
                    attachment_ids=order.l10n_jo_edi_pos_xml_attachment_id.ids,
                )

    def action_pos_order_paid(self):
        # EXTENDS 'point_of_sale'
        """
        Once an order is paid, sync it with JoFotara if possible
        """
        result = super().action_pos_order_paid()
        if self.country_code == 'JO' and self.l10n_jo_edi_pos_enabled:
            self._l10n_jo_edi_send()
        return result

    def button_l10n_jo_edi_pos(self):
        if error_message := self._l10n_jo_edi_send():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': error_message,
                    'next': {
                        'type': 'ir.actions.act_window_close',
                    },
                }
            }

    @api.depends('country_code', 'l10n_jo_edi_pos_error')
    def _compute_l10n_jo_edi_pos_computed_xml(self):
        for order in self:
            if order.country_code == 'JO' and not order.l10n_jo_edi_pos_error:
                xml_content = order.env['pos.edi.xml.ubl_21.jo']._export_pos_order(order)[0]
                order.l10n_jo_edi_pos_computed_xml = base64.b64encode(xml_content)
            else:
                order.l10n_jo_edi_pos_computed_xml = False

    def download_l10n_jo_edi_pos_computed_xml(self):
        if error_message := self.company_id._l10n_jo_validate_config() or self._l10n_jo_validate_fields():
            raise ValidationError(self.env._("The following errors have to be fixed in order to create an XML:\n") + error_message)
        params = urlencode({
            'model': self._name,
            'id': self.id,
            'field': 'l10n_jo_edi_pos_computed_xml',
            'filename': self._l10n_jo_edi_pos_get_xml_attachment_name(),
            'mimetype': 'application/xml',
            'download': 'true',
        })
        return {'type': 'ir.actions.act_url', 'url': '/web/content/?' + params, 'target': 'new'}

    def _is_single_jo_order(self):
        return len(self) == 1 and self.country_code == 'JO'

    def _prepare_invoice_vals(self):
        # EXTENDS 'point_of_sale'
        vals = super()._prepare_invoice_vals()
        if not self._is_single_jo_order():
            return vals
        return {
            **vals,
            'ref': self.l10n_jo_edi_pos_return_reason,
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
        if not self._is_single_jo_order():
            return
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
