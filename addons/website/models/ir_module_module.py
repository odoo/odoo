# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class Module(models.Model):
    _inherit = 'ir.module.module'

    def _check(self):
        super()._check()
        View = self.env['ir.ui.view']
        website_views_to_adapt = getattr(self.pool, 'website_views_to_adapt', [])
        if website_views_to_adapt:
            for view_replay in website_views_to_adapt:
                cow_view = View.browse(view_replay[0])
                View._load_records_write_on_cow(cow_view, view_replay[1], view_replay[2])
            self.pool.website_views_to_adapt.clear()
