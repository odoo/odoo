# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _

class HelpdeskTeam(models.Model):
    _inherit = "helpdesk.team"

    show_knowledge_base_slide_channel = fields.Boolean(compute="_compute_show_knowledge_base_slide_channel")
    website_slide_channel_ids = fields.Many2many('slide.channel', string='Courses',
        help="Customers will see only the content from chosen courses in the help center. If you want all courses to be accessible, just leave the field empty. Alternatively, you can make courses private to restrict this feature to internal users.")
    website_top_channels = fields.Many2many('slide.channel', string='Most Popular Courses', compute="_compute_website_top_channels")

    @api.depends('website_slide_channel_ids')
    def _compute_show_knowledge_base_slide_channel(self):
        # 'show_knowledge_base_slide_channel' determines whether the help page of the website displays a link to slide channels.
        # It should be true
        # if the team has slide channels and the user has access to at least one of them,
        # or the team has no slide channel and the user has access to at least one of all.
        accessible_channels = self.env['slide.channel'].search_count([], limit=1)
        accessible_all_teams_channels = set(self.sudo().website_slide_channel_ids.sudo(False)._filter_access_rules_python('read').ids)
        for team in self:
            team_sudo = team.sudo()
            if not team_sudo.use_website_helpdesk_slides:
                team_sudo.sudo().show_knowledge_base_slide_channel = False
                continue
            team_channels = set(team_sudo.sudo().website_slide_channel_ids.ids)
            accessible_team_channels = team_channels & accessible_all_teams_channels
            team_sudo.sudo().show_knowledge_base_slide_channel =\
                bool(team_channels and accessible_team_channels) or bool(not team_channels and accessible_channels)

    def _compute_website_top_channels(self):
        teams_without_channel = self.filtered(lambda team: not team.website_slide_channel_ids)

        def filtered_channels(channel_ids):
            return channel_ids.filtered(
                lambda channel: (
                    channel.website_published and (
                        channel.visibility == 'public'
                        or (channel.visibility == 'members' and channel.is_member)
                        or (channel.visibility == 'connected' and not self.env.user._is_public())
                    )
                )
            )

        if teams_without_channel:
            channels = filtered_channels(
                self.env['slide.channel'].search([('website_published', '=', True)], order='total_views desc')
            )[:5]

        for team in self:
            if team.website_slide_channel_ids:
                team.website_top_channels = filtered_channels(team.website_slide_channel_ids).sorted(key="total_views", reverse=True)[:5]
            else:
                team.website_top_channels = channels

    @api.model
    def _get_knowledge_base_fields(self):
        return super()._get_knowledge_base_fields() + ['show_knowledge_base_slide_channel']

    def _helpcenter_filter_types(self):
        res = super()._helpcenter_filter_types()
        if not self.show_knowledge_base_slide_channel:
            return res

        res['slides'] = _('Courses')
        return res

    def _helpcenter_filter_tags(self, search_type):
        res = super()._helpcenter_filter_tags(search_type)
        if not self.show_knowledge_base_slide_channel or (search_type and search_type != 'slides'):
            return res

        course_tags = self.env['slide.tag'].search([])
        channel_tags = self.env['slide.channel.tag'].search([])
        return res + course_tags.mapped(lambda t: t.name and t.name.lower()) + channel_tags.mapped(lambda t: t.name and t.name.lower())
