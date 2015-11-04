# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class WebsitePricelist(models.Model):
    _name = 'website_pricelist'
    _description = 'Website Pricelist'

    website_id = fields.Many2one('website', string="Website", required=True)
    selectable = fields.Boolean(help="Allow the end user to choose this price list")
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    country_group_ids = fields.Many2many('res.country.group', 'res_country_group_website_pricelist_rel',
                                         'website_pricelist_id', 'res_country_group_id', string='Country Groups')

    def clear_cache(self):
        # website._get_pl() is cached to avoid to recompute at each request the
        # list of available pricelists. So, we need to invalidate the cache when
        # we change the config of website price list to force to recompute.
        website = self.env['website']
        website._get_pl.clear_cache(website)

    @api.multi
    def name_get(self):
        return [(website_pl.id, _("Website Pricelist for %s") % website_pl.pricelist_id.name) for website_pl in self]

    @api.model
    def create(self, data):
        res = super(WebsitePricelist, self).create(data)
        self.clear_cache()
        return res

    @api.multi
    def write(self, data):
        res = super(WebsitePricelist, self).write(data)
        self.clear_cache()
        return res

    @api.multi
    def unlink(self):
        res = super(WebsitePricelist, self).unlink()
        self.clear_cache()
        return res
