# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Routing(models.Model):
    """ For specifying the routings of Work Centers. """
    _name = 'mrp.routing'
    _description = 'Routings'

    name = fields.Char('Name', required=True)
    active = fields.Boolean(
        'Active', default=True,
        help="If the active field is set to False, it will allow you to hide the routing without removing it.")
    code = fields.Char('Code', size=8)
    note = fields.Text('Description')
    workcenter_lines = fields.One2many(
        'mrp.routing.workcenter', 'routing_id', 'Work Centers', copy=True)
    location_id = fields.Many2one(
        'stock.location', 'Production Location',
        help="Keep empty if you produce at the location where the finished products are needed."
             "Set a location if you produce at a fixed location. This can be a partner location "
             "if you subcontract the manufacturing operations.")
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('mrp.routing'))


class RoutingWorkcenter(models.Model):
    """ Defines working cycles and hours of a Work Center using routings. """
    _name = 'mrp.routing.workcenter'
    _description = 'Work Center Usage'
    _order = 'sequence, id'

    workcenter_id = fields.Many2one('mrp.workcenter', 'Work Center', required=True)
    name = fields.Char('Name', required=True)
    sequence = fields.Integer(
        'Sequence', default=100,
        help="Gives the sequence order when displaying a list of routing Work Centers.")
    cycle_nbr = fields.Float(
        'Number of Cycles',
        default=1.0, required=True,
        help="Number of iterations this work center has to do in the specified operation of the routing.")
    hour_nbr = fields.Float(
        'Number of Hours',
        default=0.0, required=True,
        help="Time in hours for this Work Center to achieve the operation of the specified routing.")
    routing_id = fields.Many2one(
        'mrp.routing', 'Parent Routing',
        index=True, ondelete='cascade',
        help="Routings indicates all the Work Centers used, for how long and/or cycles."
             "If Routings is set then,the third tab of a production order (Work Centers) will be automatically pre-completed.")
    note = fields.Text('Description')
    company_id = fields.Many2one(
        'res.company', 'Company', related='routing_id.company_id',
        readonly=True, store=True)
