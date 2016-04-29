# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class mrp_routing(osv.osv):
    """
    For specifying the routings of Work Centers.
    """
    _name = 'mrp.routing'
    _description = 'Routings'
    _columns = {
        'name': fields.char('Name', required=True),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the routing without removing it."),
        'code': fields.char('Code', size=8),

        'note': fields.text('Description'),
        'workcenter_lines': fields.one2many('mrp.routing.workcenter', 'routing_id', 'Work Centers', copy=True),

        'location_id': fields.many2one('stock.location', 'Production Location',
            help="Keep empty if you produce at the location where the finished products are needed." \
                "Set a location if you produce at a fixed location. This can be a partner location " \
                "if you subcontract the manufacturing operations."
        ),
        'company_id': fields.many2one('res.company', 'Company'),
    }
    _defaults = {
        'active': lambda *a: 1,
        'company_id': lambda self, cr, uid, context: self.pool.get('res.company')._company_default_get(cr, uid, 'mrp.routing', context=context)
    }

class mrp_routing_workcenter(osv.osv):
    """
    Defines working cycles and hours of a Work Center using routings.
    """
    _name = 'mrp.routing.workcenter'
    _description = 'Work Center Usage'
    _order = 'sequence, id'
    _columns = {
        'workcenter_id': fields.many2one('mrp.workcenter', 'Work Center', required=True),
        'name': fields.char('Name', required=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of routing Work Centers."),
        'cycle_nbr': fields.float('Number of Cycles', required=True,
            help="Number of iterations this work center has to do in the specified operation of the routing."),
        'hour_nbr': fields.float('Number of Hours', required=True, help="Time in hours for this Work Center to achieve the operation of the specified routing."),
        'routing_id': fields.many2one('mrp.routing', 'Parent Routing', select=True, ondelete='cascade',
             help="Routings indicates all the Work Centers used, for how long and/or cycles." \
                "If Routings is set then,the third tab of a production order (Work Centers) will be automatically pre-completed."),
        'note': fields.text('Description'),
        'company_id': fields.related('routing_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
    }
    _defaults = {
        'cycle_nbr': lambda *a: 1.0,
        'hour_nbr': lambda *a: 0.0,
        'sequence': 100,
    }