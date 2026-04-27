from odoo.http import request
from odoo.addons.portal.controllers import portal


class KnowledgePortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'knowledge_count' in counters:
            values['knowledge_count'] = request.env['knowledge.article'].search_count(self._prepare_knowledge_article_domain())
        return values

    def _prepare_knowledge_article_domain(self):
        """Generate the domain for the portal's articles"""
        return []
