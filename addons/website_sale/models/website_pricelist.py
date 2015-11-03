# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.osv import osv, fields
from odoo import _


class website_pricelist(osv.Model):
    _name = 'website_pricelist'
    _description = 'Website Pricelist'

    def _get_display_name(self, cr, uid, ids, name, arg, context=None):
        result = {}
        for o in self.browse(cr, uid, ids, context=context):
            result[o.id] = _("Website Pricelist for %s") % o.pricelist_id.name
        return result

    _columns = {
        'name': fields.function(_get_display_name, string='Pricelist Name', type="char"),
        'website_id': fields.many2one('website', string="Website", required=True),
        'selectable': fields.boolean('Selectable', help="Allow the end user to choose this price list"),
        'pricelist_id': fields.many2one('product.pricelist', string='Pricelist'),
        'country_group_ids': fields.many2many('res.country.group', 'res_country_group_website_pricelist_rel',
                                              'website_pricelist_id', 'res_country_group_id', string='Country Groups'),
    }

    def clear_cache(self):
        # website._get_pl() is cached to avoid to recompute at each request the
        # list of available pricelists. So, we need to invalidate the cache when
        # we change the config of website price list to force to recompute.
        website = self.pool['website']
        website._get_pl.clear_cache(website)

    def create(self, cr, uid, data, context=None):
        res = super(website_pricelist, self).create(cr, uid, data, context=context)
        self.clear_cache()
        return res

    def write(self, cr, uid, ids, data, context=None):
        res = super(website_pricelist, self).write(cr, uid, ids, data, context=context)
        self.clear_cache()
        return res

    def unlink(self, cr, uid, ids, context=None):
        res = super(website_pricelist, self).unlink(cr, uid, ids, context=context)
        self.clear_cache()
        return res
