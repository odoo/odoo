# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request


class WebsiteMail(http.Controller):

    @http.route(['/website_mail/follow'], type='json', auth="public", website=True)
    def website_message_subscribe(self, id=0, object=None, message_is_follower="on", email=False, **post):
        cr, uid, context = request.cr, request.uid, request.context

        partner_obj = request.registry['res.partner']
        user_obj = request.registry['res.users']

        _id = int(id)
        _message_is_follower = message_is_follower == 'on'
        _object = request.registry[object]

        # search partner_id
        public_id = request.website.user_id.id
        if uid != public_id:
            partner_ids = [user_obj.browse(cr, uid, uid, context).partner_id.id]
        else:
            # mail_thread method
            partner_ids = _object._find_partner_from_emails(
                cr, SUPERUSER_ID, _id, [email], context=context, check_followers=True)
            if not partner_ids or not partner_ids[0]:
                partner_ids = [partner_obj.create(cr, SUPERUSER_ID, {'name': email, 'email': email}, context=context)]

        # add or remove follower
        if _message_is_follower:
            _object.check_access_rule(cr, uid, [_id], 'read', context)
            _object.message_unsubscribe(cr, SUPERUSER_ID, [_id], partner_ids, context=context)
            return False
        else:
            _object.check_access_rule(cr, uid, [_id], 'read', context)
            # add partner to session
            request.session['partner_id'] = partner_ids[0]
            _object.message_subscribe(cr, SUPERUSER_ID, [_id], partner_ids, context=context)
            return True

    @http.route(['/website_mail/is_follower'], type='json', auth="public", website=True)
    def call(self, model, id, **post):
        id = int(id)
        cr, uid, context = request.cr, request.uid, request.context

        partner_obj = request.registry.get('res.partner')
        users_obj = request.registry.get('res.users')
        obj = request.registry.get(model)

        partner_id = None
        public_id = request.website.user_id.id
        if uid != public_id:
            partner_id = users_obj.browse(cr, SUPERUSER_ID, uid, context).partner_id
        elif request.session.get('partner_id'):
            partner_id = partner_obj.browse(cr, SUPERUSER_ID, request.session.get('partner_id'), context)
        email = partner_id and partner_id.email or ""

        values = {
            'is_user': uid != public_id,
            'email': email,
            'is_follower': False,
            'alias_name': False,
        }

        if not obj:
            return values
        obj_ids = obj.exists(cr, SUPERUSER_ID, [id], context=context)
        if obj_ids:
            if partner_id:
                values['is_follower'] = len(
                    request.registry['mail.followers'].search(
                        cr, SUPERUSER_ID, [
                            ('res_model', '=', model),
                            ('res_id', '=', obj_ids[0]),
                            ('partner_id', '=', partner_id.id)
                        ], context=context)) == 1
        return values
