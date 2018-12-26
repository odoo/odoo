# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round
from odoo.addons import decimal_precision as dp


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
    qty_remaining = fields.Float('Quantity To Be Produced', compute='_compute_qty_remaining', digits=dp.get_precision('Product Unit of Measure'))
    qty_produced = fields.Float(
        'Quantity', default=0.0,
        readonly=True,
        digits=dp.get_precision('Product Unit of Measure'),
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
    date_planned_start = fields.Datetime(
        'Scheduled Date Start',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    date_planned_finished = fields.Datetime(
        'Scheduled Date Finished',
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
        'stock.move', 'workorder_id', 'Moves')
    move_line_ids = fields.One2many(
        'stock.move.line', 'workorder_id', 'Moves to Track',
        help="Inventory moves for which you must scan a lot number at this work order")
    final_lot_id = fields.Many2one(
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
    workorder_line_ids = fields.One2many('mrp.workorder.line', 'workorder_id', string='Workorder lines')

    @api.multi
    def name_get(self):
        return [(wo.id, "%s - %s - %s" % (wo.production_id.name, wo.product_id.name, wo.name)) for wo in self]

    @api.one
    @api.depends('production_id.product_qty', 'qty_produced')
    def _compute_is_produced(self):
        rounding = self.production_id.product_uom_id.rounding
        self.is_produced = float_compare(self.qty_produced, self.production_id.product_qty, precision_rounding=rounding) >= 0

    @api.one
    @api.depends('time_ids.duration', 'qty_produced')
    def _compute_duration(self):
        self.duration = sum(self.time_ids.mapped('duration'))
        self.duration_unit = round(self.duration / max(self.qty_produced, 1), 2)  # rounding 2 because it is a time
        if self.duration_expected:
            self.duration_percent = 100 * (self.duration_expected - self.duration) / self.duration_expected
        else:
            self.duration_percent = 0

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

    def generate_wo_lines(self):
        """ Generate workorder line """
        self.ensure_one()
        raw_moves = self.move_raw_ids.filtered(
            lambda move: move.state not in ('done', 'cancel')
        )
        for move in raw_moves:
            qty_to_consume = move.product_uom._compute_quantity(
                self.qty_producing * move.unit_factor,
                move.product_id.uom_id,
                round=False
            )
            line_values = self._generate_lines_values(move, qty_to_consume)
            self.workorder_line_ids |= self.env['mrp.workorder.line'].create(line_values)

    def _assign_default_final_lot_id(self):
        self.final_lot_id = self.env['stock.production.lot'].search([('use_next_on_work_order_id', '=', self.id)],
                                                                    order='create_date, id', limit=1)

    def _get_byproduct_move_line(self, by_product_move, quantity):
        return {
            'move_id': by_product_move.id,
            'product_id': by_product_move.product_id.id,
            'product_uom_qty': quantity,
            'product_uom_id': by_product_move.product_uom.id,
            'qty_done': quantity,
            'location_id': by_product_move.location_id.id,
            'location_dest_id': by_product_move.location_dest_id.id,
        }

    def _link_to_quality_check(self, old_move_line, new_move_line):
        return True

    @api.multi
    def record_production(self):
        if not self:
            return True

        self.ensure_one()
        if self.qty_producing <= 0:
            raise UserError(_('Please set the quantity you are currently producing. It should be different from zero.'))

        # One a piece is produced, you can launch the next work order
        if self.next_work_order_id.state == 'pending':
            self.next_work_order_id.state = 'ready'

        # If last work order, then post lots used
        # TODO: should be same as checking if for every workorder something has been done?
        if not self.next_work_order_id:
            self._update_finished_move()
            self.production_id.move_finished_ids.filtered(
                lambda move: move.product_id == self.product_id and
                move.state not in ('done', 'cancel')
            ).workorder_id = self.id

        # Transfer quantities from temporary to final move line or make them final
        self._update_raw_moves()

        # Update workorder quantity produced
        self.qty_produced += self.qty_producing

        if self.final_lot_id:
            self.final_lot_id.use_next_on_work_order_id = self.next_work_order_id
            self.final_lot_id = False

        # Set a qty producing
        rounding = self.production_id.product_uom_id.rounding
        if float_compare(self.qty_produced, self.production_id.product_qty, precision_rounding=rounding) >= 0:
            self.qty_producing = 0
        elif self.production_id.product_id.tracking == 'serial':
            self._assign_default_final_lot_id()
            self.qty_producing = 1.0
            self.generate_wo_lines()
        else:
            self.qty_producing = float_round(self.production_id.product_qty - self.qty_produced, precision_rounding=rounding)
            self.generate_wo_lines()

        if self.next_work_order_id and self.production_id.product_id.tracking != 'none':
            self.next_work_order_id._assign_default_final_lot_id()

        if float_compare(self.qty_produced, self.production_id.product_qty, precision_rounding=rounding) >= 0:
            self.button_finish()
        return True

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
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.scrap',
            'view_id': self.env.ref('stock.stock_scrap_form_view2').id,
            'type': 'ir.actions.act_window',
            'context': {'default_workorder_id': self.id, 'default_production_id': self.production_id.id, 'product_ids': (self.production_id.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel')) | self.production_id.move_finished_ids.filtered(lambda x: x.state == 'done')).mapped('product_id').ids},
            # 'context': {'product_ids': self.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel')).mapped('product_id').ids + [self.production_id.product_id.id]},
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

    workorder_id = fields.Many2one('mrp.workorder', 'Workorder')

    def _get_final_lot(self):
        return self.workorder_id.final_lot_id

    def _get_production(self):
        return self.workorder_id.production_id
