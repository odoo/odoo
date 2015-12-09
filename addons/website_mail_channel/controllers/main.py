# -*- coding: utf-8 -*-

import datetime
from dateutil import relativedelta

from openerp import tools, SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.website.models.website import slug
from openerp.addons.web.http import request


class MailGroup(http.Controller):
    _thread_per_page = 20
    _replies_per_page = 10

    def _get_archives(self, group_id):
        MailMessage = request.registry['mail.message']
        groups = MailMessage.read_group(
            request.cr, request.uid, [('model', '=', 'mail.channel'), ('res_id', '=', group_id)], ['subject', 'date'],
            groupby="date", orderby="date desc", context=request.context)
        for group in groups:
            begin_date = datetime.datetime.strptime(group['__domain'][0][2], tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
            end_date = datetime.datetime.strptime(group['__domain'][1][2], tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
            group['date_begin'] = '%s' % datetime.date.strftime(begin_date, tools.DEFAULT_SERVER_DATE_FORMAT)
            group['date_end'] = '%s' % datetime.date.strftime(end_date, tools.DEFAULT_SERVER_DATE_FORMAT)
        return groups

    @http.route("/groups", type='http', auth="public", website=True)
    def view(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        group_obj = request.registry.get('mail.channel')
        mail_message_obj = request.registry.get('mail.message')
        group_ids = group_obj.search(cr, uid, [('alias_id', '!=', False), ('alias_id.alias_name', '!=', False)], context=context)
        groups = group_obj.browse(cr, uid, group_ids, context)

        # compute statistics
        month_date = datetime.datetime.today() - relativedelta.relativedelta(months=1)
        result = mail_message_obj.read_group(
            cr, SUPERUSER_ID,
            [('model', '=', 'mail.channel'), ('date', '>=', month_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT))],
            [], ['res_id'],
            context=context)
        result = dict([(x['res_id'], x['res_id_count']) for x in result])

        group_data = dict()
        for group in groups:
            group_data[group.id] = {'monthly_message_nbr': result.get(group.id, 0)}

        values = {'groups': groups, 'group_data': group_data}
        return request.website.render('website_mail_channel.mail_channels', values)

    @http.route(["/groups/is_member"], type='json', auth="public", website=True)
    def is_member(self, channel_id=0, **kw):
        """ Determine if the current user is member of the given channel_id
            :param channel_id : the channel_id to check
        """
        current_user_id = request.uid
        session_partner_id = request.session.get('partner_id')
        public_id = request.website.user_id.id
        partner = None
        # find the current partner
        if current_user_id != public_id:
            partner = request.env['res.users'].sudo().browse(current_user_id).partner_id
        elif session_partner_id:
            partner = request.env['res.partner'].sudo().browse(session_partner_id)

        values = {
            'is_user': current_user_id != public_id,
            'email': partner and partner.email or "",
            'is_member': False,
            'alias_name': False,
        }
        # check if the current partner is member or not
        channel = request.env['mail.channel'].browse(int(channel_id))
        if channel.exists() and partner is not None:
            values['is_member'] = bool(partner in channel.sudo().channel_partner_ids)
        return values

    @http.route(["/groups/subscription"], type='json', auth="public", website=True)
    def subscription(self, channel_id=0, subscription="on", email='', **kw):
        """ Subscribe to a mailing list : this will create a partner with its email address (if public user not
            registered yet) and add it as channel member
            :param channel_id : the channel id to join/quit
            :param subscription : 'on' to unsubscribe the user, 'off' to subscribe
        """
        subscribe = subscription == 'on'
        channel = request.env['mail.channel'].browse(int(channel_id))
        partner_ids = []

        # search partner_id
        current_user_id = request.uid
        public_id = request.website.user_id.id
        if current_user_id != public_id:
            partner_ids = [request.env['res.users'].browse(current_user_id).partner_id.id]
        else:  # mail_thread method
            partner_ids = channel.sudo()._find_partner_from_emails([email], check_followers=True)
            if not partner_ids or not partner_ids[0]:
                name = email.split('@')[0]
                partner_ids = [request.env['res.partner'].sudo().create({'name': name, 'email': email}).id]

        # add or remove channel members
        if subscribe:
            channel.check_access_rule('read')
            channel.sudo().write({'channel_partner_ids': [(3, partner_id) for partner_id in partner_ids]})
            return False
        else:  # add partner to the channel
            request.session['partner_id'] = partner_ids[0]
            channel.check_access_rule('read')
            channel.sudo().write({'channel_partner_ids': [(4, partner_id) for partner_id in partner_ids]})
        return True

    @http.route([
        "/groups/<model('mail.channel'):group>",
        "/groups/<model('mail.channel'):group>/page/<int:page>"
    ], type='http', auth="public", website=True)
    def thread_headers(self, group, page=1, mode='thread', date_begin=None, date_end=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        thread_obj = request.registry.get('mail.message')

        domain = [('model', '=', 'mail.channel'), ('res_id', '=', group.id), ('message_type', '!=', 'notification')]
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
            'replies_per_page': self._replies_per_page,
        }
        return request.website.render('website_mail_channel.group_messages', values)

    @http.route([
        '''/groups/<model('mail.channel'):group>/<model('mail.message', "[('model','=','mail.channel'), ('res_id','=',group[0])]"):message>''',
    ], type='http', auth="public", website=True)
    def thread_discussion(self, group, message, mode='thread', date_begin=None, date_end=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        Message = request.registry['mail.message']
        if mode == 'thread':
            base_domain = [('model', '=', 'mail.channel'), ('res_id', '=', group.id), ('parent_id', '=', message.parent_id and message.parent_id.id or False)]
        else:
            base_domain = [('model', '=', 'mail.channel'), ('res_id', '=', group.id)]
        next_message = None
        next_message_ids = Message.search(cr, uid, base_domain + [('date', '<', message.date)], order="date DESC", limit=1, context=context)
        if next_message_ids:
            next_message = Message.browse(cr, uid, next_message_ids[0], context=context)
        prev_message = None
        prev_message_ids = Message.search(cr, uid, base_domain + [('date', '>', message.date)], order="date ASC", limit=1, context=context)
        if prev_message_ids:
            prev_message = Message.browse(cr, uid, prev_message_ids[0], context=context)
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
        return request.website.render('website_mail_channel.group_message', values)

    @http.route(
        '''/groups/<model('mail.channel'):group>/<model('mail.message', "[('model','=','mail.channel'), ('res_id','=',group[0])]"):message>/get_replies''',
        type='json', auth="public", methods=['POST'], website=True)
    def render_messages(self, group, message, **post):
        last_displayed_id = post.get('last_displayed_id')
        if not last_displayed_id:
            return False
        Message = request.registry['mail.message']
        replies_domain = [('id', '<', int(last_displayed_id)), ('parent_id', '=', message.id)]
        msg_ids = Message.search(request.cr, request.uid, replies_domain, limit=self._replies_per_page, context=request.context)
        msg_count = Message.search(request.cr, request.uid, replies_domain, count=True, context=request.context)
        messages = Message.browse(request.cr, request.uid, msg_ids, context=request.context)
        values = {
            'group': group,
            'thread_header': message,
            'messages': messages,
            'msg_more_count': msg_count - self._replies_per_page,
            'replies_per_page': self._replies_per_page,
        }
        return request.registry['ir.ui.view'].render(request.cr, request.uid, 'website_mail_channel.messages_short', values, engine='ir.qweb', context=request.context)

    @http.route("/groups/<model('mail.channel'):group>/get_alias_info", type='json', auth='public', website=True)
    def get_alias_info(self, group, **post):
        return {
            'alias_name': group.alias_id and group.alias_id.alias_name and group.alias_id.alias_domain and '%s@%s' % (group.alias_id.alias_name, group.alias_id.alias_domain) or False
        }
