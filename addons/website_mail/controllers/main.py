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
from openerp.addons.website import website


class WebsiteMail(http.Controller):

    def _find_or_create_partner(self, email, context=None):
        # TDE TODO: FIXME: use mail_thread method
        partner_obj = request.registry['res.partner']
        user_obj = request.registry['res.users']
        partner_ids = []
        if request.context['is_public_user'] and email:
            partner_ids = partner_obj.search(request.cr, SUPERUSER_ID, [("email", "=", email)], context=request.context)
            if not partner_ids:
                partner_ids = [partner_obj.create(request.cr, SUPERUSER_ID, {"email": email, "name": email}, request.context)]
        else:
            partner_ids = [user_obj.browse(request.cr, request.uid, request.uid, request.context).partner_id.id]
        return partner_ids

    @website.route(['/website_mail/follow/'], type='http', auth="public")
    def website_message_subscribe(self, **post):
        _id = int(post['id'])
        _message_is_follower = post['message_is_follower'] == 'on'
        _object = request.registry[post['object']]
        partner_ids = self._find_or_create_partner(post.get('email'), request.context)

        if _message_is_follower:
            _object.check_access_rule(request.cr, request.uid, [_id], 'read', request.context)
            _object.message_unsubscribe(request.cr, SUPERUSER_ID, [_id], partner_ids, context=request.context)
        else:
            _object.check_access_rule(request.cr, request.uid, [_id], 'read', request.context)
            _object.message_subscribe(request.cr, SUPERUSER_ID, [_id], partner_ids, context=request.context)
        obj = _object.browse(request.cr, request.uid, _id)

        return obj.message_is_follower and "1" or "0"
