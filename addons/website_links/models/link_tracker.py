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
        if not self.env.website:
            return super()._compute_short_url_host()
<<<<<<< e025434a8dbb14a3c83251f18f6c7a926a05954e
        base_url = self.env.website.get_base_url() if self.env.website == self.env.company.website_id else self.env.company.get_base_url()
||||||| 6a57ec66ae0a587974dc5f175fe97d94060a0e88
        base_url = current_website.get_base_url() if current_website == self.env.company.website_id else self.env.company.get_base_url()
=======
        base_url = current_website.get_base_url() if current_website.company_id == self.env.company else self.env.company.get_base_url()
>>>>>>> 0214ed75d08f04f07b4bdf5ceefde8a32d03fde6
        for tracker in self:
            tracker.short_url_host = urls.urljoin(base_url, '/r/')
