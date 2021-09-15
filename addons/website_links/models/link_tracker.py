# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _

from werkzeug import urls


class LinkTracker(models.Model):
    _inherit = ['link.tracker']

    def action_visit_page_statistics(self):
        return {
            'name': _("Visit Webpage Statistics"),
            'type': 'ir.actions.act_url',
            'url': '%s+' % (self.short_url),
            'target': 'new',
        }

    def _compute_short_url_host(self):
        for tracker in self:
            base_url = self.env['website'].get_current_website().get_base_url()
            tracker.short_url_host = urls.url_join(base_url, '/r/')
