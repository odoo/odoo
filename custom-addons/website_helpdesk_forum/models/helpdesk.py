# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HelpdeskTeam(models.Model):
    _inherit = "helpdesk.team"

    show_knowledge_base_forum = fields.Boolean(compute="_compute_show_knowledge_base_forum")
    website_forum_ids = fields.Many2many('forum.forum', string='Forums', help="In the help center, customers will only be able to see posts from the selected forums.")
    top_forum_posts = fields.Many2many('forum.post', string='Top Posts', help="These are the top posts in the forums associated with this helpdesk team", compute="_compute_top_forum_posts")

    @api.depends('website_forum_ids')
    def _compute_show_knowledge_base_forum(self):
        # 'show_knowledge_base_forum' determines whether the help page of the website displays a link to forums.
        # It should be true
        # if the team has forums and the user has access to at least one of them,
        # or the team has no forum and the user has access to at least one of all.
        accessible_forums = self.env['forum.forum'].search_count([], limit=1)
        accessible_all_teams_forums = set(self.sudo().website_forum_ids.sudo(False)._filter_access_rules_python('read').ids)
        for team in self:
            team_sudo = team.sudo()
            if not team_sudo.use_website_helpdesk_forum:
                team_sudo.sudo().show_knowledge_base_forum = False
                continue
            team_forums = set(team_sudo.sudo().website_forum_ids.ids)
            accessible_team_forums = team_forums & accessible_all_teams_forums
            team_sudo.sudo().show_knowledge_base_forum =\
                bool(team_forums and accessible_team_forums) or bool(not team_forums and accessible_forums)

    def _ensure_help_center_is_activated(self):
        self.ensure_one()
        if not self.show_knowledge_base_forum:
            raise UserError(_('Help Center not active for this team.'))
        return True

    @api.model
    def _get_knowledge_base_fields(self):
        return super()._get_knowledge_base_fields() + ['show_knowledge_base_forum']

    def _helpcenter_filter_types(self):
        res = super()._helpcenter_filter_types()
        if not self.show_knowledge_base_forum:
            return res

        res['forum_posts_only'] = _('Forum Posts')
        return res

    def _helpcenter_filter_tags(self, search_type):
        res = super()._helpcenter_filter_tags(search_type)
        if not self.show_knowledge_base_forum or (search_type and search_type != 'forum_posts_only'):
            return res

        tags = self.env['forum.tag'].search([
            ('posts_count', '>', 0),
        ], order='posts_count desc', limit=20)
        return res + tags.mapped(lambda t: t.name and t.name.lower())

    def _compute_top_forum_posts(self):
        for team in self:
            search_domain = [('parent_id', '=', False)]
            if team.website_forum_ids:
                search_domain.append(('forum_id', 'in', team.website_forum_ids.ids))

            team.top_forum_posts = self.env['forum.post'].search(search_domain, order='vote_count desc, last_activity_date desc', limit=5)

class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    forum_post_ids = fields.Many2many('forum.post', string="Forum Posts", copy=False)
    forum_post_count = fields.Integer(compute='_compute_forum_post_count')
    use_website_helpdesk_forum = fields.Boolean(related='team_id.use_website_helpdesk_forum', string='Help Center Active', readonly=True)
    can_share_forum = fields.Boolean(compute='_compute_can_share_forum')

    @api.depends_context('uid')
    @api.depends('use_website_helpdesk_forum')
    def _compute_can_share_forum(self):
        forum_count = self.env['forum.forum'].search_count([])
        for ticket in self:
            ticket.can_share_forum = ticket.use_website_helpdesk_forum and forum_count

    @api.depends_context('uid')
    @api.depends('forum_post_ids')
    def _compute_forum_post_count(self):
        rg = self.env['forum.post']._read_group([('can_view', '=', True), ('id', 'in', self.forum_post_ids.ids)], ['ticket_id'], ['__count'])
        posts_count = {ticket.id: count for ticket, count in rg}
        for ticket in self:
            ticket.forum_post_count = posts_count.get(ticket.id, 0)

    def action_share_ticket_on_forum(self):
        self.ensure_one()
        self.team_id._ensure_help_center_is_activated()
        return self.env['ir.actions.actions']._for_xml_id('website_helpdesk_forum.helpdesk_ticket_select_forum_wizard_action')

    def action_open_forum_posts(self, edit=False):
        self.ensure_one()
        self.team_id._ensure_help_center_is_activated()
        if not self.forum_post_ids:
            raise UserError(_('No posts associated to this ticket.'))

        if len(self.forum_post_ids) > 1:
            action = self.env['ir.actions.actions']._for_xml_id('website_forum.forum_post_action_forum_main')
            action['domain'] = [('id', 'in', self.forum_post_ids.ids)]
            return action

        return self.forum_post_ids.open_forum_post(edit)
