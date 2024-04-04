# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil import relativedelta
from datetime import timedelta, datetime
from functools import partial
from pytz import timezone
from random import randint

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.resource.models.resource import make_aware, Intervals
from odoo.tools.float_utils import float_compare


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
    note = fields.Html(
        'Description')
    default_capacity = fields.Float(
        'Capacity', default=1.0,
        help="Default number of pieces (in product UoM) that can be produced in parallel (at the same time) at this work center. For example: the capacity is 5 and you need to produce 10 units, then the operation time listed on the BOM will be multiplied by two. However, note that both time before and after production will only be counted once.")
    sequence = fields.Integer(
        'Sequence', default=1, required=True,
        help="Gives the sequence order when displaying a list of work centers.")
    color = fields.Integer('Color')
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id', readonly=True, required=True)
    costs_hour = fields.Float(string='Cost per hour', help='Hourly processing cost.', default=0.0)
    time_start = fields.Float('Setup Time')
    time_stop = fields.Float('Cleanup Time')
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
    tag_ids = fields.Many2many('mrp.workcenter.tag')
    capacity_ids = fields.One2many('mrp.workcenter.capacity', 'workcenter_id', string='Product Capacities',
        help="Specific number of pieces that can be produced in parallel per product.", copy=True)

    @api.constrains('alternative_workcenter_ids')
    def _check_alternative_workcenter(self):
        for workcenter in self:
            if workcenter in workcenter.alternative_workcenter_ids:
                raise ValidationError(_("Workcenter %s cannot be an alternative of itself.", workcenter.name))

    @api.depends('order_ids.duration_expected', 'order_ids.workcenter_id', 'order_ids.state', 'order_ids.date_planned_start')
    def _compute_workorder_count(self):
        MrpWorkorder = self.env['mrp.workorder']
        result = {wid: {} for wid in self._ids}
        result_duration_expected = {wid: 0 for wid in self._ids}
        # Count Late Workorder
        data = MrpWorkorder._read_group(
            [('workcenter_id', 'in', self.ids), ('state', 'in', ('pending', 'waiting', 'ready')), ('date_planned_start', '<', datetime.now().strftime('%Y-%m-%d'))],
            ['workcenter_id'], ['workcenter_id'])
        count_data = dict((item['workcenter_id'][0], item['workcenter_id_count']) for item in data)
        # Count All, Pending, Ready, Progress Workorder
        res = MrpWorkorder._read_group(
            [('workcenter_id', 'in', self.ids)],
            ['workcenter_id', 'state', 'duration_expected'], ['workcenter_id', 'state'],
            lazy=False)
        for res_group in res:
            result[res_group['workcenter_id'][0]][res_group['state']] = res_group['__count']
            if res_group['state'] in ('pending', 'waiting', 'ready', 'progress'):
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
        data = self.env['mrp.workcenter.productivity']._read_group([
            ('date_start', '>=', fields.Datetime.to_string(datetime.now() - relativedelta.relativedelta(months=1))),
            ('workcenter_id', 'in', self.ids),
            ('date_end', '!=', False),
            ('loss_type', '!=', 'productive')],
            ['duration', 'workcenter_id'], ['workcenter_id'], lazy=False)
        count_data = dict((item['workcenter_id'][0], item['duration']) for item in data)
        for workcenter in self:
            workcenter.blocked_time = count_data.get(workcenter.id, 0.0) / 60.0

    def _compute_productive_time(self):
        # TDE FIXME: productivity loss type should be only losses, probably count other time logs differently
        data = self.env['mrp.workcenter.productivity']._read_group([
            ('date_start', '>=', fields.Datetime.to_string(datetime.now() - relativedelta.relativedelta(months=1))),
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
        wo_data = self.env['mrp.workorder']._read_group([
            ('date_start', '>=', fields.Datetime.to_string(datetime.now() - relativedelta.relativedelta(months=1))),
            ('workcenter_id', 'in', self.ids),
            ('state', '=', 'done')], ['duration_expected', 'workcenter_id', 'duration'], ['workcenter_id'], lazy=False)
        duration_expected = dict((data['workcenter_id'][0], data['duration_expected']) for data in wo_data)
        duration = dict((data['workcenter_id'][0], data['duration']) for data in wo_data)
        for workcenter in self:
            if duration.get(workcenter.id):
                workcenter.performance = 100 * duration_expected.get(workcenter.id, 0.0) / duration[workcenter.id]
            else:
                workcenter.performance = 0.0

    @api.constrains('default_capacity')
    def _check_capacity(self):
        if any(workcenter.default_capacity <= 0.0 for workcenter in self):
            raise exceptions.UserError(_('The capacity must be strictly positive.'))

    def unblock(self):
        self.ensure_one()
        if self.working_state != 'blocked':
            raise exceptions.UserError(_("It has already been unblocked."))
        times = self.env['mrp.workcenter.productivity'].search([('workcenter_id', '=', self.id), ('date_end', '=', False)])
        times.write({'date_end': datetime.now()})
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

    def action_show_operations(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('mrp.mrp_routing_action')
        action['domain'] = [('workcenter_id', '=', self.id)]
        action['context'] = {
            'default_workcenter_id': self.id,
        }
        return action

    def action_work_order(self):
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.action_work_orders")
        return action

    def _get_unavailability_intervals(self, start_datetime, end_datetime):
        """Get the unavailabilities intervals for the workcenters in `self`.

        Return the list of unavailabilities (a tuple of datetimes) indexed
        by workcenter id.

        :param start_datetime: filter unavailability with only slots after this start_datetime
        :param end_datetime: filter unavailability with only slots before this end_datetime
        :rtype: dict
        """
        unavailability_ressources = self.resource_id._get_unavailable_intervals(start_datetime, end_datetime)
        return {wc.id: unavailability_ressources.get(wc.resource_id.id, []) for wc in self}

    def _get_first_available_slot(self, start_datetime, duration):
        """Get the first available interval for the workcenter in `self`.

        The available interval is disjoinct with all other workorders planned on this workcenter, but
        can overlap the time-off of the related calendar (inverse of the working hours).
        Return the first available interval (start datetime, end datetime) or,
        if there is none before 700 days, a tuple error (False, 'error message').

        :param start_datetime: begin the search at this datetime
        :param duration: minutes needed to make the workorder (float)
        :rtype: tuple
        """
        self.ensure_one()
        start_datetime, revert = make_aware(start_datetime)

        resource = self.resource_id
        get_available_intervals = partial(self.resource_calendar_id._work_intervals_batch, domain=[('time_type', 'in', ['other', 'leave'])], resources=resource, tz=timezone(self.resource_calendar_id.tz))
        get_workorder_intervals = partial(self.resource_calendar_id._leave_intervals_batch, domain=[('time_type', '=', 'other')], resources=resource, tz=timezone(self.resource_calendar_id.tz))

        remaining = duration
        start_interval = start_datetime
        delta = timedelta(days=14)

        for n in range(50):  # 50 * 14 = 700 days in advance (hardcoded)
            dt = start_datetime + delta * n
            available_intervals = get_available_intervals(dt, dt + delta)[resource.id]
            workorder_intervals = get_workorder_intervals(dt, dt + delta)[resource.id]
            for start, stop, dummy in available_intervals:
                # Shouldn't loop more than 2 times because the available_intervals contains the workorder_intervals
                # And remaining == duration can only occur at the first loop and at the interval intersection (cannot happen several time because available_intervals > workorder_intervals
                for _i in range(2):
                    interval_minutes = (stop - start).total_seconds() / 60
                    # If the remaining minutes has never decrease update start_interval
                    if remaining == duration:
                        start_interval = start
                    # If there is a overlap between the possible available interval and a others WO
                    if Intervals([(start_interval, start + timedelta(minutes=min(remaining, interval_minutes)), dummy)]) & workorder_intervals:
                        remaining = duration
                    elif float_compare(interval_minutes, remaining, precision_digits=3) >= 0:
                        return revert(start_interval), revert(start + timedelta(minutes=remaining))
                    else:
                        # Decrease a part of the remaining duration
                        remaining -= interval_minutes
                        # Go to the next available interval because the possible current interval duration has been used
                        break
        return False, 'Not available slot 700 days after the planned start'

    def action_archive(self):
        res = super().action_archive()
        filtered_workcenters = ", ".join(workcenter.name for workcenter in self.filtered('routing_line_ids'))
        if filtered_workcenters:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                'title': _("Note that archived work center(s): '%s' is/are still linked to active Bill of Materials, which means that operations can still be planned on it/them. "
                           "To prevent this, deletion of the work center is recommended instead.", filtered_workcenters),
                'type': 'warning',
                'sticky': True,  #True/False will display for few seconds if false
                'next': {'type': 'ir.actions.act_window_close'},
                },
            }
        return res

    def _get_capacity(self, product):
        product_capacity = self.capacity_ids.filtered(lambda capacity: capacity.product_id == product)
        return product_capacity.capacity if product_capacity else self.default_capacity

    def _get_expected_duration(self, product_id):
        """Compute the expected duration when using this work-center
        Always include workcenter startup time and clean-up time.
        In case there are specific capacities defined in the workcenter
        that matches the product we are producing. Add the extra-time.
        """
        capacity = self.capacity_ids.filtered(lambda p: p.product_id == product_id)
        return self.time_start + self.time_stop + (capacity.time_start + capacity.time_stop if capacity else 0.0)


class WorkcenterTag(models.Model):
    _name = 'mrp.workcenter.tag'
    _description = 'Add tag for the workcenter'
    _order = 'name'

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char("Tag Name", required=True)
    color = fields.Integer("Color Index", default=_get_default_color)

    _sql_constraints = [
        ('tag_name_unique', 'unique(name)',
         'The tag name must be unique.'),
    ]


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

    def _convert_to_duration(self, date_start, date_stop, workcenter=False):
        """ Convert a date range into a duration in minutes.
        If the productivity type is not from an employee (extra hours are allow)
        and the workcenter has a calendar, convert the dates into a duration based on
        working hours.
        """
        duration = 0
        for productivity_loss in self:
            if (productivity_loss.loss_type not in ('productive', 'performance')) and workcenter and workcenter.resource_calendar_id:
                r = workcenter._get_work_days_data_batch(date_start, date_stop)[workcenter.id]['hours']
                duration = max(duration, r * 60)
            else:
                duration = max(duration, (date_stop - date_start).total_seconds() / 60.0)
        return round(duration, 2)

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

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', related='workorder_id.production_id', readonly=True)
    workcenter_id = fields.Many2one('mrp.workcenter', "Work Center", required=True, check_company=True, index=True)
    company_id = fields.Many2one(
        'res.company', required=True, index=True,
        default=lambda self: self._get_default_company_id())
    workorder_id = fields.Many2one('mrp.workorder', 'Work Order', check_company=True, index=True)
    user_id = fields.Many2one(
        'res.users', "User",
        default=lambda self: self.env.uid)
    loss_id = fields.Many2one(
        'mrp.workcenter.productivity.loss', "Loss Reason",
        ondelete='restrict', required=True)
    loss_type = fields.Selection(
        string="Effectiveness", related='loss_id.loss_type', store=True, readonly=False)
    description = fields.Text('Description')
    date_start = fields.Datetime('Start Date', default=fields.Datetime.now, required=True)
    date_end = fields.Datetime('End Date')
    duration = fields.Float('Duration', compute='_compute_duration', store=True)

    @api.depends('date_end', 'date_start')
    def _compute_duration(self):
        for blocktime in self:
            if blocktime.date_start and blocktime.date_end:
                blocktime.duration = blocktime.loss_id._convert_to_duration(blocktime.date_start.replace(microsecond=0), blocktime.date_end.replace(microsecond=0), blocktime.workcenter_id)
            else:
                blocktime.duration = 0.0

    @api.constrains('workorder_id')
    def _check_open_time_ids(self):
        for workorder in self.workorder_id:
            open_time_ids_by_user = self.env["mrp.workcenter.productivity"].read_group([("id", "in", workorder.time_ids.ids), ("date_end", "=", False)], ["user_id", "open_time_ids_count:count(id)"], ["user_id"])
            if any(data["open_time_ids_count"] > 1 for data in open_time_ids_by_user):
                raise ValidationError(_('The Workorder (%s) cannot be started twice!', workorder.display_name))

    def button_block(self):
        self.ensure_one()
        self.workcenter_id.order_ids.end_all()

    def _close(self):
        underperformance_timers = self.env['mrp.workcenter.productivity']
        for timer in self:
            wo = timer.workorder_id
            timer.write({'date_end': fields.Datetime.now()})
            if wo.duration > wo.duration_expected:
                productive_date_end = timer.date_end - relativedelta.relativedelta(minutes=wo.duration - wo.duration_expected)
                if productive_date_end <= timer.date_start:
                    underperformance_timers |= timer
                else:
                    underperformance_timers |= timer.copy({'date_start': productive_date_end})
                    timer.write({'date_end': productive_date_end})
        if underperformance_timers:
            underperformance_type = self.env['mrp.workcenter.productivity.loss'].search([('loss_type', '=', 'performance')], limit=1)
            if not underperformance_type:
                raise UserError(_("You need to define at least one unactive productivity loss in the category 'Performance'. Create one from the Manufacturing app, menu: Configuration / Productivity Losses."))
            underperformance_timers.write({'loss_id': underperformance_type.id})


class MrpWorkCenterCapacity(models.Model):
    _name = 'mrp.workcenter.capacity'
    _description = 'Work Center Capacity'
    _check_company_auto = True

    workcenter_id = fields.Many2one('mrp.workcenter', string='Work Center', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Product UoM', related='product_id.uom_id')
    capacity = fields.Float('Capacity', default=1.0, help="Number of pieces that can be produced in parallel for this product.")
    time_start = fields.Float('Setup Time (minutes)', help="Additional time in minutes for the setup.")
    time_stop = fields.Float('Cleanup Time (minutes)', help="Additional time in minutes for the cleaning.")

    _sql_constraints = [
        ('positive_capacity', 'CHECK(capacity > 0)', 'Capacity should be a positive number.'),
        ('unique_product', 'UNIQUE(workcenter_id, product_id)', 'Product capacity should be unique for each workcenter.'),
    ]
