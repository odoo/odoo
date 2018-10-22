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
    _inherit = ['mail.thread']

    name = fields.Char(
        'Work Order', required=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})

    workcenter_id = fields.Many2one(
        'mrp.workcenter', 'Work Center', required=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    working_state = fields.Selection(
        'Workcenter Status', related='workcenter_id.working_state', readonly=False,
        help='Technical: used in views only')

    production_id = fields.Many2one(
        'mrp.production', 'Manufacturing Order',
        index=True, ondelete='cascade', required=True, track_visibility='onchange',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    product_id = fields.Many2one(
        'product.product', 'Product',
        related='production_id.product_id', readonly=True,
        help='Technical: used in views only.', store=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        related='production_id.product_uom_id', readonly=True,
        help='Technical: used in views only.')
    production_availability = fields.Selection(
        'Stock Availability', readonly=True,
        related='production_id.availability', store=True,
        help='Technical: used in views and domains only.')
    production_state = fields.Selection(
        'Production State', readonly=True,
        related='production_id.state',
        help='Technical: used in views only.')
    product_tracking = fields.Selection(
        'Product Tracking', related='production_id.product_id.tracking', readonly=False,
        help='Technical: used in views only.')
    qty_production = fields.Float('Original Production Quantity', readonly=True, related='production_id.product_qty')
    qty_remaining = fields.Float('Quantity To Be Produced', compute='_compute_qty_remaining', digits=dp.get_precision('Product Unit of Measure'))
    qty_produced = fields.Float(
        'Quantity', default=0.0,
        readonly=True,
        digits=dp.get_precision('Product Unit of Measure'),
        help="The number of products already handled by this work order")
    qty_producing = fields.Float(
        'Currently Produced Quantity', default=1.0,
        digits=dp.get_precision('Product Unit of Measure'),
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    is_produced = fields.Boolean(string="Has Been Produced",
        compute='_compute_is_produced')

    state = fields.Selection([
        ('pending', 'Pending'),
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
        domain=[('done_wo', '=', True)],
        help="Inventory moves for which you must scan a lot number at this work order")
    active_move_line_ids = fields.One2many(
        'stock.move.line', 'workorder_id',
        domain=[('done_wo', '=', False)])
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

    @api.onchange('qty_producing')
    def _onchange_qty_producing(self):
        """ Update stock.move.lot records, according to the new qty currently
        produced. """
        moves = self.move_raw_ids.filtered(lambda move: move.state not in ('done', 'cancel') and move.product_id.tracking != 'none' and move.product_id.id != self.production_id.product_id.id)
        for move in moves:
            move_lots = self.active_move_line_ids.filtered(lambda move_lot: move_lot.move_id == move)
            if not move_lots:
                continue
            rounding = move.product_uom.rounding
            new_qty = float_round(move.unit_factor * self.qty_producing, precision_rounding=rounding)
            if move.product_id.tracking == 'lot':
                move_lots[0].product_qty = new_qty
                move_lots[0].qty_done = new_qty
            elif move.product_id.tracking == 'serial':
                # Create extra pseudo record
                qty_todo = float_round(new_qty - sum(move_lots.mapped('qty_done')), precision_rounding=rounding)
                if float_compare(qty_todo, 0.0, precision_rounding=rounding) > 0:
                    while float_compare(qty_todo, 0.0, precision_rounding=rounding) > 0:
                        self.active_move_line_ids += self.env['stock.move.line'].new({
                            'move_id': move.id,
                            'product_id': move.product_id.id,
                            'lot_id': False,
                            'product_uom_qty': 0.0,
                            'product_uom_id': move.product_uom.id,
                            'qty_done': min(1.0, qty_todo),
                            'workorder_id': self.id,
                            'done_wo': False,
                            'location_id': move.location_id.id,
                            'location_dest_id': move.location_dest_id.id,
                            'date': move.date,
                        })
                        qty_todo -= 1
                elif float_compare(qty_todo, 0.0, precision_rounding=rounding) < 0:
                    qty_todo = abs(qty_todo)
                    for move_lot in move_lots:
                        if float_compare(qty_todo, 0, precision_rounding=rounding) <= 0:
                            break
                        if not move_lot.lot_id and float_compare(qty_todo, move_lot.qty_done, precision_rounding=rounding) >= 0:
                            qty_todo = float_round(qty_todo - move_lot.qty_done, precision_rounding=rounding)
                            self.active_move_line_ids -= move_lot  # Difference operator
                        else:
                            #move_lot.product_qty = move_lot.product_qty - qty_todo
                            if float_compare(move_lot.qty_done - qty_todo, 0, precision_rounding=rounding) == 1:
                                move_lot.qty_done = move_lot.qty_done - qty_todo
                            else:
                                move_lot.qty_done = 0
                            qty_todo = 0

    @api.multi
    def write(self, values):
        if ('date_planned_start' in values or 'date_planned_finished' in values) and any(workorder.state == 'done' for workorder in self):
            raise UserError(_('You can not change the finished work order.'))
        return super(MrpWorkorder, self).write(values)

    def _generate_lot_ids(self):
        """ Generate stock move lines """
        self.ensure_one()
        MoveLine = self.env['stock.move.line']
        tracked_moves = self.move_raw_ids.filtered(
            lambda move: move.state not in ('done', 'cancel') and move.product_id.tracking != 'none' and move.product_id != self.production_id.product_id and move.bom_line_id)
        for move in tracked_moves:
            qty = move.unit_factor * self.qty_producing
            if move.product_id.tracking == 'serial':
                while float_compare(qty, 0.0, precision_rounding=move.product_uom.rounding) > 0:
                    MoveLine.create({
                        'move_id': move.id,
                        'product_uom_qty': 0,
                        'product_uom_id': move.product_uom.id,
                        'qty_done': min(1, qty),
                        'production_id': self.production_id.id,
                        'workorder_id': self.id,
                        'product_id': move.product_id.id,
                        'done_wo': False,
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                    })
                    qty -= 1
            else:
                MoveLine.create({
                    'move_id': move.id,
                    'product_uom_qty': 0,
                    'product_uom_id': move.product_uom.id,
                    'qty_done': qty,
                    'product_id': move.product_id.id,
                    'production_id': self.production_id.id,
                    'workorder_id': self.id,
                    'done_wo': False,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    })

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
            'workorder_id': self.id,
            'location_id': by_product_move.location_id.id,
            'location_dest_id': by_product_move.location_dest_id.id,
        }

    @api.multi
    def record_production(self):
        if not self:
            return True

        self.ensure_one()
        if self.qty_producing <= 0:
            raise UserError(_('Please set the quantity you are currently producing. It should be different from zero.'))

        if (self.production_id.product_id.tracking != 'none') and not self.final_lot_id and self.move_raw_ids:
            raise UserError(_('You should provide a lot/serial number for the final product.'))

        # Update quantities done on each raw material line
        # For each untracked component without any 'temporary' move lines,
        # (the new workorder tablet view allows registering consumed quantities for untracked components)
        # we assume that only the theoretical quantity was used
        for move in self.move_raw_ids:
            if move.has_tracking == 'none' and (move.state not in ('done', 'cancel')) and move.bom_line_id\
                        and move.unit_factor and not move.move_line_ids.filtered(lambda ml: not ml.done_wo):
                rounding = move.product_uom.rounding
                if self.product_id.tracking != 'none':
                    qty_to_add = float_round(self.qty_producing * move.unit_factor, precision_rounding=rounding)
                    move._generate_consumed_move_line(qty_to_add, self.final_lot_id)
                elif len(move._get_move_lines()) < 2:
                    move.quantity_done += float_round(self.qty_producing * move.unit_factor, precision_rounding=rounding)
                else:
                    move._set_quantity_done(move.quantity_done + float_round(self.qty_producing * move.unit_factor, precision_rounding=rounding))

        # Transfer quantities from temporary to final move lots or make them final
        for move_line in self.active_move_line_ids:
            # Check if move_line already exists
            if move_line.qty_done <= 0:  # rounding...
                move_line.sudo().unlink()
                continue
            if move_line.product_id.tracking != 'none' and not move_line.lot_id:
                raise UserError(_('You should provide a lot/serial number for a component.'))
            # Search other move_line where it could be added:
            lots = self.move_line_ids.filtered(lambda x: (x.lot_id.id == move_line.lot_id.id) and (not x.lot_produced_id) and (not x.done_move) and (x.product_id == move_line.product_id))
            if lots:
                lots[0].qty_done += move_line.qty_done
                lots[0].lot_produced_id = self.final_lot_id.id
                move_line.sudo().unlink()
            else:
                move_line.lot_produced_id = self.final_lot_id.id
                move_line.done_wo = True

        # One a piece is produced, you can launch the next work order
        if self.next_work_order_id.state == 'pending':
            self.next_work_order_id.state = 'ready'

        self.move_line_ids.filtered(
            lambda move_line: not move_line.done_move and not move_line.lot_produced_id and move_line.qty_done > 0
        ).write({
            'lot_produced_id': self.final_lot_id.id,
            'lot_produced_qty': self.qty_producing
        })

        # If last work order, then post lots used
        # TODO: should be same as checking if for every workorder something has been done?
        if not self.next_work_order_id:
            production_move = self.production_id.move_finished_ids.filtered(
                                lambda x: (x.product_id.id == self.production_id.product_id.id) and (x.state not in ('done', 'cancel')))
            if production_move.product_id.tracking != 'none':
                move_line = production_move.move_line_ids.filtered(lambda x: x.lot_id.id == self.final_lot_id.id)
                if move_line:
                    move_line.product_uom_qty += self.qty_producing
                    move_line.qty_done += self.qty_producing
                else:
                    move_line.create({'move_id': production_move.id,
                             'product_id': production_move.product_id.id,
                             'lot_id': self.final_lot_id.id,
                             'product_uom_qty': self.qty_producing,
                             'product_uom_id': production_move.product_uom.id,
                             'qty_done': self.qty_producing,
                             'workorder_id': self.id,
                             'location_id': production_move.location_id.id,
                             'location_dest_id': production_move.location_dest_id.id,
                    })
            else:
                production_move.quantity_done += self.qty_producing

        if not self.next_work_order_id:
            for by_product_move in self.production_id.move_finished_ids.filtered(lambda x: (x.product_id.id != self.production_id.product_id.id) and (x.state not in ('done', 'cancel'))):
                if by_product_move.has_tracking != 'serial':
                    values = self._get_byproduct_move_line(by_product_move, self.qty_producing * by_product_move.unit_factor)
                    self.env['stock.move.line'].create(values)
                elif by_product_move.has_tracking == 'serial':
                    qty_todo = by_product_move.product_uom._compute_quantity(self.qty_producing * by_product_move.unit_factor, by_product_move.product_id.uom_id)
                    for i in range(0, int(float_round(qty_todo, precision_digits=0))):
                        values = self._get_byproduct_move_line(by_product_move, 1)
                        self.env['stock.move.line'].create(values)

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
            self._generate_lot_ids()
        else:
            self.qty_producing = float_round(self.production_id.product_qty - self.qty_produced, precision_rounding=rounding)
            self._generate_lot_ids()

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
        for workorder in self:
            if workorder.production_id.state != 'progress':
                workorder.production_id.write({
                    'state': 'progress',
                    'date_start': datetime.now(),
                })
            timeline.create({
                'workorder_id': workorder.id,
                'workcenter_id': workorder.workcenter_id.id,
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
