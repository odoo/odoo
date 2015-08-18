# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.addons.website.models.website import slug


class WebsiteResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'website.seo.metadata', 'website.published.mixin']

    website_private = fields.Boolean(string='Private Profile', compute='_compute_private',
                                            inverse='_set_private', search='_search_private')
    website_description = fields.Html('Website Partner Full Description', strip_style=True)
    website_short_description = fields.Text('Website Partner Short Description')
    # hack to allow using plain browse record in qweb views
    self = fields.Many2one(comodel_name=_name, compute='_compute_get_ids')

    @api.one
    def _compute_get_ids(self):
        self.self = self.id

    @api.multi
    def _compute_private(self):
        for partner in self:
            partner.website_private = not partner.website_published

    def _set_private(self):
        for partner in self:
            partner.website_published = not partner.website_private

    def _search_private(self, operator, value):
        return [('website_published', '=', not value)]

    @api.multi
    def _website_url(self, field_name, arg):
        res = super(WebsiteResPartner, self)._website_url(field_name, arg)
        for partner in self:
            res[partner.id] = "/partners/%s" % slug(partner)
        return res
