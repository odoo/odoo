# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.osv import osv, fields


class CountryGroup(osv.Model):
    _inherit = 'res.country.group'
    _columns = {
        'website_pricelist_ids': fields.many2many('website_pricelist', 'res_country_group_website_pricelist_rel',
                                                  'res_country_group_id', 'website_pricelist_id', string='Website Price Lists'),
    }
