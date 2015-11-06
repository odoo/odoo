# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil import relativedelta
import time

from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import SUPERUSER_ID, api, models, fields
import openerp.addons.decimal_precision as dp
from openerp.addons.procurement import procurement
from openerp.exceptions import UserError


class stock_move(models.Model):
    _name = "stock.move"
    _description = "Stock Move"
    _order = 'picking_id, sequence, id'
    _log_create = False
    _frozen_fields = set(['product_qty', 'product_uom', 'location_id', 'location_dest_id', 'product_id'])

    def get_price_unit(self, cr, uid, move, context=None):
        """ Returns the unit price to store on the quant """
        # TDE note: use not stored function field ?
        # used in stock_quant, overriden in purchase/stock.py
        return move.price_unit or move.product_id.standard_price

    @api.multi
    def name_get(self):
        res = []
        for line in self:
            name = line.location_id.name + ' > ' + line.location_dest_id.name
            if line.product_id.code:
                name = line.product_id.code + ': ' + name
            if line.picking_id.origin:
                name = line.picking_id.origin + '/ ' + name
            res.append((line.id, name))
        return res

    @api.model
    def _get_default_group_id(self):
        if self._context.get('default_picking_id'):
            return self.env['stock.picking'].browse(self._context['default_picking_id']).group_id
        return self.env['procurement.group']

    sequence = fields.Integer('Sequence', default=10)
    name = fields.Char('Description', required=True, select=True)
    priority = fields.Selection(procurement.PROCUREMENT_PRIORITIES, 'Priority', default='1')
    create_date = fields.Datetime('Creation Date', readonly=True, select=True)
    date = fields.Datetime(
        'Date',
        required=True, select=True,
        default=fields.Datetime.now,
        states={'done': [('readonly', True)]},
        help="Move date: scheduled date until move is done, then date of actual move processing")
    date_expected = fields.Datetime(
        'Expected Date',
        required=True, select=True,
        default=fields.Datetime.now,
        states={'done': [('readonly', True)]},
        help="Scheduled date for the processing of this move")
    note = fields.Text('Notes')
    state = fields.Selection([
        ('draft', 'New'),
        ('cancel', 'Cancelled'),
        ('waiting', 'Waiting Another Move'),
        ('confirmed', 'Waiting Availability'),
        ('assigned', 'Available'),
        ('done', 'Done')],
        string='Status',
        readonly=True, select=True, copy=False,
        default='draft',
        help="* New: When the stock move is created and not yet confirmed.\n"
             "* Waiting Another Move: This state can be seen when a move is waiting for another one, for example in a chained flow.\n"
             "* Waiting Availability: This state is reached when the procurement resolution is not straight forward. It may need the scheduler to run, a component to me manufactured...\n"
             "* Available: When products are reserved, it is set to \'Available\'.\n"
             "* Done: When the shipment is processed, the state is \'Done\'.")
    partially_available = fields.Boolean(
        'Partially Available',
        readonly=True, copy=False,
        help="Checks if the move has some stock reserved")  # TDE note: linked to picking.state ? Why not use the latter one ? OR directly in state ?
    company_id = fields.Many2one(
        'res.company', 'Company',
        required=True, select=True,
        default=lambda self: self.env['res.company']._company_default_get('stock.move'))
    origin = fields.Char("Source Document")  # TDE note: become chatter link
    # product
    product_id = fields.Many2one(
        'product.product', 'Product',
        required=True, select=True,
        domain=[('type', 'in', ['product', 'consu'])],
        states={'done': [('readonly', True)]})
    product_qty = fields.Float(
        'Quantity', digits=0,
        compute='_compute_product_quantity',
        inverse='_set_product_quantity',
        store=True,
        help='Quantity in the default UoM of the product')
    product_uom_qty = fields.Float(
        'Quantity', digits_compute=dp.get_precision('Product Unit of Measure'),
        required=True,
        default=1.0,
        states={'done': [('readonly', True)]},
        help="This is the quantity of products from an inventory point of view. "
             "For moves in the state 'done', this is the quantity of products "
             "that were actually moved. For other moves, this is the quantity "
             "of product that is planned to be moved. Lowering this quantity does "
             "not generate a backorder. Changing this quantity on assigned moves "
             "affects the product reservation, and should be done with care."
    )
    product_uom = fields.Many2one(
        'product.uom', 'Unit of Measure',
        required=True,
        states={'done': [('readonly', True)]})  # TDE TODO: rename to product_uom_id
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product Template',
        related='product_id.product_tmpl_id')
    product_packaging = fields.Many2one(
        'product.packaging', string='Preferred Packaging',
        help="It specifies attributes of packaging like type, quantity of packaging,etc.")  # TDE TODO: rename to product_packaging_id
    price_unit = fields.Float(
        'Unit Price',
        help="Technical field used to record the product cost set by the user during a picking "
             "confirmation (when costing method used is 'average price' or 'real'). Value given "
             "in company currency and in product uom.")  # as it's a technical field, we intentionally don't provide the digits attribute
    # location
    location_id = fields.Many2one(
        'stock.location', 'Source Location',
        required=True, select=True,
        auto_join=True,
        states={'done': [('readonly', True)]},
        help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations.")
    location_dest_id = fields.Many2one(
        'stock.location', 'Destination Location',
        required=True, select=True,
        auto_join=True,
        states={'done': [('readonly', True)]},
        help="Location where the system will stock the finished products.")
    partner_id = fields.Many2one(
        'res.partner', 'Destination Address ',
        states={'done': [('readonly', True)]},
        help="Optional address where goods are to be delivered, specifically used for allotment")
    scrapped = fields.Boolean(
        'Scrapped',
        related='location_dest_id.scrap_location',
        readonly=True)  # TDE note: used in stock_picking, sale_stock, mrp  # TDE note2: related and updated below ???? what da fouque ?
    # stock move
    move_dest_id = fields.Many2one(
        'stock.move', 'Destination Move',
        select=True, copy=False,
        help="Optional: next stock move when chaining them")
    move_orig_ids = fields.One2many(
        'stock.move', 'move_dest_id', 'Original Move',
        select=True,
        help="Optional: previous stock move when chaining them")  # TDE TODO: select on a o2m ???
    picking_id = fields.Many2one(
        'stock.picking', 'Transfer Reference',
        select=True,
        states={'done': [('readonly', True)]})
    # backorder_id = fields.Many2one(
    #     'stock.picking', string="Back Order of",
    #     select=True,
    #     related='picking_id.backorder_id')  # TDE note: does not seem to be used, let's comment it
    split_from = fields.Many2one(
        'stock.move', string="Move Split From",
        copy=False,
        help="Technical field used to track the origin of a split move, which can be useful in case of debug")
    # quants
    quant_ids = fields.Many2many(
        'stock.quant', 'stock_quant_move_rel', 'move_id', 'quant_id',
        'Moved Quants',
        copy=False)
    reserved_quant_ids = fields.One2many(
        'stock.quant', 'reservation_id',
        'Reserved quants')
    # operation
    linked_move_operation_ids = fields.One2many(
        'stock.move.operation.link', 'move_id',
        string='Linked Operations',
        readonly=True,
        help='Operations that impact this move for the computation of the remaining quantities')
    remaining_qty = fields.Float(
        'Remaining Quantity',
        compute='_compute_remaining_qty',
        digits=0,
        states={'done': [('readonly', True)]},
        help="Remaining Quantity in default UoM according to operations matched with this move")
    # procurement
    procure_method = fields.Selection([
        ('make_to_stock', 'Default: Take From Stock'),
        ('make_to_order', 'Advanced: Apply Procurement Rules')],
        'Supply Method', required=True,
        default='make_to_stock',
        help="By default, the system will take from the stock in the source location and passively "
             "wait for availability. The other possibility allows you to directly create a "
             "procurement on the source location (and thus ignore its current stock) to gather "
             "products. If we want to chain moves and have this one to wait for the previous, this "
             "second option should be chosen.")
    procurement_id = fields.Many2one('procurement.order', 'Procurement')
    group_id = fields.Many2one('procurement.group', 'Procurement Group', default=_get_default_group_id)
    rule_id = fields.Many2one('procurement.rule', 'Procurement Rule', help='The procurement rule that created this stock move')

    # don't know, but hey, who's the boss
    push_rule_id = fields.Many2one(
        'stock.location.path', 'Push Rule',
        help='The push rule that created this stock move')
    propagate = fields.Boolean(
        'Propagate cancel and split',
        dfeault=True,
        help='If checked, when this move is cancelled, cancel the linked move too')
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type')
    inventory_id = fields.Many2one('stock.inventory', 'Inventory')
    lot_ids = fields.Many2many(
        string='Lots',
        relation='stock.production.lot',
        compute='_compute_lot_ids')
    origin_returned_move_id = fields.Many2one(
        'stock.move', 'Origin return move',
        copy=False,
        help='move that created the return move')
    returned_move_ids = fields.One2many(
        'stock.move', 'origin_returned_move_id',
        'All returned moves',
        help='Optional: all returned moves created from this move')

    # oops
    reserved_availability = fields.Float(
        'Quantity Reserved',
        compute='_compute_reserved_availability',
        readonly=True,
        help='Quantity that has already been reserved for this move')
    availability = fields.Float(
        'Forecasted Quantity',
        compute='_compute_product_availability',
        readonly=True,
        help='Quantity in stock that can still be reserved for this move')
    string_availability_info = fields.Text(
        'Availability',
        compute='_compute_string_qty_information',
        readonly=True,
        help='Show various information on stock availability for this move')

    # don't know actually
    restrict_lot_id = fields.Many2one(
        'stock.production.lot',
        string='Lot',
        help="Technical field used to depict a restriction on the lot of quants to consider when marking this move as 'done'")  # TDE note: update label / help
    restrict_partner_id = fields.Many2one(
        'res.partner',
        string='Owner ',
        help="Technical field used to depict a restriction on the ownership of quants to consider when marking this move as 'done'")  # TDE note: update label / help
    route_ids = fields.Many2many(
        'stock.location.route', 'stock_location_route_move',
        'move_id', 'route_id',
        string='Destination route',
        help="Preferred route to be followed by the procurement order")
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        help="Technical field depicting the warehouse to consider for the route selection on the next procurement (if any).")  # TDE note: udpate label / help

    @api.one
    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_product_quantity(self):
        # TDE NOTE: _compute_qty_obj does not work in batch, so let's one
        self.product_qty = self.env['product.uom']._compute_qty_obj(self.product_uom, self.product_uom_qty, self.product_id.uom_id)

    def _set_product_quantity(self, value):
        """ The meaning of product_qty field changed lately and is now a functional field computing the quantity
            in the default product UoM. This code has been added to raise an error if a write is made given a value
            for `product_qty`, where the same write should set the `product_uom_qty` field instead, in order to
            detect errors.
        """
        raise UserError(_('The requested operation cannot be processed because of a programming error setting the `product_qty` field instead of the `product_uom_qty`.'))

    @api.multi
    def _compute_remaining_qty(self):
        for move in self:
            move.remaining_qty = float_round(
                move.product_qty - sum(operation.qty for operation in move.linked_move_operation_ids),
                precision_rounding=move.product_id.uom_id.rounding)

    @api.multi
    def _compute_lot_ids(self):
        for move in self:
            if move.state == 'done':
                move.lot_ids = [q.lot_id.id for q in move.quant_ids if q.lot_id]
            else:
                move.lot_ids = [q.lot_id.id for q in move.reserved_quant_ids if q.lot_id]

    @api.multi
    def _compute_string_qty_information(self):
        # look in the settings if we need to display the UoM name or not
        config = self.env['stock.config.settings'].search([], limit=1, order='id DESC')
        add_uom = bool(config.group_uom)
        uom_obj = self.env['product.uom']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for move in self:
            if move.state in ('draft', 'done', 'cancel') or move.location_id.usage != 'internal':
                move.string_availability_info = ''  # 'not applicable' or 'n/a' could work too
                continue
            total_available = min(move.product_qty, move.reserved_availability + move.availability)
            total_available = uom_obj._compute_qty_obj(move.product_id.uom_id, total_available, move.product_uom, round=False)
            total_available = float_round(total_available, precision_digits=precision)
            info = str(total_available)
            if add_uom:
                info += ' ' + move.product_uom.name
            if move.reserved_availability:
                if move.reserved_availability != total_available:
                    # some of the available quantity is assigned and some are available but not reserved
                    reserved_available = uom_obj._compute_qty_obj(move.product_id.uom_id, move.reserved_availability, move.product_uom, round=False)
                    reserved_available = float_round(reserved_available, precision_digits=precision)
                    info += _(' (%s reserved)') % str(reserved_available)
                else:
                    # all available quantity is assigned
                    info += _(' (reserved)')
            move.string_availability_info = info

    @api.multi
    def _compute_reserved_availability(self):
        for move in self:
            move.reserved_availability = sum(quant.qty for quant in move.reserved_quant_ids)

    @api.multi
    def _compute_product_availability(self):
        quant_obj = self.env['stock.quant']
        for move in self:
            if move.state == 'done':
                move.availability = move.product_qty
            else:
                sublocation_ids = self.env['stock.location'].search([('id', 'child_of', [move.location_id.id])])
                quant_ids = quant_obj.search([('location_id', 'in', sublocation_ids.ids), ('product_id', '=', move.product_id.id), ('reservation_id', '=', False)])
                availability = 0
                for quant in quant_ids:
                    availability += quant.qty
                move.availability = min(move.product_qty, availability)

    @api.multi
    def _check_uom(self):
        return not(any(move.product_id.uom_id.category_id.id != move.product_uom.category_id.id for move in self))

    _constraints = [
        (_check_uom,
            'You try to move a product using a UoM that is not compatible with the UoM of the product moved. Please use an UoM in the same UoM category.',
            ['product_uom']),
    ]

    def init(self, cr):
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_move_product_location_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX stock_move_product_location_index ON stock_move (product_id, location_id, location_dest_id, company_id, state)')

    @api.multi
    def unlink(self):
        if any(move.state not in ('draft', 'cancel') for move in self):
                raise UserError(_('You can only delete draft moves.'))
        return super(stock_move, self).unlink()

    @api.multi
    def write(self, vals):
        if any(updated_field in self._frozen_fields for updated_field in vals):
            if any(move.state == 'done' for move in self):
                # TDE note: why "except bu-y the Administrator", because he will
                # go through this error as well ?
                raise UserError(_('Quantities, Units of Measure, Products and Locations cannot be modified on stock moves that have already been processed (except by the Administrator).'))

        propagated_changes_dict = {}
        # propagation of quantity change
        if vals.get('product_uom_qty'):
            propagated_changes_dict['product_uom_qty'] = vals['product_uom_qty']
        if vals.get('product_uom_id'):
            propagated_changes_dict['product_uom_id'] = vals['product_uom_id']
        # propagation of expected date:
        propagated_date_field = False
        if vals.get('date_expected'):
            # propagate any manual change of the expected date
            propagated_date_field = 'date_expected'
        elif vals.get('state', '') == 'done' and vals.get('date'):
            # propagate also any delta observed when setting the move as done
            propagated_date_field = 'date'

        if not self._context.get('do_not_propagate') and (propagated_date_field or propagated_changes_dict):
            # any propagation is (maybe) needed
            to_propagate = self.filtered(lambda self: bool(self.move_dest_id) and move.propagate)
            if propagated_date_field:  # TDE note: date depends on each move, not done in batch
                for move in to_propagate:
                    # TDE note: seems useless code
                    # if 'date_expected' in propagated_changes_dict:
                    #     propagated_changes_dict.pop('date_expected')

                    # TDE note: what does this code ? why mixing date_expected, the
                    # compute date (date / date_expected) and anyway write on
                    # date_expected ? Where you drunk ?
                    if propagated_date_field:
                        current_date = datetime.strptime(move.date_expected, DEFAULT_SERVER_DATETIME_FORMAT)
                        new_date = datetime.strptime(vals.get(propagated_date_field), DEFAULT_SERVER_DATETIME_FORMAT)
                        delta = new_date - current_date
                        if abs(delta.days) >= move.company_id.propagation_minimum_delta:
                            old_move_date = datetime.strptime(move.move_dest_id.date_expected, DEFAULT_SERVER_DATETIME_FORMAT)
                            new_move_date = (old_move_date + relativedelta.relativedelta(days=delta.days or 0)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                            propagated_changes_dict['date_expected'] = new_move_date
                    #For pushed moves as well as for pulled moves, propagate by recursive call of write().
                    #Note that, for pulled moves we intentionally don't propagate on the procurement.
                    if propagated_changes_dict:
                        move.move_dest_id.write(propagated_changes_dict)
            else:
                to_propagate.mapped('move_dest_id').write(propagated_changes_dict)
        return super(stock_move, self).write(vals)

    @api.onchange('product_id', 'product_qty', 'product_uom_qty', 'product_uom')
    def onchange_quantity(self):
        """ On change of product quantity finds UoM
        @param product_id: Product id
        @param product_qty: Changed Quantity of product
        @param product_uom: Unit of measure of product
        @return: Dictionary of values
        """
        # TDE note: docstring of this method is completely wrong
        if not self.product_id or self.product_qty <= 0.0:
            return {'value': {'product_qty': 0.0}}
        if any(self.product_qty < move.product_qty for move in self.read('product_qty')):
            return {'warning': {
                'title': _('Information'),
                'message': _("By changing this quantity here, you accept the "
                             "new quantity as complete: Odoo will not "
                             "automatically generate a back order.")}}
        return {'value': {}}

    @api.onchange('product_id', 'partner_id')
    def onchange_product_id(self):
        """ On change of product id, if finds UoM, quantity
        @param prod_id: Changed Product id
        @param loc_id: Source location id
        @param loc_dest_id: Destination location id
        @param partner_id: Address id of partner
        @return: Dictionary of values
        """
        if not self.product_id:
            return {'domain': {'product_uom': []}}
        lang = self.partner_id.lang or self.env.user.lang
        translated_product = self.product_id.with_context(lang=lang)
        self.name = translated_product.partner_ref
        self.product_uom = translated_product.uom_id
        self.product_uom_qty = 1.0
        return {
            'domain': {'product_uom': [('category_id', '=', translated_product.uom_id.category_id.id)]}
        }

    @api.onchange('date', 'date_expected')
    def onchange_date(self):
        """ On change of Scheduled Date gives a Move date.
        @param date_expected: Scheduled Date
        @param date: Move Date
        @return: Move Date
        """
        # TDE note: purpose of this method ? why is it depending on 'date' ?
        if not self.date_expected:
            self.date_expected = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.date = self.date_expected

    @api.multi
    def do_unreserve(self):
        # TDE note: called by stock_picking.do_unreserve()
        Quant = self.env["stock.quant"]
        for move in self:
            if move.state in ('done', 'cancel'):
                # TDE note: update error message according to condition
                raise UserError(_('Cannot unreserve a done move'))
            # TDE note: weird that the main method is on quant, to check
            Quant.quants_unreserve(move)
            # TDE note: find_move_ancestors -> has_ancestor (TO DEVELOP)
            if move.find_move_ancestors():
                move.write({'state': 'waiting'})
            else:
                move.write({'state': 'confirmed'})

    @api.multi
    def _prepare_procurement_from_move(self):
        self.ensure_one()
        origin = (self.group_id and (self.group_id.name + ":") or "") + (self.rule_id and self.rule_id.name or self.origin or self.picking_id.name or "/")
        group_id = self.group_id and self.group_id.id or False
        if self.rule_id:
            if self.rule_id.group_propagation_option == 'fixed' and self.rule_id.group_id:
                group_id = self.rule_id.group_id.id
            elif self.rule_id.group_propagation_option == 'none':
                group_id = False
        return {
            'name': self.rule_id and self.rule_id.name or "/",
            'origin': origin,
            'company_id': self.company_id and self.company_id.id or False,
            'date_planned': self.date,
            'product_id': self.product_id.id,
            'product_qty': self.product_uom_qty,
            'product_uom': self.product_uom.id,
            'location_id': self.location_id.id,
            'move_dest_id': self.id,
            'group_id': group_id,
            'route_ids': [(4, x.id) for x in self.route_ids],
            'warehouse_id': self.warehouse_id.id or (self.picking_type_id and self.picking_type_id.warehouse_id.id or False),
            'priority': self.priority,
        }

    @api.multi
    def _create_procurements(self):
        # TDE note: called by action_confirm
        procurements = self.env['procurement.order']
        for move in self:
            procurements &= self.env['procurement.order'].create(move._prepare_procurement_from_move())
        return procurements

    @api.multi
    def _prepare_picking_assign(self):
        """ Prepares a new picking for this move as it could not be assigned to
        another picking. This method is designed to be inherited.
        """
        self.ensure_one()
        values = {
            'origin': self.origin,
            'company_id': self.company_id and self.company_id.id or False,
            'move_type': self.group_id and self.group_id.move_type or 'direct',
            'partner_id': self.partner_id.id or False,
            'picking_type_id': self.picking_type_id and self.picking_type_id.id or False,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
        }
        return values

    @api.one
    def _picking_assign(self):
        """Try to assign the moves to an existing picking
        that has not been reserved yet and has the same
        procurement group, locations and picking type  (moves should already have them identical)
         Otherwise, create a new picking to assign them to.
        """
        Picking = self.env["stock.picking"]
        pickings = Picking.search([
            ('group_id', '=', self.group_id.id),
            ('location_id', '=', self.location_id.id),
            ('location_dest_id', '=', self.location_dest_id.id),
            ('picking_type_id', '=', self.picking_type_id.id),
            ('printed', '=', False),
            ('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])], limit=1)
        if pickings:
            picking = pickings[0]
        else:
            picking = Picking.create(self._prepare_picking_assign())
        self.write({'picking_id': picking.id})

    def attribute_price(self, cr, uid, move, context=None):
        """
            Attribute price to move, important in inter-company moves or receipts with only one partner
        """
        # TDE note: seems highly suspicious, especially with get_price, ... 
        # Why not Zoidberg and/or a correct function field ?
        if not move.price_unit:
            price = move.product_id.standard_price
            self.write(cr, uid, [move.id], {'price_unit': price})

    @api.multi
    def _push_apply(self):
        # TDE note: internal method for stock.move
        # TDE FIXME: was cr, uid, moves
        push_obj = self.env["stock.location.path"]
        for move in self:
            #1) if the move is already chained, there is no need to check push rules
            #2) if the move is a returned move, we don't want to check push rules, as returning a returned move is the only decent way
            #   to receive goods without triggering the push rules again (which would duplicate chained operations)
            if not move.move_dest_id:
                domain = [('location_from_id', '=', move.location_dest_id.id)]
                #priority goes to the route defined on the product and product category
                route_ids = [x.id for x in move.product_id.route_ids + move.product_id.categ_id.total_route_ids]
                rules = push_obj.search(domain + [('route_id', 'in', route_ids)], order='route_sequence, sequence')
                if not rules:
                    #then we search on the warehouse if a rule can apply
                    wh_route_ids = []
                    if move.warehouse_id:
                        wh_route_ids = [x.id for x in move.warehouse_id.route_ids]
                    elif move.picking_id.picking_type_id.warehouse_id:
                        wh_route_ids = [x.id for x in move.picking_id.picking_type_id.warehouse_id.route_ids]
                    if wh_route_ids:
                        rules = push_obj.search(domain + [('route_id', 'in', wh_route_ids)], order='route_sequence, sequence')
                    if not rules:
                        #if no specialized push rule has been found yet, we try to find a general one (without route)
                        rules = push_obj.search(domain + [('route_id', '=', False)], order='sequence')
                if rules:
                    rule = rules[0]
                    # Make sure it is not returning the return
                    if (not move.origin_returned_move_id or move.origin_returned_move_id.location_id.id != rule.location_dest_id.id):
                        push_obj._apply(rule, move)
        return True

    @api.multi
    def action_confirm(self):
        """ Confirms stock move or put it in waiting if it's linked to another move.
        @return: List of ids.
        """
        states = {
            'confirmed': [],
            'waiting': []
        }
        to_assign = {}
        for move in self:
            self.attribute_price(move)
            state = 'confirmed'
            #if the move is preceeded, then it's waiting (if preceeding move is done, then action_assign has been called already and its state is already available)
            if move.move_orig_ids:
                state = 'waiting'
            #if the move is split and some of the ancestor was preceeded, then it's waiting as well
            elif move.split_from:
                move2 = move.split_from
                while move2 and state != 'waiting':
                    if move2.move_orig_ids:
                        state = 'waiting'
                    move2 = move2.split_from
            states[state].append(move.id)

            if not move.picking_id and move.picking_type_id:
                key = (move.group_id.id, move.location_id.id, move.location_dest_id.id)
                if key not in to_assign:
                    to_assign[key] = []
                to_assign[key].append(move.id)
        moves = self.browse(states['confirmed']).filtered(lambda self: self.procure_method == 'make_to_order')
        # TDE note: move procurement.order.run() from _create_procurements to here
        procurements = moves._create_procurements()
        procurements.run()
        for move in moves:
            states['waiting'].append(move.id)
            states['confirmed'].remove(move.id)

        for state, write_ids in states.items():
            if len(write_ids):
                self.browse(write_ids).write({'state': state})
        #assign picking in batch for all confirmed move that share the same details
        for key, move_ids in to_assign.items():
            self.browse(move_ids)._picking_assign()
        self._push_apply(self)
        return self.ids

    @api.multi
    def force_assign(self):
        res = self.write({'state': 'assigned'})
        self.check_recompute_pack_op()
        return res

    @api.multi
    def check_recompute_pack_op(self, cr, uid, ids, context=None):
        pickings = self.mapped('picking_id')
        pickings_partial = pickings.filtered(lambda self: not any([operation.qty_done > 0 for operation in self.pack_operation_ids]))
        pickings_write = pickings - pickings_partial
        pickings_partial.do_prepare_partial()
        pickings_write.write({'recompute_pack_op': True})

    @api.multi
    def check_tracking(self, ops):
        """ Checks if serial number is assigned to stock move or not and raise an error if it had to.
        """
        # TDE note: override in mrp/stock.py
        # TDE note: same check_tracking on stock_pack_operation
        # TDE note: comment is simple, condition is impossible to understand
        # TDE note: go to real multi
        self.ensure_one()
        # TDE note: what is the meaning of this condition ?
        if self.picking_id and (self.picking_id.picking_type_id.use_existing_lots or self.picking_id.picking_type_id.use_create_lots) and \
            self.product_id.tracking != 'none':
            if not self.restrict_lot_id and not (ops and (ops.product_id and ops.pack_lot_ids)) and not (ops and not ops.product_id):
                raise UserError(_('You need to provide a Lot/Serial Number for product %s') % self.product_id.name)

    @api.multi
    def action_assign(self, no_prepare=False):
        """ Checks the product type and accordingly writes the state.
        """
        # TDE note: seems called by procurement.py and stock_picking.py, not directly through view
        quant_obj = self.pool.get("stock.quant")
        uom_obj = self.pool['product.uom']

        moves_to_assign = self.env['stock.move']

        to_assign_moves = []
        main_domain = {}
        todo_moves = []
        operations = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.state not in ('confirmed', 'waiting', 'assigned'):
                continue
            if move.location_id.usage in ('supplier', 'inventory', 'production'):
                to_assign_moves.append(move.id)
                #in case the move is returned, we want to try to find quants before forcing the assignment
                if not move.origin_returned_move_id:
                    continue
            if move.product_id.type == 'consu':
                to_assign_moves.append(move.id)
                continue
            else:
                todo_moves.append(move)

                #we always keep the quants already assigned and try to find the remaining quantity on quants not assigned only
                main_domain[move.id] = [('reservation_id', '=', False), ('qty', '>', 0)]

                #if the move is preceeded, restrict the choice of quants in the ones moved previously in original move
                ancestors = self.find_move_ancestors(cr, uid, move, context=context)
                if move.state == 'waiting' and not ancestors:
                    #if the waiting move hasn't yet any ancestor (PO/MO not confirmed yet), don't find any quant available in stock
                    main_domain[move.id] += [('id', '=', False)]
                elif ancestors:
                    main_domain[move.id] += [('history_ids', 'in', ancestors)]

                #if the move is returned from another, restrict the choice of quants to the ones that follow the returned move
                if move.origin_returned_move_id:
                    main_domain[move.id] += [('history_ids', 'in', move.origin_returned_move_id.id)]
                for link in move.linked_move_operation_ids:
                    operations.add(link.operation_id)


        # Check all ops and sort them: we want to process first the packages, then operations with lot then the rest
        operations = list(operations)
        operations.sort(key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))
        for ops in operations:
            #first try to find quants based on specific domains given by linked operations for the case where we want to rereserve according to existing pack operations
            if not (ops.product_id and ops.pack_lot_ids):
                for record in ops.linked_move_operation_ids:
                    move = record.move_id
                    if move.id in main_domain:
                        qty = record.qty
                        domain = main_domain[move.id]
                        if qty:
                            quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, ops=ops, domain=domain, preferred_domain_list=[], context=context)
                            quant_obj.quants_reserve(cr, uid, quants, move, record, context=context)
            else:
                lot_qty = {}
                rounding = ops.product_id.uom_id.rounding
                for pack_lot in ops.pack_lot_ids:
                    lot_qty[pack_lot.lot_id.id] = uom_obj._compute_qty(cr, uid, ops.product_uom_id.id, pack_lot.qty, ops.product_id.uom_id.id)
                for record in ops.linked_move_operation_ids:
                    move_qty = record.qty
                    move = record.move_id
                    domain = main_domain[move.id]
                    for lot in lot_qty:
                        if float_compare(lot_qty[lot], 0, precision_rounding=rounding) > 0 and float_compare(move_qty, 0, precision_rounding=rounding) > 0:
                            qty = min(lot_qty[lot], move_qty)
                            quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, ops=ops, lot_id=lot, domain=domain, preferred_domain_list=[], context=context)
                            quant_obj.quants_reserve(cr, uid, quants, move, record, context=context)
                            lot_qty[lot] -= qty
                            move_qty -= qty

        for move in todo_moves:
            if move.linked_move_operation_ids:
                continue
            #then if the move isn't totally assigned, try to find quants without any specific domain
            if move.state != 'assigned':
                qty_already_assigned = move.reserved_availability
                qty = move.product_qty - qty_already_assigned
                quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, domain=main_domain[move.id], preferred_domain_list=[], context=context)
                quant_obj.quants_reserve(cr, uid, quants, move, context=context)

        #force assignation of consumable products and incoming from supplier/inventory/production
        # Do not take force_assign as it would create pack operations
        if to_assign_moves:
            self.write(cr, uid, to_assign_moves, {'state': 'assigned'}, context=context)
        if not no_prepare:
            self.check_recompute_pack_op(cr, uid, ids, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        """ Cancels the moves and if all moves are cancelled it cancels the picking.
        @return: True
        """
        procurement_obj = self.pool.get('procurement.order')
        context = context or {}
        procs_to_check = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.state == 'done':
                raise UserError(_('You cannot cancel a stock move that has been set to \'Done\'.'))
            if move.reserved_quant_ids:
                self.pool.get("stock.quant").quants_unreserve(cr, uid, move, context=context)
            if context.get('cancel_procurement'):
                if move.propagate:
                    procurement_ids = procurement_obj.search(cr, uid, [('move_dest_id', '=', move.id)], context=context)
                    procurement_obj.cancel(cr, uid, procurement_ids, context=context)
            else:
                if move.move_dest_id:
                    if move.propagate:
                        self.action_cancel(cr, uid, [move.move_dest_id.id], context=context)
                    elif move.move_dest_id.state == 'waiting':
                        #If waiting, the chain will be broken and we are not sure if we can still wait for it (=> could take from stock instead)
                        self.write(cr, uid, [move.move_dest_id.id], {'state': 'confirmed'}, context=context)
                if move.procurement_id:
                    # Does the same as procurement check, only eliminating a refresh
                    procs_to_check.append(move.procurement_id.id)

        res = self.write(cr, uid, ids, {'state': 'cancel', 'move_dest_id': False}, context=context)
        if procs_to_check:
            procurement_obj.check(cr, uid, procs_to_check, context=context)
        return res

    def _check_package_from_moves(self, cr, uid, ids, context=None):
        pack_obj = self.pool.get("stock.quant.package")
        packs = set()
        for move in self.browse(cr, uid, ids, context=context):
            packs |= set([q.package_id for q in move.quant_ids if q.package_id and q.qty > 0])
        return pack_obj._check_location_constraint(cr, uid, list(packs), context=context)

    def find_move_ancestors(self, cr, uid, move, context=None):
        '''Find the first level ancestors of given move '''
        # TDE note: the author was probably drunk when writing this method
        ancestors = []
        move2 = move
        while move2:
            ancestors += [x.id for x in move2.move_orig_ids]
            #loop on the split_from to find the ancestor of split moves only if the move has not direct ancestor (priority goes to them)
            move2 = not move2.move_orig_ids and move2.split_from or False
        return ancestors

    @api.cr_uid_ids_context
    def recalculate_move_state(self, cr, uid, move_ids, context=None):
        '''Recompute the state of moves given because their reserved quants were used to fulfill another operation'''
        for move in self.browse(cr, uid, move_ids, context=context):
            vals = {}
            reserved_quant_ids = move.reserved_quant_ids
            if len(reserved_quant_ids) > 0 and not move.partially_available:
                vals['partially_available'] = True
            if len(reserved_quant_ids) == 0 and move.partially_available:
                vals['partially_available'] = False
            if move.state == 'assigned':
                if self.find_move_ancestors(cr, uid, move, context=context):
                    vals['state'] = 'waiting'
                else:
                    vals['state'] = 'confirmed'
            if vals:
                self.write(cr, uid, [move.id], vals, context=context)

    def _move_quants_by_lot(self, cr, uid, ops, lot_qty, quants_taken, false_quants, lot_move_qty, quant_dest_package_id, context=None):
        """
        This function is used to process all the pack operation lots of a pack operation
        For every move:
            First, we check the quants with lot already reserved (and those are already subtracted from the lots to do)
            Then go through all the lots to process:
                Add reserved false lots lot by lot
                Check if there are not reserved quants or reserved elsewhere with that lot or without lot (with the traditional method)
        """
        quant_obj = self.pool['stock.quant']
        fallback_domain = [('reservation_id', '=', False)]
        fallback_domain2 = ['&', ('reservation_id', 'not in', [x for x in lot_move_qty.keys()]), ('reservation_id', '!=', False)]
        preferred_domain_list = [fallback_domain] + [fallback_domain2]
        rounding = ops.product_id.uom_id.rounding
        for move in lot_move_qty:
            move_quants_dict = {}
            move_rec = self.pool['stock.move'].browse(cr, uid, move, context=context)
            # Assign quants already reserved with lot to the correct
            for quant in quants_taken:
                move_quants_dict.setdefault(quant[0].lot_id.id, [])
                move_quants_dict[quant[0].lot_id.id] += [quant]
            false_quants_move = [x for x in false_quants if x[0].reservation_id.id == move]
            for lot in lot_qty:
                move_quants_dict.setdefault(lot, [])
                redo_false_quants = False
                # Take remaining reserved quants with  no lot first
                # (This will be used mainly when incoming had no lot and you do outgoing with)
                while false_quants_move and float_compare(lot_qty[lot], 0, precision_rounding=rounding) > 0 and float_compare(lot_move_qty[move], 0, precision_rounding=rounding) > 0:
                    qty_min = min(lot_qty[lot], lot_move_qty[move])
                    if false_quants_move[0].qty > qty_min:
                        move_quants_dict[lot] += [(false_quants_move[0], qty_min)]
                        qty = qty_min
                        redo_false_quants = True
                    else:
                        qty = false_quants_move[0].qty
                        move_quants_dict[lot] += [(false_quants_move[0], qty)]
                        false_quants_move.pop(0)
                    lot_qty[lot] -= qty
                    lot_move_qty[move] -= qty

                # Search other with first matching lots and then without lots
                if float_compare(lot_move_qty[move], 0, precision_rounding=rounding) > 0 and float_compare(lot_qty[lot], 0, precision_rounding=rounding) > 0:
                    # Search if we can find quants with that lot
                    domain = [('qty', '>', 0)]
                    qty = min(lot_qty[lot], lot_move_qty[move])
                    quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move_rec, ops=ops, lot_id=lot, domain=domain,
                                                        preferred_domain_list=preferred_domain_list, context=context)
                    move_quants_dict[lot] += quants
                    lot_qty[lot] -= qty
                    lot_move_qty[move] -= qty

                #Move all the quants related to that lot/move
                if move_quants_dict[lot]:
                    quant_obj.quants_move(cr, uid, move_quants_dict[lot], move_rec, ops.location_dest_id, location_from=ops.location_id,
                                                    lot_id=lot, owner_id=ops.owner_id.id, src_package_id=ops.package_id.id,
                                                    dest_package_id=quant_dest_package_id, context=context)
                    if redo_false_quants:
                        move_rec = self.pool['stock.move'].browse(cr, uid, move, context=context)
                        false_quants_move = [(x, x.qty) for x in move_rec.reserved_quant_ids if not x.lot_id]

    def action_done(self, cr, uid, ids, context=None):
        """ Process completely the moves given as ids and if all moves are done, it will finish the picking.
        """
        context = context or {}
        picking_obj = self.pool.get("stock.picking")
        quant_obj = self.pool.get("stock.quant")
        uom_obj = self.pool.get("product.uom")
        todo = [move.id for move in self.browse(cr, uid, ids, context=context) if move.state == "draft"]
        if todo:
            ids = self.action_confirm(cr, uid, todo, context=context)
        pickings = set()
        procurement_ids = set()
        #Search operations that are linked to the moves
        operations = set()
        move_qty = {}
        for move in self.browse(cr, uid, ids, context=context):
            move_qty[move.id] = move.product_qty
            for link in move.linked_move_operation_ids:
                operations.add(link.operation_id)

        #Sort operations according to entire packages first, then package + lot, package only, lot only
        operations = list(operations)
        operations.sort(key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))

        for ops in operations:
            if ops.picking_id:
                pickings.add(ops.picking_id.id)
            entire_pack=False
            if ops.product_id:
                #If a product is given, the result is always put immediately in the result package (if it is False, they are without package)
                quant_dest_package_id  = ops.result_package_id.id
            else:
                # When a pack is moved entirely, the quants should not be written anything for the destination package
                quant_dest_package_id = False
                entire_pack=True
            lot_qty = {}
            tot_qty = 0.0
            for pack_lot in ops.pack_lot_ids:
                qty = uom_obj._compute_qty(cr, uid, ops.product_uom_id.id, pack_lot.qty, ops.product_id.uom_id.id)
                lot_qty[pack_lot.lot_id.id] = qty
                tot_qty += pack_lot.qty
            if ops.pack_lot_ids and ops.product_id and float_compare(tot_qty, ops.product_qty, precision_rounding=ops.product_uom_id.rounding) != 0.0:
                raise UserError(_('You have a difference between the quantity on the operation and the quantities specified for the lots. '))

            quants_taken = []
            false_quants = []
            lot_move_qty = {}
            #Group links by move first
            move_qty_ops = {}
            for record in ops.linked_move_operation_ids:
                move = record.move_id
                if not move_qty_ops.get(move):
                    move_qty_ops[move] = record.qty
                else:
                    move_qty_ops[move] += record.qty
            #Process every move only once for every pack operation
            for move in move_qty_ops:
                main_domain = [('qty', '>', 0)]
                move.check_tracking(ops)
                preferred_domain = [('reservation_id', '=', move.id)]
                fallback_domain = [('reservation_id', '=', False)]
                fallback_domain2 = ['&', ('reservation_id', '!=', move.id), ('reservation_id', '!=', False)]
                if not ops.pack_lot_ids:
                    preferred_domain_list = [preferred_domain] + [fallback_domain] + [fallback_domain2]
                    quants = quant_obj.quants_get_preferred_domain(cr, uid, move_qty_ops[move], move, ops=ops, domain=main_domain,
                                                        preferred_domain_list=preferred_domain_list, context=context)
                    quant_obj.quants_move(cr, uid, quants, move, ops.location_dest_id, location_from=ops.location_id,
                                          lot_id=False, owner_id=ops.owner_id.id, src_package_id=ops.package_id.id,
                                          dest_package_id=quant_dest_package_id, entire_pack=entire_pack, context=context)
                else:
                    # Check what you can do with reserved quants already
                    qty_on_link = move_qty_ops[move]
                    rounding = ops.product_id.uom_id.rounding
                    for reserved_quant in move.reserved_quant_ids:
                        if not reserved_quant.lot_id:
                            false_quants += [reserved_quant]
                        elif float_compare(lot_qty.get(reserved_quant.lot_id.id, 0), 0, precision_rounding=rounding) > 0:
                            if float_compare(lot_qty[reserved_quant.lot_id.id], reserved_quant.qty, precision_rounding=rounding) >= 0:
                                lot_qty[reserved_quant.lot_id.id] -= reserved_quant.qty
                                quants_taken += [(reserved_quant, reserved_quant.qty)]
                                qty_on_link -= reserved_quant.qty
                            else:
                                quants_taken += [(reserved_quant, lot_qty[reserved_quant.lot_id.id])]
                                lot_qty[reserved_quant.lot_id.id] = 0
                                qty_on_link -= lot_qty[reserved_quant.lot_id.id]
                    lot_move_qty[move.id] = qty_on_link

                if not move_qty.get(move.id):
                    raise UserError(_("The roundings of your Unit of Measures %s on the move vs. %s on the product don't allow to do these operations or you are not transferring the picking at once. ") % (move.product_uom.name, move.product_id.uom_id.name))
                move_qty[move.id] -= move_qty_ops[move]

            #Handle lots separately
            if ops.pack_lot_ids:
                self._move_quants_by_lot(cr, uid, ops, lot_qty, quants_taken, false_quants, lot_move_qty, quant_dest_package_id, context=context)

            # Handle pack in pack
            if not ops.product_id and ops.package_id and ops.result_package_id.id != ops.package_id.parent_id.id:
                self.pool.get('stock.quant.package').write(cr, SUPERUSER_ID, [ops.package_id.id], {'parent_id': ops.result_package_id.id}, context=context)
        #Check for remaining qtys and unreserve/check move_dest_id in
        move_dest_ids = set()
        for move in self.browse(cr, uid, ids, context=context):
            move_qty_cmp = float_compare(move_qty[move.id], 0, precision_rounding=move.product_id.uom_id.rounding)
            if move_qty_cmp > 0:  # (=In case no pack operations in picking)
                main_domain = [('qty', '>', 0)]
                preferred_domain = [('reservation_id', '=', move.id)]
                fallback_domain = [('reservation_id', '=', False)]
                fallback_domain2 = ['&', ('reservation_id', '!=', move.id), ('reservation_id', '!=', False)]
                preferred_domain_list = [preferred_domain] + [fallback_domain] + [fallback_domain2]
                move.check_tracking(False)
                qty = move_qty[move.id]
                quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, domain=main_domain, preferred_domain_list=preferred_domain_list, context=context)
                quant_obj.quants_move(cr, uid, quants, move, move.location_dest_id, lot_id=move.restrict_lot_id.id, owner_id=move.restrict_partner_id.id, context=context)

            # If the move has a destination, add it to the list to reserve
            if move.move_dest_id and move.move_dest_id.state in ('waiting', 'confirmed'):
                move_dest_ids.add(move.move_dest_id.id)

            if move.procurement_id:
                procurement_ids.add(move.procurement_id.id)

            #unreserve the quants and make them available for other operations/moves
            quant_obj.quants_unreserve(cr, uid, move, context=context)
        # Check the packages have been placed in the correct locations
        self._check_package_from_moves(cr, uid, ids, context=context)
        #set the move as done
        self.write(cr, uid, ids, {'state': 'done', 'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
        self.pool.get('procurement.order').check(cr, uid, list(procurement_ids), context=context)
        #assign destination moves
        if move_dest_ids:
            self.action_assign(cr, uid, list(move_dest_ids), context=context)
        #check picking state to set the date_done is needed
        done_picking = []
        for picking in picking_obj.browse(cr, uid, list(pickings), context=context):
            if picking.state == 'done' and not picking.date_done:
                done_picking.append(picking.id)
        if done_picking:
            picking_obj.write(cr, uid, done_picking, {'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
        return True

    def action_scrap(self, cr, uid, ids, quantity, location_id, restrict_lot_id=False, restrict_partner_id=False, context=None):
        """ Move the scrap/damaged product into scrap location
        @param cr: the database cursor
        @param uid: the user id
        @param ids: ids of stock move object to be scrapped
        @param quantity : specify scrap qty
        @param location_id : specify scrap location
        @param context: context arguments
        @return: Scraped lines
        """
        quant_obj = self.pool.get("stock.quant")
        #quantity should be given in MOVE UOM
        if quantity <= 0:
            raise UserError(_('Please provide a positive quantity to scrap.'))
        res = []
        for move in self.browse(cr, uid, ids, context=context):
            source_location = move.location_id
            if move.state == 'done':
                source_location = move.location_dest_id
            #Previously used to prevent scraping from virtual location but not necessary anymore
            #if source_location.usage != 'internal':
                #restrict to scrap from a virtual location because it's meaningless and it may introduce errors in stock ('creating' new products from nowhere)
                #raise UserError(_('Forbidden operation: it is not allowed to scrap products from a virtual location.'))
            move_qty = move.product_qty
            default_val = {
                'location_id': source_location.id,
                'product_uom_qty': quantity,
                'state': move.state,
                'scrapped': True,
                'location_dest_id': location_id,
                'restrict_lot_id': restrict_lot_id,
                'restrict_partner_id': restrict_partner_id,
            }
            new_move = self.copy(cr, uid, move.id, default_val)

            res += [new_move]
            product_obj = self.pool.get('product.product')
            for product in product_obj.browse(cr, uid, [move.product_id.id], context=context):
                if move.picking_id:
                    uom = product.uom_id.name if product.uom_id else ''
                    message = _("%s %s %s has been <b>moved to</b> scrap.") % (quantity, uom, product.name)
                    move.picking_id.message_post(body=message)

            # We "flag" the quant from which we want to scrap the products. To do so:
            #    - we select the quants related to the move we scrap from
            #    - we reserve the quants with the scrapped move
            # See self.action_done, et particularly how is defined the "preferred_domain" for clarification
            scrap_move = self.browse(cr, uid, new_move, context=context)
            if move.state == 'done' and scrap_move.location_id.usage not in ('supplier', 'inventory', 'production'):
                domain = [('qty', '>', 0), ('history_ids', 'in', [move.id])]
                # We use scrap_move data since a reservation makes sense for a move not already done
                quants = quant_obj.quants_get_preferred_domain(cr, uid, scrap_move.location_id,
                        scrap_move.product_id, quantity, domain=domain, preferred_domain_list=[],
                        restrict_lot_id=scrap_move.restrict_lot_id.id, restrict_partner_id=scrap_move.restrict_partner_id.id, context=context)
                quant_obj.quants_reserve(cr, uid, quants, scrap_move, context=context)
        self.action_done(cr, uid, res, context=context)
        return res

    def split(self, cr, uid, move, qty, restrict_lot_id=False, restrict_partner_id=False, context=None):
        # TDE note: called from where ??
        return move.split_new_api(qty, restrict_lot_id=restrict_lot_id, restrict_partner_id=restrict_partner_id)

    def split_new_api(self, qty, restrict_lot_id=False, restrict_partner_id=False):
        """ Splits qty from move move into a new move
        :param move: browse record
        :param qty: float. quantity to split (given in product UoM)
        :param restrict_lot_id: optional production lot that can be given in order to force the new move to restrict its choice of quants to this lot.
        :param restrict_partner_id: optional partner that can be given in order to force the new move to restrict its choice of quants to the ones belonging to this partner.
        :param context: dictionay. can contains the special key 'source_location_id' in order to force the source location when copying the move

        returns the ID of the backorder move created
        """
        self.ensure_one()
        if self.state in ('done', 'cancel'):
            raise UserError(_('You cannot split a move done'))
        if self.state == 'draft':
            # we restrict the split of a draft move because if not confirmed yet, it may be replaced by several other moves in
            # case of phantom bom (with mrp module). And we don't want to deal with this complexity by copying the product that will explode.
            raise UserError(_('You cannot split a draft move. It needs to be confirmed first.'))

        if self.product_qty <= qty or qty == 0:
            return self.id

        # HALF-UP rounding as only rounding errors will be because of propagation of error from default UoM
        uom_qty = self.env['product.uom']._compute_qty_obj(self.product_id.uom_id, qty, self.product_uom, rounding_method='HALF-UP')
        defaults = {
            'product_uom_qty': uom_qty,
            'procure_method': 'make_to_stock',
            'restrict_lot_id': restrict_lot_id,
            'restrict_partner_id': restrict_partner_id,
            'split_from': self.id,
            'procurement_id': self.procurement_id.id,
            'move_dest_id': self.move_dest_id.id,
            'origin_returned_move_id': self.origin_returned_move_id.id,
        }
        if restrict_partner_id:
            defaults['restrict_partner_id'] = restrict_partner_id
        if self._context.get('source_location_id'):
            defaults['location_id'] = self._context['source_location_id']
        new_move = self.copy(defaults)
        self.with_context(do_not_propagate=True).write({'product_uom_qty': self.product_uom_qty - uom_qty})

        if self.move_dest_id and self.propagate and self.move_dest_id.state not in ('done', 'cancel'):
            new_move_prop = self.move_dest_id.split(qty)
            new_move.write({'move_dest_id': new_move_prop})
        # returning the first element of list returned by action_confirm is ok because we checked it wouldn't be exploded (and
        # thus the result of action_confirm should always be a list of 1 element length)
        # TDE note: whaaat ?
        return new_move.action_confirm()[0]

    def get_code_from_locs(self, cr, uid, move, location_id=False, location_dest_id=False, context=None):
        """
        Returns the code the picking type should have.  This can easily be used
        to check if a move is internal or not
        move, location_id and location_dest_id are browse records
        """
        # TDE note: this code seems unnecesary and creates unnecessary calls
        # used only in mrp/mrp.py
        code = 'internal'
        src_loc = location_id or move.location_id
        dest_loc = location_dest_id or move.location_dest_id
        if src_loc.usage == 'internal' and dest_loc.usage != 'internal':
            code = 'outgoing'
        if src_loc.usage != 'internal' and dest_loc.usage == 'internal':
            code = 'incoming'
        return code

    @api.multi
    def show_picking(self):
        if self.picking_id:
            view_id = self.env['ir.model.data'].xmlid_to_res_id('stock.view_picking_form')
            return {
                'name': _('Transfer'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'views': [(view_id, 'form')],
                'view_id': view_id,
                'target': 'new',
                'res_id': self.picking_id.id,
            }
