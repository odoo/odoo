# -*- coding: utf-8 -*-

import datetime

from openerp import tools
from openerp.addons.web import http
from openerp.addons.website.models.website import slug
from openerp.addons.web.http import request


class MailGroup(http.Controller):
    _thread_per_page = 10

    def _get_archives(self, group_id):
        MailMessage = request.registry['mail.message']
        groups = MailMessage.read_group(
            request.cr, request.uid, [('model', '=', 'mail.group'), ('res_id', '=', group_id)], ['subject', 'date'],
            groupby="date", orderby="date asc", context=request.context)
        for group in groups:
            begin_date = datetime.datetime.strptime(group['__domain'][0][2], tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
            end_date = datetime.datetime.strptime(group['__domain'][1][2], tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
            group['date_begin'] = '%s' % datetime.date.strftime(begin_date, tools.DEFAULT_SERVER_DATE_FORMAT)
            group['date_end'] = '%s' % datetime.date.strftime(end_date, tools.DEFAULT_SERVER_DATE_FORMAT)
        return groups

    @http.route("/groups", type='http', auth="public", website=True)
    def view(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        group_obj = request.registry.get('mail.group')
        group_ids = group_obj.search(cr, uid, [], context=context)
        values = {'groups': group_obj.browse(cr, uid, group_ids, context)}
        return request.website.render('website_mail_group.mail_groups', values)

    @http.route(["/groups/subscription/"], type='json', auth="user")
    def subscription(self, group_id=0, action=False, **post):
        cr, uid, context = request.cr, request.uid, request.context
        group_obj = request.registry.get('mail.group')
        if action:
            group_obj.message_subscribe_users(cr, uid, [group_id], context=context)
        else:
            group_obj.message_unsubscribe_users(cr, uid, [group_id], context=context)
        return []

    @http.route([
        "/groups/<model('mail.group'):group>",
        "/groups/<model('mail.group'):group>/page/<int:page>"
    ], type='http', auth="public", website=True)
    def thread_headers(self, group, page=1, mode='thread', date_begin=None, date_end=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        thread_obj = request.registry.get('mail.message')

        domain = [('model', '=', 'mail.group'), ('res_id', '=', group.id)]
        if mode == 'thread':
            domain += [('parent_id', '=', False)]
        if date_begin and date_end:
            domain += [('date', '>=', date_begin), ('date', '<=', date_end)]

        thread_count = thread_obj.search_count(cr, uid, domain, context=context)
        pager = request.website.pager(
            url='/groups/%s' % slug(group),
            total=thread_count,
            page=page,
            step=self._thread_per_page,
            url_args={'mode': mode, 'date_begin': date_begin or '', 'date_end': date_end or ''},
        )
        thread_ids = thread_obj.search(cr, uid, domain, limit=self._thread_per_page, offset=pager['offset'])
        messages = thread_obj.browse(cr, uid, thread_ids, context)
        values = {
            'messages': messages,
            'group': group,
            'pager': pager,
            'mode': mode,
            'archives': self._get_archives(group.id),
            'date_begin': date_begin,
            'date_end': date_end,
        }
        return request.website.render('website_mail_group.group_messages', values)

    @http.route([
        '''/groups/<model('mail.group'):group>/<model('mail.message', "[('model','=','mail.group'), ('res_id','=',group[0])]"):message>''',
    ], type='http', auth="public", website=True)
    def thread_discussion(self, group, message, mode='thread', date_begin=None, date_end=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        values = {
            'message': message,
            'group': group,
            'mode': mode,
            'date_begin': date_begin,
            'date_end': date_end,
        }
        return request.website.render('website_mail_group.group_message', values)
