# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict
from openerp import api, fields, models, _
from openerp.exceptions import AccessError, UserError, Warning
from openerp.tools import float_compare, float_is_zero, DEFAULT_SERVER_DATETIME_FORMAT, html2plaintext
import openerp.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import math


class MrpProduction(models.Model):
    """ Manufacturing Orders """
    _name = 'mrp.production'
    _description = 'Manufacturing Order'
    _date_name = 'date_planned'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'date_planned asc,id'

    # Returns the destination location or default value from the picking type if none provided
    @api.multi
    def location_source(self):
        self.ensure_one()
        if self.location_src_id: return self.location_src_id
        if not self.picking_type_id.default_location_src_id:
            raise UserError(_('Please set a default source location in the operation type, using the coniguration menu of the Inventory app.'))
        return self.picking_type_id.default_location_src_id

    # Returns the destination location or default value from the picking type if none provided
    @api.multi
    def location_destination(self):
        self.ensure_one()
        if self.location_dest_id: return self.location_dest_id
        if not self.picking_type_id.default_location_dest_id:
            raise UserError(_('Please set a default destination location in the operation type, using the coniguration menu of the Inventory app.'))
        return self.picking_type_id.default_location_dest_id

    @api.model
    def _default_picking_type(self):
        type_obj = self.env['stock.picking.type']
        company_id = self.env.context.get('company_id') or self.env.user.company_id.id
        types = type_obj.search([('code', '=', 'mrp_operation'), ('warehouse_id.company_id', 'in', [company_id, False])])
        return types[0].id if types else False

    @api.multi
    @api.depends('move_raw_ids.state', 'work_order_ids.move_raw_ids')
    def _compute_availability(self):
        for order in self:
            if not order.move_raw_ids:
                order.availability = 'none'
                continue
            if order.bom_id.ready_to_produce == 'all_available':
                assigned_list = [x.state in ('assigned','done','cancel') for x in order.move_raw_ids]
            else:
                # TODO: improve this check
                assigned_list = [x.state in ('assigned','done','cancel') for x in order.move_raw_ids]
            order.availability = all(assigned_list) and 'assigned' or 'waiting'

    @api.multi
    @api.depends('work_order_ids')
    def _compute_nb_orders(self):
        for mo in self:
            mo.nb_orders = len(mo.work_order_ids)
            mo.nb_done = len(mo.work_order_ids.filtered(lambda x: x.state=='done'))

    @api.multi
    @api.depends('move_raw_ids.quantity_done', 'move_finished_ids.quantity_done')
    def _compute_post_visible(self):
        for order in self:
            order.post_visible = any(order.move_raw_ids.filtered(lambda x: (x.quantity_done) > 0 and (x.state<>'done'))) or \
                any(order.move_finished_ids.filtered(lambda x: (x.quantity_done) > 0 and (x.state<>'done')))

    name = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    origin = fields.Char(string='Source', help="Reference of the document that generated this manufacturing order.", copy=False)
    product_id = fields.Many2one('product.product', string='Product', required=True, readonly=True, states={'confirmed': [('readonly', False)]}, domain=[('type', 'in', ['product', 'consu'])])
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', related='product_id.product_tmpl_id')
    product_qty = fields.Float(string='Quantity to Produce', digits=dp.get_precision('Product Unit of Measure'), required=True, readonly=True, states={'confirmed': [('readonly', False)]}, default=1.0)
    product_uom_id = fields.Many2one('product.uom', string='Product Unit of Measure', required=True, readonly=True, states={'confirmed': [('readonly', False)]}, oldname='product_uom')

    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type', default=_default_picking_type, required=True)
    location_src_id = fields.Many2one('stock.location', string='Raw Materials Location', 
                                      readonly=True, states={'confirmed': [('readonly', False)]})
    location_dest_id = fields.Many2one('stock.location', string='Finished Products Location',
                                       readonly=True, states={'confirmed': [('readonly', False)]})
    date_planned = fields.Datetime(string='Expected Date', required=True, index=True, readonly=True, states={'confirmed': [('readonly', False)]}, copy=False, default=fields.Datetime.now)

    date_start = fields.Datetime(string='Start Date', readonly=True, copy=False)
    date_finished = fields.Datetime(string='End Date', readonly=True, copy=False)

    bom_id = fields.Many2one('mrp.bom', string='Bill of Material', readonly=True, states={'confirmed': [('readonly', False)]})
    routing_id = fields.Many2one('mrp.routing', string='Routing', related='bom_id.routing_id', store=True, readonly=True)

    # FP Note: what's the goal of this field? -> It is like the destination move of the production move
    move_prod_id = fields.Many2one('stock.move', string='Product Move', readonly=True, copy=False)
    move_raw_ids = fields.One2many('stock.move', 'raw_material_production_id', string='Raw Materials', states={'done': [('readonly', True)]}, copy=False)
    move_finished_ids = fields.One2many('stock.move', 'production_id', string='Finished Products', states={'done': [('readonly', True)]}, copy=False)
    work_order_ids = fields.One2many('mrp.production.work.order', 'production_id', string='Work Orders', readonly=True, oldname='workcenter_lines', copy=False)

    nb_orders = fields.Integer('# Work Orders', compute='_compute_nb_orders')
    nb_done = fields.Integer('# Done Work Orders', compute='_compute_nb_orders')

    state = fields.Selection([('confirmed', 'Confirmed'), ('planned', 'Planned'), ('progress', 'In Progress'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', default='confirmed', copy=False)

    availability = fields.Selection([('assigned', 'Available'), ('partially_available', 'Partially available'), ('none', 'None'), ('waiting', 'Waiting')], compute='_compute_availability', store=True, default="none")

    post_visible = fields.Boolean('Inventory Post Visible', compute='_compute_post_visible', help='Technical field to check when we can post')

    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env['res.company']._company_default_get('mrp.production'))

    check_to_done = fields.Boolean(compute="_get_produced_qty", string="Check Produced Qty")
    qty_produced = fields.Float(compute="_get_produced_qty", string="Quantity Produced")
    procurement_group_id = fields.Many2one('procurement.group', 'Procurement Group', copy=False)
    propagate = fields.Boolean(string='Propagate cancel and split', help='If checked, when the previous move of the move (which was generated by a next procurement) is cancelled or split, the move generated by this move will too')

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per Company!'),
        ('qty_positive', 'check (product_qty > 0)', 'The quantity to produce must be positive!'),
    ]

    @api.model
    def create(self, values):
        if not values.get('name', False):
            values['name'] = self.env['ir.sequence'].next_by_code('mrp.production') or 'New'
        if not values.get('procurement_group_id'):
            values['procurement_group_id'] = self.env["procurement.group"].create({'name': values['name']}).id
        production = super(MrpProduction, self).create(values)
        production._generate_moves()
        return production

    @api.multi
    def _workorders_create(self, bom, qty):
        state = 'ready'
        old = False
        tocheck = []
        for operation in bom.routing_id.work_order_ids:
            workcenter = operation.workcenter_id
            cycle_number = math.ceil(qty / bom.product_qty / workcenter.capacity) #TODO: float_round UP
            duration =  workcenter.time_start + workcenter.time_stop + cycle_number * operation.time_cycle * 100.0 / workcenter.time_efficiency
            workorder_id = self.work_order_ids.create({
                'name': operation.name,
                'production_id': self.id,
                'workcenter_id': operation.workcenter_id.id,
                'operation_id': operation.id,
                'duration': duration,
                'state': state
            })
            if old: old.next_work_order_id = workorder_id.id
            old = workorder_id
            tocheck = [workorder_id.operation_id.id]
            # Latest workorder receive all move not assigned to an operation
            if operation == bom.routing_id.work_order_ids[-1]:
                tocheck.append(False)

            # Add raw materials for this operation
            self.move_raw_ids.filtered(lambda x: x.operation_id.id in tocheck).write({
                'workorder_id': workorder_id.id
            })
            # Add finished products for this operation
            self.move_finished_ids.filtered(lambda x: x.operation_id.id in tocheck).write({
                'workorder_id': workorder_id.id
            })
            workorder_id._generate_lot_ids()
            state = 'pending'
        return True

    @api.multi
    def button_plan(self):
        orders_new = self.filtered(lambda x: x.routing_id and x.state == 'confirmed')
        # Create all work orders if not already created
        for order in orders_new:
            quantity = order.product_uom_id._compute_qty(order.product_qty, order.bom_id.product_uom_id.id)
            order.bom_id.explode(order.product_id, quantity, method_wo=order._workorders_create)
        orders_new.write({'state': 'planned'})

    def _check_serial(self):
        '''
            Checks if the production should help with this
        '''
        self.ensure_one()
        for move in self.move_raw_ids:
            if move.product_id.tracking == 'serial':
                return True
        for move in self.move_finished_ids:
            if move.product_id.tracking == 'serial':
                return True
        return False

    @api.multi
    def unlink(self):
        for production in self:
            if production.state not in ('draft', 'cancel'):
                raise UserError(_('Cannot delete a manufacturing order in state \'%s\'.') % production.state)
        return super(MrpProduction, self).unlink()

    @api.multi
    @api.onchange('product_id', 'company_id', 'picking_type_id')
    def onchange_product_id(self):
        if not self.product_id:
            self.product_uom_id = False
            self.bom_id = False
        else:
            bom_point = self.env['mrp.bom']._bom_find(product=self.product_id, picking_type=self.picking_type_id)
            self.product_uom_id = self.product_id.uom_id.id
            self.bom_id = bom_point.id
            return {'domain': {'product_uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}}

    @api.onchange('bom_id')
    def onchange_bom_id(self):
        if not self.bom_id:
            self.routing_id = False
        self.routing_id = self.bom_id.routing_id.id or False

    @api.multi
    def action_cancel(self):
        """ Cancels the production order and related stock moves.
        :return: True
        """
        ProcurementOrder = self.env['procurement.order']
        for production in self:
            if production.move_finished_ids:
                production.move_finished_ids.action_cancel()
            procs = ProcurementOrder.search([('move_dest_id', 'in', [record.id for record in production.move_raw_ids])])
            if procs:
                procs.cancel()
            production.move_raw_ids.action_cancel()
        self.write({'state': 'cancel'})
        # Put related procurements in exception
        procs = ProcurementOrder.search([('production_id', 'in', [self.ids])])
        if procs:
            procs.message_post(body=_('Manufacturing order cancelled.'))
            procs.write({'state': 'exception'})
        return True

    @api.multi
    def _cal_price(self, consumed_moves):
        return True

    @api.multi
    def post_inventory(self):
        for order in self:
            moves_to_do = order.move_raw_ids.move_validate()
            #order.move_finished_ids.filtered(lambda x: x.state not in ('done','cancel')).move_validate()
            order._cal_price(moves_to_do)
            moves_to_finish = order.move_finished_ids.move_validate()
            for move in moves_to_finish:
                quants = self.env['stock.quant']
                #Group quants by lots
                lot_quants = {}
                raw_lot_quants = {}
                if move.has_tracking != 'none':
                    for quant in move.quant_ids:
                        lot_quants.setdefault(quant.lot_id.id, self.env['stock.quant'])
                        raw_lot_quants.setdefault(quant.lot_id.id, self.env['stock.quant'])
                        lot_quants[quant.lot_id.id] |= quant
                for move_raw in moves_to_do:
                    if (move.has_tracking != 'none') and (move_raw.has_tracking != 'none'):
                        for lot in lot_quants:
                            lots = move_raw.quantity_lots.filtered(lambda x: x.lot_produced_id.id == lot).mapped('lot_id')
                            raw_lot_quants[lot] |= move_raw.quant_ids.filtered(lambda x: (x.lot_id in lots) and (x.qty > 0.0))
                    else:
                        quants |= move_raw.quant_ids.filtered(lambda x: x.qty > 0.0)
                if move.has_tracking != 'none':
                    for lot in lot_quants:
                        lot_quants[lot].write({'consumed_quant_ids': [(6, 0, [x.id for x in raw_lot_quants[lot] | quants])]})
                else:
                    move.quant_ids.write({'consumed_quant_ids': [(6, 0, [x.id for x in quants])]})
        return True

    @api.multi
    def button_mark_done(self):
        self.post_inventory()
        # self._costs_generate()
        write_res = self.write({'state': 'done', 'date_finished': fields.datetime.now()})
        self.env["procurement.order"].search([('production_id', 'in', self.ids)]).check()
        self.write({'state': 'done'})

    @api.multi
    def _get_produced_qty(self):
        for production in self:
            done_moves = self.move_finished_ids.filtered(lambda x: x.state!='cancel' and x.product_id.id == production.product_id.id)
            qty_produced = sum(done_moves.mapped('quantity_done'))
            production.check_to_done = done_moves and (qty_produced >= production.product_qty) and (production.state not in ('done', 'cancel'))
            production.qty_produced = qty_produced
        return True

    def _make_production_produce_line(self):
        procs = self.env['procurement.order'].search([('production_id', '=', self.id)])
        procurement = procs and procs[0]
        data = {
            'name': self.name,
            'date': self.date_planned,
            'date_expected': self.date_planned,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': self.product_qty,
            'location_id': self.product_id.property_stock_production.id,
            'location_dest_id': self.location_destination().id,
            'move_dest_id': self.move_prod_id.id,
            'procurement_id': procurement and procurement.id or False,
            'company_id': self.company_id.id,
            'production_id': self.id,
            'origin': self.name,
            'group_id': self.procurement_group_id.id,
        }
        move_id = self.env['stock.move'].create(data)
        move_id.action_confirm()
        return True

    @api.multi
    def _update_move(self, bom_line, quantity, result=None):
        self.ensure_one()
        move = self.move_raw_ids.filtered(lambda x:x.bom_line_id.id == bom_line.id and x.state not in ('done', 'cancel'))
        if move:
            move.write({'product_uom_qty': quantity})
            return move
        else:
            self._generate_move(bom_line, quantity)

    @api.multi
    def _generate_move(self, bom_line, quantity, result=None):
        self.ensure_one()
        if bom_line.product_id.type not in ['product', 'consu']:
            return False
        if self.bom_id.routing_id and self.bom_id.routing_id.location_id:
            source_location = self.bom_id.routing_id.location_id
        else:
            source_location = self.location_source()
        data = {
            'name': self.name,
            'date': self.date_planned,
            'bom_line_id': bom_line.id,
            'product_id': bom_line.product_id.id,
            'product_uom_qty': quantity,
            'product_uom': bom_line.product_uom_id.id,
            'location_id': source_location.id,
            'location_dest_id': self.product_id.property_stock_production.id,
            'raw_material_production_id': self.id,
            'company_id': self.company_id.id,
            'operation_id': bom_line.operation_id.id,
            'price_unit': bom_line.product_id.standard_price,
            'procure_method': bom_line.procure_method,
            'origin': self.name,
            'warehouse_id': source_location.get_warehouse(),
            'group_id': self.procurement_group_id.id,
            'propagate': self.propagate,
        }
        return self.env['stock.move'].create(data).action_confirm()

    @api.multi
    def _generate_moves(self):
        for production in self:
            production._make_production_produce_line()
            factor = self.env['product.uom']._compute_qty(self.product_uom_id.id, production.product_qty, production.bom_id.product_uom_id.id)
            production.bom_id.explode(production.product_id, factor / production.bom_id.product_qty, self._generate_move)
        return True

    @api.multi
    def action_assign(self):
        for production in self:
            production.move_raw_ids.action_assign()
        return True

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
            'context': {'product_ids': (self.move_raw_ids | self.move_finished_ids).mapped('product_id').ids},
            'target': 'new',
        }


class MrpProductionWorkcenterLine(models.Model):
    _name = 'mrp.production.work.order'
    _description = 'Work Order'
    _order = 'sequence'
    _inherit = ['mail.thread']

    @api.multi
    @api.depends('time_ids.state')
    def _compute_delay(self):
        for workorder in self:
            duration = sum(workorder.time_ids.filtered(lambda x: x.state == 'done').mapped('duration'))
            workorder.delay = duration
            workorder.delay_unit = round(duration / max(workorder.qty_produced, 1), 2)

    @api.multi
    @api.depends('move_raw_ids.state')
    def _compute_availability(self):
        for workorder in self:
            if workorder.move_raw_ids:
                if any([x.state != 'assigned' for x in workorder.move_raw_ids]):
                    workorder.availability = 'waiting'
                else:
                    workorder.availability = 'assigned'
            else:
                workorder.availability = workorder.production_id.availability == 'assigned' and 'assigned' or 'waiting'

    @api.depends('production_id', 'workcenter_id', 'production_id.bom_id', 'production_id.picking_type_id')
    def _get_inventory_message(self):
        InventoryMessage = self.env['inventory.message']
        for workorder in self:
            domain = [
                ('picking_type_id', '=', workorder.production_id.picking_type_id.id), '|',
                ('bom_id', '=', workorder.production_id.bom_id.id),
                ('workcenter_id', '=', workorder.workcenter_id.id),
                ('valid_until', '>=', fields.Date.today())
            ]
            messages = InventoryMessage.search(domain).mapped('message')
            workorder.inv_message = "<br/>".join(messages) or False

    name = fields.Char(string='Work Order', required=True, states={'done': [('readonly', True)]})
    workcenter_id = fields.Many2one('mrp.workcenter', string='Work Center', required=True, states={'done': [('readonly', True)]})
    duration = fields.Float(string='Expected Duration', digits=(16, 2), help="Expected duration in minutes", states={'done': [('readonly', True)]})
    sequence = fields.Integer(required=True, default=1, help="Gives the sequence order when displaying a list of work orders.")
    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', track_visibility='onchange', index=True, ondelete='cascade', required=True, states={'done': [('readonly', True)]})
    state = fields.Selection([('pending', 'Pending'), ('ready', 'Ready'), ('progress', 'In Progress'), ('done', 'Finished'), ('cancel', 'Cancelled')], default='pending')
    date_planned_start = fields.Datetime('Scheduled Date Start', states={'done': [('readonly', True)]})
    date_planned_end = fields.Datetime('Scheduled Date Finished', states={'done': [('readonly', True)]})

    date_start = fields.Datetime('Effective Start Date')
    date_finished = fields.Datetime('Effective End Date')
    delay = fields.Float('Real Duration', compute='_compute_delay', readonly=True, store=True, group_operator="avg")
    delay_unit = fields.Float('Duration Per Unit', compute='_compute_delay', readonly=True, store=True, group_operator="avg")

    qty_produced = fields.Float('Quantity', readonly=True, help="The number of products already handled by this work order", default=0.0) #TODO: decimal precision
    operation_id = fields.Many2one('mrp.routing.workcenter', 'Operation') #Should be used differently as BoM can change in the meantime

    move_raw_ids = fields.One2many('stock.move', 'workorder_id', 'Moves')
    move_traceability_ids = fields.One2many('stock.move.lots', 'workorder_id', string='Moves to Track',
        help="Inventory moves for which you must scan a lot number at this work order")
    active_move_traceability_ids = fields.One2many('stock.move.lots', 'workorder_id', string='Active Moves to Track',
        help="Active Inventory moves for which you must scan a lot number at this work order", domain=[('done', '=', False)])

    # FP TODO: replace by a related through MO, otherwise too much computation without need
    availability = fields.Selection([('waiting', 'Waiting'), ('assigned', 'Available')], 'Stock Availability', store=True, compute='_compute_availability')

    production_state = fields.Selection(related='production_id.state', readonly=True)
    product = fields.Many2one('product.product', related='production_id.product_id', string="Product", readonly=True) #should be product_id
    has_tracking = fields.Selection(related='production_id.product_id.tracking')
    qty = fields.Float(related='production_id.product_qty', string='Qty', readonly=True)
    uom = fields.Many2one('product.uom', related='production_id.product_uom_id', string='Unit of Measure')

    time_ids = fields.One2many('mrp.production.work.order.time', 'workorder_id')
    worksheet = fields.Binary('Worksheet', related='operation_id.worksheet', readonly=True)
    show_state = fields.Boolean(compute='_get_current_state')
    inv_message = fields.Html(compute="_get_inventory_message")
    final_lot_id = fields.Many2one('stock.production.lot', 'Current Lot', domain="[('product_id', '=', product)]")
    qty_producing = fields.Float('Qty Producing', default=1.0, states={'done': [('readonly', True)]})
    next_work_order_id = fields.Many2one('mrp.production.work.order', "Next Work Order")
    tracking = fields.Selection(related='product.tracking', readonly=True)

    @api.multi
    def write(self, values):
        if self.state == 'done' and values.get('date_planned_start') and values.get('date_planned_end'):
            raise UserError(_('You can not change the finished work order.'))
        return super(MrpProductionWorkcenterLine, self).write(values)

    def _generate_lot_ids(self):
        """
            Generate stock move lots
        """
        self.ensure_one()
        move_lot_obj = self.env['stock.move.lots']
        if self.move_raw_ids:
            moves = self.move_raw_ids.filtered(lambda x: (x.state not in ('done', 'cancel')) and (x.product_id.tracking != 'none') and (x.product_id.id != self.product.id))
            for move in moves:
                qty = self.qty_producing / move.bom_line_id.bom_id.product_qty * move.bom_line_id.product_qty
                if move.product_id.tracking=='serial':
                    while qty > 0.000001:
                        move_lot_obj.create({
                            'move_id': move.id,
                            'quantity': min(1,qty),
                            'product_id': move.product_id.id,
                            'production_id': self.production_id.id,
                            'workorder_id': self.id,
                        })
                        qty -= 1
                else:
                    move_lot_obj.create({
                        'move_id': move.id,
                        'quantity': qty,
                        'product_id': move.product_id.id,
                        'production_id': self.production_id.id,
                        'workorder_id': self.id,
                        })
                #self.env['stock.move.lots'].create({'':''})

    @api.multi
    def record_production(self):
        self.ensure_one()
        if self.qty_producing <= 0:
            raise UserError(_('Please set the quantity you produced in the Current Qty field. It can not be 0!'))

        # Update quantities done on each raw material line
        raw_moves = self.move_raw_ids.filtered(lambda x: (x.has_tracking == 'none') and (x.state not in ('done', 'cancel')))
        for move in raw_moves:
            factor = 1.0
            #if it's a finished product, we use factor 1 as no bom_line
            if move.bom_line_id:
                factor = move.bom_line_id.bom_id.product_qty * move.bom_line_id.product_qty
            move.quantity_done += self.qty_producing / factor

        # One a piece is produced, you can launch the next work order
        if self.next_work_order_id.state=='pending':
            self.next_work_order_id.state='ready'
        if self.next_work_order_id and self.final_lot_id and not self.next_work_order_id.final_lot_id:
            self.next_work_order_id.final_lot_id = self.final_lot_id.id

        #TODO: add filter for those that have not been done yet
        self.move_traceability_ids.write({'lot_produced_id': self.final_lot_id.id,
                                          'lot_produced_qty': self.qty_producing,
                                          'done': True})

        # If last work order, then post lots used
        #TODO: should be same as checking if for every workorder something has been done?
        if not self.next_work_order_id:
            production_move = self.production_id.move_finished_ids.filtered(lambda x: (x.product_id.id == self.production_id.product_id.id) and (x.state not in ('done', 'cancel')))
            if production_move.product_id.tracking != 'none':
                move_lot = production_move.quantity_lots.filtered(lambda x: x.lot_id.id == self.final_lot_id.id)
                if move_lot:
                    move_lot.quantity += self.qty_producing
                else:
                    move_lot.create({'move_id': production_move.id,
                                     'lot_id': self.final_lot_id.id,
                                     'quantity': self.qty_producing, })
            else:
                production_move.product_uom_qty += self.qty_producing #TODO: UoM conversion?
        # Update workorder quantity produced
        self.qty_produced += self.qty_producing
        self.qty_producing = 1.0
        self._generate_lot_ids()
        self.final_lot_id = False
        if self.qty_produced >= self.qty:
            self.button_finish()

    def _get_current_state(self):
        for order in self:
            if order.time_ids.filtered(lambda x : x.user_id.id == self.env.user.id and x.state == 'running'):
                order.show_state = True
            else:
                order.show_state = False

    @api.multi
    def button_start(self):
        timeline = self.env['mrp.production.work.order.time']
        for workorder in self:
            if workorder.production_id.state != 'progress':
                workorder.production_id.state = 'progress'
            timeline.create({'workorder_id': workorder.id,
                             'state': 'running',
                             'date_start': datetime.now(),
                             'user_id': self.env.user.id})
        self.write({'state': 'progress',
                    'date_start': datetime.now(),
                    })

    @api.multi
    def button_finish(self):
        self.ensure_one()
        self.end_all()
        self.write({'state': 'done'})
        if not self.production_id.work_order_ids.filtered(lambda x: x.state not in ('done','cancel')):
            self.production_id.button_mark_done()

    @api.multi
    def end_previous(self):
        timeline_obj = self.env['mrp.production.work.order.time']
        for workorder in self:
            timeline = timeline_obj.search([('workorder_id', '=', workorder.id), ('state', '=', 'running'), ('user_id', '=', self.env.user.id)], limit=1)
            timed = datetime.now() - fields.Datetime.from_string(timeline.date_start)
            duration = timed.total_seconds() / 60.0
            timeline.write({'state': 'done',
                            'duration': duration})

    @api.multi
    def end_all(self):
        timeline_obj = self.env['mrp.production.work.order.time']
        for workorder in self:
            timelines = timeline_obj.search([('workorder_id', '=', workorder.id), ('state', '=', 'running')])
            for timeline in timelines:
                timed = datetime.now() - fields.Datetime.from_string(timeline.date_start)
                duration = timed.total_seconds() / 60.0
                timeline.write({'state': 'done',
                                'duration': duration})

    @api.multi
    def button_pending(self):
        self.end_previous()

    @api.multi
    def button_cancel(self):
        self.write({'state': 'cancel'})

    @api.multi
    def button_done(self):
        self.end_all()
        self.write({'state': 'done',
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
            'context': {'product_ids': self.move_raw_ids.mapped('product_id').ids + [self.product.id]},
            'target': 'new',
        }


class MrpProductionWorkcenterLineTime(models.Model):
    _name='mrp.production.work.order.time'
    _description = 'Work Order Time'
    workorder_id = fields.Many2one('mrp.production.work.order', 'Work Order')
    date_start = fields.Datetime('Start Date')
    duration = fields.Float('Duration')
    user_id = fields.Many2one('res.users', string="User")
    state = fields.Selection([('running', 'Running'), ('done', 'Done')], string="Status", default="running")


class MrpUnbuild(models.Model):
    _name = "mrp.unbuild"
    _description = "Unbuild Order"
    _inherit = ['mail.thread']
    _order = 'id desc'

    def _src_id_default(self):
        try:
            location = self.env.ref('stock.stock_location_stock')
            location.check_access_rule('read')
        except (AccessError, ValueError):
            location = False
        return location

    def _dest_id_default(self):
        try:
            location = self.env.ref('stock.stock_location_stock')
            location.check_access_rule('read')
        except (AccessError, ValueError):
            location = False
        return location

    name = fields.Char(string='Reference', readonly=True, copy=False, default=False)
    product_id = fields.Many2one('product.product', string="Product", required=True, states={'done': [('readonly', True)]})
    product_qty = fields.Float('Quantity', required=True, states={'done': [('readonly', True)]})
    product_uom_id = fields.Many2one('product.uom', string="Unit of Measure", required=True, states={'done': [('readonly', True)]})
    bom_id = fields.Many2one('mrp.bom', 'Bill of Material', required=True, domain=[('product_tmpl_id', '=', 'product_id.product_tmpl_id')], states={'done': [('readonly', True)]})  # Add domain
    mo_id = fields.Many2one('mrp.production', string='Manufacturing Order', states={'done': [('readonly', True)]})
    lot_id = fields.Many2one('stock.production.lot', 'Lot', domain="[('product_id','=', product_id)]", states={'done': [('readonly', True)]})
    location_id = fields.Many2one('stock.location', 'Location', required=True, default=_src_id_default, states={'done': [('readonly', True)]})
    consume_line_id = fields.Many2one('stock.move', readonly=True)
    produce_line_ids = fields.One2many('stock.move', 'unbuild_id', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft', index=True)
    location_dest_id = fields.Many2one('stock.location', string='Destination Location', required=True, default=_dest_id_default, states={'done': [('readonly', True)]})

    @api.constrains('product_qty')
    def _check_qty(self):
        if self.product_qty <= 0:
            raise ValueError(_('Unbuild product quantity cannot be negative or zero!'))

    def _get_bom(self):
        # search BoM structure and route
        bom_point = self.bom_id
        if not bom_point:
            bom_point = self.env['mrp.bom']._bom_find(product=self.product_id)
            if bom_point:
                self.write({'bom_id': bom_point.id})
        if not bom_point:
            raise UserError(_("Cannot find a bill of material for this product."))
        return bom_point

    @api.multi
    def _generate_moves(self):
        for unbuild in self:
            bom = unbuild._get_bom()
            factor = unbuild.product_uom_id._compute_qty(unbuild.product_qty, bom.product_uom_id.id)
            bom.explode(unbuild.product_id, factor / bom.product_qty, self._generate_move)
            unbuild.consume_line_id.action_confirm()
        return True

    @api.model
    def create(self, vals):
        if not vals.get('name', False):
            vals['name'] = self.env['ir.sequence'].next_by_code('mrp.unbuild') or 'New'
        unbuild = super(MrpUnbuild, self).create(vals)
        unbuild._make_unbuild_consume_line()
        unbuild.consume_line_id.action_assign()
        unbuild._generate_moves()
        return unbuild

    def _make_unbuild_consume_line(self):
        data = {
            'name': self.name,
            'date': self.create_date,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': self.product_qty,
            'restrict_lot_id': self.lot_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.product_id.property_stock_production.id,
            'raw_material_unbuild_id': self.id,
            'origin': self.name
        }
        rec = self.env['stock.move'].create(data).action_confirm()
        return rec

    @api.multi
    def _generate_move(self, bom_line, quantity, result=None):
        self.ensure_one()
        data = {
            'name': self.name,
            'date': self.create_date,
            'bom_line_id': bom_line.id,
            'product_id': bom_line.product_id.id,
            'product_uom_qty': quantity,
            'product_uom': bom_line.product_uom_id.id,
            'procure_method': 'make_to_stock',
            'location_dest_id': self.location_dest_id.id,
            'location_id': self.product_id.property_stock_production.id,
            'unbuild_id': self.id,
        }
        return self.env['stock.move'].create(data)


    @api.onchange('mo_id')
    def onchange_mo_id(self):
        if self.mo_id:
            self.product_id = self.mo_id.product_id.id
            self.product_qty = self.mo_id.product_qty

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.bom_id = self.env['mrp.bom']._bom_find(product=self.product_id)
            self.product_uom_id = self.product_id.uom_id.id

    @api.multi
    def button_unbuild(self):
        self.consume_line_id.action_assign()
        # TODO : Need to assign quants which consumed at build product.
        self.quant_move_rel()
        self.consume_line_id.action_done()
        self.write({'state': 'done'})


    @api.multi
    def button_open_move(self):
        stock_moves = self.env['stock.move'].search(['|', ('unbuild_id', '=', self.id), ('raw_material_unbuild_id', '=', self.id)])
        return {
            'name': _('Stock Moves'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'stock.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', stock_moves.ids)],
        }

    @api.multi
    def _get_consumed_quants(self):
        self.ensure_one()
        quants = self.env['stock.quant']
        for move in self.consume_line_ids:
            for quant in move.reserved_quant_ids:
                quants = quants | quant.consumed_quant_ids
        return quants

    #TODO: need quants defined here
    @api.multi
    def quant_move_rel(self):
        self.ensure_one()
        todo_moves = self.env['stock.move']
        consumed_quants = self._get_consumed_quants()
        if consumed_quants:
            for move in self.produce_line_ids:
                res = []
                quants = consumed_quants.filtered(lambda x: x.product_id == move.product_id)
                if quants:
                    for quant in quants:
                        res += [(quant, quant.qty)]
                    self.env['stock.quant'].quants_move(res, move, move.location_dest_id)
                else:
                    todo_moves = todo_moves | move
        assigned_moves = self.produce_line_ids - todo_moves
        assigned_moves.write({'state': 'done'})
        todo_moves.action_done()


class InventoryMessage(models.Model):
    _name = "inventory.message"
    _description = "Inventory Message"

    @api.depends('message')
    def _get_note_first_line(self):
        for invmessage in self:
            invmessage.name = (invmessage.message and html2plaintext(invmessage.message) or "").strip().replace('*', '').split("\n")[0]

    @api.model
    def _default_valid_until(self):
        return datetime.today() + relativedelta(days=7)

    name = fields.Text(compute='_get_note_first_line', store=True)
    message = fields.Html(required=True)
    picking_type_id = fields.Many2one('stock.picking.type', string="Alert on Operation", required=True)
    code = fields.Selection(related='picking_type_id.code', store=True)
    product_id = fields.Many2one('product.product', string="Product", required=True)
    bom_id = fields.Many2one('mrp.bom', 'Bill of Material')
    workcenter_id = fields.Many2one('mrp.workcenter', string='Work Center')
    valid_until = fields.Date(default=_default_valid_until, required=True)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.bom_id = self.env['mrp.bom']._bom_find(product=self.product_id)
