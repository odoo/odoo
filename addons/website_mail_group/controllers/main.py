# -*- coding: utf-8 -*-

import datetime
from dateutil import relativedelta

from openerp import http, tools
from openerp.addons.website.models.website import slug
from openerp.http import request


class MailGroup(http.Controller):
    _thread_per_page = 20
    _replies_per_page = 10

    def _get_archives(self, group_id):
        MailMessage = request.env['mail.message']
        groups = MailMessage.read_group(
            [('model', '=', 'mail.group'), ('res_id', '=', group_id)],
            fields=['subject', 'date'], groupby="date", orderby="date desc"
        )
        for group in groups:
            begin_date = datetime.datetime.strptime(group['__domain'][0][2],
                                                    tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
            end_date = datetime.datetime.strptime(group['__domain'][1][2],
                                                  tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
            group['date_begin'] = '%s' % datetime.date.strftime(begin_date, tools.DEFAULT_SERVER_DATE_FORMAT)
            group['date_end'] = '%s' % datetime.date.strftime(end_date, tools.DEFAULT_SERVER_DATE_FORMAT)
        return groups

    @http.route("/groups", type='http', auth="public", website=True)
    def view(self, **post):
        Group = request.env['mail.group']
        MailMessage = request.env['mail.message']
        groups = Group.search([('alias_id', '!=', False), ('alias_id.alias_name', '!=', False)])

        # compute statistics
        month_date = datetime.datetime.today() - relativedelta.relativedelta(months=1)
        result = MailMessage.sudo().read_group([('model', '=', 'mail.group'),
                                                     ('date', '>=',
                                                      month_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT))],
                                                    fields=['res_id'], groupby=['res_id'])
        result = dict([(x['res_id'], x['res_id_count']) for x in result])

        group_data = dict()
        for group in groups:
            group_data[group.id] = {'monthly_message_nbr': result.get(group.id, 0)}
        values = {'groups': groups, 'group_data': group_data}
        return request.website.render('website_mail_group.mail_groups', values)

    @http.route(["/groups/subscription/"], type='json', auth="user")
    def subscription(self, group_id=0, action=False, **post):
        """ TDE FIXME: seems dead code """
        Group = request.env['mail.group']
        if action:
            Group.message_subscribe_users([group_id])
        else:
            Group.message_unsubscribe_users([group_id])
        return []

    @http.route(["/groups/<model('mail.group'):group>", "/groups/<model('mail.group'):group>/page/<int:page>"],
                type='http', auth="public", website=True)
    def thread_headers(self, group, page=1, mode='thread', date_begin=None, date_end=None, **post):
        MailMessage = request.env['mail.message']

        domain = [('model', '=', 'mail.group'), ('res_id', '=', group.id)]
        if mode == 'thread':
            domain += [('parent_id', '=', False)]
        if date_begin and date_end:
            domain += [('date', '>=', date_begin), ('date', '<=', date_end)]

        thread_count = MailMessage.search_count(domain)
        pager = request.website.pager(
            url='/groups/%s' % slug(group),
            total=thread_count,
            page=page,
            step=self._thread_per_page,
            url_args={'mode': mode, 'date_begin': date_begin or '', 'date_end': date_end or ''},
        )
        messages = MailMessage.search(domain, limit=self._thread_per_page, offset=pager['offset'])
        values = {
            'messages': messages,
            'group': group,
            'pager': pager,
            'mode': mode,
            'archives': self._get_archives(group.id),
            'date_begin': date_begin,
            'date_end': date_end,
            'replies_per_page': self._replies_per_page,
        }
        return request.website.render('website_mail_group.group_messages', values)

    @http.route(['''/groups/<model('mail.group'):group>/<model('mail.message', "[('model','=','mail.group'), ('res_id','=',group[0])]"):message>''', ],
                type='http', auth="public", website=True)
    def thread_discussion(self, group, message, mode='thread', date_begin=None, date_end=None, **post):
        Message = request.env['mail.message']
        if mode == 'thread':
            base_domain = [('model', '=', 'mail.group'), ('res_id', '=', group.id),
                           ('parent_id', '=', message.parent_id and message.parent_id.id or False)]
        else:
            base_domain = [('model', '=', 'mail.group'), ('res_id', '=', group.id)]
        next_message = Message.search(base_domain + [('date', '<', message.date)], order="date DESC", limit=1)
        prev_message = Message.search(base_domain + [('date', '>', message.date)], order="date ASC", limit=1)
        values = {
            'message': message,
            'group': group,
            'mode': mode,
            'archives': self._get_archives(group.id),
            'date_begin': date_begin,
            'date_end': date_end,
            'replies_per_page': self._replies_per_page,
            'next_message': next_message,
            'prev_message': prev_message,
        }
        return request.website.render('website_mail_group.group_message', values)

    @http.route('''/groups/<model('mail.group'):group>/<model('mail.message', "[('model','=','mail.group'), ('res_id','=',group[0])]"):message>/get_replies''',
                type='json', auth="public", methods=['POST'], website=True)
    def render_messages(self, group, message, **post):
        last_displayed_id = post.get('last_displayed_id')
        if not last_displayed_id:
            return False
        Message = request.env['mail.message']
        replies_domain = [('id', '<', int(last_displayed_id)), ('parent_id', '=', message.id)]
        messages = Message.search(replies_domain, limit=self._replies_per_page)
        msg_count = Message.search_count(replies_domain)
        values = {
            'group': group,
            'thread_header': message,
            'messages': messages,
            'msg_more_count': msg_count - self._replies_per_page,
            'replies_per_page': self._replies_per_page,
        }
        return request.env['ir.ui.view'].render('website_mail_group.messages_short', values)

    @http.route("/groups/<model('mail.group'):group>/get_alias_info", type='json', auth='public', website=True)
    def get_alias_info(self, group, **post):
        return {
            'alias_name': group.alias_id and group.alias_id.alias_name and group.alias_id.alias_domain and '%s@%s' % (
                group.alias_id.alias_name, group.alias_id.alias_domain) or False
        }
