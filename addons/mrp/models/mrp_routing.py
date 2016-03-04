# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class MrpRouting(models.Model):
    """
    For specifying the routings of Work Centers.
    """
    _name = 'mrp.routing'

    _description = 'Routings'
    name = fields.Char(required=True, string="Routing Name")
    active = fields.Boolean(default=True, help="If the active field is set to False, it will allow you to hide the routing without removing it.")
    code = fields.Char('Reference', copy=False, readonly=True, default='New')
    note = fields.Text(string='Description')
    work_order_ids = fields.One2many('mrp.routing.workcenter', 'routing_id', string='Work Centers', copy=True, oldname='workcenter_lines')
    location_id = fields.Many2one('stock.location', string='Production Location',
                                  help="Keep empty if you produce at the location where the finished products are needed."
                                  "Set a location if you produce at a fixed location. This can be a partner location "
                                  "if you subcontract the manufacturing operations.")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get('mrp.routing'))

    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code('mrp.routing') or '/'
        new_rec = super(MrpRouting, self).create(vals)
        return new_rec


class MrpRoutingWorkcenter(models.Model):
    _name = 'mrp.routing.workcenter'
    _description = 'Work Center Usage'
    _order = 'sequence, id'

    workcenter_id = fields.Many2one('mrp.workcenter', string='Work Center', required=True)
    name = fields.Char(required=True, string="Operation")
    sequence = fields.Integer(default=100, help="Gives the sequence order when displaying a list of routing Work Centers.")
    routing_id = fields.Many2one('mrp.routing', string='Parent Routing', index=True, ondelete='cascade', required=True,
                                 help="Routings indicates all the Work Centers used and for how long."
                                 "If Routings is indicated then,the third tab of a production order (Work Centers) will be automatically pre-completed.")
    note = fields.Text(string='Description')
    company_id = fields.Many2one('res.company', related='routing_id.company_id', string='Company', store=True, readonly=True)
    worksheet = fields.Binary('worksheet')
    time_mode = fields.Selection([
        ('auto','Compute based on real time'), ('manual','Set duration manually')],
        'Duration Computation', default='auto')
    time_mode_batch = fields.Integer('Based on', default=10)
    time_cycle_manual = fields.Float(string='Manual Duration', default=60, help="Time in minutes")
    time_cycle = fields.Float(string='Duration', compute="_get_time_cycle")
    wo_count = fields.Integer(string="# of Work Orders", compute="_wo_count")

    @api.multi
    def _wo_count(self):
        result = self.env['mrp.production.work.order'].read_group([('operation_id', 'in', self.mapped('id')),('state','=','done')], ['operation_id'], ['operation_id'])
        mapped_data = dict([(op['operation_id'][0], op['operation_id_count']) for op in result])
        for operation in self:
            operation.wo_count = mapped_data.get(operation.id, 0)

    @api.multi
    def _get_time_cycle(self):
        results = self.env['mrp.production.work.order'].read_group([('state','=','done'),('operation_id','in',self.mapped('id'))], ['operation_id', 'delay','qty_produced'], ['operation_id'])
        totals = dict(map(lambda x: (x['operation_id'][0], (x['delay'], x['qty_produced'])), results))
        for operation in self:
            if operation.time_mode=='manual':
                operation.time_cycle = operation.time_cycle_manual
                continue
            (delay, qty) = totals.get(operation.id, (operation.time_cycle_manual, 1))
            operation.time_cycle = delay / qty
