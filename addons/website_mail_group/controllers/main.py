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

from openerp.addons.web import http
from openerp.addons.web.http import request


class MailGroup(http.Controller):
    _thread_per_page = 10

    @http.route([
        "/groups",
    ], type='http', auth="public", website=True)
    def view(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        group_obj = request.registry.get('mail.group')
        
        group_ids = group_obj.search(cr, uid, [], context=context)
        values = {
            'groups': group_obj.browse(cr, uid, group_ids, context),
        }
        return request.website.render('website_mail_group.mail_groups', values)

    @http.route([
        "/groups/subscription/",
    ], type='json', auth="public", website=True)
    def subscription(self, group_id=0, action=False ,**post):
        cr, uid, context = request.cr, request.uid, request.context
        group_obj = request.registry.get('mail.group')
        public_uid = request.registry['website'].get_public_user(cr , uid, context)
        if uid == public_uid:
            return ['is_public']
        if action:
            group_obj.message_subscribe_users(cr, uid, [group_id], context=context)
        else:
            group_obj.message_unsubscribe_users(cr, uid, [group_id], context=context)
        return []

    @http.route([
        "/groups/<model('mail.group'):group>/",
        "/groups/<model('mail.group'):group>/page/<int:page>/"
    ], type='http', auth="public", website=True)
    def thread(self, group, page=1, **post):
        cr, uid, context = request.cr, request.uid, request.context
        group_obj = request.registry.get('mail.group')
        thread_obj = request.registry.get('mail.message')
        thread_ids = thread_obj.search(cr, uid, [('model','=','mail.group'), ('res_id','=',group.id), ('parent_id','=',False)])
        group_ids = group_obj.search(cr, uid, [])
        pager = request.website.pager(
            url='/groups/%s/' % group.id,
            total=len(thread_ids),
            page=page,
            step=self._thread_per_page,
        )
        pager_begin = (page - 1) * self._thread_per_page
        pager_end = page * self._thread_per_page
        thread_ids = thread_ids[pager_begin:pager_end]
        values = {
            'groups': group_obj.browse(cr, uid, group_ids, context),
            'thread_list': thread_obj.browse(cr, uid, thread_ids, context),
            'active_group': group,
            'pager': pager,
        }
        return request.website.render('website_mail_group.group_thread_list', values)

    @http.route([
        "/groups/<model('mail.group'):group>/message/<model('mail.message'):message>",
    ], type='http', auth="public", website=True)
    def get_thread(self, group, message, **post):
        cr, uid, context = request.cr, request.uid, request.context
        thread_obj = request.registry.get('mail.message')
        child_ids = thread_obj.search(cr, uid, [('parent_id','=',message.id)], order='date')
        values = {
            'main_thread': message,
            'child_thread': thread_obj.browse(cr, uid, child_ids, context),
        }
        return request.website.render('website_mail_group.group_thread', values)
