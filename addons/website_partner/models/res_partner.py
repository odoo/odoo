# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.addons.website.models.website import slug


class WebsiteResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'website.seo.metadata', 'website.published.mixin']

    website_description = fields.Html('Website Partner Full Description', strip_style=True)
    website_short_description = fields.Text('Website Partner Short Description')

    @api.multi
    def _compute_website_url(self):
        super(WebsiteResPartner, self)._compute_website_url()
        for partner in self:
            partner.website_url = "/partners/%s" % slug(partner)
