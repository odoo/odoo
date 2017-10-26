# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from datetime import datetime
from dateutil import relativedelta

from odoo import http, fields, tools, _
from odoo.http import request
from odoo.addons.website.models.website import slug

class MailGroup(http.Controller):
    _thread_per_page = 20
    _replies_per_page = 10

    def _get_archives(self, group_id):
        MailMessage = request.env['mail.message']
        groups = MailMessage._read_group_raw(
            [('model', '=', 'mail.channel'), ('res_id', '=', group_id), ('message_type', '!=', 'notification')],
            ['subject', 'date'],
            groupby=["date"], orderby="date desc")
        for group in groups:
            (r, label) = group['date']
            start, end = r.split('/')
            group['date'] = label
            group['date_begin'] = self._to_date(start)
            group['date_end'] = self._to_date(end)
        return groups

    def _to_date(self, dt):
        """ date is (of course) a datetime so start and end are datetime
        strings, but we just want date strings
        """
        return (datetime
            .strptime(dt, tools.DEFAULT_SERVER_DATETIME_FORMAT)
            .date() # may be unnecessary?
            .strftime(tools.DEFAULT_SERVER_DATE_FORMAT))

    @http.route("/groups", type='http', auth="public", website=True)
    def view(self, **post):
        groups = request.env['mail.channel'].search([('alias_id.alias_name', '!=', False)])

        # compute statistics
        month_date = datetime.today() - relativedelta.relativedelta(months=1)
        messages = request.env['mail.message'].read_group(
            [('model', '=', 'mail.channel'), ('date', '>=', fields.Datetime.to_string(month_date)), ('message_type', '!=', 'notification')],
            [], ['res_id'])
        message_data = dict((message['res_id'], message['res_id_count']) for message in messages)

        group_data = dict((group.id, {'monthly_message_nbr': message_data.get(group.id, 0)}) for group in groups)
        return request.render('website_mail_channel.mail_channels', {'groups': groups, 'group_data': group_data})

    @http.route(["/groups/is_member"], type='json', auth="public", website=True)
    def is_member(self, channel_id=0, **kw):
        """ Determine if the current user is member of the given channel_id
            :param channel_id : the channel_id to check
        """
        current_user = request.env.user
        session_partner_id = request.session.get('partner_id')
        public_user = request.website.user_id
        partner = None
        # find the current partner
        if current_user != public_user:
            partner = current_user.partner_id
        elif session_partner_id:
            partner = request.env['res.partner'].sudo().browse(session_partner_id)

        values = {
            'is_user': current_user != public_user,
            'email': partner.email if partner else "",
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
        unsubscribe = subscription == 'on'
        channel = request.env['mail.channel'].browse(int(channel_id))
        partner_ids = []

        # search partner_id
        if request.env.user != request.website.user_id:
            # connected users are directly (un)subscribed
            partner_ids = request.env.user.partner_id.ids

            # add or remove channel members
            if unsubscribe:
                channel.check_access_rule('read')
                channel.sudo().write({'channel_partner_ids': [(3, partner_id) for partner_id in partner_ids]})
                return "off"
            else:  # add partner to the channel
                request.session['partner_id'] = partner_ids[0]
                channel.check_access_rule('read')
                channel.sudo().write({'channel_partner_ids': [(4, partner_id) for partner_id in partner_ids]})
            return "on"

        else:
            # public users will recieve confirmation email
            partner_ids = channel.sudo()._find_partner_from_emails([email], check_followers=True)
            if not partner_ids or not partner_ids[0]:
                name = email.split('@')[0]
                partner_ids = [request.env['res.partner'].sudo().create({'name': name, 'email': email}).id]

            channel.sudo()._send_confirmation_email(partner_ids, unsubscribe)
            return "email"


    @http.route([
        "/groups/<model('mail.channel'):group>",
        "/groups/<model('mail.channel'):group>/page/<int:page>"
    ], type='http', auth="public", website=True)
    def thread_headers(self, group, page=1, mode='thread', date_begin=None, date_end=None, **post):
        if group.channel_type != 'channel':
            raise werkzeug.exceptions.NotFound()

        Message = request.env['mail.message']

        domain = [('model', '=', 'mail.channel'), ('res_id', '=', group.id), ('message_type', '!=', 'notification')]
        if mode == 'thread':
            domain += [('parent_id', '=', False)]
        if date_begin and date_end:
            domain += [('date', '>=', date_begin), ('date', '<=', date_end)]

        pager = request.website.pager(
            url='/groups/%s' % slug(group),
            total=Message.search_count(domain),
            page=page,
            step=self._thread_per_page,
            url_args={'mode': mode, 'date_begin': date_begin or '', 'date_end': date_end or ''},
        )
        messages = Message.search(domain, limit=self._thread_per_page, offset=pager['offset'])
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
        return request.render('website_mail_channel.group_messages', values)

    @http.route([
        '''/groups/<model('mail.channel'):group>/<model('mail.message', "[('model','=','mail.channel'), ('res_id','=',group[0])]"):message>''',
    ], type='http', auth="public", website=True)
    def thread_discussion(self, group, message, mode='thread', date_begin=None, date_end=None, **post):
        if group.channel_type != 'channel':
            raise werkzeug.exceptions.NotFound()

        Message = request.env['mail.message']
        if mode == 'thread':
            base_domain = [('model', '=', 'mail.channel'), ('res_id', '=', group.id), ('parent_id', '=', message.parent_id and message.parent_id.id or False)]
        else:
            base_domain = [('model', '=', 'mail.channel'), ('res_id', '=', group.id)]
        next_message = Message.search(base_domain + [('date', '<', message.date)], order="date DESC", limit=1) or None
        prev_message = Message.search(base_domain + [('date', '>', message.date)], order="date", limit=1) or None
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
        return request.render('website_mail_channel.group_message', values)

    @http.route(
        '''/groups/<model('mail.channel'):group>/<model('mail.message', "[('model','=','mail.channel'), ('res_id','=',group[0])]"):message>/get_replies''',
        type='json', auth="public", methods=['POST'], website=True)
    def render_messages(self, group, message, **post):
        if group.channel_type != 'channel':
            return False

        last_displayed_id = post.get('last_displayed_id')
        if not last_displayed_id:
            return False

        replies_domain = [('id', '<', int(last_displayed_id)), ('parent_id', '=', message.id)]
        messages = request.env['mail.message'].search(replies_domain, limit=self._replies_per_page)
        message_count = request.env['mail.message'].search_count(replies_domain)
        values = {
            'group': group,
            'thread_header': message,
            'messages': messages,
            'msg_more_count': message_count - self._replies_per_page,
            'replies_per_page': self._replies_per_page,
        }
        return request.env.ref('website_mail_channel.messages_short').render(values, engine='ir.qweb')

    @http.route("/groups/<model('mail.channel'):group>/get_alias_info", type='json', auth='public', website=True)
    def get_alias_info(self, group, **post):
        return {
            'alias_name': group.alias_id and group.alias_id.alias_name and group.alias_id.alias_domain and '%s@%s' % (group.alias_id.alias_name, group.alias_id.alias_domain) or False
        }

    @http.route("/groups/subscribe/<model('mail.channel'):channel>/<int:partner_id>/<string:token>", type='http', auth='public', website=True)
    def confirm_subscribe(self, channel, partner_id, token, **kw):
        subscriber = request.env['mail.channel.partner'].search([('channel_id', '=', channel.id), ('partner_id', '=', partner_id)])
        if subscriber:
            # already registered, maybe clicked twice
            return request.render('website_mail_channel.invalid_token_subscription')

        subscriber_token = channel._generate_action_token(partner_id, action='subscribe')
        if token != subscriber_token:
            return request.render('website_mail_channel.invalid_token_subscription')

        # add partner
        channel.sudo().write({'channel_partner_ids': [(4, partner_id)]})

        return request.render("website_mail_channel.confirmation_subscription", {'subscribing': True})

    @http.route("/groups/unsubscribe/<model('mail.channel'):channel>/<int:partner_id>/<string:token>", type='http', auth='public', website=True)
    def confirm_unsubscribe(self, channel, partner_id, token, **kw):
        subscriber = request.env['mail.channel.partner'].search([('channel_id', '=', channel.id), ('partner_id', '=', partner_id)])
        if not subscriber:
            partner = request.env['res.partner'].browse(partner_id).sudo().exists()
            # FIXME: remove try/except in master
            try:
                response = request.render(
                    'website_mail_channel.not_subscribed',
                    {'partner_id': partner})
                # make sure the rendering (and thus error if template is
                # missing) happens inside the try block
                response.flatten()
                return response
            except ValueError:
                return _("The address %s is already unsubscribed or was never subscribed to any mailing list") % (
                    partner.email
                )

        subscriber_token = channel._generate_action_token(partner_id, action='unsubscribe')
        if token != subscriber_token:
            return request.render('website_mail_channel.invalid_token_subscription')

        # remove partner
        channel.sudo().write({'channel_partner_ids': [(3, partner_id)]})

        return request.render("website_mail_channel.confirmation_subscription", {'subscribing': False})
