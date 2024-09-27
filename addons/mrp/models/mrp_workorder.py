# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, format_datetime, float_is_zero, float_round


class MrpWorkorder(models.Model):
    _name = 'mrp.workorder'
    _description = 'Work Order'
    _order = 'sequence, leave_id, date_start, id'

    def _default_sequence(self):
        return self.operation_id.sequence or 100

    def _read_group_workcenter_id(self, workcenters, domain):
        workcenter_ids = self.env.context.get('default_workcenter_id')
        if not workcenter_ids:
            # bypass ir.model.access checks, but search with ir.rules
            search_domain = self.env['ir.rule']._compute_domain(workcenters._name)
            workcenter_ids = workcenters.sudo()._search(search_domain, order=workcenters._order)
        return workcenters.browse(workcenter_ids)

    name = fields.Char(
        'Work Order', required=True)
    sequence = fields.Integer("Sequence", default=_default_sequence)
    barcode = fields.Char(compute='_compute_barcode', store=True)
    workcenter_id = fields.Many2one(
        'mrp.workcenter', 'Work Center', required=True,
        group_expand='_read_group_workcenter_id', check_company=True)
    working_state = fields.Selection(
        string='Workcenter Status', related='workcenter_id.working_state') # technical: used in views only
    product_id = fields.Many2one(related='production_id.product_id', readonly=True, store=True, check_company=True)
    product_tracking = fields.Selection(related="product_id.tracking")
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True, readonly=True)
    production_id = fields.Many2one('mrp.production', 'Manufacturing Order', required=True, check_company=True, readonly=True, index='btree')
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
    date_start = fields.Datetime(
        'Start',
        compute='_compute_dates',
        inverse='_set_dates',
        store=True, copy=False)
    date_finished = fields.Datetime(
        'End',
        compute='_compute_dates',
        inverse='_set_dates',
        store=True, copy=False)
    duration_expected = fields.Float(
        'Expected Duration', digits=(16, 2), compute='_compute_duration_expected',
        readonly=False, store=True) # in minutes
    duration = fields.Float(
        'Real Duration', compute='_compute_duration', inverse='_set_duration',
        readonly=False, store=True, copy=False)
    duration_unit = fields.Float(
        'Duration Per Unit', compute='_compute_duration',
        aggregator="avg", readonly=True, store=True)
    duration_percent = fields.Integer(
        'Duration Deviation (%)', compute='_compute_duration',
        aggregator="avg", readonly=True, store=True)
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
        'stock.lot', string='Lot/Serial Number', related='production_id.lot_producing_id',
        domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]",
        readonly=False, check_company=True)
    time_ids = fields.One2many(
        'mrp.workcenter.productivity', 'workorder_id', copy=False)
    is_user_working = fields.Boolean(
        'Is the Current User Working', compute='_compute_working_users') # technical: is the current user working
    working_user_ids = fields.One2many('res.users', string='Working user on this work order.', compute='_compute_working_users')
    last_working_user_id = fields.One2many('res.users', string='Last user that worked on this work order.', compute='_compute_working_users')
    costs_hour = fields.Float(
        string='Cost per hour',
        default=0.0, aggregator="avg")
        # Technical field to store the hourly cost of workcenter at time of work order completion (i.e. to keep a consistent cost).',

    scrap_ids = fields.One2many('stock.scrap', 'workorder_id')
    scrap_count = fields.Integer(compute='_compute_scrap_move_count', string='Scrap Move')
    production_date = fields.Datetime('Production Date', compute='_compute_production_date', store=True)
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

    @api.depends('production_id.date_start', 'date_start')
    def _compute_production_date(self):
        for workorder in self:
            workorder.production_date = workorder.date_start or workorder.production_id.date_start

    @api.depends('production_state', 'date_start', 'date_finished')
    def _compute_json_popover(self):
        if self.ids:
            conflicted_dict = self._get_conflicted_workorder_ids()
        for wo in self:
            infos = []
            if not wo.date_start or not wo.date_finished or not wo.ids:
                wo.show_json_popover = False
                wo.json_popover = False
                continue
            if wo.state in ('pending', 'waiting', 'ready'):
                previous_wos = wo.blocked_by_workorder_ids
                prev_start = min([workorder.date_start for workorder in previous_wos]) if previous_wos else False
                prev_finished = max([workorder.date_finished for workorder in previous_wos]) if previous_wos else False
                if wo.state == 'pending' and prev_start and not (prev_start > wo.date_start):
                    infos.append({
                        'color': 'text-primary',
                        'msg': _("Waiting the previous work order, planned from %(start)s to %(end)s",
                            start=format_datetime(self.env, prev_start, dt_format=False),
                            end=format_datetime(self.env, prev_finished, dt_format=False))
                    })
                if wo.date_finished < fields.Datetime.now():
                    infos.append({
                        'color': 'text-warning',
                        'msg': _("The work order should have already been processed.")
                    })
                if prev_start and prev_start > wo.date_start:
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

    @api.depends('production_id.qty_producing')
    def _compute_qty_producing(self):
        for workorder in self:
            workorder.qty_producing = workorder.production_id.qty_producing

    def _set_qty_producing(self):
        for workorder in self:
            if workorder.qty_producing != 0 and workorder.production_id.qty_producing != workorder.qty_producing:
                workorder.production_id.qty_producing = workorder.qty_producing
                workorder.production_id._set_qty_producing()

    # Both `date_start` and `date_finished` are related fields on `leave_id`. Let's say
    # we slide a workorder on a gantt view, a single call to write is made with both
    # fields Changes. As the ORM doesn't batch the write on related fields and instead
    # makes multiple call, the constraint check_dates() is raised.
    # That's why the compute and set methods are needed. to ensure the dates are updated
    # in the same time.
    @api.depends('leave_id')
    def _compute_dates(self):
        for workorder in self:
            workorder.date_start = workorder.leave_id.date_from
            workorder.date_finished = workorder.leave_id.date_to

    def _set_dates(self):
        for wo in self.sudo():
            if wo.leave_id:
                if (not wo.date_start or not wo.date_finished):
                    raise UserError(_("It is not possible to unplan one single Work Order. "
                              "You should unplan the Manufacturing Order instead in order to unplan all the linked operations."))
                wo.leave_id.write({
                    'date_from': wo.date_start,
                    'date_to': wo.date_finished,
                })
            elif wo.date_start:
                wo.date_finished = wo._calculate_date_finished()
                wo.leave_id = wo.env['resource.calendar.leaves'].create({
                    'name': wo.display_name,
                    'calendar_id': wo.workcenter_id.resource_calendar_id.id,
                    'date_from': wo.date_start,
                    'date_to': wo.date_finished,
                    'resource_id': wo.workcenter_id.resource_id.id,
                    'time_type': 'other',
                })

    @api.constrains('blocked_by_workorder_ids')
    def _check_no_cyclic_dependencies(self):
        if self._has_cycle('blocked_by_workorder_ids'):
            raise ValidationError(_("You cannot create cyclic dependency."))

    @api.depends('production_id.name')
    def _compute_barcode(self):
        for wo in self:
            wo.barcode = f"{wo.production_id.name}/{wo.id}"

    @api.depends('production_id', 'product_id')
    @api.depends_context('prefix_product')
    def _compute_display_name(self):
        for wo in self:
            wo.display_name = f"{wo.production_id.name} - {wo.name}"
            if self.env.context.get('prefix_product'):
                wo.display_name = f"{wo.product_id.name} - {wo.production_id.name} - {wo.name}"

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
                if order.state not in ('progress', 'done'):
                    order.state = 'progress'
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
        data = self.env['stock.scrap']._read_group([('workorder_id', 'in', self.ids)], ['workorder_id'], ['__count'])
        count_data = {workorder.id: count for workorder, count in data}
        for workorder in self:
            workorder.scrap_count = count_data.get(workorder.id, 0)

    @api.onchange('operation_id')
    def _onchange_operation_id(self):
        if self.operation_id:
            self.name = self.operation_id.name
            self.workcenter_id = self.operation_id.workcenter_id.id

    @api.onchange('date_start', 'duration_expected', 'workcenter_id')
    def _onchange_date_start(self):
        if self.date_start and self.workcenter_id:
            self.date_finished = self._calculate_date_finished()

    def _calculate_date_finished(self, date_finished=False):
        return self.workcenter_id.resource_calendar_id.plan_hours(
            self.duration_expected / 60.0, date_finished or self.date_start,
            compute_leaves=True, domain=[('time_type', 'in', ['leave', 'other'])]
        )

    @api.onchange('date_finished')
    def _onchange_date_finished(self):
        if self.date_start and self.date_finished and self.workcenter_id:
            self.duration_expected = self._calculate_duration_expected()
        if not self.date_finished and self.date_start:
            raise UserError(_("It is not possible to unplan one single Work Order. "
                              "You should unplan the Manufacturing Order instead in order to unplan all the linked operations."))

    def _calculate_duration_expected(self, date_start=False, date_finished=False):
        interval = self.workcenter_id.resource_calendar_id.get_work_duration_data(
            date_start or self.date_start, date_finished or self.date_finished,
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
                    workorder.duration_expected = workorder._get_duration_expected()
                    if workorder.date_start:
                        workorder.date_finished = workorder._calculate_date_finished()
        if 'date_start' in values or 'date_finished' in values:
            for workorder in self:
                date_start = fields.Datetime.to_datetime(values.get('date_start', workorder.date_start))
                date_finished = fields.Datetime.to_datetime(values.get('date_finished', workorder.date_finished))
                if date_start and date_finished and date_start > date_finished:
                    raise UserError(_('The planned end date of the work order cannot be prior to the planned start date, please correct this to save the work order.'))
                if 'duration_expected' not in values and not self.env.context.get('bypass_duration_calculation'):
                    if values.get('date_start') and values.get('date_finished'):
                        computed_finished_time = workorder._calculate_date_finished(date_start)
                        values['date_finished'] = computed_finished_time
                    elif date_start and date_finished:
                        computed_duration = workorder._calculate_duration_expected(date_start=date_start, date_finished=date_finished)
                        values['duration_expected'] = computed_duration
                # Update MO dates if the start date of the first WO or the
                # finished date of the last WO is update.
                if workorder == workorder.production_id.workorder_ids[0] and 'date_start' in values:
                    if values['date_start']:
                        workorder.production_id.with_context(force_date=True).write({
                            'date_start': fields.Datetime.to_datetime(values['date_start'])
                        })
                if workorder == workorder.production_id.workorder_ids[-1] and 'date_finished' in values:
                    if values['date_finished']:
                        workorder.production_id.with_context(force_date=True).write({
                            'date_finished': fields.Datetime.to_datetime(values['date_finished'])
                        })
        return super(MrpWorkorder, self).write(values)

    @api.model_create_multi
    def create(self, values):
        res = super().create(values)

        # resequence the workorders if necessary
        for mo in res.mapped('production_id'):
            if len(set(mo.workorder_ids.mapped('sequence'))) != len(mo.workorder_ids):
                mo._resequence_workorders()

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
        date_start = max(self.production_id.date_start, datetime.now())
        for workorder in self.blocked_by_workorder_ids:
            if workorder.state in ['done', 'cancel']:
                continue
            workorder._plan_workorder(replan)
            if workorder.date_finished and workorder.date_finished > date_start:
                date_start = workorder.date_finished
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
        best_date_finished = datetime.max
        vals = {}
        for workcenter in workcenters:
            if not workcenter.resource_calendar_id:
                raise UserError(_('There is no defined calendar on workcenter %s.', workcenter.name))
            # Compute theoretical duration
            if self.workcenter_id == workcenter:
                duration_expected = self.duration_expected
            else:
                duration_expected = self._get_duration_expected(alternative_workcenter=workcenter)
            from_date, to_date = workcenter._get_first_available_slot(date_start, duration_expected)
            # If the workcenter is unavailable, try planning on the next one
            if not from_date:
                continue
            # Check if this workcenter is better than the previous ones
            if to_date and to_date < best_date_finished:
                best_date_start = from_date
                best_date_finished = to_date
                best_workcenter = workcenter
                vals = {
                    'workcenter_id': workcenter.id,
                    'duration_expected': duration_expected,
                }
        # If none of the workcenter are available, raise
        if best_date_finished == datetime.max:
            raise UserError(_('Impossible to plan the workorder. Please check the workcenter availabilities.'))
        # Create leave on chosen workcenter calendar
        leave = self.env['resource.calendar.leaves'].create({
            'name': self.display_name,
            'calendar_id': best_workcenter.resource_calendar_id.id,
            'date_from': best_date_start,
            'date_to': best_date_finished,
            'resource_id': best_workcenter.resource_id.id,
            'time_type': 'other'
        })
        vals['leave_id'] = leave.id
        self.write(vals)

    def _cal_cost(self, date=False):
        """Returns total cost of time spent on workorder.

        :param date datetime: Only calculate for time_ids that ended before this date
        """
        total = 0
        for wo in self:
            if date:
                duration = sum(wo.time_ids.filtered(lambda t: t.date_end <= date).mapped('duration'))
            else:
                duration = sum(wo.time_ids.mapped('duration'))
            total += (duration / 60.0) * wo.workcenter_id.costs_hour
        return total

    def button_start(self, raise_on_invalid_state=False):
        if any(wo.working_state == 'blocked' for wo in self):
            raise UserError(_('Please unblock the work center to start the work order.'))
        for wo in self:
            if any(not time.date_end for time in wo.time_ids.filtered(lambda t: t.user_id.id == self.env.user.id)):
                continue
            if wo.state in ('done', 'cancel'):
                if raise_on_invalid_state:
                    continue
                raise UserError(_('You cannot start a work order that is already done or cancelled'))

            if wo.product_tracking == 'serial' and wo.qty_producing == 0:
                wo.qty_producing = 1.0
            elif wo.qty_producing == 0:
                wo.qty_producing = wo.qty_remaining

            if wo._should_start_timer():
                self.env['mrp.workcenter.productivity'].create(
                    wo._prepare_timeline_vals(wo.duration, fields.Datetime.now())
                )

            if wo.production_id.state != 'progress':
                wo.production_id.write({
                    'date_start': fields.Datetime.now()
                })
            if wo.state == 'progress':
                continue
            date_start = fields.Datetime.now()
            vals = {
                'state': 'progress',
                'date_start': date_start,
            }
            if not wo.leave_id:
                leave = self.env['resource.calendar.leaves'].create({
                    'name': wo.display_name,
                    'calendar_id': wo.workcenter_id.resource_calendar_id.id,
                    'date_from': date_start,
                    'date_to': date_start + relativedelta(minutes=wo.duration_expected),
                    'resource_id': wo.workcenter_id.resource_id.id,
                    'time_type': 'other'
                })
                vals['date_finished'] = leave.date_to
                vals['leave_id'] = leave.id
                wo.write(vals)
            else:
                if not wo.date_start or wo.date_start > date_start:
                    vals['date_start'] = date_start
                    vals['date_finished'] = wo._calculate_date_finished(date_start)
                if wo.date_finished and wo.date_finished < date_start:
                    vals['date_finished'] = date_start
                wo.with_context(bypass_duration_calculation=True).write(vals)

    def button_finish(self):
        date_finished = fields.Datetime.now()
        for workorder in self:
            if workorder.state in ('done', 'cancel'):
                continue
            moves = (self.move_raw_ids + self.production_id.move_byproduct_ids.filtered(lambda m: m.operation_id == self.operation_id))
            for move in moves:
                if not move.picked:
                    if float_is_zero(workorder.production_id.qty_producing, precision_rounding=workorder.production_id.product_uom_id.rounding):
                        qty_available = workorder.production_id.product_qty
                    else:
                        qty_available = workorder.production_id.qty_producing
                    new_qty = float_round(qty_available * move.unit_factor, precision_rounding=move.product_uom.rounding)
                    move._set_quantity_done(new_qty)
            moves.picked = True
            workorder.end_all()
            vals = {
                'qty_produced': workorder.qty_produced or workorder.qty_producing or workorder.qty_production,
                'state': 'done',
                'date_finished': date_finished,
                'costs_hour': workorder.workcenter_id.costs_hour
            }
            if not workorder.date_start or date_finished < workorder.date_start:
                vals['date_start'] = date_finished
            workorder.with_context(bypass_duration_calculation=True).write(vals)
        return True

    def end_previous(self, doall=False):
        """
        @param: doall:  This will close all open time lines on the open work orders when doall = True, otherwise
        only the one of the current user
        """
        # TDE CLEANME
        domain = [('workorder_id', 'in', self.ids), ('date_end', '=', False)]
        if not doall:
            domain.append(('user_id', '=', self.env.user.id))
        self.env['mrp.workcenter.productivity'].search(domain, limit=None if doall else 1)._close()
        return True

    def end_all(self):
        return self.end_previous(doall=True)

    def button_pending(self):
        self.end_previous()

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
            'costs_hour': self.workcenter_id.costs_hour
        })

    def button_scrap(self):
        self.ensure_one()
        return {
            'name': _('Scrap Products'),
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
        self.flush_model(['state', 'date_start', 'date_finished', 'workcenter_id'])
        sql = """
            SELECT wo1.id, wo2.id
            FROM mrp_workorder wo1, mrp_workorder wo2
            WHERE
                wo1.id IN %s
                AND wo1.state IN ('pending', 'waiting', 'ready')
                AND wo2.state IN ('pending', 'waiting', 'ready')
                AND wo1.id != wo2.id
                AND wo1.workcenter_id = wo2.workcenter_id
                AND (DATE_TRUNC('second', wo2.date_start), DATE_TRUNC('second', wo2.date_finished))
                    OVERLAPS (DATE_TRUNC('second', wo1.date_start), DATE_TRUNC('second', wo1.date_finished))
        """
        self.env.cr.execute(sql, [tuple(self.ids)])
        res = defaultdict(list)
        for wo1, wo2 in self.env.cr.fetchall():
            res[wo1].append(wo2)
        return res

    def _get_operation_values(self):
        self.ensure_one()
        ratio = 1 / self.qty_production
        if self.operation_id.bom_id:
            ratio = self.production_id._get_ratio_between_mo_and_bom_quantities(self.operation_id.bom_id)
        return {
            'company_id': self.company_id.id,
            'name': self.name,
            'time_cycle_manual': self.duration_expected * ratio,
            'workcenter_id': self.workcenter_id.id,
        }

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
                move_line.picked = True
                move_line.quantity += self.qty_producing
            else:
                quantity = self.product_uom_id._compute_quantity(self.qty_producing, self.product_id.uom_id, rounding_method='HALF-UP')
                putaway_location = production_move.location_dest_id._get_putaway_strategy(self.product_id, quantity)
                move_line.create({
                    'move_id': production_move.id,
                    'product_id': production_move.product_id.id,
                    'lot_id': self.finished_lot_id.id,
                    'product_uom_id': self.product_uom_id.id,
                    'quantity': self.qty_producing,
                    'location_id': production_move.location_id.id,
                    'location_dest_id': putaway_location.id,
                })
        else:
            rounding = production_move.product_uom.rounding
            production_move.quantity = float_round(self.qty_producing, precision_rounding=rounding)

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

    def get_duration(self):
        self.ensure_one()
        return sum(self.time_ids.mapped('duration')) + self.get_working_duration()

    def action_mark_as_done(self):
        for wo in self:
            if wo.working_state == 'blocked':
                raise UserError(_('Please unblock the work center to validate the work order'))
            wo.button_finish()
            if wo.duration == 0.0:
                wo.duration = wo.duration_expected
                wo.duration_percent = 100

    def _compute_expected_operation_cost(self, without_employee_cost=False):
        return (self.duration_expected / 60.0) * (self.costs_hour or self.workcenter_id.costs_hour)

    def _compute_current_operation_cost(self):
        return (self.get_duration() / 60.0) * (self.costs_hour or self.workcenter_id.costs_hour)

    def _get_current_theorical_operation_cost(self, without_employee_cost=False):
        return (self.get_duration() / 60.0) * (self.costs_hour or self.workcenter_id.costs_hour)
