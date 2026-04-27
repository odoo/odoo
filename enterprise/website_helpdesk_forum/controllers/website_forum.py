# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route, request
from odoo.osv import expression
from odoo.addons.website_forum.controllers.website_forum import WebsiteForum


class WebsiteForumHelpdesk(WebsiteForum):

    @route('/helpdesk/<model("helpdesk.team"):team>/forums', type='http', auth="public", website=True, sitemap=True)
    def helpdesk_forums(self, team=None):
        if not team or not team.website_forum_ids:
            return request.redirect('/forum')
        domain = expression.AND([request.website.website_domain(), [('id', 'in', team.website_forum_ids.ids)]])
        forums = request.env['forum.forum'].search(domain)
        if len(forums) == 1:
            return request.redirect('/forum/%s' % request.env['ir.http']._slug(forums[0]), code=302)
        return request.render(self.get_template_xml_id(), {
            'forums': forums
        })

    @route('/forum/<model("forum.forum"):forum>/<model("forum.post"):question>/get-forum-data', type='json', auth="user", website=True)
    def create_ticket_and_view(self, forum, question):
        teams = []
        teams_per_forum_read_group = request.env['helpdesk.team']._read_group(
            domain=[('use_website_helpdesk_forum', '=', True), ('website_id', '=', request.website.id)],
            groupby=['website_forum_ids'],
            aggregates=['id:recordset'],
        )
        teams_per_forum_dict = dict(teams_per_forum_read_group)
        # When the forum isn't connected to any team then all the teams should be shown to the users
        if teams_per_forum_dict.get(request.env["forum.forum"]):
            teams = [
                (t.id, t.display_name)
                for teams in teams_per_forum_dict.values()
                for t in teams
            ]
        elif helpdesk_teams := teams_per_forum_dict.get(forum):
            teams = [(t.id, t.display_name) for t in helpdesk_teams]
        else:
            teams = []
        return {
            'post_creator_id': question.create_uid.partner_id.id,
            'post_creator_name': question.create_uid.name,
            'post_description': question.content,
            'post_title': question.display_name,
            'teams': teams,
        }

    def get_template_xml_id(self):
        return "website_helpdesk_forum.forum_all"

    def _prepare_question_template_vals(self, forum, post, question):
        values = super()._prepare_question_template_vals(forum, post, question)
        teams_per_forum_read_group = request.env['helpdesk.team']._read_group(
            [('use_website_helpdesk_forum', '=', True), ('website_id', '=', request.website.id)],
            ['website_forum_ids'],
            ['id:recordset'],
            [('__count', '>', 0)],
        )
        teams_per_forum_dict = dict(teams_per_forum_read_group)
        if teams_per_forum_dict.get(request.env["forum.forum"]):
            values['show_create_ticket'] = True
        else:
            values['show_create_ticket'] = bool(teams_per_forum_dict.get(forum))
        return values
