# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
import json

from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, format_datetime, float_is_zero


class MrpWorkorder(models.Model):
    _name = 'mrp.workorder'
    _description = 'Work Order'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'mrp.abstract.workorder']

    def _read_group_workcenter_id(self, workcenters, domain, order):
        workcenter_ids = self.env.context.get('default_workcenter_id')
        if not workcenter_ids:
            workcenter_ids = workcenters._search([], order=order, access_rights_uid=SUPERUSER_ID)
        return workcenters.browse(workcenter_ids)

    name = fields.Char(
        'Work Order', required=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company,
        required=True, index=True, readonly=True)
    workcenter_id = fields.Many2one(
        'mrp.workcenter', 'Work Center', required=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        group_expand='_read_group_workcenter_id', check_company=True)
    working_state = fields.Selection(
        'Workcenter Status', related='workcenter_id.working_state', readonly=False,
        help='Technical: used in views only')
    production_availability = fields.Selection(
        'Stock Availability', readonly=True,
        related='production_id.reservation_state', store=True,
        help='Technical: used in views and domains only.')
    production_state = fields.Selection(
        'Production State', readonly=True,
        related='production_id.state',
        help='Technical: used in views only.')
    qty_production = fields.Float('Original Production Quantity', readonly=True, related='production_id.product_qty')
    qty_remaining = fields.Float('Quantity To Be Produced', compute='_compute_qty_remaining', digits='Product Unit of Measure')
    qty_produced = fields.Float(
        'Quantity', default=0.0,
        readonly=True,
        digits='Product Unit of Measure',
        help="The number of products already handled by this work order")
    is_produced = fields.Boolean(string="Has Been Produced",
        compute='_compute_is_produced')
    state = fields.Selection([
        ('pending', 'Waiting for another WO'),
        ('ready', 'Ready'),
        ('progress', 'In Progress'),
        ('done', 'Finished'),
        ('cancel', 'Cancelled')], string='Status',
        default='pending')
    leave_id = fields.Many2one(
        'resource.calendar.leaves',
        help='Slot into workcenter calendar once planned',
        check_company=True)
    date_planned_start = fields.Datetime(
        'Scheduled Date Start',
        compute='_compute_dates_planned',
        inverse='_set_dates_planned',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        store=True,
        tracking=True)
    date_planned_finished = fields.Datetime(
        'Scheduled Date Finished',
        compute='_compute_dates_planned',
        inverse='_set_dates_planned',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        store=True,
        tracking=True)
    date_start = fields.Datetime(
        'Effective Start Date',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    date_finished = fields.Datetime(
        'Effective End Date',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})

    duration_expected = fields.Float(
        'Expected Duration', digits=(16, 2),
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="Expected duration (in minutes)")
    duration = fields.Float(
        'Real Duration', compute='_compute_duration',
        readonly=True, store=True)
    duration_unit = fields.Float(
        'Duration Per Unit', compute='_compute_duration',
        readonly=True, store=True)
    duration_percent = fields.Integer(
        'Duration Deviation (%)', compute='_compute_duration',
        group_operator="avg", readonly=True, store=True)
    progress = fields.Float('Progress Done (%)', digits=(16, 2), compute='_compute_progress')

    operation_id = fields.Many2one(
        'mrp.routing.workcenter', 'Operation',
        check_company=True)
        # Should be used differently as BoM can change in the meantime
    worksheet = fields.Binary(
        'Worksheet', related='operation_id.worksheet', readonly=True)
    worksheet_type = fields.Selection(
        'Worksheet Type', related='operation_id.worksheet_type', readonly=True)
    worksheet_google_slide = fields.Char(
        'Worksheet URL', related='operation_id.worksheet_google_slide', readonly=True)
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
        'stock.production.lot', 'Lot/Serial Number', domain="[('id', 'in', allowed_lots_domain)]",
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, check_company=True)
    time_ids = fields.One2many(
        'mrp.workcenter.productivity', 'workorder_id')
    is_user_working = fields.Boolean(
        'Is the Current User Working', compute='_compute_working_users',
        help="Technical field indicating whether the current user is working. ")
    working_user_ids = fields.One2many('res.users', string='Working user on this work order.', compute='_compute_working_users')
    last_working_user_id = fields.One2many('res.users', string='Last user that worked on this work order.', compute='_compute_working_users')

    next_work_order_id = fields.Many2one('mrp.workorder', "Next Work Order", check_company=True)
    scrap_ids = fields.One2many('stock.scrap', 'workorder_id')
    scrap_count = fields.Integer(compute='_compute_scrap_move_count', string='Scrap Move')
    production_date = fields.Datetime('Production Date', related='production_id.date_planned_start', store=True, readonly=False)
    raw_workorder_line_ids = fields.One2many('mrp.workorder.line',
        'raw_workorder_id', string='Components')
    finished_workorder_line_ids = fields.One2many('mrp.workorder.line',
        'finished_workorder_id', string='By-products')
    allowed_lots_domain = fields.One2many(comodel_name='stock.production.lot', compute="_compute_allowed_lots_domain")
    is_finished_lines_editable = fields.Boolean(compute='_compute_is_finished_lines_editable')
    json_popover = fields.Char('Popover Data JSON', compute='_compute_json_popover')

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
        conflicted_dict = self._get_conflicted_workorder_ids()
        for wo in self:
            infos = []
            if wo.state in ['pending', 'ready']:
                previous_wo = previous_wo_dict.get(wo.id)
                prev_start = previous_wo and previous_wo['date_planned_start'] or False
                prev_finished = previous_wo and previous_wo['date_planned_finished'] or False
                if wo.state == 'pending' and prev_start and not (prev_start > wo.date_planned_finished):
                    infos.append({
                        'color': 'text-primary',
                        'msg': _("Waiting the previous work order, planned from %s to %s") % (
                            format_datetime(self.env, prev_start, dt_format=False),
                            format_datetime(self.env, prev_finished, dt_format=False))
                    })
                if wo.date_planned_finished < fields.Datetime.now():
                    infos.append({
                        'color': 'text-warning',
                        'msg': _("The work order should have already been processed.")
                    })
                if prev_start and prev_start > wo.date_planned_finished:
                    infos.append({
                        'color': 'text-danger',
                        'msg': _("Scheduled before the previous work order, planned from %s to %s") % (
                            format_datetime(self.env, prev_start, dt_format=False),
                            format_datetime(self.env, prev_finished, dt_format=False))
                    })
                if conflicted_dict.get(wo.id):
                    infos.append({
                        'color': 'text-danger',
                        'msg': _("Planned at the same time than other workorder(s) at %s" % wo.workcenter_id.display_name)
                    })
            color_icon = infos and infos[-1]['color'] or 'd-none'
            wo.json_popover = json.dumps({
                'infos': infos,
                'color': color_icon,
                'replan': color_icon not in ['d-none', 'text-primary']
            })

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
        date_from = self[0].date_planned_start
        date_to = self[0].date_planned_finished
        self.mapped('leave_id').write({
            'date_from': date_from,
            'date_to': date_to,
        })

    @api.depends('state')
    def _compute_is_finished_lines_editable(self):
        for workorder in self:
            if self.user_has_groups('mrp.group_mrp_byproducts') and workorder.state not in ('cancel', 'done'):
                workorder.is_finished_lines_editable = True
            else:
                workorder.is_finished_lines_editable = False

    @api.onchange('finished_lot_id')
    def _onchange_finished_lot_id(self):
        """When the user changes the lot being currently produced, suggest
        a quantity to produce consistent with the previous workorders. """
        previous_wo = self.env['mrp.workorder'].search([
            ('next_work_order_id', '=', self.id)
        ])
        if previous_wo:
            line = previous_wo.finished_workorder_line_ids.filtered(lambda line: line.product_id == self.product_id and line.lot_id == self.finished_lot_id)
            if line:
                self.qty_producing = line.qty_done

    @api.onchange('date_planned_finished')
    def _onchange_date_planned_finished(self):
        if self.date_planned_start and self.date_planned_finished:
            diff = self.date_planned_finished - self.date_planned_start
            self.duration_expected = diff.total_seconds() / 60

    @api.depends('production_id.workorder_ids.finished_workorder_line_ids',
    'production_id.workorder_ids.finished_workorder_line_ids.qty_done',
    'production_id.workorder_ids.finished_workorder_line_ids.lot_id')
    def _compute_allowed_lots_domain(self):
        """ Check if all the finished products has been assigned to a serial
        number or a lot in other workorders. If yes, restrict the selectable lot
        to the lot/sn used in other workorders.
        """
        productions = self.mapped('production_id')
        treated = self.browse()
        for production in productions:
            if production.product_id.tracking == 'none':
                continue

            rounding = production.product_uom_id.rounding
            finished_workorder_lines = production.workorder_ids.mapped('finished_workorder_line_ids').filtered(lambda wl: wl.product_id == production.product_id)
            qties_done_per_lot = defaultdict(list)
            for finished_workorder_line in finished_workorder_lines:
                # It is possible to have finished workorder lines without a lot (eg using the dummy
                # test type). Ignore them when computing the allowed lots.
                if finished_workorder_line.lot_id:
                    qties_done_per_lot[finished_workorder_line.lot_id.id].append(finished_workorder_line.qty_done)

            qty_to_produce = production.product_qty
            allowed_lot_ids = self.env['stock.production.lot']
            qty_produced = sum([max(qty_dones) for qty_dones in qties_done_per_lot.values()])
            if float_compare(qty_produced, qty_to_produce, precision_rounding=rounding) < 0:
                # If we haven't produced enough, all lots are available
                allowed_lot_ids = self.env['stock.production.lot'].search([
                    ('product_id', '=', production.product_id.id),
                    ('company_id', '=', production.company_id.id),
                ])
            else:
                # If we produced enough, only the already produced lots are available
                allowed_lot_ids = self.env['stock.production.lot'].browse(qties_done_per_lot.keys())
            workorders = production.workorder_ids.filtered(lambda wo: wo.state not in ('done', 'cancel'))
            for workorder in workorders:
                if workorder.product_tracking == 'serial':
                    workorder.allowed_lots_domain = allowed_lot_ids - workorder.finished_workorder_line_ids.filtered(lambda wl: wl.product_id == production.product_id).mapped('lot_id')
                else:
                    workorder.allowed_lots_domain = allowed_lot_ids
                treated |= workorder
        (self - treated).allowed_lots_domain = False

    def name_get(self):
        return [(wo.id, "%s. %s - %s - %s" % (wo.production_id.workorder_ids.ids.index(wo.id) + 1, wo.production_id.name, wo.product_id.name, wo.name)) for wo in self]

    def unlink(self):
        # Removes references to workorder to avoid Validation Error
        (self.mapped('move_raw_ids') | self.mapped('move_finished_ids')).write({'workorder_id': False})
        self.mapped('leave_id').unlink()
        return super(MrpWorkorder, self).unlink()

    @api.depends('production_id.product_qty', 'qty_produced')
    def _compute_is_produced(self):
        self.is_produced = False
        for order in self.filtered(lambda p: p.production_id):
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
                order.last_working_user_id = order.time_ids.sorted('date_end')[-1].user_id
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

    @api.onchange('date_planned_start', 'duration_expected')
    def _onchange_date_planned_start(self):
        if self.date_planned_start and self.duration_expected:
            self.date_planned_finished = self.date_planned_start + relativedelta(minutes=self.duration_expected)

    def write(self, values):
        if 'production_id' in values:
            raise UserError(_('You cannot link this work order to another manufacturing order.'))
        if 'workcenter_id' in values:
            for workorder in self:
                if workorder.workcenter_id.id != values['workcenter_id']:
                    if workorder.state in ('progress', 'done', 'cancel'):
                        raise UserError(_('You cannot change the workcenter of a work order that is in progress or done.'))
                    workorder.leave_id.resource_id = self.env['mrp.workcenter'].browse(values['workcenter_id']).resource_id
        if list(values.keys()) != ['time_ids'] and any(workorder.state == 'done' for workorder in self):
            raise UserError(_('You can not change the finished work order.'))
        if 'date_planned_start' in values or 'date_planned_finished' in values:
            for workorder in self:
                start_date = fields.Datetime.to_datetime(values.get('date_planned_start')) or workorder.date_planned_start
                end_date = fields.Datetime.to_datetime(values.get('date_planned_finished')) or workorder.date_planned_finished
                if start_date and end_date and start_date > end_date:
                    raise UserError(_('The planned end date of the work order cannot be prior to the planned start date, please correct this to save the work order.'))
                # Update MO dates if the start date of the first WO or the
                # finished date of the last WO is update.
                if workorder == workorder.production_id.workorder_ids[0] and 'date_planned_start' in values:
                    workorder.production_id.with_context(force_date=True).write({
                        'date_planned_start': fields.Datetime.to_datetime(values['date_planned_start'])
                    })
                if workorder == workorder.production_id.workorder_ids[-1] and 'date_planned_finished' in values:
                    workorder.production_id.with_context(force_date=True).write({
                        'date_planned_finished': fields.Datetime.to_datetime(values['date_planned_finished'])
                    })
        return super(MrpWorkorder, self).write(values)

    def _generate_wo_lines(self):
        """ Generate workorder line """
        self.ensure_one()
        moves = (self.move_raw_ids | self.move_finished_ids).filtered(
            lambda move: move.state not in ('done', 'cancel')
        )
        for move in moves:
            qty_to_consume = self._prepare_component_quantity(move, self.qty_producing)
            line_values = self._generate_lines_values(move, qty_to_consume)
            self.env['mrp.workorder.line'].create(line_values)

    def _apply_update_workorder_lines(self):
        """ update existing line on the workorder. It could be trigger manually
        after a modification of qty_producing.
        """
        self.ensure_one()
        line_values = self._update_workorder_lines()
        self.env['mrp.workorder.line'].create(line_values['to_create'])
        if line_values['to_delete']:
            line_values['to_delete'].unlink()
        for line, vals in line_values['to_update'].items():
            line.write(vals)

    def _refresh_wo_lines(self):
        """ Modify exisiting workorder line in order to match the reservation on
        stock move line. The strategy is to remove the line that were not
        processed yet then call _generate_lines_values that recreate workorder
        line depending the reservation.
        """
        for workorder in self:
            raw_moves = workorder.move_raw_ids.filtered(
                lambda move: move.state not in ('done', 'cancel')
            )
            wl_to_unlink = self.env['mrp.workorder.line']
            for move in raw_moves:
                rounding = move.product_uom.rounding
                qty_already_consumed = 0.0
                workorder_lines = workorder.raw_workorder_line_ids.filtered(lambda w: w.move_id == move)
                for wl in workorder_lines:
                    if not wl.qty_done:
                        wl_to_unlink |= wl
                        continue

                    qty_already_consumed += wl.qty_done
                qty_to_consume = self._prepare_component_quantity(move, workorder.qty_producing)
                wl_to_unlink.unlink()
                if float_compare(qty_to_consume, qty_already_consumed, precision_rounding=rounding) > 0:
                    line_values = workorder._generate_lines_values(move, qty_to_consume - qty_already_consumed)
                    self.env['mrp.workorder.line'].create(line_values)

    def _defaults_from_finished_workorder_line(self, reference_lot_lines):
        for r_line in reference_lot_lines:
            # see which lot we could suggest and its related qty_producing
            if not r_line.lot_id:
                continue
            candidates = self.finished_workorder_line_ids.filtered(lambda line: line.lot_id == r_line.lot_id)
            rounding = self.product_uom_id.rounding
            if not candidates:
                self.write({
                    'finished_lot_id': r_line.lot_id.id,
                    'qty_producing': r_line.qty_done,
                })
                return True
            elif float_compare(candidates.qty_done, r_line.qty_done, precision_rounding=rounding) < 0:
                self.write({
                    'finished_lot_id': r_line.lot_id.id,
                    'qty_producing': r_line.qty_done - candidates.qty_done,
                })
                return True
        return False

    def record_production(self):
        if not self:
            return True

        self.ensure_one()
        self._check_sn_uniqueness()
        self._check_company()
        if float_compare(self.qty_producing, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise UserError(_('Please set the quantity you are currently producing. It should be different from zero.'))
        if 'check_ids' not in self:
            for line in self.raw_workorder_line_ids | self.finished_workorder_line_ids:
                line._check_line_sn_uniqueness()
        # If last work order, then post lots used
        if not self.next_work_order_id:
            self._update_finished_move()

        # Transfer quantities from temporary to final move line or make them final
        self._update_moves()

        # Transfer lot (if present) and quantity produced to a finished workorder line
        if self.product_tracking != 'none':
            self._create_or_update_finished_line()

        # Update workorder quantity produced
        self.qty_produced += self.qty_producing

        # Suggest a finished lot on the next workorder
        if self.next_work_order_id and self.product_tracking != 'none' and (not self.next_work_order_id.finished_lot_id or self.next_work_order_id.finished_lot_id == self.finished_lot_id):
            self.next_work_order_id._defaults_from_finished_workorder_line(self.finished_workorder_line_ids)
            # As we may have changed the quantity to produce on the next workorder,
            # make sure to update its wokorder lines
            self.next_work_order_id._apply_update_workorder_lines()

        # One a piece is produced, you can launch the next work order
        self._start_nextworkorder()

        # Test if the production is done
        rounding = self.production_id.product_uom_id.rounding
        if float_compare(self.qty_produced, self.production_id.product_qty, precision_rounding=rounding) < 0:
            previous_wo = self.env['mrp.workorder']
            if self.product_tracking != 'none':
                previous_wo = self.env['mrp.workorder'].search([
                    ('next_work_order_id', '=', self.id)
                ])
            candidate_found_in_previous_wo = False
            if previous_wo:
                candidate_found_in_previous_wo = self._defaults_from_finished_workorder_line(previous_wo.finished_workorder_line_ids)
            if not candidate_found_in_previous_wo:
                # self is the first workorder
                self.qty_producing = self.qty_remaining
                self.finished_lot_id = False
                if self.product_tracking == 'serial':
                    self.qty_producing = 1

            self._apply_update_workorder_lines()
        else:
            self.qty_producing = 0
            self.button_finish()
        return True

    def _get_byproduct_move_to_update(self):
        return self.production_id.move_finished_ids.filtered(lambda x: (x.product_id.id != self.production_id.product_id.id) and (x.state not in ('done', 'cancel')))

    def _create_or_update_finished_line(self):
        """
        1. Check that the final lot and the quantity producing is valid regarding
            other workorders of this production
        2. Save final lot and quantity producing to suggest on next workorder
        """
        self.ensure_one()
        final_lot_quantity = self.qty_production
        rounding = self.product_uom_id.rounding
        # Get the max quantity possible for current lot in other workorders
        for workorder in (self.production_id.workorder_ids - self):
            # We add the remaining quantity to the produced quantity for the
            # current lot. For 5 finished products: if in the first wo it
            # creates 4 lot A and 1 lot B and in the second it create 3 lot A
            # and it remains 2 units to product, it could produce 5 lot A.
            # In this case we select 4 since it would conflict with the first
            # workorder otherwise.
            line = workorder.finished_workorder_line_ids.filtered(lambda line: line.lot_id == self.finished_lot_id)
            line_without_lot = workorder.finished_workorder_line_ids.filtered(lambda line: line.product_id == workorder.product_id and not line.lot_id)
            quantity_remaining = workorder.qty_remaining + line_without_lot.qty_done
            quantity = line.qty_done + quantity_remaining
            if line and float_compare(quantity, final_lot_quantity, precision_rounding=rounding) <= 0:
                final_lot_quantity = quantity
            elif float_compare(quantity_remaining, final_lot_quantity, precision_rounding=rounding) < 0:
                final_lot_quantity = quantity_remaining

        # final lot line for this lot on this workorder.
        current_lot_lines = self.finished_workorder_line_ids.filtered(lambda line: line.lot_id == self.finished_lot_id)

        # this lot has already been produced
        if float_compare(final_lot_quantity, current_lot_lines.qty_done + self.qty_producing, precision_rounding=rounding) < 0:
            raise UserError(_('You have produced %s %s of lot %s in the previous workorder. You are trying to produce %s in this one') %
                (final_lot_quantity, self.product_id.uom_id.name, self.finished_lot_id.name, current_lot_lines.qty_done + self.qty_producing))

        # Update workorder line that regiter final lot created
        if not current_lot_lines:
            current_lot_lines = self.env['mrp.workorder.line'].create({
                'finished_workorder_id': self.id,
                'product_id': self.product_id.id,
                'lot_id': self.finished_lot_id.id,
                'qty_done': self.qty_producing,
            })
        else:
            current_lot_lines.qty_done += self.qty_producing

    def _start_nextworkorder(self):
        rounding = self.product_id.uom_id.rounding
        if self.next_work_order_id.state == 'pending' and (
                (self.operation_id.batch == 'no' and
                 float_compare(self.qty_production, self.qty_produced, precision_rounding=rounding) <= 0) or
                (self.operation_id.batch == 'yes' and
                 float_compare(self.operation_id.batch_size, self.qty_produced, precision_rounding=rounding) <= 0)):
            self.next_work_order_id.state = 'ready'

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
        # As button_start is automatically called in the new view
        if self.state in ('done', 'cancel'):
            return True

        # Need a loss in case of the real time exceeding the expected
        timeline = self.env['mrp.workcenter.productivity']
        if self.duration < self.duration_expected:
            loss_id = self.env['mrp.workcenter.productivity.loss'].search([('loss_type','=','productive')], limit=1)
            if not len(loss_id):
                raise UserError(_("You need to define at least one productivity loss in the category 'Productivity'. Create one from the Manufacturing app, menu: Configuration / Productivity Losses."))
        else:
            loss_id = self.env['mrp.workcenter.productivity.loss'].search([('loss_type','=','performance')], limit=1)
            if not len(loss_id):
                raise UserError(_("You need to define at least one productivity loss in the category 'Performance'. Create one from the Manufacturing app, menu: Configuration / Productivity Losses."))
        if self.production_id.state != 'progress':
            self.production_id.write({
                'date_start': datetime.now(),
            })
        timeline.create({
            'workorder_id': self.id,
            'workcenter_id': self.workcenter_id.id,
            'description': _('Time Tracking: ')+self.env.user.name,
            'loss_id': loss_id[0].id,
            'date_start': datetime.now(),
            'user_id': self.env.user.id,  # FIXME sle: can be inconsistent with company_id
            'company_id': self.company_id.id,
        })
        if self.state == 'progress':
            return True
        else:
            start_date = datetime.now()
            vals = {
                'state': 'progress',
                'date_start': start_date,
                'date_planned_start': start_date,
            }
            if self.date_planned_finished < start_date:
                vals['date_planned_finished'] = start_date
            return self.write(vals)

    def button_finish(self):
        self.ensure_one()
        self.end_all()
        end_date = datetime.now()
        return self.write({
            'state': 'done',
            'date_finished': end_date,
            'date_planned_finished': end_date
        })

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
        if any([x.state in ('done', 'cancel') for x in self]):
            raise UserError(_('A Manufacturing Order is already done or cancelled.'))
        self.end_all()
        end_date = datetime.now()
        return self.write({
            'state': 'done',
            'date_finished': end_date,
            'date_planned_finished': end_date,
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
        action = self.env.ref('stock.action_stock_scrap').read()[0]
        action['domain'] = [('workorder_id', '=', self.id)]
        return action

    @api.depends('qty_production', 'qty_produced')
    def _compute_qty_remaining(self):
        for wo in self:
            wo.qty_remaining = float_round(wo.qty_production - wo.qty_produced, precision_rounding=wo.production_id.product_uom_id.rounding)

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
                AND wo1.state IN ('pending','ready')
                AND wo2.state IN ('pending','ready')
                AND wo1.id != wo2.id
                AND wo1.workcenter_id = wo2.workcenter_id
                AND (wo2.date_planned_start, wo2.date_planned_finished) OVERLAPS (wo1.date_planned_start, wo1.date_planned_finished)
        """
        self.env.cr.execute(sql, [tuple(self.ids)])
        res = defaultdict(list)
        for wo1, wo2 in self.env.cr.fetchall():
            res[wo1].append(wo2)
        return res

    def _update_quantity(self, qty_per_operation):
        for workorder in self:
            operation = workorder.operation_id
            if qty_per_operation.get(operation.id):
                cycle_number = float_round(qty_per_operation[operation.id] / operation.workcenter_id.capacity,
                    precision_digits=0, rounding_method='UP')
                workorder.duration_expected = (
                    operation.workcenter_id.time_start +
                    operation.workcenter_id.time_stop +
                    cycle_number * operation.time_cycle * 100.0 /
                    operation.workcenter_id.time_efficiency)

            remaining_quantity = workorder.qty_production - workorder.qty_produced
            precision = workorder.product_uom_id.rounding
            if workorder.product_id.tracking == 'serial' and\
                    not float_is_zero(remaining_quantity, precision_rounding=precision):
                remaining_quantity = 1.0

            if float_is_zero(remaining_quantity, precision_rounding=precision):
                workorder.finished_lot_id = False
                workorder._workorder_line_ids().unlink()

            workorder.qty_producing = remaining_quantity
            if workorder.qty_produced < workorder.qty_production and workorder.state == 'done':
                workorder.state = 'progress'
            if workorder.qty_produced == workorder.qty_production and workorder.state == 'progress':
                workorder.state = 'done'

            if workorder.state not in ('done', 'cancel'):
                line_values = workorder._update_workorder_lines()
                workorder._workorder_line_ids().create(line_values['to_create'])
                if line_values['to_delete']:
                    line_values['to_delete'].unlink()
                for line, vals in line_values['to_update'].items():
                    line.write(vals)

class MrpWorkorderLine(models.Model):
    _name = 'mrp.workorder.line'
    _inherit = ["mrp.abstract.workorder.line"]
    _description = "Workorder move line"

    raw_workorder_id = fields.Many2one('mrp.workorder', 'Component for Workorder',
        ondelete='cascade')
    finished_workorder_id = fields.Many2one('mrp.workorder', 'Finished Product for Workorder',
        ondelete='cascade')

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for line in res:
            wo = line.raw_workorder_id
            if wo and\
                    wo.consumption == 'strict' and\
                    wo.state == 'progress' and\
                    line.product_id.id not in wo.production_id.bom_id.bom_line_ids.product_id.ids:
                raise UserError(_('You cannot consume additional component as the consumption defined on the Bill of Material is set to "strict"'))
        return res

    @api.model
    def _get_raw_workorder_inverse_name(self):
        return 'raw_workorder_id'

    @api.model
    def _get_finished_workoder_inverse_name(self):
        return 'finished_workorder_id'

    def _get_final_lots(self):
        return (self.raw_workorder_id or self.finished_workorder_id).finished_lot_id

    def _get_production(self):
        return (self.raw_workorder_id or self.finished_workorder_id).production_id
