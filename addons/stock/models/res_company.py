# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _

class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'propagation_minimum_delta': fields.integer('Minimum Delta for Propagation of a Date Change on moves linked together'),
        'internal_transit_location_id': fields.many2one('stock.location', 'Internal Transit Location', help="Technical field used for resupply routes between warehouses that belong to this company", on_delete="restrict"),
    }

    def create_transit_location(self, cr, uid, company_id, company_name, context=None):
        '''Create a transit location with company_id being the given company_id. This is needed
           in case of resuply routes between warehouses belonging to the same company, because
           we don't want to create accounting entries at that time.
        '''
        data_obj = self.pool.get('ir.model.data')
        try:
            parent_loc = data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_locations')[1]
        except:
            parent_loc = False
        location_vals = {
            'name': _('%s: Transit Location') % company_name,
            'usage': 'transit',
            'company_id': company_id,
            'location_id': parent_loc,
        }
        location_id = self.pool.get('stock.location').create(cr, uid, location_vals, context=context)
        self.write(cr, uid, [company_id], {'internal_transit_location_id': location_id}, context=context)

    def create(self, cr, uid, vals, context=None):
        company_id = super(res_company, self).create(cr, uid, vals, context=context)
        self.pool['stock.warehouse'].create(cr, uid, {
            'name': vals['name'],
            'code': vals['name'][:5],
            'company_id': company_id,
        }, context=context)
        self.create_transit_location(cr, uid, company_id, vals['name'], context=context)
        return company_id

    _defaults = {
        'propagation_minimum_delta': 1,
    }
