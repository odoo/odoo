# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil import relativedelta
import datetime

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import ValidationError


class MrpWorkcenter(models.Model):
    _name = 'mrp.workcenter'
    _description = 'Work Center'
    _order = "sequence, id"
    _inherit = ['resource.mixin']
    _check_company_auto = True

    # resource
    name = fields.Char('Work Center', related='resource_id.name', store=True, readonly=False)
    time_efficiency = fields.Float('Time Efficiency', related='resource_id.time_efficiency', default=100, store=True, readonly=False)
    active = fields.Boolean('Active', related='resource_id.active', default=True, store=True, readonly=False)

    code = fields.Char('Code', copy=False)
    note = fields.Text(
        'Description',
        help="Description of the Work Center.")
    capacity = fields.Float(
        'Capacity', default=1.0,
        help="Number of pieces that can be produced in parallel. In case the work center has a capacity of 5 and you have to produce 10 units on your work order, the usual operation time will be multiplied by 2.")
    sequence = fields.Integer(
        'Sequence', default=1, required=True,
        help="Gives the sequence order when displaying a list of work centers.")
    color = fields.Integer('Color')
    costs_hour = fields.Float(string='Cost per hour', help='Specify cost of work center per hour.', default=0.0)
    time_start = fields.Float('Time before prod.', help="Time in minutes for the setup.")
    time_stop = fields.Float('Time after prod.', help="Time in minutes for the cleaning.")
    routing_line_ids = fields.One2many('mrp.routing.workcenter', 'workcenter_id', "Routing Lines")
    order_ids = fields.One2many('mrp.workorder', 'workcenter_id', "Orders")
    workorder_count = fields.Integer('# Work Orders', compute='_compute_workorder_count')
    workorder_ready_count = fields.Integer('# Read Work Orders', compute='_compute_workorder_count')
    workorder_progress_count = fields.Integer('Total Running Orders', compute='_compute_workorder_count')
    workorder_pending_count = fields.Integer('Total Pending Orders', compute='_compute_workorder_count')
    workorder_late_count = fields.Integer('Total Late Orders', compute='_compute_workorder_count')

    time_ids = fields.One2many('mrp.workcenter.productivity', 'workcenter_id', 'Time Logs')
    working_state = fields.Selection([
        ('normal', 'Normal'),
        ('blocked', 'Blocked'),
        ('done', 'In Progress')], 'Workcenter Status', compute="_compute_working_state", store=True)
    blocked_time = fields.Float(
        'Blocked Time', compute='_compute_blocked_time',
        help='Blocked hours over the last month', digits=(16, 2))
    productive_time = fields.Float(
        'Productive Time', compute='_compute_productive_time',
        help='Productive hours over the last month', digits=(16, 2))
    oee = fields.Float(compute='_compute_oee', help='Overall Equipment Effectiveness, based on the last month')
    oee_target = fields.Float(string='OEE Target', help="Overall Effective Efficiency Target in percentage", default=90)
    performance = fields.Integer('Performance', compute='_compute_performance', help='Performance over the last month')
    workcenter_load = fields.Float('Work Center Load', compute='_compute_workorder_count')
    alternative_workcenter_ids = fields.Many2many(
        'mrp.workcenter',
        'mrp_workcenter_alternative_rel',
        'workcenter_id',
        'alternative_workcenter_id',
        domain="[('id', '!=', id), '|', ('company_id', '=', company_id), ('company_id', '=', False)]",
        string="Alternative Workcenters", check_company=True,
        help="Alternative workcenters that can be substituted to this one in order to dispatch production"
    )

    @api.constrains('alternative_workcenter_ids')
    def _check_alternative_workcenter(self):
        if self in self.alternative_workcenter_ids:
            raise ValidationError(_("A workcenter cannot be an alternative of itself"))

    @api.depends('order_ids.duration_expected', 'order_ids.workcenter_id', 'order_ids.state', 'order_ids.date_planned_start')
    def _compute_workorder_count(self):
        MrpWorkorder = self.env['mrp.workorder']
        result = {wid: {} for wid in self._ids}
        result_duration_expected = {wid: 0 for wid in self._ids}
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

    @api.constrains('capacity')
    def _check_capacity(self):
        if any(workcenter.capacity <= 0.0 for workcenter in self):
            raise exceptions.UserError(_('The capacity must be strictly positive.'))

    def unblock(self):
        self.ensure_one()
        if self.working_state != 'blocked':
            raise exceptions.UserError(_("It has already been unblocked."))
        times = self.env['mrp.workcenter.productivity'].search([('workcenter_id', '=', self.id), ('date_end', '=', False)])
        times.write({'date_end': fields.Datetime.now()})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.model_create_multi
    def create(self, vals_list):
        # resource_type is 'human' by default. As we are not living in
        # /r/latestagecapitalism, workcenters are 'material'
        records = super(MrpWorkcenter, self.with_context(default_resource_type='material')).create(vals_list)
        return records

    def write(self, vals):
        if 'company_id' in vals:
            self.resource_id.company_id = vals['company_id']
        return super(MrpWorkcenter, self).write(vals)

    def action_work_order(self):
        action = self.env.ref('mrp.action_work_orders').read()[0]
        return action


class MrpWorkcenterProductivityLossType(models.Model):
    _name = "mrp.workcenter.productivity.loss.type"
    _description = 'MRP Workorder productivity losses'
    _rec_name = 'loss_type'

    @api.depends('loss_type')
    def name_get(self):
        """ As 'category' field in form view is a Many2one, its value will be in
        lower case. In order to display its value capitalized 'name_get' is
        overrided.
        """
        result = []
        for rec in self:
            result.append((rec.id, rec.loss_type.title()))
        return result

    loss_type = fields.Selection([
            ('availability', 'Availability'),
            ('performance', 'Performance'),
            ('quality', 'Quality'),
            ('productive', 'Productive')], string='Category', default='availability', required=True)


class MrpWorkcenterProductivityLoss(models.Model):
    _name = "mrp.workcenter.productivity.loss"
    _description = "Workcenter Productivity Losses"
    _order = "sequence, id"

    name = fields.Char('Blocking Reason', required=True)
    sequence = fields.Integer('Sequence', default=1)
    manual = fields.Boolean('Is a Blocking Reason', default=True)
    loss_id = fields.Many2one('mrp.workcenter.productivity.loss.type', domain=([('loss_type', 'in', ['quality', 'availability'])]), string='Category')
    loss_type = fields.Selection(string='Effectiveness Category', related='loss_id.loss_type', store=True, readonly=False)


class MrpWorkcenterProductivity(models.Model):
    _name = "mrp.workcenter.productivity"
    _description = "Workcenter Productivity Log"
    _order = "id desc"
    _rec_name = "loss_id"
    _check_company_auto = True

    def _get_default_company_id(self):
        company_id = False
        if self.env.context.get('default_company_id'):
            company_id = self.env.context['default_company_id']
        if not company_id and self.env.context.get('default_workorder_id'):
            workorder = self.env['mrp.workorder'].browse(self.env.context['default_workorder_id'])
            company_id = workorder.company_id
        if not company_id and self.env.context.get('default_workcenter_id'):
            workcenter = self.env['mrp.workcenter'].browse(self.env.context['default_workcenter_id'])
            company_id = workcenter.company_id
        if not company_id:
            company_id = self.env.company
        return company_id

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', related='workorder_id.production_id', readonly='True')
    workcenter_id = fields.Many2one('mrp.workcenter', "Work Center", required=True, check_company=True)
    company_id = fields.Many2one(
        'res.company', required=True, index=True,
        default=lambda self: self._get_default_company_id())
    workorder_id = fields.Many2one('mrp.workorder', 'Work Order', check_company=True)
    user_id = fields.Many2one(
        'res.users', "User",
        default=lambda self: self.env.uid)
    loss_id = fields.Many2one(
        'mrp.workcenter.productivity.loss', "Loss Reason",
        ondelete='restrict', required=True)
    loss_type = fields.Selection(
        "Effectiveness", related='loss_id.loss_type', store=True, readonly=False)
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
                    r = blocktime.workcenter_id._get_work_days_data_batch(d1, d2)[blocktime.workcenter_id.id]['hours']
                    blocktime.duration = round(r * 60, 2)
                else:
                    blocktime.duration = round(diff.total_seconds() / 60.0, 2)
            else:
                blocktime.duration = 0.0

    def button_block(self):
        self.ensure_one()
        self.workcenter_id.order_ids.end_all()

