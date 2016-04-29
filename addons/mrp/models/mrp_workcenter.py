# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv

#----------------------------------------------------------
# Work Centers
#----------------------------------------------------------
# capacity_hour : capacity per hour. default: 1.0.
#          Eg: If 5 concurrent operations at one time: capacity = 5 (because 5 employees)
# unit_per_cycle : how many units are produced for one cycle


class mrp_workcenter(osv.osv):
    _name = 'mrp.workcenter'
    _description = 'Work Center'
    _inherits = {'resource.resource':"resource_id"}
    _columns = {
        'active': fields.boolean('Active'),
        'note': fields.text('Description', help="Description of the Work Center. Explain here what's a cycle according to this Work Center."),
        'capacity_per_cycle': fields.float('Capacity per Cycle', help="Number of operations this Work Center can do in parallel. If this Work Center represents a team of 5 workers, the capacity per cycle is 5."),
        'time_cycle': fields.float('Time for 1 cycle (hour)', help="Time in hours for doing one cycle."),
        'time_start': fields.float('Time before prod.', help="Time in hours for the setup."),
        'time_stop': fields.float('Time after prod.', help="Time in hours for the cleaning."),
        'costs_hour': fields.float('Cost per hour', help="Specify Cost of Work Center per hour."),
        'costs_hour_account_id': fields.many2one('account.analytic.account', 'Hour Account',
            help="Fill this only if you want automatic analytic accounting entries on production orders."),
        'costs_cycle': fields.float('Cost per cycle', help="Specify Cost of Work Center per cycle."),
        'costs_cycle_account_id': fields.many2one('account.analytic.account', 'Cycle Account',
            help="Fill this only if you want automatic analytic accounting entries on production orders."),
        'costs_general_account_id': fields.many2one('account.account', 'General Account', domain=[('deprecated', '=', False)]),
        'resource_id': fields.many2one('resource.resource','Resource', ondelete='cascade', required=True),
        'product_id': fields.many2one('product.product','Work Center Product', help="Fill this product to easily track your production costs in the analytic accounting."),
    }
    _defaults = {
        'active': True,
        'capacity_per_cycle': 1.0,
        'resource_type': 'material',
     }

    def on_change_product_cost(self, cr, uid, ids, product_id, context=None):
        value = {}

        if product_id:
            cost = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            value = {'costs_hour': cost.standard_price}
        return {'value': value}

    def _check_capacity_per_cycle(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.capacity_per_cycle <= 0.0:
                return False
        return True

    _constraints = [
        (_check_capacity_per_cycle, 'The capacity per cycle must be strictly positive.', ['capacity_per_cycle']),
    ]