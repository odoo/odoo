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

    def _find_or_create_partner(self, email, context=None):
        # TDE TODO: FIXME: use mail_thread method
        partner_obj = request.registry['res.partner']
        user_obj = request.registry['res.users']
        partner_ids = []
        if email and email != u'false':  # post contains stringified booleans
            partner_ids = partner_obj.search(request.cr, SUPERUSER_ID, [("email", "=", email)], context=request.context)
            if not partner_ids:
                partner_ids = [partner_obj.name_create(request.cr, SUPERUSER_ID, email, request.context)[0]]
        else:
            partner_ids = [user_obj.browse(request.cr, request.uid, request.uid, request.context).partner_id.id]
        return partner_ids

    @http.route(['/website_mail/follow/'], type='json', auth="public", website=True)
    def website_message_subscribe(self, id=0, object=None, message_is_follower="on", email=False, **post):
        _id = int(id)
        _message_is_follower = message_is_follower == 'on'
        _object = request.registry[object]
        partner_ids = self._find_or_create_partner(email, request.context)

        if _message_is_follower:
            _object.check_access_rule(request.cr, request.uid, [_id], 'read', request.context)
            _object.message_unsubscribe(request.cr, SUPERUSER_ID, [_id], partner_ids, context=request.context)
        else:
            _object.check_access_rule(request.cr, request.uid, [_id], 'read', request.context)
            _object.message_subscribe(request.cr, SUPERUSER_ID, [_id], partner_ids, context=request.context)
        obj = _object.browse(request.cr, request.uid, _id)
        follower_ids = [p.id for p in obj.message_follower_ids]

        return partner_ids[0] in follower_ids and 1 or 0
