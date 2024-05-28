# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from werkzeug.urls import url_join

from odoo import api, models


class LinkTracker(models.Model):
    _inherit = ['link.tracker']

    @api.depends('mass_mailing_id.website_id')
    def _compute_short_url_host(self):
        tracker_with_website_mass_mailing = self.filtered(lambda t: t.mass_mailing_id.website_id)
        super(LinkTracker, self - tracker_with_website_mass_mailing)._compute_short_url_host()
        for tracker in tracker_with_website_mass_mailing:
            tracker.short_url_host = url_join(tracker.mass_mailing_id.website_id.get_base_url(), '/r/')
