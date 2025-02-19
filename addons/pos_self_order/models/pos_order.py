# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


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

    @api.model
    def _load_pos_self_data_domain(self, data):
        return [('id', '=', False)]

    def _process_saved_order(self, draft):
        res = super()._process_saved_order(draft)

        if self.env.context.get('from_self') is not True:
            self._send_notification(self)

        return res

    @api.model
    def remove_from_ui(self, server_ids):
        order_ids = self.env['pos.order'].browse(server_ids)
        order_ids.state = 'cancel'
        self._send_notification(order_ids)
        return super().remove_from_ui(server_ids)

    def _send_notification(self, order_ids):
        for order in order_ids:
            order._notify('ORDER_STATE_CHANGED', {
                'pos.order': order.read(order._load_pos_self_data_fields(order.config_id.id), load=False),
                'pos.order.line': order.lines.read(order._load_pos_self_data_fields(order.config_id.id), load=False),
                'pos.payment': order.payment_ids.read(order.payment_ids._load_pos_data_fields(order.config_id.id), load=False),
                'pos.payment.method': order.payment_ids.mapped('payment_method_id').read(self.env['pos.payment.method']._load_pos_data_fields(order.config_id.id), load=False),
                'product.attribute.custom.value':  order.lines.custom_attribute_value_ids.read(order.lines.custom_attribute_value_ids._load_pos_data_fields(order.config_id.id), load=False),
            })

    def _get_open_order(self, order):
        open_order = super()._get_open_order(order)
        if not self.env.context.get('from_self'):
            return open_order
        elif open_order:
            order.pop('table_id', None)
        return self.env['pos.order'].search([('uuid', '=', order.get('uuid'))], limit=1)
    
    def action_send_self_order_receipt(self, email, mail_template_id, ticket_image, basic_image):
        self.ensure_one()
        self.email = email
        mail_template = self.env['mail.template'].browse(mail_template_id)
        if not mail_template:
            raise UserError(_("The mail template with xmlid %s has been deleted.", mail_template_id))
        email_values = {'email_to': email}
        if self.state == 'paid':
            email_values['attachment_ids'] = self._get_mail_attachments(self.name, ticket_image, basic_image)
        mail_template.send_mail(self.id, force_send=True, email_values=email_values)
