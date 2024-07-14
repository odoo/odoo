# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _

class HelpdeskTeam(models.Model):
    _inherit = "helpdesk.team"

    show_knowledge_base_article = fields.Boolean(compute="_compute_show_knowledge_base_article")
    website_article_id = fields.Many2one('knowledge.article', string='Article',
        help="Article on which customers will land by default, and to which the search will be restricted.")
    website_latest_articles = fields.Many2many('knowledge.article', string="Latest Articles", compute="_compute_latest_articles")

    @api.depends('website_article_id')
    def _compute_show_knowledge_base_article(self):
        # 'show_knowledge_base_article' determines whether the help page of the website displays a link to articles.
        accessible_articles = self.env['knowledge.article'].search_count([
            ('website_published', '=', True),
            ('name', '!=', False),
            ('is_template', '=', False),
        ], limit=1) > 0
        for team_sudo in self.sudo():
            team_sudo.show_knowledge_base_article = team_sudo.use_website_helpdesk_knowledge and accessible_articles

    def _compute_latest_articles(self):
        latest_articles = self.env['knowledge.article'].search([
            ('website_published', '=', True),
            ('name', '!=', False),
            ('is_template', '=', False)
        ], limit=5, order='favorite_count desc, write_date desc')
        for team in self:
            team.website_latest_articles = latest_articles

    @api.model
    def _get_knowledge_base_fields(self):
        return super()._get_knowledge_base_fields() + ['show_knowledge_base_article']

    def _helpcenter_filter_types(self):
        res = super()._helpcenter_filter_types()
        if not self.show_knowledge_base_article:
            return res

        res['knowledge'] = _('Articles')
        return res
