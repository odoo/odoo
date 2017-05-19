# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from werkzeug.urls import url_encode
import uuid


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    website_url = fields.Char('Website URL', compute='_website_url', help='The full URL to access the document through the website.')
    payment_transaction_count = fields.Integer(compute='_compute_payment_transaction_count', string="Number of payment transactions")

    def _website_url(self):
        for so in self:
            so.website_url = '/my/orders/%s' % (so.id)

    def _compute_payment_transaction_count(self):
        transaction_data = self.env['payment.transaction'].read_group([('sale_order_id', 'in', self.ids)], ['sale_order_id'], ['sale_order_id'])
        mapped_data = dict([(m['sale_order_id'][0], m['sale_order_id_count']) for m in transaction_data])
        for order in self:
            order.payment_transaction_count = mapped_data.get(order.id, 0)

    @api.multi
    def get_access_action(self, access_uid=None):
        """ Instead of the classic form view, redirect to the online order for
        portal users or if force_website=True in the context. """
        # TDE note: read access on sales order to portal users granted to followed sales orders
        self.ensure_one()
        if self.state == 'cancel' or (self.state == 'draft' and not self.env.context.get('mark_so_as_sent')):
            return super(SaleOrder, self).get_access_action(access_uid)

        user = self.env['res.users'].sudo().browse(access_uid) if access_uid else self.env.user
        if user.share or self.env.context.get('force_website'):
            return {
                'type': 'ir.actions.act_url',
                'url': '/my/orders/%s?access_token=%s' % (self.id, self.access_token),
                'target': 'self',
                'res_id': self.id,
            }
        return super(SaleOrder, self).get_access_action(access_uid)

    def get_mail_url(self):
        self.ensure_one()
        params = {
            'model': self._name,
            'res_id': self.id,
            'access_token': self.access_token,
        }
        params.update(self.partner_id.signup_get_auth_param()[self.partner_id.id])
        return '/mail/view?' + url_encode(params)

    @api.multi
    def _notification_recipients(self, message, groups):
        groups = super(SaleOrder, self)._notification_recipients(message, groups)

        self.ensure_one()
        if self.state not in ('draft', 'cancel'):
            for group_name, group_method, group_data in groups:
                group_data['has_button_access'] = True

        return groups

    @api.multi
    def get_signup_url(self):
        self.ensure_one()
        return self.partner_id.with_context(signup_valid=True)._get_signup_url_for_action(
            action='/mail/view',
            model=self._name,
            res_id=self.id)[self.partner_id.id]

    def action_view_transaction(self):
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Payment Transactions',
            'res_model': 'payment.transaction',
        }
        if self.payment_transaction_count == 1:
            action.update({
                'res_id': self.env['payment.transaction'].search([('sale_order_id', '=', self.id)]).id,
                'view_mode': 'form',
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('sale_order_id', '=', self.id)],
            })
        return action


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    # Non-stored related field to allow portal user to see the image of the product he has ordered
    product_image = fields.Binary('Product Image', related="product_id.image", store=False)
