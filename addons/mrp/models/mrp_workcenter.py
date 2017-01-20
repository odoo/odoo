# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil import relativedelta
import datetime

from odoo import api, exceptions, fields, models, _


class MrpWorkcenter(models.Model):
    _name = 'mrp.workcenter'
    _description = 'Work Center'
    _order = "sequence, id"
    _inherit = ['resource.mixin']

    # resource
    name = fields.Char(related='resource_id.name', store=True)
    time_efficiency = fields.Float('Time Efficiency', related='resource_id.time_efficiency', store=True)
    active = fields.Boolean('Active', related='resource_id.active', default=True, store=True)

    code = fields.Char('Code', copy=False)
    note = fields.Text(
        'Description',
        help="Description of the Work Center.")
    capacity = fields.Float(
        'Capacity', default=1.0, oldname='capacity_per_cycle',
        help="Number of pieces that can be produced in parallel.")
    sequence = fields.Integer(
        'Sequence', default=1, required=True,
        help="Gives the sequence order when displaying a list of work centers.")
    color = fields.Integer('Color')
    time_start = fields.Float('Time before prod.', help="Time in minutes for the setup.")
    time_stop = fields.Float('Time after prod.', help="Time in minutes for the cleaning.")
    routing_line_ids = fields.One2many('mrp.routing.workcenter', 'workcenter_id', "Routing Lines")
    order_ids = fields.One2many('mrp.workorder', 'workcenter_id', "Orders")
    workorder_count = fields.Integer('# Work Orders', compute='_compute_workorder_count')
    workorder_ready_count = fields.Integer('# Read Work Orders', compute='_compute_workorder_count')
    workorder_progress_count = fields.Integer('Total Running Orders', compute='_compute_workorder_count')
    workorder_pending_count = fields.Integer('Total Running Orders', compute='_compute_workorder_count')
    workorder_late_count = fields.Integer('Total Late Orders', compute='_compute_workorder_count')

    time_ids = fields.One2many('mrp.workcenter.productivity', 'workcenter_id', 'Time Logs')
    working_state = fields.Selection([
        ('normal', 'Normal'),
        ('blocked', 'Blocked'),
        ('done', 'In Progress')], 'Status', compute="_compute_working_state", store=True)
    blocked_time = fields.Float(
        'Blocked Time', compute='_compute_blocked_time',
        help='Blocked hour(s) over the last month', digits=(16, 2))
    productive_time = fields.Float(
        'Productive Time', compute='_compute_productive_time',
        help='Productive hour(s) over the last month', digits=(16, 2))
    oee = fields.Float(compute='_compute_oee', help='Overall Equipment Effectiveness, based on the last month')
    oee_target = fields.Float(string='OEE Target', help="OEE Target in percentage", default=90)
    performance = fields.Integer('Performance', compute='_compute_performance', help='Performance over the last month')
    workcenter_load = fields.Float('Work Center Load', compute='_compute_workorder_count')

    @api.depends('order_ids.duration_expected', 'order_ids.workcenter_id', 'order_ids.state', 'order_ids.date_planned_start')
    def _compute_workorder_count(self):
        MrpWorkorder = self.env['mrp.workorder']
        result = {wid: {} for wid in self.ids}
        result_duration_expected = {wid: 0 for wid in self.ids}
        #Count Late Workorder
        data = MrpWorkorder.read_group([('workcenter_id', 'in', self.ids), ('state', 'in', ('pending', 'ready')), ('date_planned_start', '<', datetime.datetime.now().strftime('%Y-%m-%d'))], ['workcenter_id'], ['workcenter_id'])
        count_data = dict((item['workcenter_id'][0], item['workcenter_id_count']) for item in data)
        #Count All, Pending, Ready, Progress Workorder
        res = MrpWorkorder.read_group(
            [('workcenter_id', 'in', self.ids)],
            ['workcenter_id', 'state', 'duration_expected'], ['workcenter_id', 'state'],
            lazy=False)
        for res_group in res:
            result[res_group['workcenter_id'][0]][res_group['state']] = res_group['__count']
            if res_group['state'] in ('pending', 'ready', 'progress'):
                result_duration_expected[res_group['workcenter_id'][0]] += res_group['duration_expected']
        for workcenter in self:
            workcenter.workorder_count = sum(count for state, count in result[workcenter.id].items() if state not in ('done', 'cancel'))
            workcenter.workorder_pending_count = result[workcenter.id].get('pending', 0)
            workcenter.workcenter_load = result_duration_expected[workcenter.id]
            workcenter.workorder_ready_count = result[workcenter.id].get('ready', 0)
            workcenter.workorder_progress_count = result[workcenter.id].get('progress', 0)
            workcenter.workorder_late_count = count_data.get(workcenter.id, 0)

    @api.multi
    @api.depends('time_ids', 'time_ids.date_end', 'time_ids.loss_type')
    def _compute_working_state(self):
        for workcenter in self:
            # We search for a productivity line associated to this workcenter having no `date_end`.
            # If we do not find one, the workcenter is not currently being used. If we find one, according
            # to its `type_loss`, the workcenter is either being used or blocked.
            time_log = self.env['mrp.workcenter.productivity'].search([
                ('workcenter_id', '=', workcenter.id),
                ('date_end', '=', False)
            ], limit=1)
            if not time_log:
                # the workcenter is not being used
                workcenter.working_state = 'normal'
            elif time_log.loss_type in ('productive', 'performance'):
                # the productivity line has a `loss_type` that means the workcenter is being used
                workcenter.working_state = 'done'
            else:
                # the workcenter is blocked
                workcenter.working_state = 'blocked'

    @api.multi
    def _compute_blocked_time(self):
        # TDE FIXME: productivity loss type should be only losses, probably count other time logs differently ??
        data = self.env['mrp.workcenter.productivity'].read_group([
            ('date_start', '>=', fields.Datetime.to_string(datetime.datetime.now() - relativedelta.relativedelta(months=1))),
            ('workcenter_id', 'in', self.ids),
            ('date_end', '!=', False),
            ('loss_type', '!=', 'productive')],
            ['duration', 'workcenter_id'], ['workcenter_id'], lazy=False)
        count_data = dict((item['workcenter_id'][0], item['duration']) for item in data)
        for workcenter in self:
            workcenter.blocked_time = count_data.get(workcenter.id, 0.0) / 60.0

    @api.multi
    def _compute_productive_time(self):
        # TDE FIXME: productivity loss type should be only losses, probably count other time logs differently
        data = self.env['mrp.workcenter.productivity'].read_group([
            ('date_start', '>=', fields.Datetime.to_string(datetime.datetime.now() - relativedelta.relativedelta(months=1))),
            ('workcenter_id', 'in', self.ids),
            ('date_end', '!=', False),
            ('loss_type', '=', 'productive')],
            ['duration', 'workcenter_id'], ['workcenter_id'], lazy=False)
        count_data = dict((item['workcenter_id'][0], item['duration']) for item in data)
        for workcenter in self:
            workcenter.productive_time = count_data.get(workcenter.id, 0.0) / 60.0

    @api.depends('blocked_time', 'productive_time')
    def _compute_oee(self):
        for order in self:
            if order.productive_time:
                order.oee = round(order.productive_time * 100.0 / (order.productive_time + order.blocked_time), 2)
            else:
                order.oee = 0.0

    @api.multi
    def _compute_performance(self):
        wo_data = self.env['mrp.workorder'].read_group([
            ('date_start', '>=', fields.Datetime.to_string(datetime.datetime.now() - relativedelta.relativedelta(months=1))),
            ('workcenter_id', 'in', self.ids),
            ('state', '=', 'done')], ['duration_expected', 'workcenter_id', 'duration'], ['workcenter_id'], lazy=False)
        duration_expected = dict((data['workcenter_id'][0], data['duration_expected']) for data in wo_data)
        duration = dict((data['workcenter_id'][0], data['duration']) for data in wo_data)
        for workcenter in self:
            if duration.get(workcenter.id):
                workcenter.performance = 100 * duration_expected.get(workcenter.id, 0.0) / duration[workcenter.id]
            else:
                workcenter.performance = 0.0

    @api.multi
    @api.constrains('capacity')
    def _check_capacity(self):
        if any(workcenter.capacity <= 0.0 for workcenter in self):
            raise exceptions.UserError(_('The capacity must be strictly positive.'))

    @api.multi
    def unblock(self):
        self.ensure_one()
        if self.working_state != 'blocked':
            raise exceptions.UserError(_("It has been unblocked already. "))
        times = self.env['mrp.workcenter.productivity'].search([('workcenter_id', '=', self.id), ('date_end', '=', False)])
        times.write({'date_end': fields.Datetime.now()})
        return {'type': 'ir.actions.client', 'tag': 'reload'}


class MrpWorkcenterProductivityLoss(models.Model):
    _name = "mrp.workcenter.productivity.loss"
    _description = "TPM Big Losses"
    _order = "sequence, id"

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
    _rec_name = "loss_id"

    workcenter_id = fields.Many2one('mrp.workcenter', "Work Center", required=True)
    workorder_id = fields.Many2one('mrp.workorder', 'Work Order')
    user_id = fields.Many2one(
        'res.users', "User",
        default=lambda self: self.env.uid)
    loss_id = fields.Many2one(
        'mrp.workcenter.productivity.loss', "Loss Reason",
        ondelete='restrict', required=True)
    loss_type = fields.Selection(
        "Effectiveness", related='loss_id.loss_type', store=True)
    description = fields.Text('Description')
    date_start = fields.Datetime('Start Date', default=fields.Datetime.now, required=True)
    date_end = fields.Datetime('End Date')
    duration = fields.Float('Duration', compute='_compute_duration', store=True)

    @api.depends('date_end', 'date_start')
    def _compute_duration(self):
        for blocktime in self:
            if blocktime.date_end:
                d1 = fields.Datetime.from_string(blocktime.date_start)
                d2 = fields.Datetime.from_string(blocktime.date_end)
                diff = d2 - d1
                if (blocktime.loss_type not in ('productive', 'performance')) and blocktime.workcenter_id.resource_calendar_id:
                    r = blocktime.workcenter_id.resource_calendar_id.get_work_hours_count(d1, d2, blocktime.workcenter_id.resource_id.id)
                    blocktime.duration = round(r * 60, 2)
                else:
                    blocktime.duration = round(diff.total_seconds() / 60.0, 2)
            else:
                blocktime.duration = 0.0

    @api.multi
    def button_block(self):
        self.ensure_one()
        self.workcenter_id.order_ids.end_all()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
