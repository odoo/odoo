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

    def _send_notification(self, order_ids):
        config_ids = order_ids.config_id
        for config in config_ids:
            config.notify_synchronisation(config.current_session_id.id, self.env.context.get('login_number', 0))
            config._notify('ORDER_STATE_CHANGED', {})

    def _notify_new_self_order(self):
        for config in self.config_id:
            order_ids = self.filtered(lambda o: o.config_id.id == config.id).ids
            config._notify('NEW_SELF_ORDER', {'order_ids': order_ids})

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
