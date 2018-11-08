# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round

class MrpProduction(models.Model):
    """ Manufacturing Orders """
    _name = 'mrp.production'
    _description = 'Production Order'
    _date_name = 'date_planned_start'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_planned_start asc,id'

    @api.model
    def _get_default_picking_type(self):
        return self.env['stock.picking.type'].search([
            ('code', '=', 'mrp_operation'),
            ('warehouse_id.company_id', 'in', [self.env.context.get('company_id', self.env.user.company_id.id), False])],
            limit=1).id

    @api.model
    def _get_default_location_src_id(self):
        location = False
        if self._context.get('default_picking_type_id'):
            location = self.env['stock.picking.type'].browse(self.env.context['default_picking_type_id']).default_location_src_id
        if not location:
            location = self.env.ref('stock.stock_location_stock', raise_if_not_found=False)
        return location and location.id or False

    @api.model
    def _get_default_location_dest_id(self):
        location = False
        if self._context.get('default_picking_type_id'):
            location = self.env['stock.picking.type'].browse(self.env.context['default_picking_type_id']).default_location_dest_id
        if not location:
            location = self.env.ref('stock.stock_location_stock', raise_if_not_found=False)
        return location and location.id or False

    name = fields.Char(
        'Reference', copy=False, readonly=True, default=lambda x: _('New'))
    origin = fields.Char(
        'Source', copy=False,
        help="Reference of the document that generated this production order request.")

    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('type', 'in', ['product', 'consu'])],
        readonly=True, required=True,
        states={'draft': [('readonly', False)]})
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', related='product_id.product_tmpl_id')
    product_qty = fields.Float(
        'Quantity To Produce',
        default=1.0, digits=dp.get_precision('Product Unit of Measure'),
        readonly=True, required=True, track_visibility='onchange',
        states={'draft': [('readonly', False)]})
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        oldname='product_uom', readonly=True, required=True,
        states={'draft': [('readonly', False)]})
    product_uom_qty = fields.Float(string='Total Quantity', compute='_compute_product_uom_qty', store=True)
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        default=_get_default_picking_type, required=True)
    location_src_id = fields.Many2one(
        'stock.location', 'Raw Materials Location',
        default=_get_default_location_src_id,
        readonly=True,  required=True,
        states={'draft': [('readonly', False)]},
        help="Location where the system will look for components.")
    location_dest_id = fields.Many2one(
        'stock.location', 'Finished Products Location',
        default=_get_default_location_dest_id,
        readonly=True,  required=True,
        states={'draft': [('readonly', False)]},
        help="Location where the system will stock the finished products.")
    date_planned_start = fields.Datetime(
        'Deadline Start', copy=False, default=fields.Datetime.now,
        index=True, required=True,
        states={'draft': [('readonly', False)]}, oldname="date_planned")
    date_planned_finished = fields.Datetime(
        'Deadline End', copy=False, default=fields.Datetime.now,
        index=True,
        states={'draft': [('readonly', False)]})
    date_start = fields.Datetime('Start Date', copy=False, index=True, readonly=True)
    date_finished = fields.Datetime('End Date', copy=False, index=True, readonly=True)
    bom_id = fields.Many2one(
        'mrp.bom', 'Bill of Material',
        readonly=True, states={'draft': [('readonly', False)]},
        help="Bill of Materials allow you to define the list of required raw materials to make a finished product.")
    routing_id = fields.Many2one(
        'mrp.routing', 'Routing',
        readonly=True, compute='_compute_routing', store=True,
        help="The list of operations (list of work centers) to produce the finished product. The routing "
             "is mainly used to compute work center costs during operations and to plan future loads on "
             "work centers based on production planning.")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('planned', 'Planned'),
        ('progress', 'In Progress'),
        ('to_close', 'To Close'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='State',
        compute='_compute_state', copy=False, index=True, readonly=True,
        store=True, track_visibility='onchange',
        help=" * Draft: The MO is not confirmed yet.\n"
             " * Confirmed: The MO is confirmed, the stock rules and the reordering of the components are trigerred.\n"
             " * Planned: The WO are planned.\n"
             " * In Progress: The production has started (on the MO or on the WO).\n"
             " * To Close: The production is done, the MO has to be closed.\n"
             " * Done: The MO is closed, the stock moves are posted. \n"
             " * Cancelled: The MO has been cancelled, can't be confirmed anymore.")
    reservation_state = fields.Selection([
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('waiting', 'Waiting Another Operation')],
        string='Material Availability',
        compute='_compute_state', copy=False, index=True, readonly=True,
        store=True, track_visibility='onchange', oldname='availability',
        help=" * Ready: The material is available to start the production.\n\
            * Waiting: The material is not available to start the production.\n\
            The material availability is impacted by the manufacturing readiness\
            defined on the BoM.")

    move_raw_ids = fields.One2many(
        'stock.move', 'raw_material_production_id', 'Raw Materials', oldname='move_lines',
        copy=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        domain=[('scrapped', '=', False)])
    move_finished_ids = fields.One2many(
        'stock.move', 'production_id', 'Finished Products',
        copy=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        domain=[('scrapped', '=', False)])
    finished_move_line_ids = fields.One2many(
        'stock.move.line', compute='_compute_lines', inverse='_inverse_lines', string="Finished Product"
        )
    workorder_ids = fields.One2many(
        'mrp.workorder', 'production_id', 'Work Orders',
        copy=False, oldname='workcenter_lines', readonly=True)
    workorder_count = fields.Integer('# Work Orders', compute='_compute_workorder_count')
    workorder_done_count = fields.Integer('# Done Work Orders', compute='_compute_workorder_done_count')
    move_dest_ids = fields.One2many('stock.move', 'created_production_id',
        string="Stock Movements of Produced Goods")

    unreserve_visible = fields.Boolean(
        'Allowed to Unreserve Inventory', compute='_compute_unreserve_visible',
        help='Technical field to check when we can unreserve')
    post_visible = fields.Boolean(
        'Allowed to Post Inventory', compute='_compute_post_visible',
        help='Technical field to check when we can post')
    consumed_less_than_planned = fields.Boolean(
        compute='_compute_consumed_less_than_planned',
        help='Technical field used to see if we have to display a warning or not when confirming an order.')

    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self._uid)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('mrp.production'),
        required=True)

    qty_produced = fields.Float(compute="_get_produced_qty", string="Quantity Produced")
    procurement_group_id = fields.Many2one(
        'procurement.group', 'Procurement Group',
        copy=False)
    propagate = fields.Boolean(
        'Propagate cancel and split',
        help='If checked, when the previous move of the move (which was generated by a next procurement) is cancelled or split, the move generated by this move will too')
    scrap_ids = fields.One2many('stock.scrap', 'production_id', 'Scraps')
    scrap_count = fields.Integer(compute='_compute_scrap_move_count', string='Scrap Move')
    priority = fields.Selection([('0', 'Not urgent'), ('1', 'Normal'), ('2', 'Urgent'), ('3', 'Very Urgent')], 'Priority',
                                readonly=True, states={'draft': [('readonly', False)]}, default='1')
    is_locked = fields.Boolean('Is Locked', default=True, copy=False)
    show_final_lots = fields.Boolean('Show Final Lots', compute='_compute_show_lots')
    production_location_id = fields.Many2one('stock.location', "Production Location", related='product_id.property_stock_production', readonly=False)
    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking_ids', string='Picking associated to this manufacturing order')
    delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_picking_ids')

    @api.depends('procurement_group_id')
    def _compute_picking_ids(self):
        for order in self:
            order.picking_ids = self.env['stock.picking'].search([
                ('group_id', '=', order.procurement_group_id.id),
            ])
            order.delivery_count = len(order.picking_ids)

    def action_view_mo_delivery(self):
        """ This function returns an action that display picking related to
        manufacturing order orders. It can either be a in a list or in a form
        view, if there is only one picking to show.
        """
        self.ensure_one()
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        pickings = self.mapped('picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action

    @api.depends('product_uom_id', 'product_qty', 'product_id.uom_id')
    def _compute_product_uom_qty(self):
        for production in self:
            if production.product_id.uom_id != production.product_uom_id:
                production.product_uom_qty = production.product_uom_id._compute_quantity(production.product_qty, production.product_id.uom_id)
            else:
                production.product_uom_qty = production.product_qty

    @api.depends('product_id.tracking')
    def _compute_show_lots(self):
        for production in self:
            production.show_final_lots = production.product_id.tracking != 'none'

    def _inverse_lines(self):
        """ Little hack to make sure that when you change something on these objects, it gets saved"""
        pass

    @api.depends('move_finished_ids.move_line_ids')
    def _compute_lines(self):
        for production in self:
            production.finished_move_line_ids = production.move_finished_ids.mapped('move_line_ids')

    @api.multi
    @api.depends('bom_id.routing_id', 'bom_id.routing_id.operation_ids')
    def _compute_routing(self):
        for production in self:
            if production.bom_id.routing_id.operation_ids:
                production.routing_id = production.bom_id.routing_id.id
            else:
                production.routing_id = False

    @api.multi
    @api.depends('workorder_ids')
    def _compute_workorder_count(self):
        data = self.env['mrp.workorder'].read_group([('production_id', 'in', self.ids)], ['production_id'], ['production_id'])
        count_data = dict((item['production_id'][0], item['production_id_count']) for item in data)
        for production in self:
            production.workorder_count = count_data.get(production.id, 0)

    @api.multi
    @api.depends('workorder_ids.state')
    def _compute_workorder_done_count(self):
        data = self.env['mrp.workorder'].read_group([
            ('production_id', 'in', self.ids),
            ('state', '=', 'done')], ['production_id'], ['production_id'])
        count_data = dict((item['production_id'][0], item['production_id_count']) for item in data)
        for production in self:
            production.workorder_done_count = count_data.get(production.id, 0)

    @api.multi
    @api.depends('move_raw_ids.state', 'move_finished_ids.state', 'workorder_ids', 'workorder_ids.state', 'qty_produced', 'move_raw_ids.quantity_done', 'product_qty')
    def _compute_state(self):
        """ Compute the production state. It use the same process than stock
        picking. It exists 3 extra steps for production:
        - planned: Workorder has been launched (workorders only)
        - progress: At least one item is produced.
        - to_close: The quantity produced is greater than the quantity to
        produce and all work orders has been finished.
        """
        # TODO: duplicated code with stock_picking.py
        for production in self:
            if not production.move_raw_ids:
                production.state = 'draft'
            elif all(move.state == 'draft' for move in production.move_raw_ids):
                production.state = 'draft'
            elif all(move.state == 'cancel' for move in production.move_raw_ids):
                production.state = 'cancel'
            elif all(move.state in ['cancel', 'done'] for move in production.move_raw_ids):
                production.state = 'done'
            elif production.move_finished_ids.filtered(lambda m: m.state not in ('cancel', 'done') and m.product_id.id == production.product_id.id)\
                 and (production.qty_produced >= production.product_qty)\
                 and (not production.routing_id or all(wo_state in ('cancel', 'done') for wo_state in production.workorder_ids.mapped('state'))):
                production.state = 'to_close'
            elif production.workorder_ids and any(wo_state in ('progress') for wo_state in production.workorder_ids.mapped('state'))\
                 or production.qty_produced > 0 and production.qty_produced < production.product_uom_qty:
                production.state = 'progress'
            elif production.workorder_ids:
                production.state = 'planned'
            else:
                production.state = 'confirmed'

            # Compute reservation state
            # State where the reservation does not matter.
            if production.state in ('draft', 'done', 'cancel'):
                production.reservation_state = False
            # Compute reservation state according to its component's moves.
            else:
                relevant_move_state = production.move_raw_ids._get_relevant_state_among_moves()
                if relevant_move_state == 'partially_available':
                    if production.routing_id and production.routing_id.operation_ids and production.bom_id.ready_to_produce == 'asap':
                        production.reservation_state = production._get_ready_to_produce_state()
                    else:
                        production.reservation_state = 'confirmed'
                elif relevant_move_state != 'draft':
                    production.reservation_state = relevant_move_state

    @api.depends('move_raw_ids', 'is_locked', 'state', 'move_raw_ids.quantity_done')
    def _compute_unreserve_visible(self):
        for order in self:
            already_reserved = order.is_locked and order.state not in ('done', 'cancel') and order.mapped('move_raw_ids.move_line_ids')
            any_quantity_done = any([m.quantity_done > 0 for m in order.move_raw_ids])
            order.unreserve_visible = not any_quantity_done and already_reserved

    @api.multi
    @api.depends('move_raw_ids.quantity_done', 'move_finished_ids.quantity_done', 'is_locked')
    def _compute_post_visible(self):
        for order in self:
            if order.product_tmpl_id._is_cost_method_standard():
                order.post_visible = order.is_locked and any((x.quantity_done > 0 and x.state not in ['done', 'cancel']) for x in order.move_raw_ids | order.move_finished_ids)
            else:
                order.post_visible = order.is_locked and any((x.quantity_done > 0 and x.state not in ['done', 'cancel']) for x in order.move_finished_ids)

    @api.multi
    @api.depends('move_raw_ids.quantity_done', 'move_raw_ids.product_uom_qty')
    def _compute_consumed_less_than_planned(self):
        """ Display a warning to the user if a component of the BoM has less
        quantity than planned.
        """
        for order in self:
            order.consumed_less_than_planned = any(order.move_raw_ids.filtered(
                lambda move: float_compare(move.quantity_done,
                                           move.product_uom_qty,
                                           precision_rounding=move.product_uom.rounding) == -1)
            )

    @api.multi
    @api.depends('workorder_ids.state', 'move_finished_ids', 'move_finished_ids.quantity_done', 'is_locked')
    def _get_produced_qty(self):
        for production in self:
            done_moves = production.move_finished_ids.filtered(lambda x: x.state != 'cancel' and x.product_id.id == production.product_id.id)
            qty_produced = sum(done_moves.mapped('quantity_done'))
            production.qty_produced = qty_produced
        return True

    @api.multi
    def _compute_scrap_move_count(self):
        data = self.env['stock.scrap'].read_group([('production_id', 'in', self.ids)], ['production_id'], ['production_id'])
        count_data = dict((item['production_id'][0], item['production_id_count']) for item in data)
        for production in self:
            production.scrap_count = count_data.get(production.id, 0)


    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per Company!'),
        ('qty_positive', 'check (product_qty > 0)', 'The quantity to produce must be positive!'),
    ]

    @api.onchange('product_id', 'picking_type_id', 'company_id')
    def onchange_product_id(self):
        """ Finds UoM of changed product. """
        if not self.product_id:
            self.bom_id = False
        else:
            bom = self.env['mrp.bom']._bom_find(product=self.product_id, picking_type=self.picking_type_id, company_id=self.company_id.id)
            if bom.type == 'normal':
                self.bom_id = bom.id
                self.product_qty = self.bom_id.product_qty
                self.product_uom_id = self.bom_id.product_uom_id.id
            else:
                self.bom_id = False
                self.product_uom_id = self.product_id.uom_id.id
            return {'domain': {'product_uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}}

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        self.product_qty = self.bom_id.product_qty
        self.product_uom_id = self.bom_id.product_uom_id.id

    @api.onchange('date_planned_start')
    def _onchange_date_planned_start(self):
        self.move_raw_ids.update({
            'date': self.date_planned_start,
            'date_expected': self.date_planned_start,
        })

    @api.onchange('bom_id', 'product_id', 'product_qty', 'product_uom_id')
    def _onchange_move_raw(self):
        self.move_raw_ids = [(2, move.id) for move in self.move_raw_ids.filtered(lambda m: m.bom_line_id)]
        if self.bom_id and self.product_qty > 0:
            moves_raw_values = self._get_moves_raw_values()
            for move_raw_values in moves_raw_values:
                self.move_raw_ids += self.env['stock.move'].new(move_raw_values)

    @api.onchange('location_src_id', 'move_raw_ids', 'routing_id')
    def _onchange_location(self):
        source_location = self._get_raw_location()
        self.move_raw_ids.update({
            'warehouse_id': source_location.get_warehouse().id,
            'location_id': source_location.id,
        })

    @api.onchange('picking_type_id')
    def onchange_picking_type(self):
        location = self.env.ref('stock.stock_location_stock')
        self.move_raw_ids.update({'picking_type_id': self.picking_type_id})
        self.location_src_id = self.picking_type_id.default_location_src_id.id or location.id
        self.location_dest_id = self.picking_type_id.default_location_dest_id.id or location.id

    @api.multi
    def write(self, vals):
        res = super(MrpProduction, self).write(vals)
        if 'date_planned_start' in vals:
            moves = (self.mapped('move_raw_ids') + self.mapped('move_finished_ids')).filtered(
                lambda r: r.state not in ['done', 'cancel'])
            moves.write({
                'date_expected': vals['date_planned_start'],
            })
        for production in self:
            if 'move_raw_ids' in vals and production.state != 'draft':
                production.move_raw_ids.filtered(lambda m: m.state == 'draft')._action_confirm()
        return res

    @api.model
    def create(self, values):
        if not values.get('name', False) or values['name'] == _('New'):
            picking_type_id = values.get('picking_type_id') or self._get_default_picking_type()
            picking_type_id = self.env['stock.picking.type'].browse(picking_type_id)
            if picking_type_id:
                values['name'] = picking_type_id.sequence_id.next_by_id()
            else:
                values['name'] = self.env['ir.sequence'].next_by_code('mrp.production') or _('New')
        if not values.get('procurement_group_id'):
            values['procurement_group_id'] = self.env["procurement.group"].create({'name': values['name']}).id
        return super(MrpProduction, self).create(values)

    @api.multi
    def unlink(self):
        if any(production.state != 'cancel' for production in self):
            raise UserError(_('Cannot delete a manufacturing order not in cancel state'))
        return super(MrpProduction, self).unlink()

    def action_toggle_is_locked(self):
        self.ensure_one()
        self.is_locked = not self.is_locked
        return True

    def _generate_finished_moves(self):
        move = self.env['stock.move'].create({
            'name': self.name,
            'date': self.date_planned_start,
            'date_expected': self.date_planned_start,
            'picking_type_id': self.picking_type_id.id,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': self.product_qty,
            'location_id': self.product_id.property_stock_production.id,
            'location_dest_id': self.location_dest_id.id,
            'company_id': self.company_id.id,
            'production_id': self.id,
            'warehouse_id': self.location_dest_id.get_warehouse().id,
            'origin': self.name,
            'group_id': self.procurement_group_id.id,
            'propagate': self.propagate,
            'move_dest_ids': [(4, x.id) for x in self.move_dest_ids],
        })
        return move

    def _get_moves_raw_values(self):
        self.ensure_one()
        moves = []
        factor = self.product_uom_id._compute_quantity(self.product_qty, self.bom_id.product_uom_id) / self.bom_id.product_qty
        boms, lines = self.bom_id.explode(self.product_id, factor, picking_type=self.bom_id.picking_type_id)
        for bom_line, line_data in lines:
            moves.append(self._get_move_raw_values(bom_line, line_data))
        return moves

    def _get_move_raw_values(self, bom_line, line_data):
        quantity = line_data['qty']
        # alt_op needed for the case when you explode phantom bom and all the lines will be consumed in the operation given by the parent bom line
        alt_op = line_data['parent_line'] and line_data['parent_line'].operation_id.id or False
        if bom_line.child_bom_id and bom_line.child_bom_id.type == 'phantom':
            return self.env['stock.move']
        if bom_line.product_id.type not in ['product', 'consu']:
            return self.env['stock.move']
        source_location = self._get_raw_location()
        data = {
            'sequence': bom_line.sequence,
            'name': self.name,
            'date': self.date_planned_start,
            'date_expected': self.date_planned_start,
            'bom_line_id': bom_line.id,
            'picking_type_id': self.picking_type_id.id,
            'product_id': bom_line.product_id.id,
            'product_uom_qty': quantity,
            'product_uom': bom_line.product_uom_id.id,
            'location_id': source_location.id,
            'location_dest_id': self.product_id.property_stock_production.id,
            'raw_material_production_id': self.id,
            'company_id': self.company_id.id,
            'operation_id': bom_line.operation_id.id or alt_op,
            'price_unit': bom_line.product_id.standard_price,
            'procure_method': 'make_to_stock',
            'origin': self.name,
            'state': 'draft',
            'warehouse_id': source_location.get_warehouse().id,
            'group_id': self.procurement_group_id.id,
            'propagate': self.propagate,
        }
        return data

    def _get_raw_location(self):
        if self.routing_id:
            routing = self.routing_id
        else:
            routing = self.bom_id.routing_id
        if routing and routing.location_id:
            return routing.location_id
        else:
            return self.location_src_id

    @api.multi
    def _adjust_procure_method(self):
        try:
            mto_route = self.env['stock.warehouse']._find_global_route('stock.route_warehouse0_mto', _('Make To Order'))
        except:
            mto_route = False
        for move in self.move_raw_ids:
            product = move.product_id
            routes = product.route_ids + product.route_from_categ_ids + move.warehouse_id.route_ids
            # TODO: optimize with read_group?
            pull = self.env['stock.rule'].search([('route_id', 'in', [x.id for x in routes]), ('location_src_id', '=', move.location_id.id),
                                                        ('location_id', '=', move.location_dest_id.id), ('action', '!=', 'push')], limit=1)
            if pull and (pull.procure_method == 'make_to_order'):
                move.procure_method = pull.procure_method
            elif not pull: # If there is no make_to_stock rule either
                if mto_route and mto_route.id in [x.id for x in routes]:
                    move.procure_method = 'make_to_order'

    @api.multi
    def _update_raw_move(self, bom_line, line_data):
        """ :returns update_move, old_quantity, new_quantity """
        quantity = line_data['qty']
        self.ensure_one()
        move = self.move_raw_ids.filtered(lambda x: x.bom_line_id.id == bom_line.id and x.state not in ('done', 'cancel'))
        if move:
            old_qty = move[0].product_uom_qty
            if quantity > 0:
                move[0].write({'product_uom_qty': quantity})
            elif quantity < 0:  # Do not remove 0 lines
                if move[0].quantity_done > 0:
                    raise UserError(_('Lines need to be deleted, but can not as you still have some quantities to consume in them. '))
                move[0]._action_cancel()
                move[0].unlink()
            return move[0], old_qty, quantity
        else:
            move_values = self._get_move_raw_values(bom_line, line_data)
            move = self.env['stock.move'].create(move_values)
            return move, 0, quantity

    def _get_ready_to_produce_state(self):
        """ returns 'assigned' if enough components are reserved in order to complete
        the first operation in the routing. If not returns 'waiting'
        """
        self.ensure_one()
        first_operation = self.routing_id.operation_ids[0]
        # Get BoM line related to first opeation in rounting. If there is only
        # one opeation in the routing then it will need all BoM lines.
        bom_line_ids = self.env['mrp.bom.line']
        if len(self.routing_id.operation_ids) == 1:
            bom_line_ids = self.bom_id.bom_line_ids
        else:
            bom_line_ids = self.bom_id.bom_line_ids.filtered(lambda bl: bl.operation_id == first_operation)
        bom_line_ids = bom_line_ids.filtered(lambda bl: not bl._skip_bom_line(self.product_id))

        moves_in_first_operation = self.move_raw_ids.filtered(lambda m: m.bom_line_id in bom_line_ids)
        if all(move.state == 'assigned' for move in moves_in_first_operation):
            return 'assigned'
        return 'confirmed'

    def action_confirm(self):
        for production in self:
            for move_raw in production.move_raw_ids:
                move_raw.write({
                    'group_id': production.procurement_group_id.id,
                    'unit_factor': move_raw.product_uom_qty / production.product_qty
                })
            production._generate_finished_moves()
            production._adjust_procure_method()
            (production.move_raw_ids | production.move_finished_ids)._action_confirm()
        return True

    @api.multi
    def action_assign(self):
        for production in self:
            production.move_raw_ids._action_assign()
        return True

    @api.multi
    def open_produce_product(self):
        self.ensure_one()
        action = self.env.ref('mrp.act_mrp_product_produce').read()[0]
        return action

    @api.multi
    def button_plan(self):
        """ Create work orders. And probably do stuff, like things. """
        orders_to_plan = self.filtered(lambda order: order.routing_id and order.state == 'confirmed')
        for order in orders_to_plan:
            order.move_raw_ids.filtered(lambda m: m.state == 'draft')._action_confirm()
            quantity = order.product_uom_id._compute_quantity(order.product_qty, order.bom_id.product_uom_id) / order.bom_id.product_qty
            boms, lines = order.bom_id.explode(order.product_id, quantity, picking_type=order.bom_id.picking_type_id)
            order._generate_workorders(boms)
        return True

    @api.multi
    def _generate_workorders(self, exploded_boms):
        workorders = self.env['mrp.workorder']
        original_one = False
        for bom, bom_data in exploded_boms:
            # If the routing of the parent BoM and phantom BoM are the same, don't recreate work orders, but use one master routing
            if bom.routing_id.id and (not bom_data['parent_line'] or bom_data['parent_line'].bom_id.routing_id.id != bom.routing_id.id):
                temp_workorders = self._workorders_create(bom, bom_data)
                workorders += temp_workorders
                if temp_workorders: # In order to avoid two "ending work orders"
                    if original_one:
                        temp_workorders[-1].next_work_order_id = original_one
                    original_one = temp_workorders[0]
        return workorders

    def _workorders_create(self, bom, bom_data):
        """
        :param bom: in case of recursive boms: we could create work orders for child
                    BoMs
        """
        workorders = self.env['mrp.workorder']
        bom_qty = bom_data['qty']

        # Initial qty producing
        if self.product_id.tracking == 'serial':
            quantity = 1.0
        else:
            quantity = self.product_qty - sum(self.move_finished_ids.mapped('quantity_done'))
            quantity = quantity if (quantity > 0) else 0

        for operation in bom.routing_id.operation_ids:
            # create workorder
            cycle_number = float_round(bom_qty / operation.workcenter_id.capacity, precision_digits=0, rounding_method='UP')
            duration_expected = (operation.workcenter_id.time_start +
                                 operation.workcenter_id.time_stop +
                                 cycle_number * operation.time_cycle * 100.0 / operation.workcenter_id.time_efficiency)
            workorder = workorders.create({
                'name': operation.name,
                'production_id': self.id,
                'workcenter_id': operation.workcenter_id.id,
                'operation_id': operation.id,
                'duration_expected': duration_expected,
                'state': len(workorders) == 0 and 'ready' or 'pending',
                'qty_producing': quantity,
                'capacity': operation.workcenter_id.capacity,
            })
            if workorders:
                workorders[-1].next_work_order_id = workorder.id
            workorders += workorder

            # assign moves; last operation receive all unassigned moves (which case ?)
            moves_raw = self.move_raw_ids.filtered(lambda move: move.operation_id == operation)
            if len(workorders) == len(bom.routing_id.operation_ids):
                moves_raw |= self.move_raw_ids.filtered(lambda move: not move.operation_id)
            moves_finished = self.move_finished_ids.filtered(lambda move: move.operation_id == operation) #TODO: code does nothing, unless maybe by_products?
            moves_raw.mapped('move_line_ids').write({'workorder_id': workorder.id})
            (moves_finished + moves_raw).write({'workorder_id': workorder.id})

            workorder._generate_lot_ids()
        return workorders

    def _check_lots(self):
        # Check that the raw materials were consumed for lots that we have produced.
        if self.product_id.tracking != 'none':
            finished_lots = set(self.finished_move_line_ids.mapped('lot_id'))
            raw_finished_lots = set(self.move_raw_ids.mapped('move_line_ids.lot_produced_id'))
            if not (raw_finished_lots <= finished_lots):
                lots_short = raw_finished_lots - finished_lots
                error_msg = _(
                    'Some raw materials have been consumed for a lot/serial number that has not been produced. '
                    'Unlock the MO and click on the components lines to correct it.\n'
                    'List of the components:\n'
                )
                move_lines = self.move_raw_ids.mapped('move_line_ids').filtered(lambda x: x.lot_produced_id in lots_short)
                for ml in move_lines:
                    error_msg += ml.product_id.display_name + ' (' + ml.lot_produced_id.name +')\n'
                raise UserError(error_msg)

    @api.multi
    def action_cancel(self):
        """ Cancels production order, unfinished stock moves and set procurement
        orders in exception """
        if any(workorder.state == 'progress' for workorder in self.mapped('workorder_ids')):
            raise UserError(_('You can not cancel production order, a work order is still in progress.'))
        documents = {}
        for production in self:
            for move_raw_id in production.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                iterate_key = self._get_document_iterate_key(move_raw_id)
                if iterate_key:
                    document = self.env['stock.picking']._log_activity_get_documents({move_raw_id: (move_raw_id.product_uom_qty, 0)}, iterate_key, 'UP')
                    for key, value in document.items():
                        if documents.get(key):
                            documents[key] += [value]
                        else:
                            documents[key] = [value]
            production.workorder_ids.filtered(lambda x: x.state != 'cancel').action_cancel()
            finish_moves = production.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            raw_moves = production.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            (finish_moves | raw_moves)._action_cancel()
            picking_ids = production.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            picking_ids.action_cancel()

        if documents:
            filtered_documents = {}
            for (parent, responsible), rendering_context in documents.items():
                if not parent or parent._name == 'stock.picking' and parent.state == 'cancel' or parent == self:
                    continue
                filtered_documents[(parent, responsible)] = rendering_context
            self._log_manufacture_exception(filtered_documents, cancel=True)
        return True

    def _get_document_iterate_key(self, move_raw_id):
        return move_raw_id.move_orig_ids and 'move_orig_ids' or False

    def _cal_price(self, consumed_moves):
        self.ensure_one()
        return True

    @api.multi
    def post_inventory(self):
        for order in self:
            moves_not_to_do = order.move_raw_ids.filtered(lambda x: x.state == 'done')
            moves_to_do = order.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            for move in moves_to_do.filtered(lambda m: m.product_qty == 0.0 and m.quantity_done > 0):
                move.product_uom_qty = move.quantity_done
            moves_to_do._action_done()
            moves_to_do = order.move_raw_ids.filtered(lambda x: x.state == 'done') - moves_not_to_do
            order._cal_price(moves_to_do)
            moves_to_finish = order.move_finished_ids.filtered(lambda x: x.state not in ('done','cancel'))
            moves_to_finish._action_done()
            order.action_assign()
            consume_move_lines = moves_to_do.mapped('active_move_line_ids')
            for moveline in moves_to_finish.mapped('active_move_line_ids'):
                if moveline.product_id == order.product_id and moveline.move_id.has_tracking != 'none':
                    if any([not ml.lot_produced_id for ml in consume_move_lines]):
                        raise UserError(_('You can not consume without telling for which lot you consumed it'))
                    # Link all movelines in the consumed with same lot_produced_id false or the correct lot_produced_id
                    filtered_lines = consume_move_lines.filtered(lambda x: x.lot_produced_id == moveline.lot_id)
                    moveline.write({'consume_line_ids': [(6, 0, [x for x in filtered_lines.ids])]})
                else:
                    # Link with everything
                    moveline.write({'consume_line_ids': [(6, 0, [x for x in consume_move_lines.ids])]})
        return True

    @api.multi
    def button_mark_done(self):
        self.ensure_one()
        for wo in self.workorder_ids:
            if wo.time_ids.filtered(lambda x: (not x.date_end) and (x.loss_type in ('productive', 'performance'))):
                raise UserError(_('Work order %s is still running') % wo.name)
        self._check_lots()
        self.post_inventory()
        moves_to_cancel = (self.move_raw_ids | self.move_finished_ids).filtered(lambda x: x.state not in ('done', 'cancel'))
        moves_to_cancel._action_cancel()
        self.write({'date_finished': fields.Datetime.now()})
        return True

    @api.multi
    def do_unreserve(self):
        for production in self:
            production.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel'))._do_unreserve()
        return True

    @api.multi
    def button_unreserve(self):
        self.ensure_one()
        self.do_unreserve()
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
            'context': {'default_production_id': self.id,
                        'product_ids': (self.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel')) | self.move_finished_ids.filtered(lambda x: x.state == 'done')).mapped('product_id').ids,
                        },
            'target': 'new',
        }

    @api.multi
    def action_see_move_scrap(self):
        self.ensure_one()
        action = self.env.ref('stock.action_stock_scrap').read()[0]
        action['domain'] = [('production_id', '=', self.id)]
        return action

    @api.model
    def get_empty_list_help(self, help):
        self = self.with_context(
            empty_list_help_document_name=_("manufacturing order"),
        )
        return super(MrpProduction, self).get_empty_list_help(help)

    def _log_downside_manufactured_quantity(self, moves_modification):

        def _keys_in_sorted(move):
            """ sort by picking and the responsible for the product the
            move.
            """
            return (move.picking_id.id, move.product_id.responsible_id.id)

        def _keys_in_groupby(move):
            """ group by picking and the responsible for the product the
            move.
            """
            return (move.picking_id, move.product_id.responsible_id)

        def _render_note_exception_quantity_mo(rendering_context):
            values = {
                'production_order': self,
                'order_exceptions': dict((key, d[key]) for d in rendering_context for key in d),
                'impacted_pickings': False,
                'cancel': False
            }
            return self.env.ref('mrp.exception_on_mo').render(values=values)

        documents = {}
        for move, (old_qty, new_qty) in moves_modification.items():
            document = self.env['stock.picking']._log_activity_get_documents(
                {move: (old_qty, new_qty)}, 'move_dest_ids', 'DOWN', _keys_in_sorted, _keys_in_groupby)
            for key, value in document.items():
                if documents.get(key):
                    documents[key] += [value]
                else:
                    documents[key] = [value]
        self.env['stock.picking']._log_activity(_render_note_exception_quantity_mo, documents)

    def _log_manufacture_exception(self, documents, cancel=False):

        def _render_note_exception_quantity_mo(rendering_context):
            visited_objects = []
            order_exceptions = {}
            for exception in rendering_context:
                order_exception, visited = exception
                order_exceptions.update(order_exception)
                visited_objects += visited
            visited_objects = self.env[visited_objects[0]._name].concat(*visited_objects)
            visited_objects |= visited_objects.mapped('move_orig_ids')
            impacted_pickings = []
            if visited_objects._name == 'stock.move':
                impacted_pickings = visited_objects.filtered(lambda m: m.state not in ('done', 'cancel')).mapped('picking_id')
            values = {
                'production_order': self,
                'order_exceptions': order_exceptions,
                'impacted_pickings': impacted_pickings,
                'cancel': cancel
            }
            return self.env.ref('mrp.exception_on_mo').render(values=values)

        self.env['stock.picking']._log_activity(_render_note_exception_quantity_mo, documents)
