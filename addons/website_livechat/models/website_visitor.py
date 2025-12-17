# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, Command, fields, models, _
from odoo.addons.mail.tools.discuss import Store
from odoo.exceptions import UserError
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

    @api.depends('discuss_channel_ids.livechat_end_dt', 'discuss_channel_ids.livechat_operator_id')
    def _compute_livechat_operator_id(self):
        results = self.env["discuss.channel"].search_read(
            [("livechat_visitor_id", "in", self.ids), ("livechat_end_dt", "=", False)],
            ["livechat_visitor_id", "livechat_operator_id"],
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
        unavailable_visitors_count = self.env["discuss.channel"].search_count(
            [("livechat_visitor_id", "in", self.ids), ("livechat_end_dt", "=", False)]
        )
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
            members_to_add = [
                Command.create(
                    {"partner_id": operator.partner_id.id, "livechat_member_type": "agent"}
                )
            ]
            if visitor.partner_id:
                members_to_add.append(
                    Command.create(
                        {"partner_id": visitor.partner_id.id, "livechat_member_type": "visitor"}
                    )
                )
            else:
                # sudo: mail.guest - creating a guest in a dedicated channel created from livechat
                guest = self.env["mail.guest"].sudo().create(
                    {
                        "country_id": country.id,
                        "lang": get_lang(self.env).code,
                        "name": _("Visitor #%d", visitor.id),
                        "timezone": visitor.timezone,
                    }
                )
                members_to_add.append(
                    Command.create({"guest_id": guest.id, "livechat_member_type": "visitor"})
                )
            discuss_channel_vals_list.append({
                "is_pending_chat_request": True,
                'livechat_channel_id': visitor.website_id.channel_id.id,
                'livechat_operator_id': operator.partner_id.id,
                "channel_member_ids": members_to_add,
                'channel_type': 'livechat',
                'country_id': country.id,
                'name': ', '.join([visitor_name, operator.livechat_username if operator.livechat_username else operator.name]),
                'livechat_visitor_id': visitor.id,
            })
        discuss_channels = self.env['discuss.channel'].create(discuss_channel_vals_list)
        # Open empty channel to allow the agent to start chatting with the visitor
        return discuss_channels.open_chat_window_action()

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
            if guest := self.env["mail.guest"]._get_guest_from_context():
                # sudo: mail.guest - guest can access their own channels and link them to newly created visitor.
                guest_livechats = guest.sudo().channel_ids.filtered(lambda c: c.channel_type == "livechat")
                guest_livechats.livechat_visitor_id = visitor_sudo.id
                guest_livechats.country_id = visitor_sudo.country_id
        return visitor_id, upsert

    def _store_visitor_history_fields(self, res: Store.FieldList):
        if not self:
            return
        self.env.cr.execute(
            """
                SELECT website_visitor.id AS visitor_id,
                       ARRAY_AGG(website_track.id ORDER BY website_track.visit_datetime DESC, website_track.id DESC) AS track_ids
                  FROM website_visitor
          JOIN LATERAL
                  (
                      SELECT website_track.id,
                             website_track.visit_datetime
                        FROM website_track
                       WHERE website_track.visitor_id = website_visitor.id
                         AND website_track.page_id IS NOT NULL
                    ORDER BY website_track.visit_datetime DESC, website_track.id DESC
                       LIMIT 3
                  ) AS website_track ON TRUE
                 WHERE website_visitor.id IN %s
              GROUP BY website_visitor.id;
            """,
            [tuple(self.ids)],
        )
        results = dict(self.env.cr.fetchall())
        all_track_ids = [track_id for track_list in results.values() for track_id in track_list]
        tracks_by_visitor = defaultdict(self.env["website.track"].browse)
        for visitor_id, track_ids in results.items():
            tracks_by_visitor[self.browse(visitor_id)] = (
                self.env["website.track"].browse(track_ids).with_prefetch(all_track_ids)
            )
        # sudo: website.track - reading the history of accessible visitor is acceptable
        res.many(
            "last_track_ids",
            lambda res: (
                res.one("page_id", ["name"]),
                res.attr("visit_datetime"),
            ),
            value=lambda v: tracks_by_visitor[v].sudo(),
        )
