# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _
from odoo.exceptions import UserError
import json


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    livechat_request_ids = fields.One2many('im_livechat.request', 'visitor_id', string='Pending Chat Request')
    livechat_operator_id = fields.Many2one('res.partner', compute='_compute_livechat_operator_id', store=True,
                                           string='Speaking with', search='_search_livechat_operator_id')
    mail_channel_ids = fields.One2many('mail.channel', 'livechat_visitor_id',
                                       string="Visitor's livechat channels", readonly=True)

    @api.depends('mail_channel_ids.livechat_active', 'mail_channel_ids.livechat_operator_id')
    def _compute_livechat_operator_id(self):
        sql = """SELECT livechat_visitor_id, livechat_operator_id
                    FROM mail_channel
                    WHERE livechat_visitor_id in %s
                    AND livechat_active = true"""
        self.env.cr.execute(sql, [tuple(self.ids)])
        results = self.env.cr.dictfetchall()
        operator_ids = self.env['res.partner'].browse([int(result['livechat_operator_id']) for result in results])

        for visitor in self:
            for result in results:
                if result['livechat_visitor_id'] == visitor.id:
                    visitor.livechat_operator_id = operator_ids.filtered(lambda o: o.id == int(result['livechat_operator_id']))
                    break

    def action_send_chat_request(self):
        """ Send a chat request to website_visitor(s).
        This creates a chat_request and a mail_channel with livechat active flag.
        But for the visitor to get the chat request, the operator still has to speak to the visitor.
        The visitor will receive the chat request the next time he navigates to a website page.
        (see _handle_visitor_response for next step)"""
        # check if visitor is available
        unavailable_visitors_count = self.env['mail.channel'].search_count([('livechat_visitor_id', 'in', self.ids), ('livechat_active', '=', True)])
        if unavailable_visitors_count:
            if len(self) == 1:
                raise UserError('This user is not available. Please refresh the page to get latest visitor status.')
            else:
                raise UserError('At least one user is not available. Please refresh the page to get latest visitors status.')
        # check if user is available as operator
        for website in self.website_id:
            if not website.channel_id:
                raise UserError(_('No Livechat Channel allows you to send a chat request for website %s.' % website.name))
        website_livechat_channels = self.website_id.channel_id
        website_livechat_channels.write({
            'user_ids': [(4, self.env.user.id)]
        })
        # Create chat_requests and linked mail_channels
        mail_channel_vals_list = []
        for visitor in self:
            visitor_name = visitor.name
            operator = self.env.user
            country = visitor.country_id
            if country:
                visitor_name = _("%s (%s)") % (visitor_name, country.name)
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
                'livechat_request_ids': [(0, 0, {
                    'visitor_id': visitor.id,
                })],
                'livechat_active': True,
            })
        if mail_channel_vals_list:
            mail_channels = self.env['mail.channel'].create(mail_channel_vals_list)
            # Open empty chatter to allow the operator to start chatting with the visitor.
            mail_channels_info = mail_channels.channel_info('channel_minimize')
            for mail_channel_info in mail_channels_info:
                self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', operator.partner_id.id), mail_channel_info)

    def _handle_visitor_response(self, response):
        """ Called when the visitor navigates to a website page.
         This checks if there is a chat request for the visitor.
         It will se the livechat session cookie of the visitor with the mail channel information
         to make the usual livechat mechanism do the rest.
         (opening the chatter if a livechat session exist for the visitor)
         This will only happen if the mail channel linked to the chat request already has a message.
         So that empty livechat channel won't pop up at client side. """
        response = super(WebsiteVisitor, self)._handle_visitor_response(response)
        visitor_id = self._decode()
        if visitor_id:
            # get active chat_request linked to visitor
            chat_request = self.env['im_livechat.request'].sudo().search([('visitor_id', '=', visitor_id)], limit=1)
            if chat_request and chat_request.mail_channel_id.channel_message_ids:
                mail_channel = chat_request.mail_channel_id
                livechat_session = json.dumps({
                    "folded": False,
                    "id": mail_channel.id,
                    "message_unread_counter": 0,
                    "operator_pid": [
                        mail_channel.livechat_operator_id.id,
                        mail_channel.livechat_operator_id.display_name
                    ],
                    "name": mail_channel.name,
                    "uuid": mail_channel.uuid,
                    "type": "chat_request"
                })
                response.set_cookie('im_livechat_session', livechat_session)
        return response
