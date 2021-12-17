# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, http, fields
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.osv import expression
from odoo.tools import float_round, float_repr


class LunchController(http.Controller):
    @http.route('/lunch/infos', type='json', auth='user')
    def infos(self, user_id=None):
        self._check_user_impersonification(user_id)
        user = request.env['res.users'].browse(user_id) if user_id else request.env.user

        infos = self._make_infos(user, order=False)

        lines = self._get_current_lines(user)
        if lines:
            lines = [{'id': line.id,
                      'product': (line.product_id.id, line.product_id.name, float_repr(float_round(line.product_id.price, 2), 2)),
                      'toppings': [(topping.name, float_repr(float_round(topping.price, 2), 2))
                                   for topping in line.topping_ids_1 | line.topping_ids_2 | line.topping_ids_3],
                      'quantity': line.quantity,
                      'price': line.price,
                      'state': line.state, # Only used for _get_state
                      'note': line.note} for line in lines]
            raw_state, state = self._get_state(lines)
            infos.update({
                'total': float_repr(float_round(sum(line['price'] for line in lines), 2), 2),
                'raw_state': raw_state,
                'state': state,
                'lines': lines,
            })
        return infos

    @http.route('/lunch/trash', type='json', auth='user')
    def trash(self, user_id=None):
        self._check_user_impersonification(user_id)
        user = request.env['res.users'].browse(user_id) if user_id else request.env.user

        lines = self._get_current_lines(user)
        lines.action_cancel()
        lines.unlink()

    @http.route('/lunch/pay', type='json', auth='user')
    def pay(self, user_id=None):
        self._check_user_impersonification(user_id)
        user = request.env['res.users'].browse(user_id) if user_id else request.env.user

        lines = self._get_current_lines(user)
        if lines:
            lines = lines.filtered(lambda line: line.state == 'new')

            lines.action_order()
            return True

        return False

    @http.route('/lunch/payment_message', type='json', auth='user')
    def payment_message(self):
        return {'message': request.env['ir.qweb']._render('lunch.lunch_payment_dialog', {})}

    @http.route('/lunch/user_location_set', type='json', auth='user')
    def set_user_location(self, location_id=None, user_id=None):
        self._check_user_impersonification(user_id)
        user = request.env['res.users'].browse(user_id) if user_id else request.env.user

        user.sudo().last_lunch_location_id = request.env['lunch.location'].browse(location_id)
        return True

    @http.route('/lunch/user_location_get', type='json', auth='user')
    def get_user_location(self, user_id=None):
        self._check_user_impersonification(user_id)
        user = request.env['res.users'].browse(user_id) if user_id else request.env.user

        company_ids = request.env.context.get('allowed_company_ids', request.env.company.ids)
        user_location = user.last_lunch_location_id
        has_multi_company_access = not user_location.company_id or user_location.company_id.id in company_ids

        if not user_location or not has_multi_company_access:
            return request.env['lunch.location'].search([('company_id', 'in', [False] + company_ids)], limit=1).id
        return user_location.id

    def _make_infos(self, user, **kwargs):
        res = dict(kwargs)

        is_manager = request.env.user.has_group('lunch.group_lunch_manager')

        currency = user.company_id.currency_id

        res.update({
            'username': user.sudo().name,
            'userimage': '/web/image?model=res.users&id=%s&field=avatar_128' % user.id,
            'wallet': request.env['lunch.cashmove'].get_wallet_balance(user, False),
            'is_manager': is_manager,
            'group_portal_id': request.env.ref('base.group_portal').id,
            'locations': request.env['lunch.location'].search_read([], ['name']),
            'currency': {'symbol': currency.symbol, 'position': currency.position},
        })

        user_location = user.last_lunch_location_id
        has_multi_company_access = not user_location.company_id or user_location.company_id.id in request._context.get('allowed_company_ids', request.env.company.ids)

        if not user_location or not has_multi_company_access:
            user.last_lunch_location_id = user_location = request.env['lunch.location'].search([], limit=1)

        alert_domain = expression.AND([
            [('available_today', '=', True)],
            [('location_ids', 'in', user_location.id)],
            [('mode', '=', 'alert')],
        ])

        res.update({
            'user_location': (user_location.id, user_location.name),
            'alerts': request.env['lunch.alert'].search_read(alert_domain, ['message']),
        })

        return res

    def _check_user_impersonification(self, user_id=None):
        if (user_id and request.env.uid != user_id and not request.env.user.has_group('lunch.group_lunch_manager')):
            raise AccessError(_('You are trying to impersonate another user, but this can only be done by a lunch manager'))

    def _get_current_lines(self, user):
        return request.env['lunch.order'].search(
            [('user_id', '=', user.id), ('date', '=', fields.Date.context_today(user)), ('state', '!=', 'cancelled')]
            )

    def _get_state(self, lines):
        """
            This method returns the lowest state of the list of lines

            eg: [confirmed, confirmed, new] will return ('new', 'To Order')
        """
        states_to_int = {'new': 0, 'ordered': 1, 'confirmed': 2, 'cancelled': 3}
        int_to_states = ['new', 'ordered', 'confirmed', 'cancelled']
        translated_states = dict(request.env['lunch.order']._fields['state']._description_selection(request.env))

        state = int_to_states[min(states_to_int[line['state']] for line in lines)]

        return (state, translated_states[state])
