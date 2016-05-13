# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.exceptions import UserError
from dateutil import relativedelta
import datetime

# ----------------------------------------------------------
# Work Centers
# ----------------------------------------------------------

class MrpWorkcenter(models.Model):
    _name = 'mrp.workcenter'
    _description = 'Work Center'
    _inherits = {'resource.resource': 'resource_id'}

    note = fields.Text(
        'Description',
        help="Description of the Work Center.")
    capacity = fields.Float(
        'Capacity', default=1.0, oldname='capacity_per_cycle',
        help="Number of pieces work center can produce in parallel.")
    sequence = fields.Integer(
        'Sequence',
        default=1, required=True,
        help="Gives the sequence order when displaying a list of work centers.")
    time_start = fields.Float(
        'Time before prod.', help="Time in minutes for the setup.")
    time_stop = fields.Float(
        'Time after prod.', help="Time in minutes for the cleaning.")
    resource_id = fields.Many2one(
        'resource.resource', string='Resource',
        ondelete='cascade', required=True)
    order_ids = fields.One2many(
        'mrp.production.work.order', 'workcenter_id', "Orders")
    routing_line_ids = fields.One2many(
        'mrp.routing.workcenter', 'workcenter_id', "Routing Lines")
    nb_orders = fields.Integer('Computed Orders', compute='_compute_orders')
    color = fields.Integer('Color')
    count_ready_order = fields.Integer('Total Ready Orders', compute='_compute_orders')
    count_progress_order = fields.Integer('Total Running Orders', compute='_compute_orders')
    working_state = fields.Selection([
        ('normal', 'Normal'),
        ('blocked', 'Blocked'),
        ('done', 'In Progress')], string='Status',
        default="normal", compute="_compute_working_state")  # TDE FIXME: store ?
    oee = fields.Float(compute='_compute_oee', help='Overall Equipment Efficiency, based on the last month')
    blocked_time = fields.Float(compute='_compute_oee', help='Blocked Hours over the last month')
    oee_target = fields.Float(string='OEE Target', help="OEE Target in percentage", default=90)
    stat_perf = fields.Integer(compute='_compute_perf', help='Performance over the last month: (expected duration - real duration) / expected duration')

    @api.multi
    def _compute_perf(self):
        prod_obj = self.env['mrp.production.work.order']
        date = (datetime.datetime.now() - relativedelta.relativedelta(months=1)).strftime('%Y-%m-%d %H:%M:%S')
        domain = [
            ('date_start','>=', date), 
            ('workcenter_id', 'in', self.mapped('id')), 
            ('state','=','done')
        ]
        wo = prod_obj.read_group(domain, ['duration','workcenter_id','delay'], ['workcenter_id'], lazy=False)
        duration = dict(map(lambda x: (x['workcenter_id'][0], x['duration']), wo))
        delay    = dict(map(lambda x: (x['workcenter_id'][0], x['delay']), wo))
        for workcenter in self:
            if delay.get(workcenter.id, 0.0):
                workcenter.stat_perf = 100 * (duration.get(workcenter.id, 0.0)-delay.get(workcenter.id, 0.0)) / delay.get(workcenter.id, 0.0)
            else:
                workcenter.stat_perf = 0.0

    @api.multi
    def _compute_oee(self):
        prod_obj = self.env['mrp.workcenter.productivity']
        date = (datetime.datetime.now() - relativedelta.relativedelta(months=1)).strftime('%Y-%m-%d %H:%M:%S')
        domain = [
            ('date_start','>=', date), 
            ('workcenter_id', 'in', self.mapped('id')), 
            ('date_end','<>',False)
        ]

        wcs_block = prod_obj.read_group(domain+[('loss_type','<>','productive')], ['duration','workcenter_id'], ['workcenter_id'], lazy=False)
        wcs_productive = prod_obj.read_group(domain+[('loss_type','=','productive')], ['duration','workcenter_id'], ['workcenter_id'], lazy=False)
        wcs_block = dict(map(lambda x: (x['workcenter_id'][0], x['duration']), wcs_block))
        wcs_productive = dict(map(lambda x: (x['workcenter_id'][0], x['duration']), wcs_productive))
        for workcenter in self:
            workcenter.blocked_time = wcs_block.get(workcenter.id)
            if wcs_productive.get(workcenter.id) and wcs_block.get(workcenter.id):
                workcenter.oee = round(wcs_productive.get(workcenter.id, 0.0) * 100.0 / (wcs_productive.get(workcenter.id, 0.0) + wcs_block.get(workcenter.id)),2)
            else:
                workcenter.oee = 0.0

    @api.multi
    def _compute_working_state(self):
        for workcenter in self:
            last = self.env['mrp.workcenter.productivity'].search([('workcenter_id','=',workcenter.id)], limit=1)
            if (not last) or (last[0].date_end):
                workcenter.working_state = 'normal'
            elif last[0].loss_type in ('productive', 'performance'):
                workcenter.working_state = 'done'
            else:
                workcenter.working_state = 'blocked'

    @api.multi
    def unblock(self):
        self.ensure_one()
        if self.working_state != 'blocked':
            raise UserError(_("It has been unblocked already. "))
        times = self.env['mrp.workcenter.productivity'].search([('workcenter_id', '=', self.id), ('date_end', '=', False)])
        times.write({'date_end': fields.Datetime.now()})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

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
        if any(workcenter.capacity <= 0.0 for workcenter in self):
            raise exceptions.UserError(_('The capacity must be strictly positive.'))


class MrpWorkcenterProductivityLoss(models.Model):
    _name = "mrp.workcenter.productivity.loss"
    _description = "TPM Big Losses"

    name = fields.Char('Reason', required=True)
    sequence = fields.Integer('Sequence', default=1)
    manual = fields.Boolean('Is a Blocking Reason', default=True)
    loss_type = fields.Selection([
        ('availability', 'Availability'),
        ('performance', 'Performance'),
        ('quality', 'Quality'),
        ('productive', 'Productive')], "Effectiveness Category",
        default='availability', required=True)


class MrpWorkcenterProductivity(models.Model):
    _name = "mrp.workcenter.productivity"
    _description = "Workcenter Productivity Log"
    _order = "id desc"

    @api.depends('date_end', 'date_start')
    def _compute_duration(self):
        for blocktime in self:
            if blocktime.date_end and blocktime.date_start:
                diff = fields.Datetime.from_string(blocktime.date_end) - fields.Datetime.from_string(blocktime.date_start)
                blocktime.duration = round(diff.total_seconds() / 60.0 , 2)
            else:
                blocktime.duration = 0.0

    @api.multi
    def button_block(self):
        self.ensure_one()
        self.workcenter_id.order_ids.end_all()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    workcenter_id = fields.Many2one(
        'mrp.workcenter', "Workcenter",
        required=True)
    user_id = fields.Many2one(
        'res.users', "User",
        default=lambda self:self.env.uid)
    loss_id = fields.Many2one(
        'mrp.workcenter.productivity.loss', "Loss Reason",
        required=True)
    loss_type = fields.Selection(
        "Effectiveness", related='loss_id.loss_type', store=True)
    description = fields.Text('Description')
    date_start = fields.Datetime('Start Date', default=fields.Datetime.now())
    date_end = fields.Datetime('End Date')
    duration = fields.Float('Duration', compute='_compute_duration', store=True)
