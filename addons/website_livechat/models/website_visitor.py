# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
import json

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import get_lang
from odoo.tools.sql import column_exists, create_column


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    livechat_operator_id = fields.Many2one('res.partner', compute='_compute_livechat_operator_id', store=True, string='Speaking with', index='btree_not_null')
    livechat_operator_name = fields.Char('Operator Name', related="livechat_operator_id.name")
    discuss_channel_ids = fields.One2many('discuss.channel', 'livechat_visitor_id',
                                       string="Visitor's livechat channels", readonly=True)
    session_count = fields.Integer('# Sessions', compute="_compute_session_count")

    def _auto_init(self):
        # Skip the computation of the field `livechat_operator_id` at the module installation
        # We can assume no livechat operator attributed to visitor if it was not installed
        if not column_exists(self.env.cr, "website_visitor", "livechat_operator_id"):
            create_column(self.env.cr, "website_visitor", "livechat_operator_id", "int4")
        return super()._auto_init()

    @api.depends('discuss_channel_ids.livechat_active', 'discuss_channel_ids.livechat_operator_id')
    def _compute_livechat_operator_id(self):
        results = self.env['discuss.channel'].search_read(
            [('livechat_visitor_id', 'in', self.ids), ('livechat_active', '=', True)],
            ['livechat_visitor_id', 'livechat_operator_id']
        )
        visitor_operator_map = {int(result['livechat_visitor_id'][0]): int(result['livechat_operator_id'][0]) for result in results}
        for visitor in self:
            visitor.livechat_operator_id = visitor_operator_map.get(visitor.id, False)

    @api.depends('discuss_channel_ids')
    def _compute_session_count(self):
        sessions = self.env['discuss.channel'].search([('livechat_visitor_id', 'in', self.ids)])
        session_count = dict.fromkeys(self.ids, 0)
        for session in sessions.filtered(lambda c: c.message_ids):
            session_count[session.livechat_visitor_id.id] += 1
        for visitor in self:
            visitor.session_count = session_count.get(visitor.id, 0)

    def action_send_chat_request(self):
        """ Send a chat request to website_visitor(s).
        This creates a chat_request and a discuss_channel with livechat active flag.
        But for the visitor to get the chat request, the operator still has to speak to the visitor.
        The visitor will receive the chat request the next time he navigates to a website page.
        (see _handle_webpage_dispatch for next step)"""
        # check if visitor is available
        unavailable_visitors_count = self.env['discuss.channel'].search_count([('livechat_visitor_id', 'in', self.ids), ('livechat_active', '=', True)])
        if unavailable_visitors_count:
            raise UserError(_('Recipients are not available. Please refresh the page to get latest visitors status.'))
        # check if user is available as operator
        for website in self.mapped('website_id'):
            if not website.channel_id:
                raise UserError(_('No Livechat Channel allows you to send a chat request for website %s.', website.name))
        self.website_id.channel_id.write({'user_ids': [(4, self.env.user.id)]})
        # Create chat_requests and linked discuss_channels
        discuss_channel_vals_list = []
        for visitor in self:
            operator = self.env.user
            country = visitor.country_id
            visitor_name = "Visitor #%d (%s)" % (visitor.id, country.name) if country else f"Visitor #{visitor.id}"
            members_to_add = [Command.link(operator.partner_id.id)]
            if visitor.partner_id:
                members_to_add.append(Command.link(visitor.partner_id.id))
            discuss_channel_vals_list.append({
                'channel_partner_ids': members_to_add,
                'livechat_channel_id': visitor.website_id.channel_id.id,
                'livechat_operator_id': self.env.user.partner_id.id,
                'channel_type': 'livechat',
                'country_id': country.id,
                'anonymous_name': visitor_name,
                'name': ', '.join([visitor_name, operator.livechat_username if operator.livechat_username else operator.name]),
                'livechat_visitor_id': visitor.id,
                'livechat_active': True,
            })
        discuss_channels = self.env['discuss.channel'].create(discuss_channel_vals_list)
        if not discuss_channels:
            return
        for channel in discuss_channels:
            if not channel.livechat_visitor_id.partner_id:
                # sudo: mail.guest - creating a guest in a dedicated channel created from livechat
                guest = self.env["mail.guest"].sudo().create(
                    {
                        "country_id": country.id,
                        "lang": get_lang(channel.env).code,
                        "name": _("Visitor #%d", channel.livechat_visitor_id.id),
                        "timezone": visitor.timezone,
                    }
                )
                channel.add_members(guest_ids=guest.ids, post_joined_message=False)
        # Open empty chatter to allow the operator to start chatting with the visitor.
        channel_members = self.env['discuss.channel.member'].sudo().search([
            ('partner_id', '=', self.env.user.partner_id.id),
            ('channel_id', 'in', discuss_channels.ids),
        ])
        channel_members.write({
            'fold_state': 'open',
            'is_minimized': True,
        })
        discuss_channels_info = discuss_channels._channel_info()
        notifications = []
        for discuss_channel_info in discuss_channels_info:
            notifications.append([operator.partner_id, 'website_livechat.send_chat_request', discuss_channel_info])
        self.env['bus.bus']._sendmany(notifications)

    def _merge_visitor(self, target):
        """ Copy sessions of the secondary visitors to the main partner visitor. """
        target.discuss_channel_ids |= self.discuss_channel_ids
        self.discuss_channel_ids.channel_partner_ids = [
            (3, self.env.ref('base.public_partner').id),
            (4, target.partner_id.id),
        ]
        return super()._merge_visitor(target)

    def _upsert_visitor(self, access_token, force_track_values=None):
        visitor_id, upsert = super()._upsert_visitor(access_token, force_track_values=force_track_values)
        if upsert == 'inserted':
            visitor_sudo = self.sudo().browse(visitor_id)
            if discuss_channel_uuid := request.httprequest.cookies.get("im_livechat_uuid"):
                discuss_channel = request.env["discuss.channel"].sudo().search([("uuid", "=", discuss_channel_uuid)])
                discuss_channel.write({
                    'livechat_visitor_id': visitor_sudo.id,
                    'anonymous_name': "Visitor #%d (%s)" % (visitor_sudo.id, visitor_sudo.country_id.name) if visitor_sudo.country_id else f"Visitor #{visitor_sudo.id}"
                })
        return visitor_id, upsert
