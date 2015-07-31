# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models


class MrpRouting(models.Model):
    """
    For specifying the routings of Work Centers.
    """
    _name = 'mrp.routing'
    _description = 'Work Order Operations'
    name = fields.Char(required=True)
    active = fields.Boolean(default=True, help="If the active field is set to False, it will allow you to hide the routing without removing it.")
    code = fields.Char(size=8)
    note = fields.Text(string='Description')
    workcenter_lines = fields.One2many('mrp.routing.workcenter', 'routing_id', string='Work Centers', copy=True)

    location_id = fields.Many2one('stock.location', string='Production Location',
        help="Keep empty if you produce at the location where the finished products are needed." \
            "Set a location if you produce at a fixed location. This can be a partner location " \
            "if you subcontract the manufacturing operations.")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get('mrp.routing'))


class MrpRoutingWorkcenter(models.Model):
    """
    Defines working cycles and hours of a Work Center using routings.
    """
    _name = 'mrp.routing.workcenter'
    _description = 'Work Center Usage'
    _order = 'sequence, id'
    workcenter_id = fields.Many2one('mrp.workcenter', string='Work Center', required=True)
    name = fields.Char(required=True)
    sequence = fields.Integer(default=100, help="Gives the sequence order when displaying a list of routing Work Centers.")
    cycle_nbr = fields.Float(string='Number of Cycles', required=True, default=1.0, help="Number of iterations this work center has to do in the specified operation of the routing.")
    hour_nbr = fields.Float(string='Number of Hours', required=True, help="Time in hours for this Work Center to achieve the operation of the specified routing.")
    routing_id = fields.Many2one('mrp.routing', string='Parent Work Order Operations', select=True, ondelete='cascade',
         help="Work Order Operations indicates all the Work Centers used, for how long and/or cycles." \
            "If Work Order Operations is indicated then,the third tab of a production order (Work Centers) will be automatically pre-completed.")
    note = fields.Text(string='Description')
    company_id = fields.Many2one('res.company', related='routing_id.company_id', string='Company', store=True, readonly=True)
