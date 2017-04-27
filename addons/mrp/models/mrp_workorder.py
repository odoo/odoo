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
        'Workcenter Status', related='workcenter_id.working_state',
        help='Technical: used in views only')

    production_id = fields.Many2one(
        'mrp.production', 'Manufacturing Order',
        index=True, ondelete='cascade', required=True, track_visibility='onchange',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    product_id = fields.Many2one(
        'product.product', 'Product',
        related='production_id.product_id', readonly=True,
        help='Technical: used in views only.')
    product_uom_id = fields.Many2one(
        'product.uom', 'Unit of Measure',
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
        'Product Tracking', related='production_id.product_id.tracking',
        help='Technical: used in views only.')
    qty_production = fields.Float('Original Production Quantity', readonly=True, related='production_id.product_qty')
    qty_produced = fields.Float(
        'Quantity', default=0.0,
        readonly=True,
        digits=dp.get_precision('Product Unit of Measure'),
        help="The number of products already handled by this work order")
    qty_producing = fields.Float(
        'Currently Produced Quantity', default=1.0,
        digits=dp.get_precision('Product Unit of Measure'),
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    is_produced = fields.Boolean(compute='_compute_is_produced')

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
    move_lot_ids = fields.One2many(
        'stock.move.lots', 'workorder_id', 'Moves to Track',
        domain=[('done_wo', '=', True)],
        help="Inventory moves for which you must scan a lot number at this work order")
    active_move_lot_ids = fields.One2many(
        'stock.move.lots', 'workorder_id',
        domain=[('done_wo', '=', False)])
    final_lot_id = fields.Many2one(
        'stock.production.lot', 'Current Lot', domain="[('product_id', '=', product_id)]",
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    time_ids = fields.One2many(
        'mrp.workcenter.productivity', 'workorder_id')
    is_user_working = fields.Boolean(
        'Is Current User Working', compute='_compute_is_user_working',
        help="Technical field indicating whether the current user is working. ")
    production_messages = fields.Html('Workorder Message', compute='_compute_production_messages')

    next_work_order_id = fields.Many2one('mrp.workorder', "Next Work Order")
    scrap_ids = fields.One2many('stock.scrap', 'workorder_id')
    scrap_count = fields.Integer(compute='_compute_scrap_move_count', string='Scrap Move')
    production_date = fields.Datetime('Production Date', related='production_id.date_planned_start', store=True)
    color = fields.Integer('Color', compute='_compute_color')
    capacity = fields.Float(
        'Capacity', default=1.0,
        help="Number of pieces that can be produced in parallel.")

    @api.one
    @api.depends('production_id.product_qty', 'qty_produced')
    def _compute_is_produced(self):
        self.is_produced = self.qty_produced >= self.production_id.product_qty

    @api.one
    @api.depends('time_ids.duration', 'qty_produced')
    def _compute_duration(self):
        self.duration = sum(self.time_ids.mapped('duration'))
        self.duration_unit = round(self.duration / max(self.qty_produced, 1), 2)  # rounding 2 because it is a time
        if self.duration_expected:
            self.duration_percent = 100 * (self.duration_expected - self.duration) / self.duration_expected
        else:
            self.duration_percent = 0

    def _compute_is_user_working(self):
        """ Checks whether the current user is working """
        for order in self:
            if order.time_ids.filtered(lambda x: (x.user_id.id == self.env.user.id) and (not x.date_end) and (x.loss_type in ('productive', 'performance'))):
                order.is_user_working = True
            else:
                order.is_user_working = False

    @api.depends('production_id', 'workcenter_id', 'production_id.bom_id')
    def _compute_production_messages(self):
        ProductionMessage = self.env['mrp.message']
        for workorder in self:
            domain = [
                ('valid_until', '>=', fields.Date.today()),
                '|', ('workcenter_id', '=', False), ('workcenter_id', '=', workorder.workcenter_id.id),
                '|', '|', '|',
                ('product_id', '=', workorder.product_id.id),
                '&', ('product_id', '=', False), ('product_tmpl_id', '=', workorder.product_id.product_tmpl_id.id),
                ('bom_id', '=', workorder.production_id.bom_id.id),
                ('routing_id', '=', workorder.operation_id.routing_id.id)]
            messages = ProductionMessage.search(domain).mapped('message')
            workorder.production_messages = "<br/>".join(messages) or False

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
            move_lots = self.active_move_lot_ids.filtered(lambda move_lot: move_lot.move_id == move)
            if not move_lots:
                continue
            new_qty = move.unit_factor * self.qty_producing
            if move.product_id.tracking == 'lot':
                move_lots[0].quantity = new_qty
                move_lots[0].quantity_done = new_qty
            elif move.product_id.tracking == 'serial':
                # Create extra pseudo record
                qty_todo = new_qty - sum(move_lots.mapped('quantity'))
                if float_compare(qty_todo, 0.0, precision_rounding=move.product_uom.rounding) > 0:
                    while float_compare(qty_todo, 0.0, precision_rounding=move.product_uom.rounding) > 0:
                        self.active_move_lot_ids += self.env['stock.move.lots'].new({
                            'move_id': move.id,
                            'product_id': move.product_id.id,
                            'lot_id': False,
                            'quantity': min(1.0, qty_todo),
                            'quantity_done': min(1.0, qty_todo),
                            'workorder_id': self.id,
                            'done_wo': False
                        })
                        qty_todo -= 1
                elif float_compare(qty_todo, 0.0, precision_rounding=move.product_uom.rounding) < 0:
                    qty_todo = abs(qty_todo)
                    for move_lot in move_lots:
                        if qty_todo <= 0:
                            break
                        if not move_lot.lot_id and qty_todo >= move_lot.quantity:
                            qty_todo = qty_todo - move_lot.quantity
                            self.active_move_lot_ids -= move_lot  # Difference operator
                        else:
                            move_lot.quantity = move_lot.quantity - qty_todo
                            if move_lot.quantity_done - qty_todo > 0:
                                move_lot.quantity_done = move_lot.quantity_done - qty_todo
                            else:
                                move_lot.quantity_done = 0
                            qty_todo = 0

    @api.multi
    def write(self, values):
        if ('date_planned_start' in values or 'date_planned_finished' in values) and any(workorder.state == 'done' for workorder in self):
            raise UserError(_('You can not change the finished work order.'))
        return super(MrpWorkorder, self).write(values)

    def _generate_lot_ids(self):
        """ Generate stock move lots """
        self.ensure_one()
        MoveLot = self.env['stock.move.lots']
        tracked_moves = self.move_raw_ids.filtered(
            lambda move: move.state not in ('done', 'cancel') and move.product_id.tracking != 'none' and move.product_id != self.production_id.product_id)
        for move in tracked_moves:
            qty = move.unit_factor * self.qty_producing
            if move.product_id.tracking == 'serial':
                while float_compare(qty, 0.0, precision_rounding=move.product_uom.rounding) > 0:
                    MoveLot.create({
                        'move_id': move.id,
                        'quantity': min(1, qty),
                        'quantity_done': min(1, qty),
                        'production_id': self.production_id.id,
                        'workorder_id': self.id,
                        'product_id': move.product_id.id,
                        'done_wo': False,
                    })
                    qty -= 1
            else:
                MoveLot.create({
                    'move_id': move.id,
                    'quantity': qty,
                    'quantity_done': qty,
                    'product_id': move.product_id.id,
                    'production_id': self.production_id.id,
                    'workorder_id': self.id,
                    'done_wo': False,
                    })

    @api.multi
    def record_production(self):
        self.ensure_one()
        if self.qty_producing <= 0:
            raise UserError(_('Please set the quantity you produced in the Current Qty field. It can not be 0!'))

        if (self.production_id.product_id.tracking != 'none') and not self.final_lot_id:
            raise UserError(_('You should provide a lot for the final product'))

        # Update quantities done on each raw material line
        raw_moves = self.move_raw_ids.filtered(lambda x: (x.has_tracking == 'none') and (x.state not in ('done', 'cancel')) and x.bom_line_id)
        for move in raw_moves:
            if move.unit_factor:
                rounding = move.product_uom.rounding
                move.quantity_done += float_round(self.qty_producing * move.unit_factor, precision_rounding=rounding)

        # Transfer quantities from temporary to final move lots or make them final
        for move_lot in self.active_move_lot_ids:
            # Check if move_lot already exists
            if move_lot.quantity_done <= 0:  # rounding...
                move_lot.unlink()
                continue
            if not move_lot.lot_id:
                raise UserError(_('You should provide a lot for a component'))
            # Search other move_lot where it could be added:
            lots = self.move_lot_ids.filtered(lambda x: (x.lot_id.id == move_lot.lot_id.id) and (not x.lot_produced_id) and (not x.done_move))
            if lots:
                lots[0].quantity_done += move_lot.quantity_done
                lots[0].lot_produced_id = self.final_lot_id.id
                move_lot.unlink()
            else:
                move_lot.lot_produced_id = self.final_lot_id.id
                move_lot.done_wo = True

        # One a piece is produced, you can launch the next work order
        if self.next_work_order_id.state == 'pending':
            self.next_work_order_id.state = 'ready'
        if self.next_work_order_id and self.final_lot_id and not self.next_work_order_id.final_lot_id:
            self.next_work_order_id.final_lot_id = self.final_lot_id.id

        self.move_lot_ids.filtered(
            lambda move_lot: not move_lot.done_move and not move_lot.lot_produced_id and move_lot.quantity_done > 0
        ).write({
            'lot_produced_id': self.final_lot_id.id,
            'lot_produced_qty': self.qty_producing
        })

        # If last work order, then post lots used
        # TODO: should be same as checking if for every workorder something has been done?
        if not self.next_work_order_id:
            production_move = self.production_id.move_finished_ids.filtered(lambda x: (x.product_id.id == self.production_id.product_id.id) and (x.state not in ('done', 'cancel')))
            if production_move.product_id.tracking != 'none':
                move_lot = production_move.move_lot_ids.filtered(lambda x: x.lot_id.id == self.final_lot_id.id)
                if move_lot:
                    move_lot.quantity += self.qty_producing
                else:
                    move_lot.create({'move_id': production_move.id,
                                     'lot_id': self.final_lot_id.id,
                                     'quantity': self.qty_producing,
                                     'quantity_done': self.qty_producing,
                                     'workorder_id': self.id,
                                     })
            else:
                production_move.quantity_done += self.qty_producing  # TODO: UoM conversion?
        # Update workorder quantity produced
        self.qty_produced += self.qty_producing

        # Set a qty producing
        if self.qty_produced >= self.production_id.product_qty:
            self.qty_producing = 0
        elif self.production_id.product_id.tracking == 'serial':
            self.qty_producing = 1.0
            self._generate_lot_ids()
        else:
            self.qty_producing = self.production_id.product_qty - self.qty_produced
            self._generate_lot_ids()

        self.final_lot_id = False
        if self.qty_produced >= self.production_id.product_qty:
            self.button_finish()
        return True

    @api.multi
    def button_start(self):
        # TDE CLEANME
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
        for timeline in timeline_obj.search(domain, limit=None if doall else 1):
            wo = timeline.workorder_id
            if timeline.loss_type != 'productive':
                timeline.write({'date_end': fields.Datetime.now()})
            else:
                maxdate = fields.Datetime.from_string(timeline.date_start) + relativedelta(minutes=wo.duration_expected - wo.duration)
                enddate = datetime.now()
                if maxdate > enddate:
                    timeline.write({'date_end': enddate})
                else:
                    timeline.write({'date_end': maxdate})
                    loss_id = self.env['mrp.workcenter.productivity.loss'].search([('loss_type', '=', 'performance')], limit=1)
                    if not len(loss_id):
                        raise UserError(_("You need to define at least one unactive productivity loss in the category 'Performance'. Create one from the Manufacturing app, menu: Configuration / Productivity Losses."))
                    timeline.copy({'date_start': maxdate, 'date_end': enddate, 'loss_id': loss_id.id})
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
            raise UserError(_('A Manufacturing Order is already done or cancelled!'))
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
