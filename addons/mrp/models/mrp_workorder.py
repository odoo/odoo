# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round


class MrpWorkorder(models.Model):
    _name = 'mrp.workorder'
    _description = 'Work Order'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'mrp.abstract.workorder']

    name = fields.Char(
        'Work Order', required=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    workcenter_id = fields.Many2one(
        'mrp.workcenter', 'Work Center', required=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
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
        help='Slot into workcenter calendar once planned')
    date_planned_start = fields.Datetime(
        'Scheduled Date Start',
        compute='_compute_dates_planned',
        inverse='_set_dates_planned',
        search='_search_date_planned_start',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    date_planned_finished = fields.Datetime(
        'Scheduled Date Finished',
        compute='_compute_dates_planned',
        inverse='_set_dates_planned',
        search='_search_date_planned_finished',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
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

    operation_id = fields.Many2one(
        'mrp.routing.workcenter', 'Operation')  # Should be used differently as BoM can change in the meantime
    worksheet = fields.Binary(
        'Worksheet', related='operation_id.worksheet', readonly=True)
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
        'stock.production.lot', 'Lot/Serial Number', domain="[('product_id', '=', product_id)]",
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    time_ids = fields.One2many(
        'mrp.workcenter.productivity', 'workorder_id')
    is_user_working = fields.Boolean(
        'Is the Current User Working', compute='_compute_working_users',
        help="Technical field indicating whether the current user is working. ")
    working_user_ids = fields.One2many('res.users', string='Working user on this work order.', compute='_compute_working_users')
    last_working_user_id = fields.One2many('res.users', string='Last user that worked on this work order.', compute='_compute_working_users')

    next_work_order_id = fields.Many2one('mrp.workorder', "Next Work Order")
    scrap_ids = fields.One2many('stock.scrap', 'workorder_id')
    scrap_count = fields.Integer(compute='_compute_scrap_move_count', string='Scrap Move')
    production_date = fields.Datetime('Production Date', related='production_id.date_planned_start', store=True, readonly=False)
    color = fields.Integer('Color', compute='_compute_color')
    capacity = fields.Float(
        'Capacity', default=1.0,
        help="Number of pieces that can be produced in parallel.")
    raw_workorder_line_ids = fields.One2many('mrp.workorder.line',
        'raw_workorder_id', string='Components')
    finished_workorder_line_ids = fields.One2many('mrp.workorder.line',
        'finished_workorder_id', string='By-products')
    allowed_lots_domain = fields.One2many(comodel_name='stock.production.lot', compute="_compute_allowed_lots_domain")

    # Both `date_planned_start` and `date_planned_finished` are related fields on `leave_id`. Let's say
    # we slide a workorder on a gantt view, a single call to write is made with both
    # fields Changes. As the ORM doesn't batch the write on related fields and instead
    # makes multiple call, the constraint check_dates() is raised.
    # That's why the compute and set methods are needed. to ensure the dates are updated
    # in the same time. The two next search method are needed as the field are non stored and
    # not direct related fields.
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

    def _search_date_planned_start(self, operator, value):
        return [('leave_id.date_from', operator, value)]

    def _search_date_planned_finished(self, operator, value):
        return [('leave_id.date_to', operator, value)]

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

    @api.depends('production_id.workorder_ids.finished_workorder_line_ids',
    'production_id.workorder_ids.finished_workorder_line_ids.qty_done',
    'production_id.workorder_ids.finished_workorder_line_ids.lot_id')
    def _compute_allowed_lots_domain(self):
        """ Check if all the finished products has been assigned to a serial
        number or a lot in other workorders. If yes, restrict the selectable lot
        to the lot/sn used in other workorders.
        """
        productions = self.mapped('production_id')
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
                allowed_lot_ids = self.env['stock.production.lot'].search([('product_id', '=', production.product_id.id)])
            else:
                # If we produced enough, only the already produced lots are available
                allowed_lot_ids = self.env['stock.production.lot'].browse(qties_done_per_lot.keys())
            workorders = production.workorder_ids.filtered(lambda wo: wo.state not in ('done', 'cancel'))
            for workorder in workorders:
                if workorder.product_tracking == 'serial':
                    workorder.allowed_lots_domain = allowed_lot_ids - workorder.finished_workorder_line_ids.filtered(lambda wl: wl.product_id == production.product_id).mapped('lot_id')
                else:
                    workorder.allowed_lots_domain = allowed_lot_ids

    @api.multi
    def name_get(self):
        return [(wo.id, "%s - %s - %s" % (wo.production_id.name, wo.product_id.name, wo.name)) for wo in self]

    @api.depends('production_id.product_qty', 'qty_produced')
    def _compute_is_produced(self):
        for order in self:
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

    def _compute_working_users(self):
        """ Checks whether the current user is working, all the users currently working and the last user that worked. """
        for order in self:
            order.working_user_ids = [(4, order.id) for order in order.time_ids.filtered(lambda time: not time.date_end).sorted('date_start').mapped('user_id')]
            if order.working_user_ids:
                order.last_working_user_id = order.working_user_ids[-1]
            elif order.time_ids:
                order.last_working_user_id = order.time_ids.sorted('date_end')[-1].user_id
            if order.time_ids.filtered(lambda x: (x.user_id.id == self.env.user.id) and (not x.date_end) and (x.loss_type in ('productive', 'performance'))):
                order.is_user_working = True
            else:
                order.is_user_working = False

    @api.multi
    def _compute_scrap_move_count(self):
        data = self.env['stock.scrap'].read_group([('workorder_id', 'in', self.ids)], ['workorder_id'], ['workorder_id'])
        count_data = dict((item['workorder_id'][0], item['workorder_id_count']) for item in data)
        for workorder in self:
            workorder.scrap_count = count_data.get(workorder.id, 0)

    @api.multi
    @api.depends('date_planned_finished', 'production_id.date_planned_finished')
    def _compute_color(self):
        late_orders = self.filtered(lambda x: x.production_id.date_planned_finished and x.date_planned_finished > x.production_id.date_planned_finished)
        for order in late_orders:
            order.color = 4
        for order in (self - late_orders):
            order.color = 2

    @api.multi
    def write(self, values):
        if list(values.keys()) != ['time_ids'] and any(workorder.state == 'done' for workorder in self):
            raise UserError(_('You can not change the finished work order.'))
        if 'date_planned_start' in values or 'date_planned_finished' in values:
            for workorder in self:
                start_date = fields.Datetime.to_datetime(values.get('date_planned_start')) or workorder.date_planned_start
                end_date = fields.Datetime.to_datetime(values.get('date_planned_finished')) or workorder.date_planned_finished
                if start_date and end_date and start_date > end_date:
                    raise UserError(_('The planned end date of the work order cannot be prior to the planned start date, please correct this to save the work order.'))
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

    @api.multi
    def record_production(self):
        if not self:
            return True

        self.ensure_one()
        if float_compare(self.qty_producing, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise UserError(_('Please set the quantity you are currently producing. It should be different from zero.'))

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
        if self.next_work_order_id and self.production_id.product_id.tracking != 'none' and not self.next_work_order_id.finished_lot_id:
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

    @api.multi
    def _start_nextworkorder(self):
        rounding = self.product_id.uom_id.rounding
        if self.next_work_order_id.state == 'pending' and (
                (self.operation_id.batch == 'no' and
                 float_compare(self.qty_production, self.qty_produced, precision_rounding=rounding) <= 0) or
                (self.operation_id.batch == 'yes' and
                 float_compare(self.operation_id.batch_size, self.qty_produced, precision_rounding=rounding) <= 0)):
            self.next_work_order_id.state = 'ready'

    @api.multi
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
            'user_id': self.env.user.id
        })
        return self.write({'state': 'progress',
                    'date_start': datetime.now(),
        })

    @api.multi
    def button_finish(self):
        self.ensure_one()
        self.end_all()
        return self.write({'state': 'done', 'date_finished': fields.Datetime.now()})

    @api.multi
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

    @api.multi
    def end_all(self):
        return self.end_previous(doall=True)

    @api.multi
    def button_pending(self):
        self.end_previous()
        return True

    @api.multi
    def button_unblock(self):
        for order in self:
            order.workcenter_id.unblock()
        return True

    @api.multi
    def action_cancel(self):
        return self.write({'state': 'cancel'})

    @api.multi
    def button_done(self):
        if any([x.state in ('done', 'cancel') for x in self]):
            raise UserError(_('A Manufacturing Order is already done or cancelled.'))
        self.end_all()
        return self.write({'state': 'done',
                    'date_finished': datetime.now()})

    @api.multi
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

    @api.multi
    def action_see_move_scrap(self):
        self.ensure_one()
        action = self.env.ref('stock.action_stock_scrap').read()[0]
        action['domain'] = [('workorder_id', '=', self.id)]
        return action

    @api.multi
    @api.depends('qty_production', 'qty_produced')
    def _compute_qty_remaining(self):
        for wo in self:
            wo.qty_remaining = float_round(wo.qty_production - wo.qty_produced, precision_rounding=wo.production_id.product_uom_id.rounding)


class MrpWorkorderLine(models.Model):
    _name = 'mrp.workorder.line'
    _inherit = ["mrp.abstract.workorder.line"]
    _description = "Workorder move line"

    raw_workorder_id = fields.Many2one('mrp.workorder', 'Component for Workorder')
    finished_workorder_id = fields.Many2one('mrp.workorder', 'Finished Product for Workorder')

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
