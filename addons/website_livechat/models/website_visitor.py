# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
import json

from odoo import models, api, fields, _
from odoo.exceptions import UserError
from odoo.http import request


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
        sessions = self.env['mail.channel'].search([('livechat_visitor_id', 'in', self.ids)])
        session_count = dict.fromkeys(self.ids, 0)
        for session in sessions.filtered(lambda c: c.message_ids):
            session_count[session.livechat_visitor_id.id] += 1
        for visitor in self:
            visitor.session_count = session_count.get(visitor.id, 0)

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
                raise UserError(_('No Livechat Channel allows you to send a chat request for website %s.', website.name))
        self.website_id.channel_id.write({'user_ids': [(4, self.env.user.id)]})
        # Create chat_requests and linked mail_channels
        mail_channel_vals_list = []
        for visitor in self:
            operator = self.env.user
            country = visitor.country_id
            visitor_name = "%s (%s)" % (visitor.display_name, country.name) if country else visitor.display_name
            channel_partner_to_add = [(4, operator.partner_id.id)]
            if visitor.partner_id:
                channel_partner_to_add.append((4, visitor.partner_id.id))
            else:
                channel_partner_to_add.append((4, self.env.ref('base.public_partner').id))
            mail_channel_vals_list.append({
                'channel_partner_ids': channel_partner_to_add,
                'livechat_channel_id': visitor.website_id.channel_id.id,
                'livechat_operator_id': self.env.user.partner_id.id,
                'channel_type': 'livechat',
                'public': 'private',
                'country_id': country.id,
                'anonymous_name': visitor_name,
                'name': ', '.join([visitor_name, operator.livechat_username if operator.livechat_username else operator.name]),
                'livechat_visitor_id': visitor.id,
                'livechat_active': True,
            })
        if mail_channel_vals_list:
            mail_channels = self.env['mail.channel'].create(mail_channel_vals_list)
            # Open empty chatter to allow the operator to start chatting with the visitor.
            channel_members = self.env['mail.channel.partner'].sudo().search([
                ('partner_id', '=', self.env.user.partner_id.id),
                ('channel_id', 'in', mail_channels.ids),
            ])
            channel_members.write({
                'fold_state': 'open',
                'is_minimized': True,
            })
            mail_channels_info = mail_channels.channel_info()
            notifications = []
            for mail_channel_info in mail_channels_info:
                notifications.append([operator.partner_id, 'website_livechat.send_chat_request', mail_channel_info])
            self.env['bus.bus']._sendmany(notifications)

    def _link_to_visitor(self, target, keep_unique=True):
        """ Copy sessions of the secondary visitors to the main partner visitor. """
        if target.partner_id:
            target.mail_channel_ids |= self.mail_channel_ids
        super(WebsiteVisitor, self)._link_to_visitor(target, keep_unique=keep_unique)

    def _link_to_partner(self, partner, update_values=None):
        """ Adapt partner in members of related livechats """
        if partner:
            self.mail_channel_ids.channel_partner_ids = [
                (3, self.env.ref('base.public_partner').id),
                (4, partner.id),
            ]
        super(WebsiteVisitor, self)._link_to_partner(partner, update_values=update_values)

    def _create_visitor(self):
        visitor = super(WebsiteVisitor, self)._create_visitor()
        mail_channel_uuid = json.loads(request.httprequest.cookies.get('im_livechat_session', '{}')).get('uuid')
        if mail_channel_uuid:
            mail_channel = request.env["mail.channel"].sudo().search([("uuid", "=", mail_channel_uuid)])
            mail_channel.write({
                'livechat_visitor_id': visitor.id,
                'anonymous_name': visitor.display_name
            })
        return visitor
