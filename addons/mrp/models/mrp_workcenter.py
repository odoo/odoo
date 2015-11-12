# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _

# ----------------------------------------------------------
# Work Centers
# ----------------------------------------------------------


class MrpWorkcenter(models.Model):
    _name = 'mrp.workcenter'
    _description = 'Work Center'
    _inherits = {'resource.resource': "resource_id"}


    note = fields.Text(string='Description', help="Description of the Work Center. ")
    capacity = fields.Float(string='Capacity', default=1.0, help="Number of pieces work center can produce in parallel.")
    time_start = fields.Float(string='Time before prod.', help="Time in minutes for the setup.")
    sequence = fields.Integer(required=True, default=1, help="Gives the sequence order when displaying a list of work centers.")
    time_stop = fields.Float(string='Time after prod.', help="Time in minutes for the cleaning.")
    resource_id = fields.Many2one('resource.resource', string='Resource', ondelete='cascade', required=True)
    order_ids = fields.One2many('mrp.production.work.order', 'workcenter_id', string="Orders")
    routing_line_ids = fields.One2many('mrp.routing.workcenter', 'workcenter_id', "Routing Lines")
    nb_orders = fields.Integer('Computed Orders', compute='_compute_orders')
    color = fields.Integer('Color')
    count_ready_order = fields.Integer(compute='_compute_orders', string="Total Ready Orders")
    count_progress_order = fields.Integer(compute='_compute_orders', string="Total Running Orders")
    stage_id = fields.Selection([('normal', 'Normal'), ('blocked', 'Blocked'), ('done', 'In Progress')], string='Status', default="normal", store=True, compute="_compute_stages")

    @api.multi
    @api.depends('order_ids', 'order_ids.state')
    def _compute_stages(self):
        for workcenter in self:
            if workcenter.count_progress_order:
                workcenter.stage_id = 'done'
            else:
                workcenter.stage_id = 'normal'


    @api.depends('order_ids')
    def _compute_orders(self):
        WorkcenterLine = self.env['mrp.production.work.order']
        for workcenter in self:
            workcenter.nb_orders = WorkcenterLine.search_count([('workcenter_id', '=', workcenter.id), ('state', '!=', 'done')]) #('state', 'in', ['pending', 'startworking'])
            workcenter.count_ready_order = WorkcenterLine.search_count([('workcenter_id', '=', workcenter.id), ('state', '=', 'ready')])
            workcenter.count_progress_order = WorkcenterLine.search_count([('workcenter_id', '=', workcenter.id), ('state', '=', 'progress')])

    @api.multi
    @api.constrains('capacity')
    def _check_capacity(self):
        for obj in self:
            if obj.capacity <= 0.0:
                raise ValueError(_('The capacity must be strictly positive.'))
