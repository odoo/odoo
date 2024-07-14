# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.knowledge.controllers.portal import KnowledgePortal


class KnowledgePortalWebsite(KnowledgePortal):

    def _prepare_knowledge_article_domain(self):
        """For portal users, we want to count the articles to which the user
        has direct access to (articles to which the user has been invited to).
        That excludes published articles, except the ones for which there is a
        member configuration for this user.
        """
        return [('user_has_access', '=', True)]
