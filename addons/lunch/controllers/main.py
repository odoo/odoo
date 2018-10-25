# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, fields
from odoo.http import request


class LunchController(http.Controller):
    @http.route('/lunch/infos', type='json', auth='user')
    def infos(self, user_id=None):
        user = request.env['res.users'].browse(user_id) if user_id else request.env.user

        infos = {
            'order': False,
            'wallet': request.env['lunch.cashmove'].get_wallet_balance(user),
            'username': user.sudo().name,
            'userimage': '/web/image?model=res.users&id=%s&field=image_small' % user.id,
            'is_manager': request.env.user.has_group('lunch.group_lunch_manager'),
            'users': request.env['res.users'].search_read([('groups_id', 'not in', [request.env.ref('base.group_portal').id])], ['name']),
        }

        order = self._get_current_order(user.id)
        if order:
            lines = [{'id': line.id,
                      'product': (line.product_id.name, line.product_id.price),
                      'toppings': [(topping.name, topping.price) for topping in line.topping_ids],
                      'quantity': line.quantity,
                      'price': line.price} for line in order.order_line_ids]
            infos.update({
                'order': order.id,
                'total': order.total,
                'state': order.state,
                'lines': lines,
            })
        return infos

    @http.route('/lunch/trash', type='json', auth='user')
    def trash(self, user_id=None):
        user = request.env['res.users'].browse(user_id) if user_id else request.env.user

        order = self._get_current_order(user.id)
        order.unlink()

    @http.route('/lunch/pay', type='json', auth='user')
    def pay(self, user_id=None):
        user = request.env['res.users'].browse(user_id) if user_id else request.env.user

        order = self._get_current_order(user.id)
        if order:
            wallet_balance = request.env['lunch.cashmove'].get_wallet_balance(user)

            if order.state == 'new' and order.total <= wallet_balance:
                return self._make_payment(order)

        return False

    @http.route('/lunch/payment_message', type='json', auth='user')
    def payment_message(self):
        return {'message': request.env['ir.qweb'].render('lunch.lunch_payment_dialog', {})}

    def _get_current_order(self, user_id):
        order = request.env['lunch.order'].search([('user_id', '=', user_id), ('date', '=', fields.Date.today())], limit=1)
        return order

    def _make_payment(self, order):
        order.action_order()
        return True
