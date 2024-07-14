# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_helpdesk.controllers.main import WebsiteHelpdesk
from odoo.addons.website_knowledge.controllers.main import KnowledgeWebsiteController

from odoo.http import request, route
from odoo.tools import config


class WebsiteHelpdeskKnowledge(WebsiteHelpdesk):

    def _format_search_results(self, search_type, records, options):
        if search_type != 'knowledge':
            return super()._format_search_results(search_type, records, options)
        return [{
            'template': 'website_helpdesk_knowledge.search_result',
            'record': article,
            'url': article.website_url,
            'icon': 'fa-book',
        } for article in records]

    def _get_knowledge_base_values(self, team):
        return {
            **super()._get_knowledge_base_values(team),
            'target': '_self' if (config['test_enable'] or config['test_file']) else '_blank',
        }

class WebsiteKnowledgeHelpdesk(KnowledgeWebsiteController):

    @route('/helpdesk/<model("helpdesk.team"):team>/knowledge/home', type='http', auth='public', website=True, sitemap=False)
    def access_helpdesk_knowledge_home(self, team=None, **kwargs):
        if not team or not team.website_article_id:
            return request.redirect('/knowledge/home')
        article = team.website_article_id
        return self.redirect_to_article(article_id=article.id)
