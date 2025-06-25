# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class WebsiteResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'website.seo.metadata']

    website_description = fields.Html('Website Partner Full Description', strip_style=True, sanitize_overridable=True, translate=html_translate)
    website_short_description = fields.Text('Website Partner Short Description', translate=True)

    def _compute_website_url(self):
        super(WebsiteResPartner, self)._compute_website_url()
        for partner in self:
            partner.website_url = "/partners/%s" % self.env['ir.http']._slug(partner)
