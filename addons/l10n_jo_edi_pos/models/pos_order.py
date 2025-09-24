import uuid

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
        error_messages = None
        order_xml = False
        order_qr = False
        try:
            with self.env.cr.savepoint():
                invoice = self._create_invoice(self._prepare_invoice_vals())
                error_messages = invoice._l10n_jo_validate_config() or invoice._l10n_jo_validate_fields() or invoice._submit_to_jofotara()
                order_xml = self.env['account.edi.xml.ubl_21.jo']._export_invoice(invoice)[0]
                order_qr = invoice.l10n_jo_edi_qr
                raise Exception('Rollback invoice creation')
        except:  # noqa: E722
            if error_messages:
                return error_messages
            self.l10n_jo_edi_pos_qr = order_qr
            self.l10n_jo_edi_pos_xml_attachment_id = self.env['ir.attachment'].create(
                {
                    'res_model': 'pos.order',
                    'res_id': self.id,
                    'name': f'{self.name}_edi.xml',
                    'raw': order_xml,
                }
            )
            self.message_post(
                body=self.env._("E-invoice (JoFotara) submitted successfully."),
                attachment_ids=self.l10n_jo_edi_pos_xml_attachment_id.ids,
            )
            self._link_xml_and_qr_to_invoice(self.account_move)

    def _l10n_jo_do_edi(self):
        for order in self:
            if error_messages := order._submit_to_jofotara():
                order.l10n_jo_edi_pos_state = False
                order.l10n_jo_edi_pos_error = error_messages
            else:
                order.l10n_jo_edi_pos_state = 'demo' if self.env.company.l10n_jo_edi_demo_mode else 'sent'
                order.l10n_jo_edi_pos_error = False

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
            self.env["pos.order"].browse(paid_orders)._l10n_jo_do_edi()

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
        self._l10n_jo_do_edi()
        if self.l10n_jo_edi_pos_error:
            raise ValidationError(self.l10n_jo_edi_pos_error)

    def download_l10n_jo_edi_pos_computed_xml(self):
        try:
            with self.env.cr.savepoint():
                invoice = self._create_invoice(self._prepare_invoice_vals())
                download_xml_action = invoice.download_l10n_jo_edi_computed_xml()
                raise Exception('Rollback invoice creation')
        except:  # noqa: E722
            return download_xml_action

    def _prepare_invoice_vals(self):
        # EXTENDS 'point_of_sale'
        vals = super()._prepare_invoice_vals()
        return {
            **vals,
            'name': self.name,
            'l10n_jo_edi_uuid': self.l10n_jo_edi_pos_uuid,
            'l10n_jo_edi_qr': self.l10n_jo_edi_pos_qr,
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
