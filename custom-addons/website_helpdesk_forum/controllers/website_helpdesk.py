# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website_helpdesk.controllers.main import WebsiteHelpdesk


class WebsiteHelpdeskForum(WebsiteHelpdesk):

    def _format_search_results(self, search_type, records, options):
        if search_type != 'forum_posts_only':
            return super()._format_search_results(search_type, records, options)

        questions = records.mapped('parent_id') | records.filtered(lambda s: not s.parent_id)
        return [{
            'template': 'website_helpdesk_forum.search_result',
            'record': question,
            'score': question.views + question.vote_count + question.favourite_count,
            'url': '/forum/%s/%s' % (slug(question.forum_id), slug(question)),
            'icon': 'fa-comments',
        } for question in questions]
