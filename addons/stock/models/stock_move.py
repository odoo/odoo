# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from collections import defaultdict
from datetime import timedelta
from operator import itemgetter

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import clean_context, OrderedSet, groupby

PROCUREMENT_PRIORITIES = [('0', 'Normal'), ('1', 'Urgent')]


class StockMove(models.Model):
    _name = "stock.move"
    _description = "Stock Move"
    _order = 'sequence, id'

    def _default_group_id(self):
        if self.env.context.get('default_picking_id'):
            return self.env['stock.picking'].browse(self.env.context['default_picking_id']).group_id.id
        return False

    name = fields.Char('Description', required=True)
    sequence = fields.Integer('Sequence', default=10)
    priority = fields.Selection(
        PROCUREMENT_PRIORITIES, 'Priority', default='0',
        compute="_compute_priority", store=True)
    date = fields.Datetime(
        'Date Scheduled', default=fields.Datetime.now, index=True, required=True,
        help="Scheduled date until move is done, then date of actual move processing")
    date_deadline = fields.Datetime(
        "Deadline", readonly=True, copy=False,
        help="Date Promise to the customer on the top level document (SO/PO)")
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company,
        index=True, required=True)
    product_id = fields.Many2one(
        'product.product', 'Product',
        check_company=True,
        domain="[('type', 'in', ['product', 'consu']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", index=True, required=True,
        states={'done': [('readonly', True)]})
    description_picking = fields.Text('Description of Picking')
    product_qty = fields.Float(
        'Real Quantity', compute='_compute_product_qty', inverse='_set_product_qty',
        digits=0, store=True, compute_sudo=True,
        help='Quantity in the default UoM of the product')
    product_uom_qty = fields.Float(
        'Demand',
        digits='Product Unit of Measure',
        default=1.0, required=True, states={'done': [('readonly', True)]},
        help="This is the quantity of products from an inventory "
             "point of view. For moves in the state 'done', this is the "
             "quantity of products that were actually moved. For other "
             "moves, this is the quantity of product that is planned to "
             "be moved. Lowering this quantity does not generate a "
             "backorder. Changing this quantity on assigned moves affects "
             "the product reservation, and should be done with care.")
    product_uom = fields.Many2one(
        'uom.uom', "UoM", required=True, domain="[('category_id', '=', product_uom_category_id)]",
        compute="_compute_product_uom", store=True, readonly=False, precompute=True,
    )
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    # TDE FIXME: make it stored, otherwise group will not work
    product_tmpl_id = fields.Many2one(
        'product.template', 'Product Template',
        related='product_id.product_tmpl_id')
    location_id = fields.Many2one(
        'stock.location', 'Source Location',
        auto_join=True, index=True, required=True,
        check_company=True,
        help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations.")
    location_dest_id = fields.Many2one(
        'stock.location', 'Destination Location',
        auto_join=True, index=True, required=True,
        check_company=True,
        help="Location where the system will stock the finished products.")
    location_usage = fields.Selection(string="Source Location Type", related='location_id.usage')
    location_dest_usage = fields.Selection(string="Destination Location Type", related='location_dest_id.usage')
    partner_id = fields.Many2one(
        'res.partner', 'Destination Address ',
        states={'done': [('readonly', True)]},
        help="Optional address where goods are to be delivered, specifically used for allotment")
    move_dest_ids = fields.Many2many(
        'stock.move', 'stock_move_move_rel', 'move_orig_id', 'move_dest_id', 'Destination Moves',
        copy=False,
        help="Optional: next stock move when chaining them")
    move_orig_ids = fields.Many2many(
        'stock.move', 'stock_move_move_rel', 'move_dest_id', 'move_orig_id', 'Original Move',
        copy=False,
        help="Optional: previous stock move when chaining them")
    picking_id = fields.Many2one('stock.picking', 'Transfer', index=True, states={'done': [('readonly', True)]}, check_company=True)
    state = fields.Selection([
        ('draft', 'New'), ('cancel', 'Cancelled'),
        ('waiting', 'Waiting Another Move'),
        ('confirmed', 'Waiting Availability'),
        ('partially_available', 'Partially Available'),
        ('assigned', 'Available'),
        ('done', 'Done')], string='Status',
        copy=False, default='draft', index=True, readonly=True,
        help="* New: When the stock move is created and not yet confirmed.\n"
             "* Waiting Another Move: This state can be seen when a move is waiting for another one, for example in a chained flow.\n"
             "* Waiting Availability: This state is reached when the procurement resolution is not straight forward. It may need the scheduler to run, a component to be manufactured...\n"
             "* Available: When products are reserved, it is set to \'Available\'.\n"
             "* Done: When the shipment is processed, the state is \'Done\'.")

    # used to record the product cost set by the user during a picking confirmation (when costing
    # method used is 'average price' or 'real'). Value given in company currency and in product uom.
    # as it's a technical field, we intentionally don't provide the digits attribute
    price_unit = fields.Float('Unit Price', copy=False)
    origin = fields.Char("Source Document")
    procure_method = fields.Selection([
        ('make_to_stock', 'Default: Take From Stock'),
        ('make_to_order', 'Advanced: Apply Procurement Rules')], string='Supply Method',
        default='make_to_stock', required=True, copy=False,
        help="By default, the system will take from the stock in the source location and passively wait for availability. "
             "The other possibility allows you to directly create a procurement on the source location (and thus ignore "
             "its current stock) to gather products. If we want to chain moves and have this one to wait for the previous, "
             "this second option should be chosen.")
    scrapped = fields.Boolean(
        'Scrapped', related='location_dest_id.scrap_location', readonly=True, store=True)
    scrap_ids = fields.One2many('stock.scrap', 'move_id')
    group_id = fields.Many2one('procurement.group', 'Procurement Group', default=_default_group_id)
    rule_id = fields.Many2one(
        'stock.rule', 'Stock Rule', ondelete='restrict', help='The stock rule that created this stock move',
        check_company=True)
    propagate_cancel = fields.Boolean(
        'Propagate cancel and split', default=True,
        help='If checked, when this move is cancelled, cancel the linked move too')
    delay_alert_date = fields.Datetime('Delay Alert Date', help='Process at this date to be on time', compute="_compute_delay_alert_date", store=True)
    picking_type_id = fields.Many2one('stock.picking.type', 'Operation Type', compute='_compute_picking_type_id', store=True, check_company=True)
    is_inventory = fields.Boolean('Inventory')
    move_line_ids = fields.One2many('stock.move.line', 'move_id')
    move_line_nosuggest_ids = fields.One2many('stock.move.line', 'move_id', domain=['|', ('reserved_qty', '=', 0.0), ('qty_done', '!=', 0.0)])
    origin_returned_move_id = fields.Many2one(
        'stock.move', 'Origin return move', copy=False, index=True,
        help='Move that created the return move', check_company=True)
    returned_move_ids = fields.One2many('stock.move', 'origin_returned_move_id', 'All returned moves', help='Optional: all returned moves created from this move')
    reserved_availability = fields.Float(
        'Quantity Reserved', compute='_compute_reserved_availability',
        digits='Product Unit of Measure',
        readonly=True, help='Quantity that has already been reserved for this move')
    availability = fields.Float(
        'Forecasted Quantity', compute='_compute_product_availability',
        readonly=True, help='Quantity in stock that can still be reserved for this move')
    # used to depict a restriction on the ownership of quants to consider when marking this move as 'done'
    restrict_partner_id = fields.Many2one(
        'res.partner', 'Owner ', check_company=True)
    route_ids = fields.Many2many(
        'stock.route', 'stock_route_move', 'move_id', 'route_id', 'Destination route', help="Preferred route",
        check_company=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', help="the warehouse to consider for the route selection on the next procurement (if any).")
    has_tracking = fields.Selection(related='product_id.tracking', string='Product with Tracking')
    quantity_done = fields.Float('Quantity Done', compute='_quantity_done_compute', digits='Product Unit of Measure', inverse='_quantity_done_set')
    show_operations = fields.Boolean(related='picking_id.picking_type_id.show_operations')
    picking_code = fields.Selection(related='picking_id.picking_type_id.code', readonly=True)
    show_details_visible = fields.Boolean('Details Visible', compute='_compute_show_details_visible')
    show_reserved_availability = fields.Boolean('From Supplier', compute='_compute_show_reserved_availability')
    product_type = fields.Selection(related='product_id.detailed_type', readonly=True)
    additional = fields.Boolean("Whether the move was added after the picking's confirmation", default=False)
    is_locked = fields.Boolean(compute='_compute_is_locked', readonly=True)
    is_initial_demand_editable = fields.Boolean('Is initial demand editable', compute='_compute_is_initial_demand_editable')
    is_quantity_done_editable = fields.Boolean('Is quantity done editable', compute='_compute_is_quantity_done_editable')
    reference = fields.Char(compute='_compute_reference', string="Reference", store=True)
    move_lines_count = fields.Integer(compute='_compute_move_lines_count')
    package_level_id = fields.Many2one('stock.package_level', 'Package Level', check_company=True, copy=False)
    picking_type_entire_packs = fields.Boolean(related='picking_type_id.show_entire_packs', readonly=True)
    display_assign_serial = fields.Boolean(compute='_compute_display_assign_serial')
    display_clear_serial = fields.Boolean(compute='_compute_display_clear_serial')
    next_serial = fields.Char('First SN')
    next_serial_count = fields.Integer('Number of SN')
    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint', 'Original Reordering Rule', check_company=True, index=True)
    forecast_availability = fields.Float('Forecast Availability', compute='_compute_forecast_information', digits='Product Unit of Measure', compute_sudo=True)
    forecast_expected_date = fields.Datetime('Forecasted Expected date', compute='_compute_forecast_information', compute_sudo=True)
    lot_ids = fields.Many2many('stock.lot', compute='_compute_lot_ids', inverse='_set_lot_ids', string='Serial Numbers', readonly=False)
    reservation_date = fields.Date('Date to Reserve', compute='_compute_reservation_date', store=True,
        help="Computes when a move should be reserved")
    product_packaging_id = fields.Many2one('product.packaging', 'Packaging', domain="[('product_id', '=', product_id)]", check_company=True)
    from_immediate_transfer = fields.Boolean(related="picking_id.immediate_transfer")

    @api.depends('product_id')
    def _compute_product_uom(self):
        for move in self:
            if not move.product_uom:
                move.product_uom = move.product_id.uom_id.id


    @api.depends('has_tracking', 'picking_type_id.use_create_lots', 'picking_type_id.use_existing_lots', 'state')
    def _compute_display_assign_serial(self):
        for move in self:
            move.display_assign_serial = (
                move.has_tracking == 'serial' and
                move.state in ('partially_available', 'assigned', 'confirmed') and
                move.picking_type_id.use_create_lots and
                not move.picking_type_id.use_existing_lots
                and not move.origin_returned_move_id.id
            )

    @api.depends('display_assign_serial', 'move_line_ids', 'move_line_nosuggest_ids')
    def _compute_display_clear_serial(self):
        self.display_clear_serial = False
        for move in self:
            move.display_clear_serial = move.display_assign_serial and move._get_move_lines()

    @api.depends('picking_id.priority')
    def _compute_priority(self):
        for move in self:
            move.priority = move.picking_id.priority or '0'

    @api.depends('picking_id.picking_type_id')
    def _compute_picking_type_id(self):
        for move in self:
            if move.picking_id:
                move.picking_type_id = move.picking_id.picking_type_id

    @api.depends('picking_id.is_locked')
    def _compute_is_locked(self):
        for move in self:
            if move.picking_id:
                move.is_locked = move.picking_id.is_locked
            else:
                move.is_locked = False

    @api.depends('product_id', 'has_tracking', 'move_line_ids')
    def _compute_show_details_visible(self):
        """ According to this field, the button that calls `action_show_details` will be displayed
        to work on a move from its picking form view, or not.
        """
        has_package = self.user_has_groups('stock.group_tracking_lot')
        multi_locations_enabled = self.user_has_groups('stock.group_stock_multi_locations')
        consignment_enabled = self.user_has_groups('stock.group_tracking_owner')

        show_details_visible = multi_locations_enabled or has_package

        for move in self:
            if not move.product_id:
                move.show_details_visible = False
            elif len(move._get_move_lines()) > 1:
                move.show_details_visible = True
            else:
                move.show_details_visible = (((consignment_enabled and move.picking_code != 'incoming') or
                                             show_details_visible or move.has_tracking != 'none') and
                                             move._show_details_in_draft() and
                                             move.show_operations is False)

    def _compute_show_reserved_availability(self):
        """ This field is only of use in an attrs in the picking view, in order to hide the
        "available" column if the move is coming from a supplier.
        """
        for move in self:
            move.show_reserved_availability = not move.location_id.usage == 'supplier'

    @api.depends('state', 'picking_id')
    def _compute_is_initial_demand_editable(self):
        for move in self:
            if not move.picking_id.immediate_transfer and move.state == 'draft':
                move.is_initial_demand_editable = True
            elif not move.picking_id.is_locked and move.state != 'done' and move.picking_id:
                move.is_initial_demand_editable = True
            else:
                move.is_initial_demand_editable = False

    @api.depends('state', 'picking_id', 'product_id')
    def _compute_is_quantity_done_editable(self):
        for move in self:
            if not move.product_id:
                move.is_quantity_done_editable = False
            elif not move.picking_id.immediate_transfer and move.picking_id.state == 'draft':
                move.is_quantity_done_editable = False
            elif move.picking_id.is_locked and move.state in ('done', 'cancel'):
                move.is_quantity_done_editable = False
            elif move.show_details_visible:
                move.is_quantity_done_editable = False
            elif move.show_operations:
                move.is_quantity_done_editable = False
            else:
                move.is_quantity_done_editable = True

    @api.depends('picking_id', 'name')
    def _compute_reference(self):
        for move in self:
            move.reference = move.picking_id.name if move.picking_id else move.name

    @api.depends('move_line_ids')
    def _compute_move_lines_count(self):
        for move in self:
            move.move_lines_count = len(move.move_line_ids)

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_product_qty(self):
        for move in self:
            move.product_qty = move.product_uom._compute_quantity(
                move.product_uom_qty, move.product_id.uom_id, rounding_method='HALF-UP')

    def _get_move_lines(self):
        """ This will return the move lines to consider when applying _quantity_done_compute on a stock.move.
        In some context, such as MRP, it is necessary to compute quantity_done on filtered sock.move.line."""
        self.ensure_one()
        if self.picking_type_id.show_reserved is False:
            return self.move_line_nosuggest_ids
        return self.move_line_ids

    @api.depends('move_orig_ids.date', 'move_orig_ids.state', 'state', 'date')
    def _compute_delay_alert_date(self):
        for move in self:
            if move.state in ('done', 'cancel'):
                move.delay_alert_date = False
                continue
            prev_moves = move.move_orig_ids.filtered(lambda m: m.state not in ('done', 'cancel') and m.date)
            prev_max_date = max(prev_moves.mapped("date"), default=False)
            if prev_max_date and prev_max_date > move.date:
                move.delay_alert_date = prev_max_date
            else:
                move.delay_alert_date = False

    @api.depends('move_line_ids.qty_done', 'move_line_ids.product_uom_id', 'move_line_nosuggest_ids.qty_done', 'picking_type_id.show_reserved')
    def _quantity_done_compute(self):
        """ This field represents the sum of the move lines `qty_done`. It allows the user to know
        if there is still work to do.

        We take care of rounding this value at the general decimal precision and not the rounding
        of the move's UOM to make sure this value is really close to the real sum, because this
        field will be used in `_action_done` in order to know if the move will need a backorder or
        an extra move.
        """
        if not any(self._ids):
            # onchange
            for move in self:
                quantity_done = 0
                for move_line in move._get_move_lines():
                    quantity_done += move_line.product_uom_id._compute_quantity(
                        move_line.qty_done, move.product_uom, round=False)
                move.quantity_done = quantity_done
        else:
            # compute
            move_lines_ids = set()
            for move in self:
                move_lines_ids |= set(move._get_move_lines().ids)

            data = self.env['stock.move.line']._read_group(
                [('id', 'in', list(move_lines_ids))],
                ['move_id', 'product_uom_id', 'qty_done'], ['move_id', 'product_uom_id'],
                lazy=False
            )

            rec = defaultdict(list)
            for d in data:
                rec[d['move_id'][0]] += [(d['product_uom_id'][0], d['qty_done'])]

            for move in self:
                uom = move.product_uom
                move.quantity_done = sum(
                    self.env['uom.uom'].browse(line_uom_id)._compute_quantity(qty, uom, round=False)
                     for line_uom_id, qty in rec.get(move.ids[0] if move.ids else move.id, [])
                )

    def _quantity_done_set(self):
        quantity_done = self[0].quantity_done  # any call to create will invalidate `move.quantity_done`
        for move in self:
            move_lines = move._get_move_lines()
            if not move_lines:
                if quantity_done:
                    # do not impact reservation here
                    move_line = self.env['stock.move.line'].create(dict(move._prepare_move_line_vals(), qty_done=quantity_done))
                    move.write({'move_line_ids': [(4, move_line.id)]})
                    move_line._apply_putaway_strategy()
            elif len(move_lines) == 1:
                move_lines[0].qty_done = quantity_done
            else:
                move._multi_line_quantity_done_set(quantity_done)

    def _multi_line_quantity_done_set(self, quantity_done):
        move_lines = self._get_move_lines()
        # Bypass the error if we're trying to write the same value.
        ml_quantity_done = 0
        for move_line in move_lines:
            ml_quantity_done += move_line.product_uom_id._compute_quantity(move_line.qty_done, self.product_uom, round=False)
        if float_compare(quantity_done, ml_quantity_done, precision_rounding=self.product_uom.rounding) != 0:
            raise UserError(_("Cannot set the done quantity from this stock move, work directly with the move lines."))

    def _set_product_qty(self):
        """ The meaning of product_qty field changed lately and is now a functional field computing the quantity
        in the default product UoM. This code has been added to raise an error if a write is made given a value
        for `product_qty`, where the same write should set the `product_uom_qty` field instead, in order to
        detect errors. """
        raise UserError(_('The requested operation cannot be processed because of a programming error setting the `product_qty` field instead of the `product_uom_qty`.'))

    @api.depends('move_line_ids.reserved_qty')
    def _compute_reserved_availability(self):
        """ Fill the `availability` field on a stock move, which is the actual reserved quantity
        and is represented by the aggregated `product_qty` on the linked move lines. If the move
        is force assigned, the value will be 0.
        """
        if not any(self._ids):
            # onchange
            for move in self:
                reserved_availability = sum(move.move_line_ids.mapped('reserved_qty'))
                move.reserved_availability = move.product_id.uom_id._compute_quantity(
                    reserved_availability, move.product_uom, rounding_method='HALF-UP')
        else:
            # compute
            result = {data['move_id'][0]: data['reserved_qty'] for data in
                      self.env['stock.move.line']._read_group([('move_id', 'in', self.ids)], ['move_id', 'reserved_qty'], ['move_id'])}
            for move in self:
                move.reserved_availability = move.product_id.uom_id._compute_quantity(
                    result.get(move.id, 0.0), move.product_uom, rounding_method='HALF-UP')

    @api.depends('state', 'product_id', 'product_qty', 'location_id')
    def _compute_product_availability(self):
        """ Fill the `availability` field on a stock move, which is the quantity to potentially
        reserve. When the move is done, `availability` is set to the quantity the move did actually
        move.
        """
        for move in self:
            if move.state == 'done':
                move.availability = move.product_qty
            else:
                total_availability = self.env['stock.quant']._get_available_quantity(move.product_id, move.location_id) if move.product_id else 0.0
                move.availability = min(move.product_qty, total_availability)

    @api.depends('product_id', 'product_qty', 'picking_type_id', 'reserved_availability', 'priority', 'state', 'product_uom_qty', 'location_id')
    def _compute_forecast_information(self):
        """ Compute forecasted information of the related product by warehouse."""
        self.forecast_availability = False
        self.forecast_expected_date = False

        # Prefetch product info to avoid fetching all product fields
        self.product_id.read(['type', 'uom_id'], load=False)

        not_product_moves = self.filtered(lambda move: move.product_id.type != 'product')
        for move in not_product_moves:
            move.forecast_availability = move.product_qty

        product_moves = (self - not_product_moves)

        outgoing_unreserved_moves_per_warehouse = defaultdict(set)
        now = fields.Datetime.now()

        def key_virtual_available(move, incoming=False):
            warehouse_id = move.location_dest_id.warehouse_id.id if incoming else move.location_id.warehouse_id.id
            return warehouse_id, max(move.date, now)

        # Prefetch efficiently virtual_available for _is_consuming draft move.
        prefetch_virtual_available = defaultdict(set)
        virtual_available_dict = {}
        for move in product_moves:
            if move._is_consuming() and move.state == 'draft':
                prefetch_virtual_available[key_virtual_available(move)].add(move.product_id.id)
            elif move.picking_type_id.code == 'incoming':
                prefetch_virtual_available[key_virtual_available(move, incoming=True)].add(move.product_id.id)
        for key_context, product_ids in prefetch_virtual_available.items():
            read_res = self.env['product.product'].browse(product_ids).with_context(warehouse=key_context[0], to_date=key_context[1]).read(['virtual_available'])
            virtual_available_dict[key_context] = {res['id']: res['virtual_available'] for res in read_res}

        for move in product_moves:
            if move._is_consuming():
                if move.state == 'assigned':
                    move.forecast_availability = move.product_uom._compute_quantity(
                        move.reserved_availability, move.product_id.uom_id, rounding_method='HALF-UP')
                elif move.state == 'draft':
                    # for move _is_consuming and in draft -> the forecast_availability > 0 if in stock
                    move.forecast_availability = virtual_available_dict[key_virtual_available(move)][move.product_id.id] - move.product_qty
                elif move.state in ('waiting', 'confirmed', 'partially_available'):
                    outgoing_unreserved_moves_per_warehouse[move.location_id.warehouse_id].add(move.id)
            elif move.picking_type_id.code == 'incoming':
                forecast_availability = virtual_available_dict[key_virtual_available(move, incoming=True)][move.product_id.id]
                if move.state == 'draft':
                    forecast_availability += move.product_qty
                move.forecast_availability = forecast_availability

        for warehouse, moves_ids in outgoing_unreserved_moves_per_warehouse.items():
            if not warehouse:  # No prediction possible if no warehouse.
                continue
            moves = self.browse(moves_ids)
            forecast_info = moves._get_forecast_availability_outgoing(warehouse)
            for move in moves:
                move.forecast_availability, move.forecast_expected_date = forecast_info[move]

    def _set_date_deadline(self, new_deadline):
        # Handle the propagation of `date_deadline` fields (up and down stream - only update by up/downstream documents)
        already_propagate_ids = self.env.context.get('date_deadline_propagate_ids', set()) | set(self.ids)
        self = self.with_context(date_deadline_propagate_ids=already_propagate_ids)
        for move in self:
            moves_to_update = (move.move_dest_ids | move.move_orig_ids)
            if move.date_deadline:
                delta = move.date_deadline - fields.Datetime.to_datetime(new_deadline)
            else:
                delta = 0
            for move_update in moves_to_update:
                if move_update.state in ('done', 'cancel'):
                    continue
                if move_update.id in already_propagate_ids:
                    continue
                if move_update.date_deadline and delta:
                    move_update.date_deadline -= delta
                else:
                    move_update.date_deadline = new_deadline

    @api.depends('move_line_ids', 'move_line_ids.lot_id', 'move_line_ids.qty_done')
    def _compute_lot_ids(self):
        domain_nosuggest = [('move_id', 'in', self.ids), ('lot_id', '!=', False), '|', ('qty_done', '!=', 0.0), ('reserved_qty', '=', 0.0)]
        domain_suggest = [('move_id', 'in', self.ids), ('lot_id', '!=', False), ('qty_done', '!=', 0.0)]
        lots_by_move_id_list = []
        for domain in [domain_nosuggest, domain_suggest]:
            lots_by_move_id = self.env['stock.move.line']._read_group(
                domain,
                ['move_id', 'lot_ids:array_agg(lot_id)'], ['move_id'],
            )
            lots_by_move_id_list.append({by_move['move_id'][0]: by_move['lot_ids'] for by_move in lots_by_move_id})
        for move in self:
            move.lot_ids = lots_by_move_id_list[0 if move.picking_type_id.show_reserved else 1].get(move._origin.id, [])

    def _set_lot_ids(self):
        for move in self:
            move_lines_commands = []
            if move.picking_type_id.show_reserved is False:
                mls = move.move_line_nosuggest_ids
            else:
                mls = move.move_line_ids
            mls = mls.filtered(lambda ml: ml.lot_id)
            for ml in mls:
                if ml.qty_done and ml.lot_id not in move.lot_ids:
                    move_lines_commands.append((2, ml.id))
            ls = move.move_line_ids.lot_id
            for lot in move.lot_ids:
                if lot not in ls:
                    move_line_vals = self._prepare_move_line_vals(quantity=0)
                    move_line_vals['lot_id'] = lot.id
                    move_line_vals['lot_name'] = lot.name
                    move_line_vals['product_uom_id'] = move.product_id.uom_id.id
                    move_line_vals['qty_done'] = 1
                    move_lines_commands.append((0, 0, move_line_vals))
                else:
                    move_line = move.move_line_ids.filtered(lambda line: line.lot_id.id == lot.id)
                    move_line.qty_done = 1
            move.write({'move_line_ids': move_lines_commands})

    @api.depends('picking_type_id', 'date', 'priority')
    def _compute_reservation_date(self):
        for move in self:
            if move.picking_type_id.reservation_method == 'by_date' and move.state in ['draft', 'confirmed', 'waiting', 'partially_available']:
                days = move.picking_type_id.reservation_days_before
                if move.priority == '1':
                    days = move.picking_type_id.reservation_days_before_priority
                move.reservation_date = fields.Date.to_date(move.date) - timedelta(days=days)

    @api.constrains('product_uom')
    def _check_uom(self):
        moves_error = self.filtered(lambda move: move.product_id.uom_id.category_id != move.product_uom.category_id)
        if moves_error:
            user_warning = _('You cannot perform the move because the unit of measure has a different category as the product unit of measure.')
            for move in moves_error:
                user_warning += _('\n\n%s --> Product UoM is %s (%s) - Move UoM is %s (%s)') % (move.product_id.display_name, move.product_id.uom_id.name, move.product_id.uom_id.category_id.name, move.product_uom.name, move.product_uom.category_id.name)
            user_warning += _('\n\nBlocking: %s') % ' ,'.join(moves_error.mapped('name'))
            raise UserError(user_warning)

    def init(self):
        self._cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_move_product_location_index',))
        if not self._cr.fetchone():
            self._cr.execute('CREATE INDEX stock_move_product_location_index ON stock_move (product_id, location_id, location_dest_id, company_id, state)')

    @api.model
    def default_get(self, fields_list):
        # We override the default_get to make stock moves created after the picking was confirmed
        # directly as available in immediate transfer mode. This allows to create extra move lines
        # in the fp view. In planned transfer, the stock move are marked as `additional` and will be
        # auto-confirmed.
        defaults = super(StockMove, self).default_get(fields_list)
        if self.env.context.get('default_picking_id'):
            picking_id = self.env['stock.picking'].browse(self.env.context['default_picking_id'])
            if picking_id.state == 'done':
                defaults['state'] = 'done'
                defaults['product_uom_qty'] = 0.0
                defaults['additional'] = True
            elif picking_id.state not in ['cancel', 'draft', 'done']:
                if picking_id.immediate_transfer:
                    defaults['state'] = 'assigned'
                defaults['product_uom_qty'] = 0.0
                defaults['additional'] = True  # to trigger `_autoconfirm_picking`
        return defaults

    def name_get(self):
        res = []
        for move in self:
            res.append((move.id, '%s%s%s>%s' % (
                move.picking_id.origin and '%s/' % move.picking_id.origin or '',
                move.product_id.code and '%s: ' % move.product_id.code or '',
                move.location_id.name, move.location_dest_id.name)))
        return res

    def write(self, vals):
        # Handle the write on the initial demand by updating the reserved quantity and logging
        # messages according to the state of the stock.move records.
        receipt_moves_to_reassign = self.env['stock.move']
        move_to_recompute_state = self.env['stock.move']
        if 'product_uom' in vals and any(move.state == 'done' for move in self):
            raise UserError(_('You cannot change the UoM for a stock move that has been set to \'Done\'.'))
        if 'product_uom_qty' in vals:
            move_to_unreserve = self.env['stock.move']
            for move in self.filtered(lambda m: m.state not in ('done', 'draft') and m.picking_id):
                if float_compare(vals['product_uom_qty'], move.product_uom_qty, precision_rounding=move.product_uom.rounding):
                    self.env['stock.move.line']._log_message(move.picking_id, move, 'stock.track_move_template', vals)
            if self.env.context.get('do_not_unreserve') is None:
                move_to_unreserve = self.filtered(
                    lambda m: m.state not in ['draft', 'done', 'cancel'] and float_compare(m.reserved_availability, vals.get('product_uom_qty'), precision_rounding=m.product_uom.rounding) == 1
                )
                move_to_unreserve._do_unreserve()
                (self - move_to_unreserve).filtered(lambda m: m.state == 'assigned').write({'state': 'partially_available'})
                # When editing the initial demand, directly run again action assign on receipt moves.
                receipt_moves_to_reassign |= move_to_unreserve.filtered(lambda m: m.location_id.usage == 'supplier')
                receipt_moves_to_reassign |= (self - move_to_unreserve).filtered(lambda m: m.location_id.usage == 'supplier' and m.state in ('partially_available', 'assigned'))
                move_to_recompute_state |= self - move_to_unreserve - receipt_moves_to_reassign
        if 'date_deadline' in vals:
            self._set_date_deadline(vals.get('date_deadline'))
        res = super(StockMove, self).write(vals)
        if move_to_recompute_state:
            move_to_recompute_state._recompute_state()
        if receipt_moves_to_reassign:
            receipt_moves_to_reassign._action_assign()
        return res

    def _delay_alert_get_documents(self):
        """Returns a list of recordset of the documents linked to the stock.move in `self` in order
        to post the delay alert next activity. These documents are deduplicated. This method is meant
        to be overridden by other modules, each of them adding an element by type of recordset on
        this list.

        :return: a list of recordset of the documents linked to `self`
        :rtype: list
        """
        return list(self.mapped('picking_id'))

    def _propagate_date_log_note(self, move_orig):
        """Post a deadline change alert log note on the documents linked to `self`."""
        # TODO : get the end document (PO/SO/MO)
        doc_orig = move_orig._delay_alert_get_documents()
        documents = self._delay_alert_get_documents()
        if not documents or not doc_orig:
            return

        msg = _("The deadline has been automatically updated due to a delay on %s.", doc_orig[0]._get_html_link())
        msg_subject = _("Deadline updated due to delay on %s", doc_orig[0].name)
        # write the message on each document
        for doc in documents:
            last_message = doc.message_ids[:1]
            # Avoids to write the exact same message multiple times.
            if last_message and last_message.subject == msg_subject:
                continue
            odoobot_id = self.env['ir.model.data']._xmlid_to_res_id("base.partner_root")
            doc.message_post(body=msg, author_id=odoobot_id, subject=msg_subject)

    def action_show_details(self):
        """ Returns an action that will open a form view (in a popup) allowing to work on all the
        move lines of a particular move. This form view is used when "show operations" is not
        checked on the picking type.
        """
        self.ensure_one()

        # If "show suggestions" is not checked on the picking type, we have to filter out the
        # reserved move lines. We do this by displaying `move_line_nosuggest_ids`. We use
        # different views to display one field or another so that the webclient doesn't have to
        # fetch both.
        if self.picking_type_id.show_reserved:
            view = self.env.ref('stock.view_stock_move_operations')
        else:
            view = self.env.ref('stock.view_stock_move_nosuggest_operations')

        if self.product_id.tracking == "serial" and self.state == "assigned":
            self.next_serial = self.env['stock.lot']._get_next_serial(self.company_id, self.product_id)

        return {
            'name': _('Detailed Operations'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.move',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.id,
            'context': dict(
                self.env.context,
                show_owner=self.picking_type_id.code != 'incoming',
                show_lots_m2o=self.has_tracking != 'none' and (self.picking_type_id.use_existing_lots or self.state == 'done' or self.origin_returned_move_id.id),  # able to create lots, whatever the value of ` use_create_lots`.
                show_lots_text=self.has_tracking != 'none' and self.picking_type_id.use_create_lots and not self.picking_type_id.use_existing_lots and self.state != 'done' and not self.origin_returned_move_id.id,
                show_source_location=self.picking_type_id.code != 'incoming',
                show_destination_location=self.picking_type_id.code != 'outgoing',
                show_package=not self.location_id.usage == 'supplier',
                show_reserved_quantity=self.state != 'done' and not self.picking_id.immediate_transfer and self.picking_type_id.code != 'incoming'
            ),
        }

    def action_assign_serial_show_details(self):
        """ On `self.move_line_ids`, assign `lot_name` according to
        `self.next_serial` before returning `self.action_show_details`.
        """
        self.ensure_one()
        if not self.next_serial:
            raise UserError(_("You need to set a Serial Number before generating more."))
        self._generate_serial_numbers()
        return self.action_show_details()

    def action_clear_lines_show_details(self):
        """ Unlink `self.move_line_ids` before returning `self.action_show_details`.
        Useful for if a user creates too many SNs by accident via action_assign_serial_show_details
        since there's no way to undo the action.
        """
        self.ensure_one()
        if self.picking_type_id.show_reserved:
            move_lines = self.move_line_ids
        else:
            move_lines = self.move_line_nosuggest_ids
        move_lines.unlink()
        return self.action_show_details()

    def action_assign_serial(self):
        """ Opens a wizard to assign SN's name on each move lines.
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.act_assign_serial_numbers")
        action['context'] = {
            'default_product_id': self.product_id.id,
            'default_move_id': self.id,
        }
        return action

    def action_product_forecast_report(self):
        self.ensure_one()
        action = self.product_id.action_product_forecast_report()
        action['context'] = {
            'active_id': self.product_id.id,
            'active_model': 'product.product',
            'move_to_match_ids': self.ids,
        }
        if self._is_consuming():
            warehouse = self.location_id.warehouse_id
        else:
            warehouse = self.location_dest_id.warehouse_id

        if warehouse:
            action['context']['warehouse'] = warehouse.id
        return action

    def _do_unreserve(self):
        moves_to_unreserve = OrderedSet()
        for move in self:
            if move.state == 'cancel' or (move.state == 'done' and move.scrapped):
                # We may have cancelled move in an open picking in a "propagate_cancel" scenario.
                # We may have done move in an open picking in a scrap scenario.
                continue
            elif move.state == 'done':
                raise UserError(_("You cannot unreserve a stock move that has been set to 'Done'."))
            moves_to_unreserve.add(move.id)
        moves_to_unreserve = self.env['stock.move'].browse(moves_to_unreserve)

        ml_to_update, ml_to_unlink = OrderedSet(), OrderedSet()
        moves_not_to_recompute = OrderedSet()
        for ml in moves_to_unreserve.move_line_ids:
            if ml.qty_done:
                ml_to_update.add(ml.id)
            else:
                ml_to_unlink.add(ml.id)
                moves_not_to_recompute.add(ml.move_id.id)
        ml_to_update, ml_to_unlink = self.env['stock.move.line'].browse(ml_to_update), self.env['stock.move.line'].browse(ml_to_unlink)
        moves_not_to_recompute = self.env['stock.move'].browse(moves_not_to_recompute)

        ml_to_update.write({'reserved_uom_qty': 0})
        ml_to_unlink.unlink()
        # `write` on `stock.move.line` doesn't call `_recompute_state` (unlike to `unlink`),
        # so it must be called for each move where no move line has been deleted.
        (moves_to_unreserve - moves_not_to_recompute)._recompute_state()
        return True

    def _generate_serial_numbers(self, next_serial_count=False):
        """ This method will generate `lot_name` from a string (field
        `next_serial`) and create a move line for each generated `lot_name`.
        """
        self.ensure_one()
        lot_names = self.env['stock.lot'].generate_lot_names(self.next_serial, next_serial_count or self.next_serial_count)
        move_lines_commands = self._generate_serial_move_line_commands(lot_names)
        self.write({'move_line_ids': move_lines_commands})
        return True

    def _push_apply(self):
        new_moves = []
        for move in self:
            # if the move is already chained, there is no need to check push rules
            if move.move_dest_ids:
                continue
            # if the move is a returned move, we don't want to check push rules, as returning a returned move is the only decent way
            # to receive goods without triggering the push rules again (which would duplicate chained operations)
            domain = [('location_src_id', '=', move.location_dest_id.id), ('action', 'in', ('push', 'pull_push'))]
            # first priority goes to the preferred routes defined on the move itself (e.g. coming from a SO line)
            warehouse_id = move.warehouse_id or move.picking_id.picking_type_id.warehouse_id
            if move.location_dest_id.company_id == self.env.company:
                rule = self.env['procurement.group']._search_rule(move.route_ids, move.product_packaging_id, move.product_id, warehouse_id, domain)
            else:
                rule = self.sudo().env['procurement.group']._search_rule(move.route_ids, move.product_packaging_id, move.product_id, warehouse_id, domain)
            # Make sure it is not returning the return
            if rule and (not move.origin_returned_move_id or move.origin_returned_move_id.location_dest_id.id != rule.location_dest_id.id):
                new_move = rule._run_push(move)
                if new_move:
                    new_moves.append(new_move)
        return self.env['stock.move'].concat(*new_moves)

    def _merge_moves_fields(self):
        """ This method will return a dict of stock move’s values that represent the values of all moves in `self` merged. """
        state = self._get_relevant_state_among_moves()
        origin = '/'.join(set(self.filtered(lambda m: m.origin).mapped('origin')))
        return {
            'product_uom_qty': sum(self.mapped('product_uom_qty')),
            'date': min(self.mapped('date')) if all(p.move_type == 'direct' for p in self.picking_id) else max(self.mapped('date')),
            'move_dest_ids': [(4, m.id) for m in self.mapped('move_dest_ids')],
            'move_orig_ids': [(4, m.id) for m in self.mapped('move_orig_ids')],
            'state': state,
            'origin': origin,
        }

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        fields = [
            'product_id', 'price_unit', 'procure_method', 'location_id', 'location_dest_id',
            'product_uom', 'restrict_partner_id', 'scrapped', 'origin_returned_move_id',
            'package_level_id', 'propagate_cancel', 'description_picking', 'date_deadline',
            'product_packaging_id',
        ]
        if self.env['ir.config_parameter'].sudo().get_param('stock.merge_only_same_date'):
            fields.append('date')
        return fields

    @api.model
    def _prepare_merge_negative_moves_excluded_distinct_fields(self):
        return ['description_picking']

    def _clean_merged(self):
        """Cleanup hook used when merging moves"""
        self.write({'propagate_cancel': False})

    def _update_candidate_moves_list(self, candidate_moves_list):
        for picking in self.mapped('picking_id'):
            candidate_moves_list.append(picking.move_ids)

    def _merge_moves(self, merge_into=False):
        """ This method will, for each move in `self`, go up in their linked picking and try to
        find in their existing moves a candidate into which we can merge the move.
        :return: Recordset of moves passed to this method. If some of the passed moves were merged
        into another existing one, return this one and not the (now unlinked) original.
        """
        distinct_fields = self._prepare_merge_moves_distinct_fields()

        candidate_moves_list = []
        if not merge_into:
            self._update_candidate_moves_list(candidate_moves_list)
        else:
            candidate_moves_list.append(merge_into | self)

        # Move removed after merge
        moves_to_unlink = self.env['stock.move']
        # Moves successfully merged
        merged_moves = self.env['stock.move']
        # Emptied moves
        moves_to_cancel = self.env['stock.move']

        moves_by_neg_key = defaultdict(lambda: self.env['stock.move'])
        # Need to check less fields for negative moves as some might not be set.
        neg_qty_moves = self.filtered(lambda m: float_compare(m.product_qty, 0.0, precision_rounding=m.product_uom.rounding) < 0)
        # Detach their picking as they will either get absorbed or create a backorder, so no extra logs will be put in the chatter
        neg_qty_moves.picking_id = False
        excluded_fields = self._prepare_merge_negative_moves_excluded_distinct_fields()
        neg_key = itemgetter(*[field for field in distinct_fields if field not in excluded_fields])

        for candidate_moves in candidate_moves_list:
            # First step find move to merge.
            candidate_moves = candidate_moves.filtered(lambda m: m.state not in ('done', 'cancel', 'draft')) - neg_qty_moves
            for __, g in groupby(candidate_moves, key=itemgetter(*distinct_fields)):
                moves = self.env['stock.move'].concat(*g)
                # Merge all positive moves together
                if len(moves) > 1:
                    # link all move lines to record 0 (the one we will keep).
                    moves.mapped('move_line_ids').write({'move_id': moves[0].id})
                    # merge move data
                    moves[0].write(moves._merge_moves_fields())
                    # update merged moves dicts
                    moves_to_unlink |= moves[1:]
                    merged_moves |= moves[0]
                # Add the now single positive move to its limited key record
                moves_by_neg_key[neg_key(moves[0])] |= moves[0]

        for neg_move in neg_qty_moves:
            # Check all the candidates that matches the same limited key, and adjust their quantites to absorb negative moves
            for pos_move in moves_by_neg_key.get(neg_key(neg_move), []):
                # If quantity can be fully absorbed by a single move, update its quantity and remove the negative move
                if float_compare(pos_move.product_uom_qty, abs(neg_move.product_uom_qty), precision_rounding=pos_move.product_uom.rounding) >= 0:
                    pos_move.product_uom_qty += neg_move.product_uom_qty
                    pos_move.write({
                        'move_dest_ids': [Command.link(m.id) for m in neg_move.mapped('move_dest_ids') if m.location_id == pos_move.location_dest_id],
                        'move_orig_ids': [Command.link(m.id) for m in neg_move.mapped('move_orig_ids') if m.location_dest_id == pos_move.location_id],
                    })
                    merged_moves |= pos_move
                    moves_to_unlink |= neg_move
                    if float_is_zero(pos_move.product_uom_qty, precision_rounding=pos_move.product_uom.rounding):
                        moves_to_cancel |= pos_move
                    break
                neg_move.product_uom_qty += pos_move.product_uom_qty
                pos_move.product_uom_qty = 0
                moves_to_cancel |= pos_move

        if moves_to_unlink:
            # We are using propagate to False in order to not cancel destination moves merged in moves[0]
            moves_to_unlink._clean_merged()
            moves_to_unlink._action_cancel()
            moves_to_unlink.sudo().unlink()

        if moves_to_cancel:
            moves_to_cancel._action_cancel()

        return (self | merged_moves) - moves_to_unlink

    def _get_relevant_state_among_moves(self):
        # We sort our moves by importance of state:
        #     ------------- 0
        #     | Assigned  |
        #     -------------
        #     |  Waiting  |
        #     -------------
        #     |  Partial  |
        #     -------------
        #     |  Confirm  |
        #     ------------- len-1
        sort_map = {
            'assigned': 4,
            'waiting': 3,
            'partially_available': 2,
            'confirmed': 1,
        }
        moves_todo = self\
            .filtered(lambda move: move.state not in ['cancel', 'done'] and not (move.state == 'assigned' and not move.product_uom_qty))\
            .sorted(key=lambda move: (sort_map.get(move.state, 0), move.product_uom_qty))
        if not moves_todo:
            return 'assigned'
        # The picking should be the same for all moves.
        if moves_todo[:1].picking_id and moves_todo[:1].picking_id.move_type == 'one':
            most_important_move = moves_todo[0]
            if most_important_move.state == 'confirmed':
                return 'confirmed' if most_important_move.product_uom_qty else 'assigned'
            elif most_important_move.state == 'partially_available':
                return 'confirmed'
            else:
                return moves_todo[:1].state or 'draft'
        elif moves_todo[:1].state != 'assigned' and any(move.state in ['assigned', 'partially_available'] for move in moves_todo):
            return 'partially_available'
        else:
            least_important_move = moves_todo[-1:]
            if least_important_move.state == 'confirmed' and least_important_move.product_uom_qty == 0:
                return 'assigned'
            else:
                return moves_todo[-1:].state or 'draft'

    @api.onchange('product_id', 'picking_type_id')
    def _onchange_product_id(self):
        product = self.product_id.with_context(lang=self._get_lang())
        self.name = product.partner_ref
        if product:
            self.description_picking = product._get_description(self.picking_type_id)

    @api.onchange('product_id', 'product_qty', 'product_uom')
    def _onchange_suggest_packaging(self):
        # remove packaging if not match the product
        if self.product_packaging_id.product_id != self.product_id:
            self.product_packaging_id = False
        # suggest biggest suitable packaging
        if self.product_id and self.product_qty and self.product_uom:
            self.product_packaging_id = self.product_id.packaging_ids._find_suitable_product_packaging(self.product_qty, self.product_uom)

    @api.onchange('lot_ids')
    def _onchange_lot_ids(self):
        quantity_done = sum(ml.product_uom_id._compute_quantity(ml.qty_done, self.product_uom) for ml in self.move_line_ids.filtered(lambda ml: not ml.lot_id and ml.lot_name))
        quantity_done += self.product_id.uom_id._compute_quantity(len(self.lot_ids), self.product_uom)
        self.update({'quantity_done': quantity_done})

        quants = self.env['stock.quant'].search([('product_id', '=', self.product_id.id),
                                                 ('lot_id', 'in', self.lot_ids.ids),
                                                 ('quantity', '!=', 0),
                                                 '|', ('location_id.usage', '=', 'customer'),
                                                      '&', ('company_id', '=', self.company_id.id),
                                                           ('location_id.usage', 'in', ('internal', 'transit'))])
        if quants:
            sn_to_location = ""
            for quant in quants:
                sn_to_location += _("\n(%s) exists in location %s", quant.lot_id.display_name, quant.location_id.display_name)
            return {
                'warning': {'title': _('Warning'), 'message': _('Existing Serial numbers. Please correct the serial numbers encoded:') + sn_to_location}
            }

    @api.onchange('move_line_ids', 'move_line_nosuggest_ids', 'picking_type_id')
    def _onchange_move_line_ids(self):
        if not self.picking_type_id.use_create_lots:
            # This onchange manages the creation of multiple lot name. We don't
            # need that if the picking type disallows the creation of new lots.
            return

        breaking_char = '\n'
        if self.picking_type_id.show_reserved:
            move_lines = self.move_line_ids
        else:
            move_lines = self.move_line_nosuggest_ids

        for move_line in move_lines:
            # Look if the `lot_name` contains multiple values.
            if breaking_char in (move_line.lot_name or ''):
                split_lines = move_line.lot_name.split(breaking_char)
                split_lines = list(filter(None, split_lines))
                move_line.lot_name = split_lines[0]
                move_lines_commands = self._generate_serial_move_line_commands(
                    split_lines[1:],
                    origin_move_line=move_line,
                )
                if self.picking_type_id.show_reserved:
                    self.update({'move_line_ids': move_lines_commands})
                else:
                    self.update({'move_line_nosuggest_ids': move_lines_commands})
                existing_lots = self.env['stock.lot'].search([
                    ('company_id', '=', self.company_id.id),
                    ('product_id', '=', self.product_id.id),
                    ('name', 'in', split_lines),
                ])
                if existing_lots:
                    return {
                        'warning': {'title': _('Warning'), 'message': _('Existing Serial Numbers (%s). Please correct the serial numbers encoded.') % ','.join(existing_lots.mapped('display_name'))}
                    }
                break

    @api.onchange('product_uom')
    def _onchange_product_uom(self):
        if self.product_uom.factor > self.product_id.uom_id.factor:
            return {
                'warning': {
                    'title': "Unsafe unit of measure",
                    'message': _("You are using a unit of measure smaller than the one you are using in "
                                 "order to stock your product. This can lead to rounding problem on reserved quantity. "
                                 "You should use the smaller unit of measure possible in order to valuate your stock or "
                                 "change its rounding precision to a smaller value (example: 0.00001)."),
                }
            }

    def _key_assign_picking(self):
        self.ensure_one()
        keys = (self.group_id, self.location_id, self.location_dest_id, self.picking_type_id)
        if self.partner_id and (self.location_id.usage == 'transit' or self.location_dest_id.usage == 'transit'):
            keys += (self.partner_id, )
        return keys

    def _search_picking_for_assignation_domain(self):
        domain = [
            ('group_id', '=', self.group_id.id),
            ('location_id', '=', self.location_id.id),
            ('location_dest_id', '=', self.location_dest_id.id),
            ('picking_type_id', '=', self.picking_type_id.id),
            ('printed', '=', False),
            ('immediate_transfer', '=', False),
            ('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])]
        if self.partner_id and (self.location_id.usage == 'transit' or self.location_dest_id.usage == 'transit'):
            domain += [('partner_id', '=', self.partner_id.id)]
        return domain

    def _search_picking_for_assignation(self):
        self.ensure_one()
        domain = self._search_picking_for_assignation_domain()
        picking = self.env['stock.picking'].search(domain, limit=1)
        return picking

    def _assign_picking(self):
        """ Try to assign the moves to an existing picking that has not been
        reserved yet and has the same procurement group, locations and picking
        type (moves should already have them identical). Otherwise, create a new
        picking to assign them to. """
        Picking = self.env['stock.picking']
        grouped_moves = groupby(self, key=lambda m: m._key_assign_picking())
        for group, moves in grouped_moves:
            moves = self.env['stock.move'].concat(*moves)
            new_picking = False
            # Could pass the arguments contained in group but they are the same
            # for each move that why moves[0] is acceptable
            picking = moves[0]._search_picking_for_assignation()
            if picking:
                # If a picking is found, we'll append `move` to its move list and thus its
                # `partner_id` and `ref` field will refer to multiple records. In this
                # case, we chose to wipe them.
                vals = {}
                if any(picking.partner_id.id != m.partner_id.id for m in moves):
                    vals['partner_id'] = False
                if any(picking.origin != m.origin for m in moves):
                    vals['origin'] = False
                if vals:
                    picking.write(vals)
            else:
                # Don't create picking for negative moves since they will be
                # reverse and assign to another picking
                moves = moves.filtered(lambda m: float_compare(m.product_uom_qty, 0.0, precision_rounding=m.product_uom.rounding) >= 0)
                if not moves:
                    continue
                new_picking = True
                picking = Picking.create(moves._get_new_picking_values())

            moves.write({'picking_id': picking.id})
            moves._assign_picking_post_process(new=new_picking)
        return True

    def _assign_picking_post_process(self, new=False):
        pass

    def _generate_serial_move_line_commands(self, lot_names, origin_move_line=None):
        """Return a list of commands to update the move lines (write on
        existing ones or create new ones).
        Called when user want to create and assign multiple serial numbers in
        one time (using the button/wizard or copy-paste a list in the field).

        :param lot_names: A list containing all serial number to assign.
        :type lot_names: list
        :param origin_move_line: A move line to duplicate the value from, default to None
        :type origin_move_line: record of :class:`stock.move.line`
        :return: A list of commands to create/update :class:`stock.move.line`
        :rtype: list
        """
        self.ensure_one()

        # Select the right move lines depending of the picking type configuration.
        move_lines = self.env['stock.move.line']
        if self.picking_type_id.show_reserved:
            move_lines = self.move_line_ids.filtered(lambda ml: not ml.lot_id and not ml.lot_name)
        else:
            move_lines = self.move_line_nosuggest_ids.filtered(lambda ml: not ml.lot_id and not ml.lot_name)

        loc_dest = origin_move_line and origin_move_line.location_dest_id
        move_line_vals = {
            'picking_id': self.picking_id.id,
            'location_id': self.location_id.id,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_id.uom_id.id,
            'qty_done': 1,
        }
        if origin_move_line:
            # `owner_id` and `package_id` are taken only in the case we create
            # new move lines from an existing move line. Also, updates the
            # `qty_done` because it could be usefull for products tracked by lot.
            move_line_vals.update({
                'owner_id': origin_move_line.owner_id.id,
                'package_id': origin_move_line.package_id.id,
                'qty_done': origin_move_line.qty_done or 1,
            })

        move_lines_commands = []
        qty_by_location = defaultdict(float)
        for lot_name in lot_names:
            # We write the lot name on an existing move line (if we have still one)...
            if move_lines:
                move_lines_commands.append((1, move_lines[0].id, {
                    'lot_name': lot_name,
                    'qty_done': 1,
                }))
                qty_by_location[move_lines[0].location_dest_id.id] += 1
                move_lines = move_lines[1:]
            # ... or create a new move line with the serial name.
            else:
                loc = loc_dest or self.location_dest_id._get_putaway_strategy(self.product_id, quantity=1, packaging=self.product_packaging_id, additional_qty=qty_by_location)
                move_line_cmd = dict(move_line_vals, lot_name=lot_name, location_dest_id=loc.id)
                move_lines_commands.append((0, 0, move_line_cmd))
                qty_by_location[loc.id] += 1
        return move_lines_commands

    def _get_new_picking_values(self):
        """ return create values for new picking that will be linked with group
        of moves in self.
        """
        origins = self.filtered(lambda m: m.origin).mapped('origin')
        origins = list(dict.fromkeys(origins)) # create a list of unique items
        # Will display source document if any, when multiple different origins
        # are found display a maximum of 5
        if len(origins) == 0:
            origin = False
        else:
            origin = ','.join(origins[:5])
            if len(origins) > 5:
                origin += "..."
        partners = self.mapped('partner_id')
        partner = len(partners) == 1 and partners.id or False
        return {
            'origin': origin,
            'company_id': self.mapped('company_id').id,
            'user_id': False,
            'move_type': self.mapped('group_id').move_type or 'direct',
            'partner_id': partner,
            'picking_type_id': self.mapped('picking_type_id').id,
            'location_id': self.mapped('location_id').id,
            'location_dest_id': self.mapped('location_dest_id').id,
        }

    def _should_be_assigned(self):
        self.ensure_one()
        return bool(not self.picking_id and self.picking_type_id)

    def _action_confirm(self, merge=True, merge_into=False):
        """ Confirms stock move or put it in waiting if it's linked to another move.
        :param: merge: According to this boolean, a newly confirmed move will be merged
        in another move of the same picking sharing its characteristics.
        """
        # Use OrderedSet of id (instead of recordset + |= ) for performance
        move_create_proc, move_to_confirm, move_waiting = OrderedSet(), OrderedSet(), OrderedSet()
        to_assign = defaultdict(OrderedSet)
        for move in self:
            if move.state != 'draft':
                continue
            # if the move is preceded, then it's waiting (if preceding move is done, then action_assign has been called already and its state is already available)
            if move.move_orig_ids:
                move_waiting.add(move.id)
            else:
                if move.procure_method == 'make_to_order':
                    move_create_proc.add(move.id)
                else:
                    move_to_confirm.add(move.id)
            if move._should_be_assigned():
                key = (move.group_id.id, move.location_id.id, move.location_dest_id.id)
                to_assign[key].add(move.id)

        move_create_proc, move_to_confirm, move_waiting = self.browse(move_create_proc), self.browse(move_to_confirm), self.browse(move_waiting)

        # create procurements for make to order moves
        procurement_requests = []
        for move in move_create_proc:
            values = move._prepare_procurement_values()
            origin = move._prepare_procurement_origin()
            procurement_requests.append(self.env['procurement.group'].Procurement(
                move.product_id, move.product_uom_qty, move.product_uom,
                move.location_id, move.rule_id and move.rule_id.name or "/",
                origin, move.company_id, values))
        self.env['procurement.group'].run(procurement_requests, raise_user_error=not self.env.context.get('from_orderpoint'))

        move_to_confirm.write({'state': 'confirmed'})
        (move_waiting | move_create_proc).write({'state': 'waiting'})
        # procure_method sometimes changes with certain workflows so just in case, apply to all moves
        (move_to_confirm | move_waiting | move_create_proc).filtered(lambda m: m.picking_type_id.reservation_method == 'at_confirm')\
            .write({'reservation_date': fields.Date.today()})

        # assign picking in batch for all confirmed move that share the same details
        for moves_ids in to_assign.values():
            self.browse(moves_ids).with_context(clean_context(self.env.context))._assign_picking()
        new_push_moves = self.filtered(lambda m: not m.picking_id.immediate_transfer)._push_apply()
        self._check_company()
        moves = self
        if merge:
            moves = self._merge_moves(merge_into=merge_into)

        # Transform remaining move in return in case of negative initial demand
        neg_r_moves = moves.filtered(lambda move: float_compare(
            move.product_uom_qty, 0, precision_rounding=move.product_uom.rounding) < 0)
        for move in neg_r_moves:
            move.location_id, move.location_dest_id = move.location_dest_id, move.location_id
            orig_move_ids, dest_move_ids = [], []
            for m in move.move_orig_ids | move.move_dest_ids:
                from_loc, to_loc = m.location_id, m.location_dest_id
                if float_compare(m.product_uom_qty, 0, precision_rounding=m.product_uom.rounding) < 0:
                    from_loc, to_loc = to_loc, from_loc
                if to_loc == move.location_id:
                    orig_move_ids += m.ids
                elif move.location_dest_id == from_loc:
                    dest_move_ids += m.ids
            move.move_orig_ids, move.move_dest_ids = [(6, 0, orig_move_ids)], [(6, 0, dest_move_ids)]
            move.product_uom_qty *= -1
            if move.picking_type_id.return_picking_type_id:
                move.picking_type_id = move.picking_type_id.return_picking_type_id
            # We are returning some products, we must take them in the source location
            move.procure_method = 'make_to_stock'
        neg_r_moves._assign_picking()

        # call `_action_assign` on every confirmed move which location_id bypasses the reservation + those expected to be auto-assigned
        moves.filtered(lambda move: not move.picking_id.immediate_transfer
                       and move.state in ('confirmed', 'partially_available')
                       and (move._should_bypass_reservation()
                            or move.picking_type_id.reservation_method == 'at_confirm'
                            or (move.reservation_date and move.reservation_date <= fields.Date.today())))\
             ._action_assign()
        if new_push_moves:
            neg_push_moves = new_push_moves.filtered(lambda sm: float_compare(sm.product_uom_qty, 0, precision_rounding=sm.product_uom.rounding) < 0)
            (new_push_moves - neg_push_moves)._action_confirm()
            # Negative moves do not have any picking, so we should try to merge it with their siblings
            neg_push_moves._action_confirm(merge_into=neg_push_moves.move_orig_ids.move_dest_ids)

        return moves

    def _prepare_procurement_origin(self):
        self.ensure_one()
        return self.group_id and self.group_id.name or (self.origin or self.picking_id.name or "/")

    def _prepare_procurement_values(self):
        """ Prepare specific key for moves or other componenets that will be created from a stock rule
        comming from a stock move. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        self.ensure_one()
        group_id = self.group_id or False
        if self.rule_id:
            if self.rule_id.group_propagation_option == 'fixed' and self.rule_id.group_id:
                group_id = self.rule_id.group_id
            elif self.rule_id.group_propagation_option == 'none':
                group_id = False
        product_id = self.product_id.with_context(lang=self._get_lang())
        return {
            'product_description_variants': self.description_picking and self.description_picking.replace(product_id._get_description(self.picking_type_id), ''),
            'date_planned': self._get_mto_procurement_date(),
            'date_deadline': self.date_deadline,
            'move_dest_ids': self,
            'group_id': group_id,
            'route_ids': self.route_ids,
            'warehouse_id': self.warehouse_id or self.picking_type_id.warehouse_id,
            'priority': self.priority,
            'orderpoint_id': self.orderpoint_id,
            'product_packaging_id': self.product_packaging_id,
        }

    def _get_mto_procurement_date(self):
        return self.date

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        self.ensure_one()
        vals = {
            'move_id': self.id,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'picking_id': self.picking_id.id,
            'company_id': self.company_id.id,
        }
        if quantity:
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            uom_quantity = self.product_id.uom_id._compute_quantity(quantity, self.product_uom, rounding_method='HALF-UP')
            uom_quantity = float_round(uom_quantity, precision_digits=rounding)
            uom_quantity_back_to_product_uom = self.product_uom._compute_quantity(uom_quantity, self.product_id.uom_id, rounding_method='HALF-UP')
            if float_compare(quantity, uom_quantity_back_to_product_uom, precision_digits=rounding) == 0:
                vals = dict(vals, reserved_uom_qty=uom_quantity)
            else:
                vals = dict(vals, reserved_uom_qty=quantity, product_uom_id=self.product_id.uom_id.id)
        package = None
        if reserved_quant:
            package = reserved_quant.package_id
            vals = dict(
                vals,
                location_id=reserved_quant.location_id.id,
                lot_id=reserved_quant.lot_id.id or False,
                package_id=package.id or False,
                owner_id =reserved_quant.owner_id.id or False,
            )
        return vals

    def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None, owner_id=None, strict=True):
        """ Create or update move lines.
        """
        self.ensure_one()

        if not lot_id:
            lot_id = self.env['stock.lot']
        if not package_id:
            package_id = self.env['stock.quant.package']
        if not owner_id:
            owner_id = self.env['res.partner']

        # do full packaging reservation when it's needed
        if self.product_packaging_id and self.product_id.product_tmpl_id.categ_id.packaging_reserve_method == "full":
            available_quantity = self.product_packaging_id._check_qty(available_quantity, self.product_id.uom_id, "DOWN")

        taken_quantity = min(available_quantity, need)

        # `taken_quantity` is in the quants unit of measure. There's a possibility that the move's
        # unit of measure won't be respected if we blindly reserve this quantity, a common usecase
        # is if the move's unit of measure's rounding does not allow fractional reservation. We chose
        # to convert `taken_quantity` to the move's unit of measure with a down rounding method and
        # then get it back in the quants unit of measure with an half-up rounding_method. This
        # way, we'll never reserve more than allowed. We do not apply this logic if
        # `available_quantity` is brought by a chained move line. In this case, `_prepare_move_line_vals`
        # will take care of changing the UOM to the UOM of the product.
        if not strict and self.product_id.uom_id != self.product_uom:
            taken_quantity_move_uom = self.product_id.uom_id._compute_quantity(taken_quantity, self.product_uom, rounding_method='DOWN')
            taken_quantity = self.product_uom._compute_quantity(taken_quantity_move_uom, self.product_id.uom_id, rounding_method='HALF-UP')

        quants = []
        rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        if self.product_id.tracking == 'serial':
            if float_compare(taken_quantity, int(taken_quantity), precision_digits=rounding) != 0:
                taken_quantity = 0

        try:
            with self.env.cr.savepoint():
                if not float_is_zero(taken_quantity, precision_rounding=self.product_id.uom_id.rounding):
                    quants = self.env['stock.quant']._update_reserved_quantity(
                        self.product_id, location_id, taken_quantity, lot_id=lot_id,
                        package_id=package_id, owner_id=owner_id, strict=strict
                    )
        except UserError:
            taken_quantity = 0

        # Find a candidate move line to update or create a new one.
        for reserved_quant, quantity in quants:
            to_update = next((line for line in self.move_line_ids if line._reservation_is_updatable(quantity, reserved_quant)), False)
            if to_update:
                uom_quantity = self.product_id.uom_id._compute_quantity(quantity, to_update.product_uom_id, rounding_method='HALF-UP')
                uom_quantity = float_round(uom_quantity, precision_digits=rounding)
                uom_quantity_back_to_product_uom = to_update.product_uom_id._compute_quantity(uom_quantity, self.product_id.uom_id, rounding_method='HALF-UP')
            if to_update and float_compare(quantity, uom_quantity_back_to_product_uom, precision_digits=rounding) == 0:
                to_update.with_context(bypass_reservation_update=True).reserved_uom_qty += uom_quantity
            else:
                if self.product_id.tracking == 'serial':
                    self.env['stock.move.line'].create([self._prepare_move_line_vals(quantity=1, reserved_quant=reserved_quant) for i in range(int(quantity))])
                else:
                    self.env['stock.move.line'].create(self._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant))
        return taken_quantity

    def _should_bypass_reservation(self, forced_location=False):
        self.ensure_one()
        location = forced_location or self.location_id
        return location.should_bypass_reservation() or self.product_id.type != 'product'

    # necessary hook to be able to override move reservation to a restrict lot, owner, pack, location...
    def _get_available_quantity(self, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, allow_negative=False):
        self.ensure_one()
        if location_id.should_bypass_reservation():
            return self.product_qty
        return self.env['stock.quant']._get_available_quantity(self.product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict, allow_negative=allow_negative)

    def _action_assign(self):
        """ Reserve stock moves by creating their stock move lines. A stock move is
        considered reserved once the sum of `reserved_qty` for all its move lines is
        equal to its `product_qty`. If it is less, the stock move is considered
        partially available.
        """

        def _get_available_move_lines(move):
            move_lines_in = move.move_orig_ids.filtered(lambda m: m.state == 'done').mapped('move_line_ids')

            def _keys_in_groupby(ml):
                return (ml.location_dest_id, ml.lot_id, ml.result_package_id, ml.owner_id)

            grouped_move_lines_in = {}
            for k, g in groupby(move_lines_in, key=_keys_in_groupby):
                qty_done = 0
                for ml in g:
                    qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
                grouped_move_lines_in[k] = qty_done
            move_lines_out_done = (move.move_orig_ids.mapped('move_dest_ids') - move)\
                .filtered(lambda m: m.state in ['done'])\
                .mapped('move_line_ids')
            # As we defer the write on the stock.move's state at the end of the loop, there
            # could be moves to consider in what our siblings already took.
            moves_out_siblings = move.move_orig_ids.mapped('move_dest_ids') - move
            moves_out_siblings_to_consider = moves_out_siblings & (StockMove.browse(assigned_moves_ids) + StockMove.browse(partially_available_moves_ids))
            reserved_moves_out_siblings = moves_out_siblings.filtered(lambda m: m.state in ['partially_available', 'assigned'])
            move_lines_out_reserved = (reserved_moves_out_siblings | moves_out_siblings_to_consider).mapped('move_line_ids')

            def _keys_out_groupby(ml):
                return (ml.location_id, ml.lot_id, ml.package_id, ml.owner_id)

            grouped_move_lines_out = {}
            for k, g in groupby(move_lines_out_done, key=_keys_out_groupby):
                qty_done = 0
                for ml in g:
                    qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
                grouped_move_lines_out[k] = qty_done
            for k, g in groupby(move_lines_out_reserved, key=_keys_out_groupby):
                grouped_move_lines_out[k] = sum(self.env['stock.move.line'].concat(*g).mapped('reserved_qty'))
            available_move_lines = {key: grouped_move_lines_in[key] - grouped_move_lines_out.get(key, 0) for key in grouped_move_lines_in}
            # pop key if the quantity available amount to 0
            rounding = move.product_id.uom_id.rounding
            return dict((k, v) for k, v in available_move_lines.items() if float_compare(v, 0, precision_rounding=rounding) > 0)

        StockMove = self.env['stock.move']
        assigned_moves_ids = OrderedSet()
        partially_available_moves_ids = OrderedSet()
        # Read the `reserved_availability` field of the moves out of the loop to prevent unwanted
        # cache invalidation when actually reserving the move.
        reserved_availability = {move: move.reserved_availability for move in self}
        roundings = {move: move.product_id.uom_id.rounding for move in self}
        move_line_vals_list = []
        # Once the quantities are assigned, we want to find a better destination location thanks
        # to the putaway rules. This redirection will be applied on moves of `moves_to_redirect`.
        moves_to_redirect = OrderedSet()
        for move in self.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available']):
            rounding = roundings[move]
            missing_reserved_uom_quantity = move.product_uom_qty - reserved_availability[move]
            missing_reserved_quantity = move.product_uom._compute_quantity(missing_reserved_uom_quantity, move.product_id.uom_id, rounding_method='HALF-UP')
            if move._should_bypass_reservation():
                # create the move line(s) but do not impact quants
                if move.move_orig_ids:
                    available_move_lines = _get_available_move_lines(move)
                    for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
                        qty_added = min(missing_reserved_quantity, quantity)
                        move_line_vals = move._prepare_move_line_vals(qty_added)
                        move_line_vals.update({
                            'location_id': location_id.id,
                            'lot_id': lot_id.id,
                            'lot_name': lot_id.name,
                            'owner_id': owner_id.id,
                        })
                        move_line_vals_list.append(move_line_vals)
                        missing_reserved_quantity -= qty_added
                        if float_is_zero(missing_reserved_quantity, precision_rounding=move.product_id.uom_id.rounding):
                            break

                if missing_reserved_quantity and move.product_id.tracking == 'serial' and (move.picking_type_id.use_create_lots or move.picking_type_id.use_existing_lots):
                    for i in range(0, int(missing_reserved_quantity)):
                        move_line_vals_list.append(move._prepare_move_line_vals(quantity=1))
                elif missing_reserved_quantity:
                    to_update = move.move_line_ids.filtered(lambda ml: ml.product_uom_id == move.product_uom and
                                                            ml.location_id == move.location_id and
                                                            ml.location_dest_id == move.location_dest_id and
                                                            ml.picking_id == move.picking_id and
                                                            not ml.lot_id and
                                                            not ml.package_id and
                                                            not ml.owner_id)
                    if to_update:
                        to_update[0].reserved_uom_qty += move.product_id.uom_id._compute_quantity(
                            missing_reserved_quantity, move.product_uom, rounding_method='HALF-UP')
                    else:
                        move_line_vals_list.append(move._prepare_move_line_vals(quantity=missing_reserved_quantity))
                assigned_moves_ids.add(move.id)
                moves_to_redirect.add(move.id)
            else:
                if float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding):
                    assigned_moves_ids.add(move.id)
                elif not move.move_orig_ids:
                    if move.procure_method == 'make_to_order':
                        continue
                    # If we don't need any quantity, consider the move assigned.
                    need = missing_reserved_quantity
                    if float_is_zero(need, precision_rounding=rounding):
                        assigned_moves_ids.add(move.id)
                        continue
                    # Reserve new quants and create move lines accordingly.
                    forced_package_id = move.package_level_id.package_id or None
                    available_quantity = move._get_available_quantity(move.location_id, package_id=forced_package_id)
                    if available_quantity <= 0:
                        continue
                    taken_quantity = move._update_reserved_quantity(need, available_quantity, move.location_id, package_id=forced_package_id, strict=False)
                    if float_is_zero(taken_quantity, precision_rounding=rounding):
                        continue
                    moves_to_redirect.add(move.id)
                    if float_compare(need, taken_quantity, precision_rounding=rounding) == 0:
                        assigned_moves_ids.add(move.id)
                    else:
                        partially_available_moves_ids.add(move.id)
                else:
                    # Check what our parents brought and what our siblings took in order to
                    # determine what we can distribute.
                    # `qty_done` is in `ml.product_uom_id` and, as we will later increase
                    # the reserved quantity on the quants, convert it here in
                    # `product_id.uom_id` (the UOM of the quants is the UOM of the product).
                    available_move_lines = _get_available_move_lines(move)
                    if not available_move_lines:
                        continue
                    for move_line in move.move_line_ids.filtered(lambda m: m.reserved_qty):
                        if available_move_lines.get((move_line.location_id, move_line.lot_id, move_line.result_package_id, move_line.owner_id)):
                            available_move_lines[(move_line.location_id, move_line.lot_id, move_line.result_package_id, move_line.owner_id)] -= move_line.reserved_qty
                    for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
                        need = move.product_qty - sum(move.move_line_ids.mapped('reserved_qty'))
                        # `quantity` is what is brought by chained done move lines. We double check
                        # here this quantity is available on the quants themselves. If not, this
                        # could be the result of an inventory adjustment that removed totally of
                        # partially `quantity`. When this happens, we chose to reserve the maximum
                        # still available. This situation could not happen on MTS move, because in
                        # this case `quantity` is directly the quantity on the quants themselves.
                        available_quantity = move._get_available_quantity(location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True)
                        if float_is_zero(available_quantity, precision_rounding=rounding):
                            continue
                        taken_quantity = move._update_reserved_quantity(need, min(quantity, available_quantity), location_id, lot_id, package_id, owner_id)
                        if float_is_zero(taken_quantity, precision_rounding=rounding):
                            continue
                        moves_to_redirect.add(move.id)
                        if float_is_zero(need - taken_quantity, precision_rounding=rounding):
                            assigned_moves_ids.add(move.id)
                            break
                        partially_available_moves_ids.add(move.id)
            if move.product_id.tracking == 'serial':
                move.next_serial_count = move.product_uom_qty

        self.env['stock.move.line'].create(move_line_vals_list)
        StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
        StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})
        if self.env.context.get('bypass_entire_pack'):
            return
        self.mapped('picking_id')._check_entire_pack()
        StockMove.browse(moves_to_redirect).move_line_ids._apply_putaway_strategy()

    def _action_cancel(self):
        if any(move.state == 'done' and not move.scrapped for move in self):
            raise UserError(_('You cannot cancel a stock move that has been set to \'Done\'. Create a return in order to reverse the moves which took place.'))
        moves_to_cancel = self.filtered(lambda m: m.state != 'cancel' and not (m.state == 'done' and m.scrapped))
        # self cannot contain moves that are either cancelled or done, therefore we can safely
        # unlink all associated move_line_ids
        moves_to_cancel._do_unreserve()

        for move in moves_to_cancel:
            siblings_states = (move.move_dest_ids.mapped('move_orig_ids') - move).mapped('state')
            if move.propagate_cancel:
                # only cancel the next move if all my siblings are also cancelled
                if all(state == 'cancel' for state in siblings_states):
                    move.move_dest_ids.filtered(lambda m: m.state != 'done')._action_cancel()
            else:
                if all(state in ('done', 'cancel') for state in siblings_states):
                    move.move_dest_ids.write({'procure_method': 'make_to_stock'})
                    move.move_dest_ids.write({'move_orig_ids': [(3, move.id, 0)]})
        moves_to_cancel.write({
            'state': 'cancel',
            'move_orig_ids': [(5, 0, 0)],
            'procure_method': 'make_to_stock',
        })
        return True

    def _prepare_extra_move_vals(self, qty):
        vals = {
            'procure_method': 'make_to_stock',
            'origin_returned_move_id': self.origin_returned_move_id.id,
            'product_uom_qty': qty,
            'picking_id': self.picking_id.id,
            'price_unit': self.price_unit,
            'date_deadline': self.date_deadline,
        }
        return vals

    def _create_extra_move(self):
        """ If the quantity done on a move exceeds its quantity todo, this method will create an
        extra move attached to a (potentially split) move line. If the previous condition is not
        met, it'll return an empty recordset.

        The rationale for the creation of an extra move is the application of a potential push
        rule that will handle the extra quantities.
        """
        extra_move = self
        rounding = self.product_uom.rounding
        # moves created after the picking is assigned do not have `product_uom_qty`, but we shouldn't create extra moves for them
        if float_compare(self.quantity_done, self.product_uom_qty, precision_rounding=rounding) > 0:
            # create the extra moves
            extra_move_quantity = float_round(
                self.quantity_done - self.product_uom_qty,
                precision_rounding=rounding,
                rounding_method='HALF-UP')
            extra_move_vals = self._prepare_extra_move_vals(extra_move_quantity)
            extra_move = self.copy(default=extra_move_vals).with_context(avoid_putaway_rules=True)

            merge_into_self = all(self[field] == extra_move[field] for field in self._prepare_merge_moves_distinct_fields())

            if merge_into_self:
                extra_move = extra_move._action_confirm(merge_into=self)
                return extra_move
            else:
                extra_move = extra_move._action_confirm()
        return extra_move | self

    def _action_done(self, cancel_backorder=False):
        self.filtered(lambda move: move.state == 'draft')._action_confirm()  # MRP allows scrapping draft moves
        moves = self.exists().filtered(lambda x: x.state not in ('done', 'cancel'))
        moves_ids_todo = OrderedSet()

        # Cancel moves where necessary ; we should do it before creating the extra moves because
        # this operation could trigger a merge of moves.
        for move in moves:
            if move.quantity_done <= 0 and not move.is_inventory:
                if float_compare(move.product_uom_qty, 0.0, precision_rounding=move.product_uom.rounding) == 0 or cancel_backorder:
                    move._action_cancel()

        # Create extra moves where necessary
        for move in moves:
            if move.state == 'cancel' or (move.quantity_done <= 0 and not move.is_inventory):
                continue

            moves_ids_todo |= move._create_extra_move().ids

        moves_todo = self.browse(moves_ids_todo)
        moves_todo._check_company()
        # Split moves where necessary and move quants
        backorder_moves_vals = []
        for move in moves_todo:
            # To know whether we need to create a backorder or not, round to the general product's
            # decimal precision and not the product's UOM.
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(move.quantity_done, move.product_uom_qty, precision_digits=rounding) < 0:
                # Need to do some kind of conversion here
                qty_split = move.product_uom._compute_quantity(move.product_uom_qty - move.quantity_done, move.product_id.uom_id, rounding_method='HALF-UP')
                new_move_vals = move._split(qty_split)
                backorder_moves_vals += new_move_vals
        backorder_moves = self.env['stock.move'].create(backorder_moves_vals)
        # The backorder moves are not yet in their own picking. We do not want to check entire packs for those
        # ones as it could messed up the result_package_id of the moves being currently validated
        backorder_moves.with_context(bypass_entire_pack=True)._action_confirm(merge=False)
        if cancel_backorder:
            backorder_moves.with_context(moves_todo=moves_todo)._action_cancel()
        moves_todo.mapped('move_line_ids').sorted()._action_done()
        # Check the consistency of the result packages; there should be an unique location across
        # the contained quants.
        for result_package in moves_todo\
                .mapped('move_line_ids.result_package_id')\
                .filtered(lambda p: p.quant_ids and len(p.quant_ids) > 1):
            if len(result_package.quant_ids.filtered(lambda q: not float_is_zero(abs(q.quantity) + abs(q.reserved_quantity), precision_rounding=q.product_uom_id.rounding)).mapped('location_id')) > 1:
                raise UserError(_('You cannot move the same package content more than once in the same transfer or split the same package into two location.'))
        picking = moves_todo.mapped('picking_id')
        moves_todo.write({'state': 'done', 'date': fields.Datetime.now()})

        new_push_moves = moves_todo.filtered(lambda m: m.picking_id.immediate_transfer)._push_apply()
        if new_push_moves:
            new_push_moves._action_confirm()
        move_dests_per_company = defaultdict(lambda: self.env['stock.move'])
        for move_dest in moves_todo.move_dest_ids:
            move_dests_per_company[move_dest.company_id.id] |= move_dest
        for company_id, move_dests in move_dests_per_company.items():
            move_dests.sudo().with_company(company_id)._action_assign()

        # We don't want to create back order for scrap moves
        # Replace by a kwarg in master
        if self.env.context.get('is_scrap'):
            return moves_todo

        if picking and not cancel_backorder:
            backorder = picking._create_backorder()
            if any([m.state == 'assigned' for m in backorder.move_ids]):
               backorder._check_entire_pack()
        return moves_todo

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_or_cancel(self):
        if any(move.state not in ('draft', 'cancel') for move in self):
            raise UserError(_('You can only delete draft moves.'))

    def unlink(self):
        # With the non plannified picking, draft moves could have some move lines.
        self.with_context(prefetch_fields=False).mapped('move_line_ids').unlink()
        return super(StockMove, self).unlink()

    def _prepare_move_split_vals(self, qty):
        vals = {
            'product_uom_qty': qty,
            'procure_method': 'make_to_stock',
            'move_dest_ids': [(4, x.id) for x in self.move_dest_ids if x.state not in ('done', 'cancel')],
            'move_orig_ids': [(4, x.id) for x in self.move_orig_ids],
            'origin_returned_move_id': self.origin_returned_move_id.id,
            'price_unit': self.price_unit,
            'date_deadline': self.date_deadline,
        }
        if self.env.context.get('force_split_uom_id'):
            vals['product_uom'] = self.env.context['force_split_uom_id']
        return vals

    def _split(self, qty, restrict_partner_id=False):
        """ Splits `self` quantity and return values for a new moves to be created afterwards

        :param qty: float. quantity to split (given in product UoM)
        :param restrict_partner_id: optional partner that can be given in order to force the new move to restrict its choice of quants to the ones belonging to this partner.
        :returns: list of dict. stock move values """
        self.ensure_one()
        if self.state in ('done', 'cancel'):
            raise UserError(_('You cannot split a stock move that has been set to \'Done\'.'))
        elif self.state == 'draft':
            # we restrict the split of a draft move because if not confirmed yet, it may be replaced by several other moves in
            # case of phantom bom (with mrp module). And we don't want to deal with this complexity by copying the product that will explode.
            raise UserError(_('You cannot split a draft move. It needs to be confirmed first.'))
        if float_is_zero(qty, precision_rounding=self.product_id.uom_id.rounding) or self.product_qty <= qty:
            return []

        decimal_precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        # `qty` passed as argument is the quantity to backorder and is always expressed in the
        # quants UOM. If we're able to convert back and forth this quantity in the move's and the
        # quants UOM, the backordered move can keep the UOM of the move. Else, we'll create is in
        # the UOM of the quants.
        uom_qty = self.product_id.uom_id._compute_quantity(qty, self.product_uom, rounding_method='HALF-UP')
        if float_compare(qty, self.product_uom._compute_quantity(uom_qty, self.product_id.uom_id, rounding_method='HALF-UP'), precision_digits=decimal_precision) == 0:
            defaults = self._prepare_move_split_vals(uom_qty)
        else:
            defaults = self.with_context(force_split_uom_id=self.product_id.uom_id.id)._prepare_move_split_vals(qty)

        if restrict_partner_id:
            defaults['restrict_partner_id'] = restrict_partner_id

        # TDE CLEANME: remove context key + add as parameter
        if self.env.context.get('source_location_id'):
            defaults['location_id'] = self.env.context['source_location_id']
        new_move_vals = self.copy_data(defaults)

        # Update the original `product_qty` of the move. Use the general product's decimal
        # precision and not the move's UOM to handle case where the `quantity_done` is not
        # compatible with the move's UOM.
        new_product_qty = self.product_id.uom_id._compute_quantity(self.product_qty - qty, self.product_uom, round=False)
        new_product_qty = float_round(new_product_qty, precision_digits=self.env['decimal.precision'].precision_get('Product Unit of Measure'))
        self.with_context(do_not_unreserve=True).write({'product_uom_qty': new_product_qty})
        return new_move_vals

    def _recompute_state(self):
        moves_state_to_write = defaultdict(set)
        for move in self:
            rounding = move.product_uom.rounding
            if move.state in ('cancel', 'done', 'draft'):
                continue
            elif float_compare(move.reserved_availability, move.product_uom_qty, precision_rounding=rounding) == 0:
                moves_state_to_write['assigned'].add(move.id)
            elif move.reserved_availability and float_compare(move.reserved_availability, move.product_uom_qty, precision_rounding=rounding) <= 0:
                moves_state_to_write['partially_available'].add(move.id)
            elif move.procure_method == 'make_to_order' and not move.move_orig_ids:
                moves_state_to_write['waiting'].add(move.id)
            elif move.move_orig_ids and any(orig.state not in ('done', 'cancel') for orig in move.move_orig_ids):
                moves_state_to_write['waiting'].add(move.id)
            else:
                moves_state_to_write['confirmed'].add(move.id)
        for state, moves_ids in moves_state_to_write.items():
            self.browse(moves_ids).filtered(lambda m: m.state != state).state = state

    def _is_consuming(self):
        self.ensure_one()
        from_wh = self.location_id.warehouse_id
        to_wh = self.location_dest_id.warehouse_id
        return self.picking_type_id.code == 'outgoing' or (from_wh and to_wh and from_wh != to_wh)

    def _get_lang(self):
        """Determine language to use for translated description"""
        return self.picking_id.partner_id.lang or self.partner_id.lang or self.env.user.lang

    def _get_source_document(self):
        """ Return the move's document, used by `report.stock.report_product_product_replenishment`
        and must be overrided to add more document type in the report.
        """
        self.ensure_one()
        return self.picking_id or False

    def _get_upstream_documents_and_responsibles(self, visited):
        if self.move_orig_ids and any(m.state not in ('done', 'cancel') for m in self.move_orig_ids):
            result = set()
            visited |= self
            for move in self.move_orig_ids:
                if move.state not in ('done', 'cancel'):
                    for document, responsible, visited in move._get_upstream_documents_and_responsibles(visited):
                        result.add((document, responsible, visited))
            return result
        else:
            return []

    def _set_quantity_done_prepare_vals(self, qty):
        res = []
        for ml in self.move_line_ids:
            ml_qty = ml.reserved_uom_qty - ml.qty_done
            if float_compare(ml_qty, 0, precision_rounding=ml.product_uom_id.rounding) <= 0:
                continue
            # Convert move line qty into move uom
            if ml.product_uom_id != self.product_uom:
                ml_qty = ml.product_uom_id._compute_quantity(ml_qty, self.product_uom, round=False)

            taken_qty = min(qty, ml_qty)
            # Convert taken qty into move line uom
            if ml.product_uom_id != self.product_uom:
                taken_qty = self.product_uom._compute_quantity(ml_qty, ml.product_uom_id, round=False)

            # Assign qty_done and explicitly round to make sure there is no inconsistency between
            # ml.qty_done and qty.
            taken_qty = float_round(taken_qty, precision_rounding=ml.product_uom_id.rounding)
            res.append((1, ml.id, {'qty_done': ml.qty_done + taken_qty}))
            if ml.product_uom_id != self.product_uom:
                taken_qty = ml.product_uom_id._compute_quantity(ml_qty, self.product_uom, round=False)
            qty -= taken_qty

            if float_compare(qty, 0.0, precision_rounding=self.product_uom.rounding) <= 0:
                break

        for ml in self.move_line_ids:
            if float_is_zero(ml.reserved_uom_qty, precision_rounding=ml.product_uom_id.rounding) and float_is_zero(ml.qty_done, precision_rounding=ml.product_uom_id.rounding):
                res.append((2, ml.id))

        if float_compare(qty, 0.0, precision_rounding=self.product_uom.rounding) > 0:
            if self.product_id.tracking != 'serial':
                vals = self._prepare_move_line_vals(quantity=0)
                vals['qty_done'] = qty
                res.append((0, 0, vals))
            else:
                uom_qty = self.product_uom._compute_quantity(qty, self.product_id.uom_id)
                for i in range(0, int(uom_qty)):
                    vals = self._prepare_move_line_vals(quantity=0)
                    vals['qty_done'] = 1
                    vals['product_uom_id'] = self.product_id.uom_id.id
                    res.append((0, 0, vals))
        return res

    def _set_quantity_done(self, qty):
        """
        Set the given quantity as quantity done on the move through the move lines. The method is
        able to handle move lines with a different UoM than the move (but honestly, this would be
        looking for trouble...).
        @param qty: quantity in the UoM of move.product_uom
        """
        existing_smls = self.move_line_ids
        self.move_line_ids = self._set_quantity_done_prepare_vals(qty)
        # `_set_quantity_done_prepare_vals` may return some commands to create new SMLs
        # These new SMLs need to be redirected thanks to putaway rules
        (self.move_line_ids - existing_smls)._apply_putaway_strategy()

    def _set_quantities_to_reservation(self):
        for move in self:
            if move.state not in ('partially_available', 'assigned'):
                continue
            for move_line in move.move_line_ids:
                if move.has_tracking != 'none' and not (move_line.lot_id or move_line.lot_name):
                    continue
                move_line.qty_done = move_line.reserved_uom_qty

    def _clear_quantities_to_zero(self):
        self.filtered(lambda m: m.state in ('partially_available', 'assigned')).move_line_ids.qty_done = 0

    def _adjust_procure_method(self):
        """ This method will try to apply the procure method MTO on some moves if
        a compatible MTO route is found. Else the procure method will be set to MTS
        """
        # Prepare the MTSO variables. They are needed since MTSO moves are handled separately.
        # We need 2 dicts:
        # - needed quantity per location per product
        # - forecasted quantity per location per product
        mtso_products_by_locations = defaultdict(list)
        mtso_needed_qties_by_loc = defaultdict(dict)
        mtso_free_qties_by_loc = {}
        mtso_moves = self.env['stock.move']

        for move in self:
            product_id = move.product_id
            domain = [
                ('location_src_id', '=', move.location_id.id),
                ('location_dest_id', '=', move.location_dest_id.id),
                ('action', '!=', 'push')
            ]
            rules = self.env['procurement.group']._search_rule(False, move.product_packaging_id, product_id, move.warehouse_id, domain)
            if rules:
                if rules.procure_method in ['make_to_order', 'make_to_stock']:
                    move.procure_method = rules.procure_method
                else:
                    # Get the needed quantity for the `mts_else_mto` moves.
                    mtso_needed_qties_by_loc[rules.location_src_id].setdefault(product_id.id, 0)
                    mtso_needed_qties_by_loc[rules.location_src_id][product_id.id] += move.product_qty

                    # This allow us to get the forecasted quantity in batch later on
                    mtso_products_by_locations[rules.location_src_id].append(product_id.id)
                    mtso_moves |= move
            else:
                move.procure_method = 'make_to_stock'

        # Get the forecasted quantity for the `mts_else_mto` moves.
        for location, product_ids in mtso_products_by_locations.items():
            products = self.env['product.product'].browse(product_ids).with_context(location=location.id)
            mtso_free_qties_by_loc[location] = {product.id: product.free_qty for product in products}

        # Now that we have the needed and forecasted quantity per location and per product, we can
        # choose whether the mtso_moves need to be MTO or MTS.
        for move in mtso_moves:
            needed_qty = move.product_qty
            forecasted_qty = mtso_free_qties_by_loc[move.location_id][move.product_id.id]
            if float_compare(needed_qty, forecasted_qty, precision_rounding=move.product_uom.rounding) <= 0:
                move.procure_method = 'make_to_stock'
                mtso_free_qties_by_loc[move.location_id][move.product_id.id] -= needed_qty
            else:
                move.procure_method = 'make_to_order'

    def _show_details_in_draft(self):
        self.ensure_one()
        return self.state != 'draft' or (self.picking_id.immediate_transfer and self.state == 'draft')

    def _trigger_scheduler(self):
        """ Check for auto-triggered orderpoints and trigger them. """
        if not self or self.env['ir.config_parameter'].sudo().get_param('stock.no_auto_scheduler'):
            return

        orderpoints_by_company = defaultdict(lambda: self.env['stock.warehouse.orderpoint'])
        orderpoints_context_by_company = defaultdict(dict)
        for move in self:
            orderpoint = self.env['stock.warehouse.orderpoint'].search([
                ('product_id', '=', move.product_id.id),
                ('trigger', '=', 'auto'),
                ('location_id', 'parent_of', move.location_id.id),
                ('company_id', '=', move.company_id.id),
                '!', ('location_id', 'parent_of', move.location_dest_id.id),
            ], limit=1)
            if orderpoint:
                orderpoints_by_company[orderpoint.company_id] |= orderpoint
            if orderpoint and move.product_qty > orderpoint.product_min_qty and move.origin:
                orderpoints_context_by_company[orderpoint.company_id].setdefault(orderpoint.id, [])
                orderpoints_context_by_company[orderpoint.company_id][orderpoint.id].append(move.origin)
        for company, orderpoints in orderpoints_by_company.items():
            orderpoints.with_context(origins=orderpoints_context_by_company[company])._procure_orderpoint_confirm(
                company_id=company, raise_user_error=False)

    def _trigger_assign(self):
        """ Check for and trigger action_assign for confirmed/partially_available moves related to done moves.
            Disable auto reservation if user configured to do so.
        """
        if not self or self.env['ir.config_parameter'].sudo().get_param('stock.picking_no_auto_reserve'):
            return

        domains = []
        for move in self:
            domains.append([('product_id', '=', move.product_id.id), ('location_id', '=', move.location_dest_id.id)])
        static_domain = [('state', 'in', ['confirmed', 'partially_available']),
                         ('procure_method', '=', 'make_to_stock'),
                         ('reservation_date', '<=', fields.Date.today())]
        moves_to_reserve = self.env['stock.move'].search(expression.AND([static_domain, expression.OR(domains)]),
                                                         order='reservation_date, priority desc, date asc, id asc')
        moves_to_reserve._action_assign()

    def _rollup_move_dests(self, seen):
        for dst in self.move_dest_ids:
            if dst.id not in seen:
                seen.add(dst.id)
                dst._rollup_move_dests(seen)
        return seen

    def _get_forecast_availability_outgoing(self, warehouse):
        """ Get forcasted information (sum_qty_expected, max_date_expected) of self for in_locations_ids as the in locations.
        It differ from _get_report_lines because it computes only the necessary information and return a
        dict by move, which is making faster to use and compute.
        :param qty: ids list/tuple of locations to consider as interne
        :return: a defaultdict of moves in self, values are tuple(sum_qty_expected, max_date_expected)
        :rtype: defaultdict
        """

        def _reconcile_out_with_ins(result, out, ins, demand, product_rounding, only_matching_move_dest=True):
            index_to_remove = []
            for index, in_ in enumerate(ins):
                if float_is_zero(in_['qty'], precision_rounding=product_rounding):
                    index_to_remove.append(index)
                    continue
                if only_matching_move_dest and in_['move_dests'] and out.id not in in_['move_dests']:
                    continue
                taken_from_in = min(demand, in_['qty'])
                demand -= taken_from_in

                if out.id in ids_in_self:
                    result[out] = (result[out][0] + taken_from_in, max(d for d in (in_['move_date'], result[out][1]) if d))

                in_['qty'] -= taken_from_in
                if in_['qty'] <= 0:
                    index_to_remove.append(index)
                if float_is_zero(demand, precision_rounding=product_rounding):
                    break
            for index in reversed(index_to_remove):
                # TODO: avoid this O(n²), maybe we shouldn't "clean" the in list
                del ins[index]
            return demand

        ids_in_self = set(self.ids)
        product_ids = self.product_id
        wh_location_query = self.env['stock.location']._search([('id', 'child_of', warehouse.view_location_id.id)])

        in_domain, out_domain = self.env['report.stock.report_product_product_replenishment']._move_confirmed_domain(
            None, product_ids.ids, wh_location_query
        )
        outs = self.env['stock.move'].search(out_domain, order='reservation_date, priority desc, date, id')
        reserved_outs = self.env['stock.move'].search(
            out_domain + [('state', 'in', ('partially_available', 'assigned'))],
            order='priority desc, date, id')
        ins = self.env['stock.move'].search(in_domain, order='priority desc, date, id')
        # Prefetch data to avoid future request
        (outs - self).read(['product_id', 'product_uom', 'product_qty', 'state'], load=False)  # remove self because data is already fetch
        ins.read(['product_id', 'product_qty', 'date', 'move_dest_ids'], load=False)

        currents = product_ids.with_context(warehouse=warehouse.id)._get_only_qty_available()

        outs_per_product = defaultdict(list)
        reserved_outs_per_product = defaultdict(list)
        ins_per_product = defaultdict(list)
        for out in outs:
            outs_per_product[out.product_id.id].append(out)
        for out in reserved_outs:
            reserved_outs_per_product[out.product_id.id].append(out)
        for in_ in ins:
            ins_per_product[in_.product_id.id].append({
                'qty': in_.product_qty,
                'move_date': in_.date,
                'move_dests': in_._rollup_move_dests(set())
            })

        result = defaultdict(lambda: (0.0, False))
        for product in product_ids:
            product_rounding = product.uom_id.rounding
            for out in reserved_outs_per_product[product.id]:
                # Reconcile with reserved stock.
                current = currents[product.id]
                reserved = out.product_uom._compute_quantity(out.reserved_availability, product.uom_id)
                currents[product.id] -= reserved
                if out.id in ids_in_self:
                    result[out] = (result[out][0] + reserved, False)

            unreconciled_outs = []
            for out in outs_per_product[product.id]:
                # Reconcile with the current stock.
                reserved = 0.0
                if out.state in ('partially_available', 'assigned'):
                    reserved = out.product_uom._compute_quantity(out.reserved_availability, product.uom_id)
                demand = out.product_qty - reserved

                if float_is_zero(demand, precision_rounding=product_rounding):
                    continue
                current = currents[product.id]
                taken_from_stock = min(demand, current)
                if not float_is_zero(taken_from_stock, precision_rounding=product_rounding):
                    currents[product.id] -= taken_from_stock
                    demand -= taken_from_stock
                    if out.id in ids_in_self:
                        result[out] = (result[out][0] + taken_from_stock, False)

                # Reconcile with the ins.
                # The while loop will finish because it will pop from ins_per_product or decrease the demand until zero
                if not float_is_zero(demand, precision_rounding=product_rounding):
                    demand = _reconcile_out_with_ins(result, out, ins_per_product[product.id], demand, product_rounding, only_matching_move_dest=True)
                if not float_is_zero(demand, precision_rounding=product_rounding):
                    unreconciled_outs.append((demand, out))

            for demand, out in unreconciled_outs:
                remaining = _reconcile_out_with_ins(result, out, ins_per_product[product.id], demand, product_rounding, only_matching_move_dest=False)
                if not float_is_zero(remaining, precision_rounding=out.product_id.uom_id.rounding) and out not in result:
                    result[out] = (-remaining, False)

        return result

    def action_open_reference(self):
        """ Open the form view of the move's reference document, if one exists, otherwise open form view of self
        """
        self.ensure_one()
        source = self.picking_id
        if source and source.check_access_rights('read', raise_exception=False):
            return {
                'res_model': source._name,
                'type': 'ir.actions.act_window',
                'views': [[False, "form"]],
                'res_id': source.id,
            }
        return {
            'res_model': self._name,
            'type': 'ir.actions.act_window',
            'views': [[False, "form"]],
            'res_id': self.id,
        }
