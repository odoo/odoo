# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.tools import urls


class LinkTracker(models.Model):
    _inherit = 'link.tracker'

    def action_visit_page_statistics(self):
        return {
            'name': _("Visit Webpage Statistics"),
            'type': 'ir.actions.act_url',
            'url': '%s+' % (self.short_url),
            'target': 'new',
        }

    def _compute_short_url_host(self):
        current_website = self.env['website'].get_current_website()
        base_url = current_website.get_base_url() if current_website == self.env.company.website_id else self.env.company.get_base_url()
        for tracker in self:
            tracker.short_url_host = urls.urljoin(base_url, '/r/')
