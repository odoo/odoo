# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.addons.website.models.website import slug


class WebsiteResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'website.seo.metadata', 'website.published.mixin']

    website_description = fields.Html('Website Partner Full Description', strip_style=True)
    website_short_description = fields.Text('Website Partner Short Description')
    # hack to allow using plain browse record in qweb views
    self = fields.Many2one(comodel_name=_name, compute='_compute_get_ids')

    @api.one
    def _compute_get_ids(self):
        self.self = self.id

    @api.multi
    def _website_url(self, field_name, arg):
        res = super(WebsiteResPartner, self)._website_url(field_name, arg)
        for partner in self:
            res[partner.id] = "/partners/%s" % slug(partner)
        return res
