# -*- coding: utf-8 -*-

from openerp import api, fields, models
from openerp.addons.website.models.website import slug


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'website.seo.metadata', 'website.published.mixin']

    website_private = fields.Boolean(string='Private Profile',
         compute='_compute_private', inverse='_inverse_private', search='_search_private')
    website_description = fields.Html(string='Website Partner Full Description', strip_style=True)
    website_short_description = fields.Text(string='Website Partner Short Description')
    website_published = fields.Boolean(default=True)

    # hack to allow using plain browse record in qweb views
    self_id = fields.Many2one(_name, compute='_compute_self_id')

    @api.depends('website_published')
    def _compute_private(self):
        for partner in self:
            partner.website_private = not partner.website_published

    def _inverse_private(self):
        for partner in self:
            partner.website_published = not partner.website_private

    def _search_private(self, operator, value):
        return [('website_published', '=', not value)]

    @api.multi
    def _compute_self_id(self):
        for partner in self:
            partner.self_id = partner

    @api.multi
    def _website_url(self, field_name, arg):
        website_url = super(WebsiteResPartner, self)._website_url(field_name, arg)
        for partner in self:
            website_url[partner.id] = "/partners/%s" % slug(partner)
        return website_url
