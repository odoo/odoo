# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
import json

from odoo import models, api, fields, _
from odoo.exceptions import UserError


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    livechat_operator_id = fields.Many2one('res.partner', compute='_compute_livechat_operator_id', store=True, string='Speaking with')
    livechat_operator_name = fields.Char('Operator Name', related="livechat_operator_id.name")
    mail_channel_ids = fields.One2many('mail.channel', 'livechat_visitor_id',
                                       string="Visitor's livechat channels", readonly=True)
    session_count = fields.Integer('# Sessions', compute="_compute_session_count")

    @api.depends('mail_channel_ids.livechat_active', 'mail_channel_ids.livechat_operator_id')
    def _compute_livechat_operator_id(self):
        results = self.env['mail.channel'].search_read(
            [('livechat_visitor_id', 'in', self.ids), ('livechat_active', '=', True)],
            ['livechat_visitor_id', 'livechat_operator_id']
        )
        visitor_operator_map = {int(result['livechat_visitor_id'][0]): int(result['livechat_operator_id'][0]) for result in results}
        for visitor in self:
            visitor.livechat_operator_id = visitor_operator_map.get(visitor.id, False)

    @api.depends('mail_channel_ids')
    def _compute_session_count(self):
        sessions = self.env['mail.channel'].read_group([('livechat_visitor_id', 'in', self.ids)], ['livechat_visitor_id'], ['livechat_visitor_id'])
        sessions_count = {session['livechat_visitor_id'][0]: session['livechat_visitor_id_count'] for session in sessions}
        for visitor in self:
            visitor.session_count = sessions_count.get(visitor.id, 0)

    def action_send_chat_request(self):
        """ Send a chat request to website_visitor(s).
        This creates a chat_request and a mail_channel with livechat active flag.
        But for the visitor to get the chat request, the operator still has to speak to the visitor.
        The visitor will receive the chat request the next time he navigates to a website page.
        (see _handle_webpage_dispatch for next step)"""
        # check if visitor is available
        unavailable_visitors_count = self.env['mail.channel'].search_count([('livechat_visitor_id', 'in', self.ids), ('livechat_active', '=', True)])
        if unavailable_visitors_count:
            raise UserError(_('Recipients are not available. Please refresh the page to get latest visitors status.'))
        # check if user is available as operator
        for website in self.mapped('website_id'):
            if not website.channel_id:
                raise UserError(_('No Livechat Channel allows you to send a chat request for website %s.' % website.name))
        self.website_id.channel_id.write({'user_ids': [(4, self.env.user.id)]})
        # Create chat_requests and linked mail_channels
        mail_channel_vals_list = []
        for visitor in self:
            operator = self.env.user
            country = visitor.country_id
            visitor_name = "%s (%s)" % (visitor.display_name, country.name) if country else visitor.display_name
            mail_channel_vals_list.append({
                'channel_partner_ids':  [(4, operator.partner_id.id)],
                'livechat_channel_id': visitor.website_id.channel_id.id,
                'livechat_operator_id': self.env.user.partner_id.id,
                'channel_type': 'livechat',
                'public': 'private',
                'email_send': False,
                'country_id': country.id,
                'anonymous_name': visitor_name,
                'name': ', '.join([visitor_name, operator.livechat_username if operator.livechat_username else operator.name]),
                'livechat_visitor_id': visitor.id,
                'livechat_active': True,
            })
        if mail_channel_vals_list:
            mail_channels = self.env['mail.channel'].create(mail_channel_vals_list)
            # Open empty chatter to allow the operator to start chatting with the visitor.
            mail_channels_info = mail_channels.channel_info('channel_minimize')
            for mail_channel_info in mail_channels_info:
                self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', operator.partner_id.id), mail_channel_info)

    def _handle_website_page_visit(self, response, website_page, visitor_sudo):
        """ Called when the visitor navigates to a website page.
         This checks if there is a chat request for the visitor.
         It will set the livechat session cookie of the visitor with the mail channel information
         to make the usual livechat mechanism do the rest.
         (opening the chatter if a livechat session exist for the visitor)
         This will only happen if the mail channel linked to the chat request already has a message.
         So that empty livechat channel won't pop up at client side. """
        super(WebsiteVisitor, self)._handle_website_page_visit(response, website_page, visitor_sudo)
        visitor_id = visitor_sudo.id or self.env['website.visitor']._get_visitor_from_request().id
        if visitor_id:
            # get active chat_request linked to visitor
            chat_request_channel = self.env['mail.channel'].sudo().search([('livechat_visitor_id', '=', visitor_id), ('livechat_active', '=', True)], order='create_date desc', limit=1)
            if chat_request_channel and chat_request_channel.channel_message_ids:
                livechat_session = json.dumps({
                    "folded": False,
                    "id": chat_request_channel.id,
                    "message_unread_counter": 0,
                    "operator_pid": [
                        chat_request_channel.livechat_operator_id.id,
                        chat_request_channel.livechat_operator_id.display_name
                    ],
                    "name": chat_request_channel.name,
                    "uuid": chat_request_channel.uuid,
                    "type": "chat_request"
                })
                expiration_date = datetime.now() + timedelta(days=100 * 365)  # never expire
                response.set_cookie('im_livechat_session', livechat_session, expires=expiration_date.timestamp())
