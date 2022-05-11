# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
import json

from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError
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
        string='Workcenter Status', related='workcenter_id.working_state',
        help='Technical: used in views only')
    product_id = fields.Many2one(related='production_id.product_id', readonly=True, store=True, check_company=True)
    product_tracking = fields.Selection(related="product_id.tracking")
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True, readonly=True)
    production_id = fields.Many2one('mrp.production', 'Manufacturing Order', required=True, check_company=True, readonly=True)
    production_availability = fields.Selection(
        string='Stock Availability', readonly=True,
        related='production_id.reservation_state', store=True,
        help='Technical: used in views and domains only.')
    production_state = fields.Selection(
        string='Production State', readonly=True,
        related='production_id.state',
        help='Technical: used in views only.')
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
        default='pending', copy=False, readonly=True)
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
        'Expected Duration', digits=(16, 2), default=60.0,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="Expected duration (in minutes)")
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
        'stock.production.lot', string='Lot/Serial Number', compute='_compute_finished_lot_id',
        inverse='_set_finished_lot_id', domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]",
        check_company=True)
    time_ids = fields.One2many(
        'mrp.workcenter.productivity', 'workorder_id', copy=False)
    is_user_working = fields.Boolean(
        'Is the Current User Working', compute='_compute_working_users',
        help="Technical field indicating whether the current user is working. ")
    working_user_ids = fields.One2many('res.users', string='Working user on this work order.', compute='_compute_working_users')
    last_working_user_id = fields.One2many('res.users', string='Last user that worked on this work order.', compute='_compute_working_users')
    costs_hour = fields.Float(
        string='Cost per hour',
        help='Technical field to store the hourly cost of workcenter at time of work order completion (i.e. to keep a consistent cost).',
        default=0.0, group_operator="avg")

    next_work_order_id = fields.Many2one('mrp.workorder', "Next Work Order", check_company=True)
    scrap_ids = fields.One2many('stock.scrap', 'workorder_id')
    scrap_count = fields.Integer(compute='_compute_scrap_move_count', string='Scrap Move')
    production_date = fields.Datetime('Production Date', related='production_id.date_planned_start', store=True)
    json_popover = fields.Char('Popover Data JSON', compute='_compute_json_popover')
    show_json_popover = fields.Boolean('Show Popover?', compute='_compute_json_popover')
    consumption = fields.Selection(related='production_id.consumption')

    @api.depends('production_availability')
    def _compute_state(self):
        # Force the flush of the production_availability, the wo state is modify in the _compute_reservation_state
        # It is a trick to force that the state of workorder is computed as the end of the
        # cyclic depends with the mo.state, mo.reservation_state and wo.state
        for workorder in self:
            if workorder.state not in ('waiting', 'ready'):
                continue
            if workorder.production_id.reservation_state not in ('waiting', 'confirmed', 'assigned'):
                continue
            if workorder.production_id.reservation_state == 'assigned' and workorder.state == 'waiting':
                workorder.state = 'ready'
            elif workorder.production_id.reservation_state != 'assigned' and workorder.state == 'ready':
                workorder.state = 'waiting'

    @api.depends('production_state', 'date_planned_start', 'date_planned_finished')
    def _compute_json_popover(self):
        previous_wo_data = self.env['mrp.workorder'].read_group(
            [('next_work_order_id', 'in', self.ids)],
            ['ids:array_agg(id)', 'date_planned_start:max', 'date_planned_finished:max'],
            ['next_work_order_id'])
        previous_wo_dict = dict([(x['next_work_order_id'][0], {
            'id': x['ids'][0],
            'date_planned_start': x['date_planned_start'],
            'date_planned_finished': x['date_planned_finished']})
            for x in previous_wo_data])
        if self.ids:
            conflicted_dict = self._get_conflicted_workorder_ids()
        for wo in self:
            infos = []
            if not wo.date_planned_start or not wo.date_planned_finished or not wo.ids:
                wo.show_json_popover = False
                wo.json_popover = False
                continue
            if wo.state in ('pending', 'waiting', 'ready'):
                previous_wo = previous_wo_dict.get(wo.id)
                prev_start = previous_wo and previous_wo['date_planned_start'] or False
                prev_finished = previous_wo and previous_wo['date_planned_finished'] or False
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
                'infos': infos,
                'color': color_icon,
                'icon': 'fa-exclamation-triangle' if color_icon in ['text-warning', 'text-danger'] else 'fa-info-circle',
                'replan': color_icon not in [False, 'text-primary']
            })

    @api.depends('production_id.lot_producing_id')
    def _compute_finished_lot_id(self):
        for workorder in self:
            workorder.finished_lot_id = workorder.production_id.lot_producing_id

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
        if self.leave_id and (not self[0].date_planned_start or not self[0].date_planned_finished):
            raise UserError(_("It is not possible to unplan one single Work Order. "
                              "You should unplan the Manufacturing Order instead in order to unplan all the linked operations."))
        date_from = self[0].date_planned_start
        date_to = self[0].date_planned_finished
        self.mapped('leave_id').sudo().write({
            'date_from': date_from,
            'date_to': date_to,
        })

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

        previous_wos = self.env['mrp.workorder'].search([
            ('next_work_order_id', 'in', self.ids),
            ('id', 'not in', self.ids)
        ])
        for pw in previous_wos:
            while pw.next_work_order_id and pw.next_work_order_id in self:
                pw.next_work_order_id = pw.next_work_order_id.next_work_order_id
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

    @api.depends('time_ids.duration', 'qty_produced')
    def _compute_duration(self):
        for order in self:
            order.duration = sum(order.time_ids.mapped('duration'))
            order.duration_unit = round(order.duration / max(order.qty_produced, 1), 2)  # rounding 2 because it is a time
            if order.duration_expected:
                order.duration_percent = 100 * (order.duration_expected - order.duration) / order.duration_expected
            else:
                order.duration_percent = 0

    def _set_duration(self):

        def _float_duration_to_second(duration):
            minutes = duration // 1
            seconds = (duration % 1) * 60
            return minutes * 60 + seconds

        for order in self:
            old_order_duation = sum(order.time_ids.mapped('duration'))
            new_order_duration = order.duration
            if new_order_duration == old_order_duation:
                continue

            delta_duration = new_order_duration - old_order_duation

            if delta_duration > 0:
                date_start = datetime.now() - timedelta(seconds=_float_duration_to_second(delta_duration))
                self.env['mrp.workcenter.productivity'].create(
                    order._prepare_timeline_vals(delta_duration, date_start, datetime.now())
                )
            else:
                duration_to_remove = abs(delta_duration)
                timelines = order.time_ids.sorted(lambda t: t.date_start)
                timelines_to_unlink = self.env['mrp.workcenter.productivity']
                for timeline in timelines:
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
        data = self.env['stock.scrap'].read_group([('workorder_id', 'in', self.ids)], ['workorder_id'], ['workorder_id'])
        count_data = dict((item['workorder_id'][0], item['workorder_id_count']) for item in data)
        for workorder in self:
            workorder.scrap_count = count_data.get(workorder.id, 0)

    @api.onchange('date_planned_finished')
    def _onchange_date_planned_finished(self):
        if self.date_planned_start and self.date_planned_finished:
            interval = self.workcenter_id.resource_calendar_id.get_work_duration_data(
                self.date_planned_start, self.date_planned_finished,
                domain=[('time_type', 'in', ['leave', 'other'])]
            )
            self.duration_expected = interval['hours'] * 60

    @api.onchange('operation_id')
    def _onchange_operation_id(self):
        if self.operation_id:
            self.name = self.operation_id.name
            self.workcenter_id = self.operation_id.workcenter_id.id

    @api.onchange('date_planned_start', 'duration_expected', 'workcenter_id')
    def _onchange_date_planned_start(self):
        if self.date_planned_start and self.duration_expected and self.workcenter_id:
            self.date_planned_finished = self.workcenter_id.resource_calendar_id.plan_hours(
                self.duration_expected / 60.0, self.date_planned_start,
                compute_leaves=True, domain=[('time_type', 'in', ['leave', 'other'])]
            )

    @api.onchange('operation_id', 'workcenter_id', 'qty_production')
    def _onchange_expected_duration(self):
        self.duration_expected = self._get_duration_expected()

    def write(self, values):
        if 'production_id' in values:
            raise UserError(_('You cannot link this work order to another manufacturing order.'))
        if 'workcenter_id' in values:
            for workorder in self:
                if workorder.workcenter_id.id != values['workcenter_id']:
                    if workorder.state in ('progress', 'done', 'cancel'):
                        raise UserError(_('You cannot change the workcenter of a work order that is in progress or done.'))
                    workorder.leave_id.resource_id = self.env['mrp.workcenter'].browse(values['workcenter_id']).resource_id
        if 'date_planned_start' in values or 'date_planned_finished' in values:
            for workorder in self:
                start_date = fields.Datetime.to_datetime(values.get('date_planned_start')) or workorder.date_planned_start
                end_date = fields.Datetime.to_datetime(values.get('date_planned_finished')) or workorder.date_planned_finished
                if start_date and end_date and start_date > end_date:
                    raise UserError(_('The planned end date of the work order cannot be prior to the planned start date, please correct this to save the work order.'))
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
        workorders_by_production = defaultdict(lambda: self.env['mrp.workorder'])
        for workorder in self:
            workorders_by_production[workorder.production_id] |= workorder

        for production, workorders in workorders_by_production.items():
            workorders_by_bom = defaultdict(lambda: self.env['mrp.workorder'])
            bom = self.env['mrp.bom']
            moves = production.move_raw_ids | production.move_finished_ids

            for workorder in workorders:
                bom = workorder.operation_id.bom_id or workorder.production_id.bom_id
                previous_workorder = workorders_by_bom[bom][-1:]
                previous_workorder.next_work_order_id = workorder.id
                workorders_by_bom[bom] |= workorder

                moves.filtered(lambda m: m.operation_id == workorder.operation_id).write({
                    'workorder_id': workorder.id
                })

            exploded_boms, dummy = production.bom_id.explode(production.product_id, 1, picking_type=production.bom_id.picking_type_id)
            exploded_boms = {b[0]: b[1] for b in exploded_boms}
            for move in moves:
                if move.workorder_id:
                    continue
                bom = move.bom_line_id.bom_id
                while bom and bom not in workorders_by_bom:
                    bom_data = exploded_boms.get(bom, {})
                    bom = bom_data.get('parent_line') and bom_data['parent_line'].bom_id or False
                if bom in workorders_by_bom:
                    move.write({
                        'workorder_id': workorders_by_bom[bom][-1:].id
                    })
                else:
                    move.write({
                        'workorder_id': workorders_by_bom[production.bom_id][-1:].id
                    })

            for workorders in workorders_by_bom.values():
                if not workorders:
                    continue
                if workorders[0].state == 'pending':
                    workorders[0].state = 'ready' if workorders[0].production_availability == 'assigned' else 'waiting'
                for workorder in workorders:
                    workorder._start_nextworkorder()

    def _get_byproduct_move_to_update(self):
        return self.production_id.move_finished_ids.filtered(lambda x: (x.product_id.id != self.production_id.product_id.id) and (x.state not in ('done', 'cancel')))

    def _start_nextworkorder(self):
        if self.state == 'done':
            next_order = self.next_work_order_id
            while next_order and next_order.state == 'cancel':
                next_order = next_order.next_work_order_id
            if next_order.state == 'pending':
                next_order.state = 'ready' if next_order.production_availability == 'assigned' else 'waiting'

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

        if self.product_tracking == 'serial':
            self.qty_producing = 1.0
        else:
            self.qty_producing = self.qty_remaining

        self.env['mrp.workcenter.productivity'].create(
            self._prepare_timeline_vals(self.duration, datetime.now())
        )
        if self.production_id.state != 'progress':
            self.production_id.write({
                'date_start': datetime.now(),
            })
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
            if self.date_planned_start > start_date:
                vals['date_planned_start'] = start_date
            if self.date_planned_finished and self.date_planned_finished < start_date:
                vals['date_planned_finished'] = start_date
            return self.write(vals)

    def button_finish(self):
        end_date = datetime.now()
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
            workorder.write(vals)

            workorder._start_nextworkorder()
        return True

    def end_previous(self, doall=False):
        """
        @param: doall:  This will close all open time lines on the open work orders when doall = True, otherwise
        only the one of the current user
        """
        # TDE CLEANME
        timeline_obj = self.env['mrp.workcenter.productivity']
        domain = [('workorder_id', 'in', self.ids), ('date_end', '=', False)]
        if not doall:
            domain.append(('user_id', '=', self.env.user.id))
        not_productive_timelines = timeline_obj.browse()
        for timeline in timeline_obj.search(domain, limit=None if doall else 1):
            wo = timeline.workorder_id
            if wo.duration_expected <= wo.duration:
                if timeline.loss_type == 'productive':
                    not_productive_timelines += timeline
                timeline.write({'date_end': fields.Datetime.now()})
            else:
                maxdate = fields.Datetime.from_string(timeline.date_start) + relativedelta(minutes=wo.duration_expected - wo.duration)
                enddate = datetime.now()
                if maxdate > enddate:
                    timeline.write({'date_end': enddate})
                else:
                    timeline.write({'date_end': maxdate})
                    not_productive_timelines += timeline.copy({'date_start': maxdate, 'date_end': enddate})
        if not_productive_timelines:
            loss_id = self.env['mrp.workcenter.productivity.loss'].search([('loss_type', '=', 'performance')], limit=1)
            if not len(loss_id):
                raise UserError(_("You need to define at least one unactive productivity loss in the category 'Performance'. Create one from the Manufacturing app, menu: Configuration / Productivity Losses."))
            not_productive_timelines.write({'loss_id': loss_id.id})
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
            'view_id': self.env.ref('stock.stock_scrap_form_view2').id,
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

    @api.depends('qty_production', 'qty_produced')
    def _compute_qty_remaining(self):
        for wo in self:
            wo.qty_remaining = float_round(wo.qty_production - wo.qty_produced, precision_rounding=wo.production_id.product_uom_id.rounding)

    def _get_duration_expected(self, alternative_workcenter=False, ratio=1):
        self.ensure_one()
        if not self.workcenter_id:
            return self.duration_expected
        if not self.operation_id:
            duration_expected_working = (self.duration_expected - self.workcenter_id.time_start - self.workcenter_id.time_stop) * self.workcenter_id.time_efficiency / 100.0
            if duration_expected_working < 0:
                duration_expected_working = 0
            return self.workcenter_id.time_start + self.workcenter_id.time_stop + duration_expected_working * ratio * 100.0 / self.workcenter_id.time_efficiency
        qty_production = self.production_id.product_uom_id._compute_quantity(self.qty_production, self.production_id.product_id.uom_id)
        cycle_number = float_round(qty_production / self.workcenter_id.capacity, precision_digits=0, rounding_method='UP')
        if alternative_workcenter:
            # TODO : find a better alternative : the settings of workcenter can change
            duration_expected_working = (self.duration_expected - self.workcenter_id.time_start - self.workcenter_id.time_stop) * self.workcenter_id.time_efficiency / (100.0 * cycle_number)
            if duration_expected_working < 0:
                duration_expected_working = 0
            alternative_wc_cycle_nb = float_round(qty_production / alternative_workcenter.capacity, precision_digits=0, rounding_method='UP')
            return alternative_workcenter.time_start + alternative_workcenter.time_stop + alternative_wc_cycle_nb * duration_expected_working * 100.0 / alternative_workcenter.time_efficiency
        time_cycle = self.operation_id.time_cycle
        return self.workcenter_id.time_start + self.workcenter_id.time_stop + cycle_number * time_cycle * 100.0 / self.workcenter_id.time_efficiency

    def _get_conflicted_workorder_ids(self):
        """Get conlicted workorder(s) with self.

        Conflict means having two workorders in the same time in the same workcenter.

        :return: defaultdict with key as workorder id of self and value as related conflicted workorder
        """
        self.flush(['state', 'date_planned_start', 'date_planned_finished', 'workcenter_id'])
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

    @api.model
    def _prepare_component_quantity(self, move, qty_producing):
        """ helper that computes quantity to consume (or to create in case of byproduct)
        depending on the quantity producing and the move's unit factor"""
        if move.product_id.tracking == 'serial':
            uom = move.product_id.uom_id
        else:
            uom = move.product_uom
        return move.product_uom._compute_quantity(
            qty_producing * move.unit_factor,
            uom,
            round=False
        )

    def _prepare_timeline_vals(self, duration, date_start, date_end=False):
        # Need a loss in case of the real time exceeding the expected
        if not self.duration_expected or duration < self.duration_expected:
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
            'date_start': date_start,
            'date_end': date_end,
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
                move_line.product_uom_qty += self.qty_producing
                move_line.qty_done += self.qty_producing
            else:
                quantity = self.product_uom_id._compute_quantity(self.qty_producing, self.product_id.uom_id, rounding_method='HALF-UP')
                putaway_location = production_move.location_dest_id._get_putaway_strategy(self.product_id, quantity)
                move_line.create({
                    'move_id': production_move.id,
                    'product_id': production_move.product_id.id,
                    'lot_id': self.finished_lot_id.id,
                    'product_uom_qty': self.qty_producing,
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
        """ Alert the user if the serial number as already been produced """
        if self.product_tracking == 'serial' and self.finished_lot_id:
            sml = self.env['stock.move.line'].search_count([
                ('lot_id', '=', self.finished_lot_id.id),
                ('location_id.usage', '=', 'production'),
                ('qty_done', '=', 1),
                ('state', '=', 'done')
            ])
            if sml:
                raise UserError(_('This serial number for product %s has already been produced', self.product_id.name))

    def _update_qty_producing(self, quantity):
        self.ensure_one()
        if self.qty_producing:
            self.qty_producing = quantity
