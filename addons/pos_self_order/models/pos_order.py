# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    combo_id = fields.Many2one('product.combo', string='Combo reference')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if (vals.get('combo_parent_uuid')):
                vals.update([
                    ('combo_parent_id', self.search([('uuid', '=', vals.get('combo_parent_uuid'))]).id)
                ])
            if 'combo_parent_uuid' in vals:
                del vals['combo_parent_uuid']
        return super().create(vals_list)

    def write(self, vals):
        if (vals.get('combo_parent_uuid')):
            vals.update([
                ('combo_parent_id', self.search([('uuid', '=', vals.get('combo_parent_uuid'))]).id)
            ])
        if 'combo_parent_uuid' in vals:
            del vals['combo_parent_uuid']
        return super().write(vals)


class PosOrder(models.Model):
    _inherit = "pos.order"

    table_stand_number = fields.Char(string="Table Stand Number")
    self_ordering_table_id = fields.Many2one('restaurant.table', string='Table reference', readonly=True)
    source = fields.Selection(selection_add=[
        ('mobile', 'Self-Order Mobile'),
        ('kiosk', 'Self-Order Kiosk')
    ])

    def write(self, vals):
        if 'table_id' in vals and self.self_ordering_table_id:
            # Clear stale self-order table link when the order is transferred to a new table.
            vals['self_ordering_table_id'] = vals['table_id']
        return super().write(vals)

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        return [('id', '=', False)]

    @api.model
    def remove_from_ui(self, server_ids):
        order_ids = self.env['pos.order'].browse(server_ids)
        order_ids.state = 'cancel'
        self._send_notification(order_ids)
        return super().remove_from_ui(server_ids)

    @api.model
    def sync_from_ui(self, orders):
        result = super().sync_from_ui(orders)
        order_ids = self.browse([order['id'] for order in result['pos.order'] if order.get('id')])
        self._send_notification(order_ids)
        return result

    def action_pos_order_cancel(self):
        orders = super().action_pos_order_cancel()
        success_orders_ids = [o['id'] for o in orders['pos.order'] if o['state'] == 'cancel']
        orders_ids = self.browse(success_orders_ids)
        self._send_notification(orders_ids)
        return orders

    def _send_notification(self, order_ids):
        config_ids = order_ids.config_id
        for config in config_ids:
            config.notify_synchronisation(config.current_session_id.id, self.env.context.get('device_identifier', 0))
            config._notify('ORDER_STATE_CHANGED', {})

    def _send_self_order_receipt(self):
        if self.email:
            try:
                self.action_send_self_order_receipt(self.email, self.preset_id.mail_template_id.id, False, False)
            except UserError as e:
                _logger.warning("Error while sending email: %s", e.args[0])

    def action_send_self_order_receipt(self, email, mail_template_id, ticket_image, basic_image):
        self.ensure_one()
        self.email = email
        mail_template = self.env['mail.template'].browse(mail_template_id)
        if not mail_template:
            raise UserError(_("The mail template with xmlid %s has been deleted.", mail_template_id))
        email_values = {'email_to': email}
        if self.state == 'paid' and ticket_image:
            email_values['attachment_ids'] = self._get_mail_attachments(self.name, ticket_image, basic_image)
        mail_template.send_mail(self.id, force_send=True, email_values=email_values)

    def _send_payment_result(self, payment_result):
        self.ensure_one()
        self.config_id._notify('PAYMENT_STATUS', {
            'payment_result': payment_result,
            'data': {
                'pos.order': self.read(self._load_pos_self_data_fields(self.config_id), load=False),
                'pos.order.line': self.lines.read(self.lines._load_pos_self_data_fields(self.config_id), load=False),
            }
        })
        if payment_result == 'Success':
            self._send_order()

    def _load_pos_self_data_fields(self, config):
        return ['id', 'uuid', 'name', 'display_name', 'access_token', 'last_order_preparation_change', 'date_order', 'amount_total', 'amount_paid', 'amount_return', 'user_id', 'amount_tax', 'lines', 'pricelist_id', 'company_id', 'country_code', 'sequence_number', 'session_id',
                'config_id', 'currency_id', 'currency_rate', 'is_refund', 'has_refundable_lines', 'state', 'account_move', 'preset_id', 'floating_order_name', 'general_customer_note', 'internal_note', 'nb_print', 'pos_reference', 'fiscal_position_id', 'payment_ids', 'to_invoice',
                'shipping_date', 'preset_time', 'is_invoiced', 'is_tipped', 'tip_amount', 'ticket_code', 'tracking_number', 'email', 'mobile', 'table_id', 'course_ids',
                'table_stand_number', 'self_ordering_table_id', 'create_date', 'write_date', 'source', 'partner_id', 'customer_count']
