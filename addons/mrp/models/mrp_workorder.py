# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
import json

from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import float_compare, float_round, format_datetime


class MrpWorkorder(models.Model):
    _name = 'mrp.workorder'
    _description = 'Work Order'

    def _read_group_workcenter_id(self, workcenters, domain, order):
        workcenter_ids = self.env.context.get('default_workcenter_id')
        if not workcenter_ids:
            workcenter_ids = workcenters._search([], order=order, access_rights_uid=SUPERUSER_ID)
        return workcenters.browse(workcenter_ids)

    name = fields.Char(
        'Work Order', required=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    workcenter_id = fields.Many2one(
        'mrp.workcenter', 'Work Center', required=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)], 'progress': [('readonly', True)]},
        group_expand='_read_group_workcenter_id', check_company=True)
    working_state = fields.Selection(
        string='Workcenter Status', related='workcenter_id.working_state') # technical: used in views only
    product_id = fields.Many2one(related='production_id.product_id', readonly=True, store=True, check_company=True)
    product_tracking = fields.Selection(related="product_id.tracking")
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True, readonly=True)
    production_id = fields.Many2one('mrp.production', 'Manufacturing Order', required=True, check_company=True, readonly=True)
    production_availability = fields.Selection(
        string='Stock Availability', readonly=True,
        related='production_id.reservation_state', store=True) # Technical: used in views and domains only
    production_state = fields.Selection(
        string='Production State', readonly=True,
        related='production_id.state') # Technical: used in views only
    production_bom_id = fields.Many2one('mrp.bom', related='production_id.bom_id')
    qty_production = fields.Float('Original Production Quantity', readonly=True, related='production_id.product_qty')
    company_id = fields.Many2one(related='production_id.company_id')
    qty_producing = fields.Float(
        compute='_compute_qty_producing', inverse='_set_qty_producing',
        string='Currently Produced Quantity', digits='Product Unit of Measure')
    qty_remaining = fields.Float('Quantity To Be Produced', compute='_compute_qty_remaining', digits='Product Unit of Measure')
    qty_produced = fields.Float(
        'Quantity', default=0.0,
        readonly=True,
        digits='Product Unit of Measure',
        copy=False,
        help="The number of products already handled by this work order")
    is_produced = fields.Boolean(string="Has Been Produced",
        compute='_compute_is_produced')
    state = fields.Selection([
        ('pending', 'Waiting for another WO'),
        ('waiting', 'Waiting for components'),
        ('ready', 'Ready'),
        ('progress', 'In Progress'),
        ('done', 'Finished'),
        ('cancel', 'Cancelled')], string='Status',
        compute='_compute_state', store=True,
        default='pending', copy=False, readonly=True, recursive=True, index=True)
    leave_id = fields.Many2one(
        'resource.calendar.leaves',
        help='Slot into workcenter calendar once planned',
        check_company=True, copy=False)
    date_planned_start = fields.Datetime(
        'Scheduled Start Date',
        compute='_compute_dates_planned',
        inverse='_set_dates_planned',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        store=True, copy=False)
    date_planned_finished = fields.Datetime(
        'Scheduled End Date',
        compute='_compute_dates_planned',
        inverse='_set_dates_planned',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        store=True, copy=False)
    date_start = fields.Datetime(
        'Start Date', copy=False,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    date_finished = fields.Datetime(
        'End Date', copy=False,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})

    duration_expected = fields.Float(
        'Expected Duration', digits=(16, 2), compute='_compute_duration_expected',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        readonly=False, store=True) # in minutes
    duration = fields.Float(
        'Real Duration', compute='_compute_duration', inverse='_set_duration',
        readonly=False, store=True, copy=False)
    duration_unit = fields.Float(
        'Duration Per Unit', compute='_compute_duration',
        group_operator="avg", readonly=True, store=True)
    duration_percent = fields.Integer(
        'Duration Deviation (%)', compute='_compute_duration',
        group_operator="avg", readonly=True, store=True)
    progress = fields.Float('Progress Done (%)', digits=(16, 2), compute='_compute_progress')

    operation_id = fields.Many2one(
        'mrp.routing.workcenter', 'Operation', check_company=True)
        # Should be used differently as BoM can change in the meantime
    worksheet = fields.Binary(
        'Worksheet', related='operation_id.worksheet', readonly=True)
    worksheet_type = fields.Selection(
        string='Worksheet Type', related='operation_id.worksheet_type', readonly=True)
    worksheet_google_slide = fields.Char(
        'Worksheet URL', related='operation_id.worksheet_google_slide', readonly=True)
    operation_note = fields.Html("Description", related='operation_id.note', readonly=True)
    move_raw_ids = fields.One2many(
        'stock.move', 'workorder_id', 'Raw Moves',
        domain=[('raw_material_production_id', '!=', False), ('production_id', '=', False)])
    move_finished_ids = fields.One2many(
        'stock.move', 'workorder_id', 'Finished Moves',
        domain=[('raw_material_production_id', '=', False), ('production_id', '!=', False)])
    move_line_ids = fields.One2many(
        'stock.move.line', 'workorder_id', 'Moves to Track',
        help="Inventory moves for which you must scan a lot number at this work order")
    finished_lot_id = fields.Many2one(
        'stock.lot', string='Lot/Serial Number', compute='_compute_finished_lot_id',
        inverse='_set_finished_lot_id', domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]",
        check_company=True, search='_search_finished_lot_id')
    time_ids = fields.One2many(
        'mrp.workcenter.productivity', 'workorder_id', copy=False)
    is_user_working = fields.Boolean(
        'Is the Current User Working', compute='_compute_working_users') # technical: is the current user working
    working_user_ids = fields.One2many('res.users', string='Working user on this work order.', compute='_compute_working_users')
    last_working_user_id = fields.One2many('res.users', string='Last user that worked on this work order.', compute='_compute_working_users')
    costs_hour = fields.Float(
        string='Cost per hour',
        default=0.0, group_operator="avg")
        # Technical field to store the hourly cost of workcenter at time of work order completion (i.e. to keep a consistent cost).',

    scrap_ids = fields.One2many('stock.scrap', 'workorder_id')
    scrap_count = fields.Integer(compute='_compute_scrap_move_count', string='Scrap Move')
    production_date = fields.Datetime('Production Date', related='production_id.date_planned_start', store=True)
    json_popover = fields.Char('Popover Data JSON', compute='_compute_json_popover')
    show_json_popover = fields.Boolean('Show Popover?', compute='_compute_json_popover')
    consumption = fields.Selection(related='production_id.consumption')
    qty_reported_from_previous_wo = fields.Float('Carried Quantity', digits='Product Unit of Measure', copy=False,
        help="The quantity already produced awaiting allocation in the backorders chain.")
    is_planned = fields.Boolean(related='production_id.is_planned')
    allow_workorder_dependencies = fields.Boolean(related='production_id.allow_workorder_dependencies')
    blocked_by_workorder_ids = fields.Many2many('mrp.workorder', relation="mrp_workorder_dependencies_rel",
                                     column1="workorder_id", column2="blocked_by_id", string="Blocked By",
                                     domain="[('allow_workorder_dependencies', '=', True), ('id', '!=', id), ('production_id', '=', production_id)]",
                                     copy=False)
    needed_by_workorder_ids = fields.Many2many('mrp.workorder', relation="mrp_workorder_dependencies_rel",
                                     column1="blocked_by_id", column2="workorder_id", string="Blocks",
                                     domain="[('allow_workorder_dependencies', '=', True), ('id', '!=', id), ('production_id', '=', production_id)]",
                                     copy=False)

    @api.depends('production_availability', 'blocked_by_workorder_ids.state')
    def _compute_state(self):
        # Force to compute the production_availability right away.
        # It is a trick to force that the state of workorder is computed at the end of the
        # cyclic depends with the mo.state, mo.reservation_state and wo.state and avoid recursion error
        self.mapped('production_availability')
        for workorder in self:
            if workorder.state == 'pending':
                if all([wo.state in ('done', 'cancel') for wo in workorder.blocked_by_workorder_ids]):
                    workorder.state = 'ready' if workorder.production_availability == 'assigned' else 'waiting'
                    continue
            if workorder.state not in ('waiting', 'ready'):
                continue
            if not all([wo.state in ('done', 'cancel') for wo in workorder.blocked_by_workorder_ids]):
                workorder.state = 'pending'
                continue
            if workorder.production_availability not in ('waiting', 'confirmed', 'assigned'):
                continue
            if workorder.production_availability == 'assigned' and workorder.state == 'waiting':
                workorder.state = 'ready'
            elif workorder.production_availability != 'assigned' and workorder.state == 'ready':
                workorder.state = 'waiting'

    @api.depends('production_state', 'date_planned_start', 'date_planned_finished')
    def _compute_json_popover(self):
        if self.ids:
            conflicted_dict = self._get_conflicted_workorder_ids()
        for wo in self:
            infos = []
            if not wo.date_planned_start or not wo.date_planned_finished or not wo.ids:
                wo.show_json_popover = False
                wo.json_popover = False
                continue
            if wo.state in ('pending', 'waiting', 'ready'):
                previous_wos = wo.blocked_by_workorder_ids
                prev_start = min([workorder.date_planned_start for workorder in previous_wos]) if previous_wos else False
                prev_finished = max([workorder.date_planned_finished for workorder in previous_wos]) if previous_wos else False
                if wo.state == 'pending' and prev_start and not (prev_start > wo.date_planned_start):
                    infos.append({
                        'color': 'text-primary',
                        'msg': _("Waiting the previous work order, planned from %(start)s to %(end)s",
                            start=format_datetime(self.env, prev_start, dt_format=False),
                            end=format_datetime(self.env, prev_finished, dt_format=False))
                    })
                if wo.date_planned_finished < fields.Datetime.now():
                    infos.append({
                        'color': 'text-warning',
                        'msg': _("The work order should have already been processed.")
                    })
                if prev_start and prev_start > wo.date_planned_start:
                    infos.append({
                        'color': 'text-danger',
                        'msg': _("Scheduled before the previous work order, planned from %(start)s to %(end)s",
                            start=format_datetime(self.env, prev_start, dt_format=False),
                            end=format_datetime(self.env, prev_finished, dt_format=False))
                    })
                if conflicted_dict.get(wo.id):
                    infos.append({
                        'color': 'text-danger',
                        'msg': _("Planned at the same time as other workorder(s) at %s", wo.workcenter_id.display_name)
                    })
            color_icon = infos and infos[-1]['color'] or False
            wo.show_json_popover = bool(color_icon)
            wo.json_popover = json.dumps({
                'popoverTemplate': 'mrp.workorderPopover',
                'infos': infos,
                'color': color_icon,
                'icon': 'fa-exclamation-triangle' if color_icon in ['text-warning', 'text-danger'] else 'fa-info-circle',
                'replan': color_icon not in [False, 'text-primary']
            })

    @api.depends('production_id.lot_producing_id')
    def _compute_finished_lot_id(self):
        for workorder in self:
            workorder.finished_lot_id = workorder.production_id.lot_producing_id

    def _search_finished_lot_id(self, operator, value):
        return [('production_id.lot_producing_id', operator, value)]

    def _set_finished_lot_id(self):
        for workorder in self:
            workorder.production_id.lot_producing_id = workorder.finished_lot_id

    @api.depends('production_id.qty_producing')
    def _compute_qty_producing(self):
        for workorder in self:
            workorder.qty_producing = workorder.production_id.qty_producing

    def _set_qty_producing(self):
        for workorder in self:
            if workorder.qty_producing != 0 and workorder.production_id.qty_producing != workorder.qty_producing:
                workorder.production_id.qty_producing = workorder.qty_producing
                workorder.production_id._set_qty_producing()

    # Both `date_planned_start` and `date_planned_finished` are related fields on `leave_id`. Let's say
    # we slide a workorder on a gantt view, a single call to write is made with both
    # fields Changes. As the ORM doesn't batch the write on related fields and instead
    # makes multiple call, the constraint check_dates() is raised.
    # That's why the compute and set methods are needed. to ensure the dates are updated
    # in the same time.
    @api.depends('leave_id')
    def _compute_dates_planned(self):
        for workorder in self:
            workorder.date_planned_start = workorder.leave_id.date_from
            workorder.date_planned_finished = workorder.leave_id.date_to

    def _set_dates_planned(self):
        if not self[0].date_planned_start:
            if not self.leave_id:
                return
            raise UserError(_("It is not possible to unplan one single Work Order. "
                              "You should unplan the Manufacturing Order instead in order to unplan all the linked operations."))
        date_from = self[0].date_planned_start
        for wo in self:
            if not wo.date_planned_finished:
                wo.date_planned_finished = wo._calculate_date_planned_finished()
        date_to = self[0].date_planned_finished
        to_write = self.env['mrp.workorder']
        for wo in self.sudo():
            if wo.leave_id:
                to_write |= wo
            else:
                wo.leave_id = wo.env['resource.calendar.leaves'].create({
                    'name': wo.display_name,
                    'calendar_id': wo.workcenter_id.resource_calendar_id.id,
                    'date_from': date_from,
                    'date_to': date_to,
                    'resource_id': wo.workcenter_id.resource_id.id,
                    'time_type': 'other',
                })
        to_write.leave_id.write({
            'date_from': date_from,
            'date_to': date_to,
        })

    @api.constrains('blocked_by_workorder_ids')
    def _check_no_cyclic_dependencies(self):
        if not self._check_m2m_recursion('blocked_by_workorder_ids'):
            raise ValidationError(_("You cannot create cyclic dependency."))

    def name_get(self):
        res = []
        for wo in self:
            if len(wo.production_id.workorder_ids) == 1:
                res.append((wo.id, "%s - %s - %s" % (wo.production_id.name, wo.product_id.name, wo.name)))
            else:
                res.append((wo.id, "%s - %s - %s - %s" % (wo.production_id.workorder_ids.ids.index(wo._origin.id) + 1, wo.production_id.name, wo.product_id.name, wo.name)))
        return res

    def unlink(self):
        # Removes references to workorder to avoid Validation Error
        (self.mapped('move_raw_ids') | self.mapped('move_finished_ids')).write({'workorder_id': False})
        self.mapped('leave_id').unlink()
        mo_dirty = self.production_id.filtered(lambda mo: mo.state in ("confirmed", "progress", "to_close"))

        for workorder in self:
            workorder.blocked_by_workorder_ids.needed_by_workorder_ids = workorder.needed_by_workorder_ids
        res = super().unlink()
        # We need to go through `_action_confirm` for all workorders of the current productions to
        # make sure the links between them are correct (`next_work_order_id` could be obsolete now).
        mo_dirty.workorder_ids._action_confirm()
        return res

    @api.depends('production_id.product_qty', 'qty_produced', 'production_id.product_uom_id')
    def _compute_is_produced(self):
        self.is_produced = False
        for order in self.filtered(lambda p: p.production_id and p.production_id.product_uom_id):
            rounding = order.production_id.product_uom_id.rounding
            order.is_produced = float_compare(order.qty_produced, order.production_id.product_qty, precision_rounding=rounding) >= 0

    @api.depends('operation_id', 'workcenter_id', 'qty_producing', 'qty_production')
    def _compute_duration_expected(self):
        for workorder in self:
            # Recompute the duration expected if the qty_producing has been changed:
            # compare with the origin record if it happens during an onchange
            if workorder.state not in ['done', 'cancel'] and (workorder.qty_producing != workorder.qty_production
                or (workorder._origin != workorder and workorder._origin.qty_producing and workorder.qty_producing != workorder._origin.qty_producing)):
                workorder.duration_expected = workorder._get_duration_expected()

    @api.depends('time_ids.duration', 'qty_produced')
    def _compute_duration(self):
        for order in self:
            order.duration = sum(order.time_ids.mapped('duration'))
            order.duration_unit = round(order.duration / max(order.qty_produced, 1), 2)  # rounding 2 because it is a time
            if order.duration_expected:
                order.duration_percent = max(-2147483648, min(2147483647, 100 * (order.duration_expected - order.duration) / order.duration_expected))
            else:
                order.duration_percent = 0

    def _set_duration(self):

        def _float_duration_to_second(duration):
            minutes = duration // 1
            seconds = (duration % 1) * 60
            return minutes * 60 + seconds

        for order in self:
            old_order_duration = sum(order.time_ids.mapped('duration'))
            new_order_duration = order.duration
            if new_order_duration == old_order_duration:
                continue

            delta_duration = new_order_duration - old_order_duration

            if delta_duration > 0:
                enddate = datetime.now()
                date_start = enddate - timedelta(seconds=_float_duration_to_second(delta_duration))
                if order.duration_expected >= new_order_duration or old_order_duration >= order.duration_expected:
                    # either only productive or only performance (i.e. reduced speed) time respectively
                    self.env['mrp.workcenter.productivity'].create(
                        order._prepare_timeline_vals(new_order_duration, date_start, enddate)
                    )
                else:
                    # split between productive and performance (i.e. reduced speed) times
                    maxdate = fields.Datetime.from_string(enddate) - relativedelta(minutes=new_order_duration - order.duration_expected)
                    self.env['mrp.workcenter.productivity'].create([
                        order._prepare_timeline_vals(order.duration_expected, date_start, maxdate),
                        order._prepare_timeline_vals(new_order_duration, maxdate, enddate)
                    ])
            else:
                duration_to_remove = abs(delta_duration)
                timelines_to_unlink = self.env['mrp.workcenter.productivity']
                for timeline in order.time_ids.sorted():
                    if duration_to_remove <= 0.0:
                        break
                    if timeline.duration <= duration_to_remove:
                        duration_to_remove -= timeline.duration
                        timelines_to_unlink |= timeline
                    else:
                        new_time_line_duration = timeline.duration - duration_to_remove
                        timeline.date_start = timeline.date_end - timedelta(seconds=_float_duration_to_second(new_time_line_duration))
                        break
                timelines_to_unlink.unlink()

    @api.depends('duration', 'duration_expected', 'state')
    def _compute_progress(self):
        for order in self:
            if order.state == 'done':
                order.progress = 100
            elif order.duration_expected:
                order.progress = order.duration * 100 / order.duration_expected
            else:
                order.progress = 0

    def _compute_working_users(self):
        """ Checks whether the current user is working, all the users currently working and the last user that worked. """
        for order in self:
            order.working_user_ids = [(4, order.id) for order in order.time_ids.filtered(lambda time: not time.date_end).sorted('date_start').mapped('user_id')]
            if order.working_user_ids:
                order.last_working_user_id = order.working_user_ids[-1]
            elif order.time_ids:
                order.last_working_user_id = order.time_ids.filtered('date_end').sorted('date_end')[-1].user_id if order.time_ids.filtered('date_end') else order.time_ids[-1].user_id
            else:
                order.last_working_user_id = False
            if order.time_ids.filtered(lambda x: (x.user_id.id == self.env.user.id) and (not x.date_end) and (x.loss_type in ('productive', 'performance'))):
                order.is_user_working = True
            else:
                order.is_user_working = False

    def _compute_scrap_move_count(self):
        data = self.env['stock.scrap']._read_group([('workorder_id', 'in', self.ids)], ['workorder_id'], ['workorder_id'])
        count_data = dict((item['workorder_id'][0], item['workorder_id_count']) for item in data)
        for workorder in self:
            workorder.scrap_count = count_data.get(workorder.id, 0)

    @api.onchange('operation_id')
    def _onchange_operation_id(self):
        if self.operation_id:
            self.name = self.operation_id.name
            self.workcenter_id = self.operation_id.workcenter_id.id

    @api.onchange('date_planned_start', 'duration_expected', 'workcenter_id')
    def _onchange_date_planned_start(self):
        if self.date_planned_start and self.workcenter_id:
            self.date_planned_finished = self._calculate_date_planned_finished()

    def _calculate_date_planned_finished(self, date_planned_start=False):
        return self.workcenter_id.resource_calendar_id.plan_hours(
            self.duration_expected / 60.0, date_planned_start or self.date_planned_start,
            compute_leaves=True, domain=[('time_type', 'in', ['leave', 'other'])]
        )

    @api.onchange('date_planned_finished')
    def _onchange_date_planned_finished(self):
        if self.date_planned_start and self.date_planned_finished and self.workcenter_id:
            self.duration_expected = self._calculate_duration_expected()

        if not self.date_planned_finished and self.date_planned_start:
            raise UserError(_("It is not possible to unplan one single Work Order. "
                              "You should unplan the Manufacturing Order instead in order to unplan all the linked operations."))

    def _calculate_duration_expected(self, date_planned_start=False, date_planned_finished=False):
        interval = self.workcenter_id.resource_calendar_id.get_work_duration_data(
            date_planned_start or self.date_planned_start, date_planned_finished or self.date_planned_finished,
            domain=[('time_type', 'in', ['leave', 'other'])]
        )
        return interval['hours'] * 60

    @api.onchange('finished_lot_id')
    def _onchange_finished_lot_id(self):
        if self.production_id:
            res = self.production_id._can_produce_serial_number(sn=self.finished_lot_id)
            if res is not True:
                return res

    def write(self, values):
        if 'production_id' in values and any(values['production_id'] != w.production_id.id for w in self):
            raise UserError(_('You cannot link this work order to another manufacturing order.'))
        if 'workcenter_id' in values:
            for workorder in self:
                if workorder.workcenter_id.id != values['workcenter_id']:
                    if workorder.state in ('progress', 'done', 'cancel'):
                        raise UserError(_('You cannot change the workcenter of a work order that is in progress or done.'))
                    workorder.leave_id.resource_id = self.env['mrp.workcenter'].browse(values['workcenter_id']).resource_id
        if 'date_planned_start' in values or 'date_planned_finished' in values:
            for workorder in self:
                start_date = fields.Datetime.to_datetime(values.get('date_planned_start', workorder.date_planned_start))
                end_date = fields.Datetime.to_datetime(values.get('date_planned_finished', workorder.date_planned_finished))
                if start_date and end_date and start_date > end_date:
                    raise UserError(_('The planned end date of the work order cannot be prior to the planned start date, please correct this to save the work order.'))
                if 'duration_expected' not in values and not self.env.context.get('bypass_duration_calculation'):
                    if values.get('date_planned_start') and values.get('date_planned_finished'):
                        computed_finished_time = workorder._calculate_date_planned_finished(start_date)
                        values['date_planned_finished'] = computed_finished_time
                    elif start_date and end_date:
                        computed_duration = workorder._calculate_duration_expected(date_planned_start=start_date, date_planned_finished=end_date)
                        values['duration_expected'] = computed_duration
                # Update MO dates if the start date of the first WO or the
                # finished date of the last WO is update.
                if workorder == workorder.production_id.workorder_ids[0] and 'date_planned_start' in values:
                    if values['date_planned_start']:
                        workorder.production_id.with_context(force_date=True).write({
                            'date_planned_start': fields.Datetime.to_datetime(values['date_planned_start'])
                        })
                if workorder == workorder.production_id.workorder_ids[-1] and 'date_planned_finished' in values:
                    if values['date_planned_finished']:
                        workorder.production_id.with_context(force_date=True).write({
                            'date_planned_finished': fields.Datetime.to_datetime(values['date_planned_finished'])
                        })
        return super(MrpWorkorder, self).write(values)

    @api.model_create_multi
    def create(self, values):
        res = super().create(values)
        # Auto-confirm manually added workorders.
        # We need to go through `_action_confirm` for all workorders of the current productions to
        # make sure the links between them are correct.
        if self.env.context.get('skip_confirm'):
            return res
        to_confirm = res.filtered(lambda wo: wo.production_id.state in ("confirmed", "progress", "to_close"))
        to_confirm = to_confirm.production_id.workorder_ids
        to_confirm._action_confirm()
        return res

    def _action_confirm(self):
        for production in self.mapped("production_id"):
            production._link_workorders_and_moves()

    def _get_byproduct_move_to_update(self):
        return self.production_id.move_finished_ids.filtered(lambda x: (x.product_id.id != self.production_id.product_id.id) and (x.state not in ('done', 'cancel')))

    def _plan_workorder(self, replan=False):
        self.ensure_one()
        # Plan workorder after its predecessors
        start_date = max(self.production_id.date_planned_start, datetime.now())
        for workorder in self.blocked_by_workorder_ids:
            workorder._plan_workorder(replan)
            if workorder.date_planned_finished and workorder.date_planned_finished > start_date:
                start_date = workorder.date_planned_finished
        # Plan only suitable workorders
        if self.state not in ['pending', 'waiting', 'ready']:
            return
        if self.leave_id:
            if replan:
                self.leave_id.unlink()
            else:
                return
        # Consider workcenter and alternatives
        workcenters = self.workcenter_id | self.workcenter_id.alternative_workcenter_ids
        best_finished_date = datetime.max
        vals = {}
        for workcenter in workcenters:
            # Compute theoretical duration
            if self.workcenter_id == workcenter:
                duration_expected = self.duration_expected
            else:
                duration_expected = self._get_duration_expected(alternative_workcenter=workcenter)
            from_date, to_date = workcenter._get_first_available_slot(start_date, duration_expected)
            # If the workcenter is unavailable, try planning on the next one
            if not from_date:
                continue
            # Check if this workcenter is better than the previous ones
            if to_date and to_date < best_finished_date:
                best_start_date = from_date
                best_finished_date = to_date
                best_workcenter = workcenter
                vals = {
                    'workcenter_id': workcenter.id,
                    'duration_expected': duration_expected,
                }
        # If none of the workcenter are available, raise
        if best_finished_date == datetime.max:
            raise UserError(_('Impossible to plan the workorder. Please check the workcenter availabilities.'))
        # Create leave on chosen workcenter calendar
        leave = self.env['resource.calendar.leaves'].create({
            'name': self.display_name,
            'calendar_id': best_workcenter.resource_calendar_id.id,
            'date_from': best_start_date,
            'date_to': best_finished_date,
            'resource_id': best_workcenter.resource_id.id,
            'time_type': 'other'
        })
        vals['leave_id'] = leave.id
        self.write(vals)

    def _cal_cost(self, times=None):
        self.ensure_one()
        times = times or self.time_ids
        duration = sum(times.mapped('duration'))
        return (duration / 60.0) * self.workcenter_id.costs_hour

    @api.model
    def gantt_unavailability(self, start_date, end_date, scale, group_bys=None, rows=None):
        """Get unavailabilities data to display in the Gantt view."""
        workcenter_ids = set()

        def traverse_inplace(func, row, **kargs):
            res = func(row, **kargs)
            if res:
                kargs.update(res)
            for row in row.get('rows'):
                traverse_inplace(func, row, **kargs)

        def search_workcenter_ids(row):
            if row.get('groupedBy') and row.get('groupedBy')[0] == 'workcenter_id' and row.get('resId'):
                workcenter_ids.add(row.get('resId'))

        for row in rows:
            traverse_inplace(search_workcenter_ids, row)
        start_datetime = fields.Datetime.to_datetime(start_date)
        end_datetime = fields.Datetime.to_datetime(end_date)
        workcenters = self.env['mrp.workcenter'].browse(workcenter_ids)
        unavailability_mapping = workcenters._get_unavailability_intervals(start_datetime, end_datetime)

        # Only notable interval (more than one case) is send to the front-end (avoid sending useless information)
        cell_dt = (scale in ['day', 'week'] and timedelta(hours=1)) or (scale == 'month' and timedelta(days=1)) or timedelta(days=28)

        def add_unavailability(row, workcenter_id=None):
            if row.get('groupedBy') and row.get('groupedBy')[0] == 'workcenter_id' and row.get('resId'):
                workcenter_id = row.get('resId')
            if workcenter_id:
                notable_intervals = filter(lambda interval: interval[1] - interval[0] >= cell_dt, unavailability_mapping[workcenter_id])
                row['unavailabilities'] = [{'start': interval[0], 'stop': interval[1]} for interval in notable_intervals]
                return {'workcenter_id': workcenter_id}

        for row in rows:
            traverse_inplace(add_unavailability, row)
        return rows

    def button_start(self):
        self.ensure_one()
        if any(not time.date_end for time in self.time_ids.filtered(lambda t: t.user_id.id == self.env.user.id)):
            return True
        # As button_start is automatically called in the new view
        if self.state in ('done', 'cancel'):
            return True

        if self.production_id.state != 'progress':
            self.production_id.write({
                'date_start': datetime.now(),
            })

        if self.product_tracking == 'serial' and self.qty_producing == 0:
            self.qty_producing = 1.0
        elif self.qty_producing == 0:
            self.qty_producing = self.qty_remaining

        if self._should_start_timer():
            self.env['mrp.workcenter.productivity'].create(
                self._prepare_timeline_vals(self.duration, datetime.now())
            )

        if self.state == 'progress':
            return True
        start_date = datetime.now()
        vals = {
            'state': 'progress',
            'date_start': start_date,
        }
        if not self.leave_id:
            leave = self.env['resource.calendar.leaves'].create({
                'name': self.display_name,
                'calendar_id': self.workcenter_id.resource_calendar_id.id,
                'date_from': start_date,
                'date_to': start_date + relativedelta(minutes=self.duration_expected),
                'resource_id': self.workcenter_id.resource_id.id,
                'time_type': 'other'
            })
            vals['leave_id'] = leave.id
            return self.write(vals)
        else:
            if not self.date_planned_start or self.date_planned_start > start_date:
                vals['date_planned_start'] = start_date
                vals['date_planned_finished'] = self._calculate_date_planned_finished(start_date)
            if self.date_planned_finished and self.date_planned_finished < start_date:
                vals['date_planned_finished'] = start_date
            return self.with_context(bypass_duration_calculation=True).write(vals)

    def button_finish(self):
        end_date = fields.Datetime.now()
        for workorder in self:
            if workorder.state in ('done', 'cancel'):
                continue
            workorder.end_all()
            vals = {
                'qty_produced': workorder.qty_produced or workorder.qty_producing or workorder.qty_production,
                'state': 'done',
                'date_finished': end_date,
                'date_planned_finished': end_date,
                'costs_hour': workorder.workcenter_id.costs_hour
            }
            if not workorder.date_start:
                vals['date_start'] = end_date
            if not workorder.date_planned_start or end_date < workorder.date_planned_start:
                vals['date_planned_start'] = end_date
            workorder.with_context(bypass_duration_calculation=True).write(vals)
        return True

    def _domain_mrp_workcenter_productivity(self, doall):
        domain = [('workorder_id', 'in', self.ids), ('date_end', '=', False)]
        if not doall:
            domain = expression.AND([domain, [('user_id', '=', self.env.user.id)]])
        return domain

    def end_previous(self, doall=False):
        """
        @param: doall:  This will close all open time lines on the open work orders when doall = True, otherwise
        only the one of the current user
        """
        # TDE CLEANME
        self.env['mrp.workcenter.productivity'].search(
            self._domain_mrp_workcenter_productivity(doall),
            limit=None if doall else 1
        )._close()
        return True

    def end_all(self):
        return self.end_previous(doall=True)

    def button_pending(self):
        self.end_previous()
        return True

    def button_unblock(self):
        for order in self:
            order.workcenter_id.unblock()
        return True

    def action_cancel(self):
        self.leave_id.unlink()
        self.end_all()
        return self.write({'state': 'cancel'})

    def action_replan(self):
        """Replan a work order.

        It actually replans every  "ready" or "pending"
        work orders of the linked manufacturing orders.
        """
        for production in self.production_id:
            production._plan_workorders(replan=True)
        return True

    def button_done(self):
        if any(x.state in ('done', 'cancel') for x in self):
            raise UserError(_('A Manufacturing Order is already done or cancelled.'))
        self.end_all()
        end_date = datetime.now()
        return self.write({
            'state': 'done',
            'date_finished': end_date,
            'date_planned_finished': end_date,
            'costs_hour': self.workcenter_id.costs_hour
        })

    def button_scrap(self):
        self.ensure_one()
        return {
            'name': _('Scrap'),
            'view_mode': 'form',
            'res_model': 'stock.scrap',
            'views': [(self.env.ref('stock.stock_scrap_form_view2').id, 'form')],
            'type': 'ir.actions.act_window',
            'context': {'default_company_id': self.production_id.company_id.id,
                        'default_workorder_id': self.id,
                        'default_production_id': self.production_id.id,
                        'product_ids': (self.production_id.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel')) | self.production_id.move_finished_ids.filtered(lambda x: x.state == 'done')).mapped('product_id').ids},
            'target': 'new',
        }

    def action_see_move_scrap(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_stock_scrap")
        action['domain'] = [('workorder_id', '=', self.id)]
        return action

    def action_open_wizard(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.mrp_workorder_mrp_production_form")
        action['res_id'] = self.id
        return action

    @api.depends('qty_production', 'qty_reported_from_previous_wo', 'qty_produced', 'production_id.product_uom_id')
    def _compute_qty_remaining(self):
        for wo in self:
            if wo.production_id.product_uom_id:
                wo.qty_remaining = max(float_round(wo.qty_production - wo.qty_reported_from_previous_wo - wo.qty_produced, precision_rounding=wo.production_id.product_uom_id.rounding), 0)
            else:
                wo.qty_remaining = 0

    def _get_duration_expected(self, alternative_workcenter=False, ratio=1):
        self.ensure_one()
        if not self.workcenter_id:
            return self.duration_expected
        if not self.operation_id:
            duration_expected_working = (self.duration_expected - self.workcenter_id.time_start - self.workcenter_id.time_stop) * self.workcenter_id.time_efficiency / 100.0
            if duration_expected_working < 0:
                duration_expected_working = 0
            if self.qty_producing not in (0, self.qty_production, self._origin.qty_producing):
                qty_ratio = self.qty_producing / (self._origin.qty_producing or self.qty_production)
            else:
                qty_ratio = 1
            return self.workcenter_id._get_expected_duration(self.product_id) + duration_expected_working * qty_ratio * ratio * 100.0 / self.workcenter_id.time_efficiency
        qty_production = self.production_id.product_uom_id._compute_quantity(self.qty_producing or self.qty_production, self.production_id.product_id.uom_id)
        capacity = self.workcenter_id._get_capacity(self.product_id)
        cycle_number = float_round(qty_production / capacity, precision_digits=0, rounding_method='UP')
        if alternative_workcenter:
            # TODO : find a better alternative : the settings of workcenter can change
            duration_expected_working = (self.duration_expected - self.workcenter_id._get_expected_duration(self.product_id)) * self.workcenter_id.time_efficiency / (100.0 * cycle_number)
            if duration_expected_working < 0:
                duration_expected_working = 0
            capacity = alternative_workcenter._get_capacity(self.product_id)
            alternative_wc_cycle_nb = float_round(qty_production / capacity, precision_digits=0, rounding_method='UP')
            return alternative_workcenter._get_expected_duration(self.product_id) + alternative_wc_cycle_nb * duration_expected_working * 100.0 / alternative_workcenter.time_efficiency
        time_cycle = self.operation_id.time_cycle
        return self.workcenter_id._get_expected_duration(self.product_id) + cycle_number * time_cycle * 100.0 / self.workcenter_id.time_efficiency

    def _get_conflicted_workorder_ids(self):
        """Get conlicted workorder(s) with self.

        Conflict means having two workorders in the same time in the same workcenter.

        :return: defaultdict with key as workorder id of self and value as related conflicted workorder
        """
        self.flush_model(['state', 'date_planned_start', 'date_planned_finished', 'workcenter_id'])
        sql = """
            SELECT wo1.id, wo2.id
            FROM mrp_workorder wo1, mrp_workorder wo2
            WHERE
                wo1.id IN %s
                AND wo1.state IN ('pending', 'waiting', 'ready')
                AND wo2.state IN ('pending', 'waiting', 'ready')
                AND wo1.id != wo2.id
                AND wo1.workcenter_id = wo2.workcenter_id
                AND (DATE_TRUNC('second', wo2.date_planned_start), DATE_TRUNC('second', wo2.date_planned_finished))
                    OVERLAPS (DATE_TRUNC('second', wo1.date_planned_start), DATE_TRUNC('second', wo1.date_planned_finished))
        """
        self.env.cr.execute(sql, [tuple(self.ids)])
        res = defaultdict(list)
        for wo1, wo2 in self.env.cr.fetchall():
            res[wo1].append(wo2)
        return res

    def _prepare_timeline_vals(self, duration, date_start, date_end=False):
        # Need a loss in case of the real time exceeding the expected
        if not self.duration_expected or duration <= self.duration_expected:
            loss_id = self.env['mrp.workcenter.productivity.loss'].search([('loss_type', '=', 'productive')], limit=1)
            if not len(loss_id):
                raise UserError(_("You need to define at least one productivity loss in the category 'Productivity'. Create one from the Manufacturing app, menu: Configuration / Productivity Losses."))
        else:
            loss_id = self.env['mrp.workcenter.productivity.loss'].search([('loss_type', '=', 'performance')], limit=1)
            if not len(loss_id):
                raise UserError(_("You need to define at least one productivity loss in the category 'Performance'. Create one from the Manufacturing app, menu: Configuration / Productivity Losses."))
        return {
            'workorder_id': self.id,
            'workcenter_id': self.workcenter_id.id,
            'description': _('Time Tracking: %(user)s', user=self.env.user.name),
            'loss_id': loss_id[0].id,
            'date_start': date_start.replace(microsecond=0),
            'date_end': date_end.replace(microsecond=0) if date_end else date_end,
            'user_id': self.env.user.id,  # FIXME sle: can be inconsistent with company_id
            'company_id': self.company_id.id,
        }

    def _update_finished_move(self):
        """ Update the finished move & move lines in order to set the finished
        product lot on it as well as the produced quantity. This method get the
        information either from the last workorder or from the Produce wizard."""
        production_move = self.production_id.move_finished_ids.filtered(
            lambda move: move.product_id == self.product_id and
            move.state not in ('done', 'cancel')
        )
        if not production_move:
            return
        if production_move.product_id.tracking != 'none':
            if not self.finished_lot_id:
                raise UserError(_('You need to provide a lot for the finished product.'))
            move_line = production_move.move_line_ids.filtered(
                lambda line: line.lot_id.id == self.finished_lot_id.id
            )
            if move_line:
                if self.product_id.tracking == 'serial':
                    raise UserError(_('You cannot produce the same serial number twice.'))
                move_line.reserved_uom_qty += self.qty_producing
                move_line.qty_done += self.qty_producing
            else:
                quantity = self.product_uom_id._compute_quantity(self.qty_producing, self.product_id.uom_id, rounding_method='HALF-UP')
                putaway_location = production_move.location_dest_id._get_putaway_strategy(self.product_id, quantity)
                move_line.create({
                    'move_id': production_move.id,
                    'product_id': production_move.product_id.id,
                    'lot_id': self.finished_lot_id.id,
                    'reserved_uom_qty': self.qty_producing,
                    'product_uom_id': self.product_uom_id.id,
                    'qty_done': self.qty_producing,
                    'location_id': production_move.location_id.id,
                    'location_dest_id': putaway_location.id,
                })
        else:
            rounding = production_move.product_uom.rounding
            production_move._set_quantity_done(
                float_round(self.qty_producing, precision_rounding=rounding)
            )

    def _check_sn_uniqueness(self):
        # todo master: remove
        pass

    def _should_start_timer(self):
        return True

    def _update_qty_producing(self, quantity):
        self.ensure_one()
        if self.qty_producing:
            self.qty_producing = quantity

    def get_working_duration(self):
        """Get the additional duration for 'open times' i.e. productivity lines with no date_end."""
        self.ensure_one()
        duration = 0
        for time in self.time_ids.filtered(lambda time: not time.date_end):
            duration += (datetime.now() - time.date_start).total_seconds() / 60
        return duration
