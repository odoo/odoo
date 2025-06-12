# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from collections import defaultdict
from datetime import timedelta
from operator import itemgetter
from re import findall as regex_findall

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError, ValidationError
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
        help="In case of outgoing flow, validate the transfer before this date to allow to deliver at promised date to the customer.\n\
        In case of incoming flow, validate the transfer before this date in order to have these products in stock at the date promised by the supplier")
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company,
        index=True, required=True)
    product_id = fields.Many2one(
        'product.product', 'Product',
        check_company=True,
        domain="[('type', '=', 'consu')]", index=True, required=True)
    never_product_template_attribute_value_ids = fields.Many2many(
        'product.template.attribute.value',
        'template_attribute_value_stock_move_rel',
        'move_id', 'template_attribute_value_id',
        string="Never attribute Values"
    )
    description_picking = fields.Text('Description of Picking')
    product_qty = fields.Float(
        'Real Quantity', compute='_compute_product_qty', inverse='_set_product_qty',
        digits=0, store=True, compute_sudo=True,
        help='Quantity in the default UoM of the product')
    product_uom_qty = fields.Float(
        'Demand',
        digits='Product Unit of Measure',
        default=0, required=True,
        help="This is the quantity of product that is planned to be moved."
             "Lowering this quantity does not generate a backorder."
             "Changing this quantity on assigned moves affects "
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
        help='The operation takes and suggests products from this location.',
        auto_join=True, index=True, required=True,
        compute='_compute_location_id', store=True, precompute=True, readonly=False,
        check_company=True)
    location_dest_id = fields.Many2one(
        'stock.location', 'Intermediate Location', required=True,
        help='The operations brings product to this location', readonly=False,
        index=True, store=True, compute='_compute_location_dest_id', precompute=True, inverse='_set_location_dest_id')
    location_final_id = fields.Many2one(
        'stock.location', 'Final Location',
        readonly=False, store=True,
        help="The operation brings the products to the intermediate location."
        "But this operation is part of a chain of operations targeting the final location.",
        auto_join=True, index=True, check_company=True)
    location_usage = fields.Selection(string="Source Location Type", related='location_id.usage')
    location_dest_usage = fields.Selection(string="Destination Location Type", related='location_dest_id.usage')
    partner_id = fields.Many2one(
        'res.partner', 'Destination Address ',
        help="Optional address where goods are to be delivered, specifically used for allotment",
        compute='_compute_partner_id', store=True, readonly=False,
        index='btree_not_null')
    move_dest_ids = fields.Many2many(
        'stock.move', 'stock_move_move_rel', 'move_orig_id', 'move_dest_id', 'Destination Moves',
        copy=False,
        help="Optional: next stock move when chaining them")
    move_orig_ids = fields.Many2many(
        'stock.move', 'stock_move_move_rel', 'move_dest_id', 'move_orig_id', 'Original Move',
        copy=False,
        help="Optional: previous stock move when chaining them")
    picking_id = fields.Many2one('stock.picking', 'Transfer', index=True, check_company=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('waiting', 'Waiting Another Move'),
        ('confirmed', 'Waiting Availability'),
        ('partially_available', 'Partially Available'),
        ('assigned', 'Available'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='Status',
        copy=False, default='draft', index=True, readonly=True,
        help="* New: The stock move is created but not confirmed.\n"
             "* Waiting Another Move: A linked stock move should be done before this one.\n"
             "* Waiting Availability: The stock move is confirmed but the product can't be reserved.\n"
             "* Available: The product of the stock move is reserved.\n"
             "* Done: The product has been transferred and the transfer has been confirmed.")
    picked = fields.Boolean(
        'Picked', compute='_compute_picked', inverse='_inverse_picked',
        store=True, readonly=False, copy=False, default=False,
        help="This checkbox is just indicative, it doesn't validate or generate any product moves.")

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
    scrap_id = fields.Many2one('stock.scrap', 'Scrap operation', readonly=True, check_company=True)
    group_id = fields.Many2one('procurement.group', 'Procurement Group', default=_default_group_id, index=True)
    rule_id = fields.Many2one(
        'stock.rule', 'Stock Rule', ondelete='restrict', help='The stock rule that created this stock move',
        check_company=True)
    propagate_cancel = fields.Boolean(
        'Propagate cancel and split', default=True,
        help='If checked, when this move is cancelled, cancel the linked move too')
    delay_alert_date = fields.Datetime('Delay Alert Date', help='Process at this date to be on time', compute="_compute_delay_alert_date", store=True)
    picking_type_id = fields.Many2one('stock.picking.type', 'Operation Type', compute='_compute_picking_type_id', store=True, readonly=False, check_company=True)
    is_inventory = fields.Boolean('Inventory')
    move_line_ids = fields.One2many('stock.move.line', 'move_id')
    origin_returned_move_id = fields.Many2one(
        'stock.move', 'Origin return move', copy=False, index=True,
        help='Move that created the return move', check_company=True)
    returned_move_ids = fields.One2many('stock.move', 'origin_returned_move_id', 'All returned moves', help='Optional: all returned moves created from this move')
    availability = fields.Float(
        'Forecasted Quantity', compute='_compute_product_availability',
        readonly=True, help='Quantity in stock that can still be reserved for this move')
    # used to depict a restriction on the ownership of quants to consider when marking this move as 'done'
    restrict_partner_id = fields.Many2one(
        'res.partner', 'Owner ', check_company=True,
        index='btree_not_null')
    route_ids = fields.Many2many(
        'stock.route', 'stock_route_move', 'move_id', 'route_id', 'Destination route', help="Preferred route")
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', help="the warehouse to consider for the route selection on the next procurement (if any).")
    has_tracking = fields.Selection(related='product_id.tracking', string='Product with Tracking')
    quantity = fields.Float(
        'Quantity', compute='_compute_quantity', digits='Product Unit of Measure', inverse='_set_quantity', store=True)
    # TODO: delete this field `show_operations`
    show_operations = fields.Boolean(related='picking_id.picking_type_id.show_operations')
    picking_code = fields.Selection(related='picking_id.picking_type_id.code', readonly=True)
    show_details_visible = fields.Boolean('Details Visible', compute='_compute_show_details_visible')
    is_storable = fields.Boolean(related='product_id.is_storable')
    additional = fields.Boolean("Whether the move was added after the picking's confirmation", default=False)
    is_locked = fields.Boolean(compute='_compute_is_locked', readonly=True)
    is_initial_demand_editable = fields.Boolean('Is initial demand editable', compute='_compute_is_initial_demand_editable')
    is_quantity_done_editable = fields.Boolean('Is quantity done editable', compute='_compute_is_quantity_done_editable')
    reference = fields.Char(compute='_compute_reference', string="Reference", store=True)
    move_lines_count = fields.Integer(compute='_compute_move_lines_count')
    package_level_id = fields.Many2one('stock.package_level', 'Package Level', check_company=True, copy=False)
    picking_type_entire_packs = fields.Boolean(related='picking_type_id.show_entire_packs', readonly=True)
    display_assign_serial = fields.Boolean(compute='_compute_display_assign_serial')
    display_import_lot = fields.Boolean(compute='_compute_display_assign_serial')
    next_serial = fields.Char('First SN/Lot')
    next_serial_count = fields.Integer('Number of SN/Lots')
    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint', 'Original Reordering Rule', index=True)
    forecast_availability = fields.Float('Forecast Availability', compute='_compute_forecast_information', digits='Product Unit of Measure', compute_sudo=True)
    forecast_expected_date = fields.Datetime('Forecasted Expected date', compute='_compute_forecast_information', compute_sudo=True)
    lot_ids = fields.Many2many('stock.lot', compute='_compute_lot_ids', inverse='_set_lot_ids', string='Serial Numbers', readonly=False)
    reservation_date = fields.Date('Date to Reserve', compute='_compute_reservation_date', store=True, help="Computes when a move should be reserved")
    product_packaging_id = fields.Many2one('product.packaging', 'Packaging', domain="[('product_id', '=', product_id)]", check_company=True)
    product_packaging_qty = fields.Float(string="Reserved Packaging Quantity", compute='_compute_product_packaging_qty')
    product_packaging_quantity = fields.Float(
        string="Done Packaging Quantity", compute='_compute_product_packaging_quantity')
    show_quant = fields.Boolean("Show Quant", compute="_compute_show_info")
    show_lots_m2o = fields.Boolean("Show lot_id", compute="_compute_show_info")
    show_lots_text = fields.Boolean("Show lot_name", compute="_compute_show_info")

    @api.depends('product_id')
    def _compute_product_uom(self):
        for move in self:
            move.product_uom = move.product_id.uom_id.id

    @api.depends('picking_id.location_id')
    def _compute_location_id(self):
        for move in self:
            if move.picked:
                continue
            if not (location := move.location_id) or move.picking_id != move._origin.picking_id or move.picking_type_id != move._origin.picking_type_id:
                if move.picking_id:
                    location = move.picking_id.location_id
                elif move.picking_type_id:
                    location = move.picking_type_id.default_location_src_id
            move.location_id = location

    @api.depends('picking_id.location_dest_id')
    def _compute_location_dest_id(self):
        for move in self:
            location_dest = False
            if move.picking_id:
                location_dest = move.picking_id.location_dest_id
            elif move.picking_type_id:
                location_dest = move.picking_type_id.default_location_dest_id
            is_move_to_interco_transit = False
            if self.env.user.has_group('base.group_multi_company') and location_dest:
                customer_loc, __ = self.env['stock.warehouse']._get_partner_locations()
                inter_comp_location = self.env.ref('stock.stock_location_inter_company', raise_if_not_found=False)
                is_move_to_interco_transit = location_dest._child_of(customer_loc) and move.location_final_id == inter_comp_location
            if location_dest and move.location_final_id and (move.location_final_id._child_of(location_dest) or is_move_to_interco_transit):
                # Force the location_final as dest in the following cases:
                # - The location_final is a sublocation of destination -> Means we reached the end
                # - The location dest is an out location (i.e. Customers) but the final dest is different (e.g. Inter-Company transfers)
                location_dest = move.location_final_id
            move.location_dest_id = location_dest

    def _set_location_dest_id(self):
        for ml in self.move_line_ids:
            parent_path = [int(loc_id) for loc_id in ml.location_dest_id.parent_path.split('/')[:-1]]
            if ml.move_id.location_dest_id.id in parent_path:
                continue
            loc_dest = ml.move_id.location_dest_id._get_putaway_strategy(ml.product_id, ml.quantity_product_uom)
            ml.location_dest_id = loc_dest

    @api.depends('has_tracking', 'picking_type_id.use_create_lots', 'picking_type_id.use_existing_lots', 'product_id')
    def _compute_display_assign_serial(self):
        for move in self:
            move.display_import_lot = (
                move.has_tracking != 'none' and
                move.product_id and
                move.picking_type_id.use_create_lots and
                not move.origin_returned_move_id.id and
                move.state not in ('done', 'cancel')
            )
            move.display_assign_serial = move.display_import_lot

    @api.depends('move_line_ids.picked', 'state')
    def _compute_picked(self):
        for move in self:
            if move.state == 'done' or any(ml.picked for ml in move.move_line_ids):
                move.picked = True
            elif move.move_line_ids:
                move.picked = False

    def _inverse_picked(self):
        for move in self:
            move.move_line_ids.picked = move.picked

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
        has_package = self.env.user.has_group('stock.group_tracking_lot')
        multi_locations_enabled = self.env.user.has_group('stock.group_stock_multi_locations')
        consignment_enabled = self.env.user.has_group('stock.group_tracking_owner')

        show_details_visible = multi_locations_enabled or has_package or consignment_enabled

        for move in self:
            if not move.product_id:
                move.show_details_visible = False
            elif not move.picking_type_id.use_create_lots and not move.picking_type_id.use_existing_lots\
                and not self.env.user.has_group('stock.group_stock_tracking_lot')\
                and not self.env.user.has_group('stock.group_stock_multi_locations'):
                move.show_details_visible = False
            elif len(move.move_line_ids) > 1:
                move.show_details_visible = True
            else:
                move.show_details_visible = show_details_visible or move.has_tracking != 'none'

    @api.depends('state', 'picking_id.is_locked')
    def _compute_is_initial_demand_editable(self):
        for move in self:
            move.is_initial_demand_editable = not move.picking_id.is_locked or move.state == 'draft'

    @api.depends('product_id')
    def _compute_is_quantity_done_editable(self):
        for move in self:
            move.is_quantity_done_editable = move.product_id

    @api.depends('picking_id', 'name', 'picking_id.name')
    def _compute_reference(self):
        for move in self:
            move.reference = move.picking_id.name if move.picking_id else move.name

    @api.depends('move_line_ids')
    def _compute_move_lines_count(self):
        for move in self:
            move.move_lines_count = len(move.move_line_ids)

    @api.depends('product_id', 'product_uom', 'product_uom_qty', 'state')
    def _compute_product_qty(self):
        for move in self:
            move.product_qty = move.product_uom._compute_quantity(
                move.product_uom_qty, move.product_id.uom_id, rounding_method='HALF-UP')

    @api.depends('picking_id.partner_id')
    def _compute_partner_id(self):
        for move in self.filtered(lambda m: m.picking_id):
            move.partner_id = move.picking_id.partner_id

    @api.depends('product_packaging_id', 'product_uom', 'product_qty')
    def _compute_product_packaging_qty(self):
        self.product_packaging_qty = False
        for move in self:
            if not move.product_packaging_id:
                continue
            move.product_packaging_qty = move.product_packaging_id._compute_qty(move.product_qty)

    @api.depends('product_packaging_id', 'product_uom', 'quantity')
    def _compute_product_packaging_quantity(self):
        self.product_packaging_quantity = False
        for move in self:
            if not move.product_packaging_id:
                continue
            move.product_packaging_quantity = move.product_packaging_id._compute_qty(move.quantity, move.product_uom)

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

    def _quantity_sml(self):
        self.ensure_one()
        quantity = 0
        for move_line in self.move_line_ids:
            quantity += move_line.product_uom_id._compute_quantity(move_line.quantity, self.product_uom, round=False)
        return quantity

    @api.depends('move_line_ids.quantity', 'move_line_ids.product_uom_id')
    def _compute_quantity(self):
        """ This field represents the sum of the move lines `quantity`. It allows the user to know
        if there is still work to do.

        We take care of rounding this value at the general decimal precision and not the rounding
        of the move's UOM to make sure this value is really close to the real sum, because this
        field will be used in `_action_done` in order to know if the move will need a backorder or
        an extra move.
        """
        if not any(self._ids):
            # onchange
            for move in self:
                move.quantity = move._quantity_sml()
        else:
            # compute
            move_lines_ids = set()
            for move in self:
                move_lines_ids |= set(move.move_line_ids.ids)

            data = self.env['stock.move.line']._read_group(
                [('id', 'in', list(move_lines_ids))],
                ['move_id', 'product_uom_id'], ['quantity:sum']
            )
            sum_qty = defaultdict(float)
            for move, product_uom, qty_sum in data:
                uom = move.product_uom
                sum_qty[move.id] += product_uom._compute_quantity(qty_sum, uom, round=False)

            for move in self:
                move.quantity = sum_qty[move.id]

    def _set_quantity(self):
        def _process_decrease(move, quantity):
            mls_to_unlink = set()
            # Since the move lines might have been created in a certain order to respect
            # a removal strategy, they need to be unreserved in the opposite order
            for ml in reversed(move.move_line_ids.sorted('id')):
                if self.env.context.get('unreserve_unpicked_only') and ml.picked:
                    continue
                if float_is_zero(quantity, precision_rounding=move.product_uom.rounding):
                    break
                qty_ml_dec = min(ml.quantity, ml.product_uom_id._compute_quantity(quantity, ml.product_uom_id, round=False))
                if float_is_zero(qty_ml_dec, precision_rounding=ml.product_uom_id.rounding):
                    continue
                if float_compare(ml.quantity, qty_ml_dec, precision_rounding=ml.product_uom_id.rounding) == 0 and ml.state not in ['done', 'cancel']:
                    mls_to_unlink.add(ml.id)
                else:
                    ml.quantity -= qty_ml_dec
                quantity -= move.product_uom._compute_quantity(qty_ml_dec, move.product_uom, round=False)
            self.env['stock.move.line'].browse(mls_to_unlink).unlink()

        def _process_increase(move, quantity):
            # move._action_assign(quantity)
            move._set_quantity_done(move.quantity)

        err = []
        for move in self:
            uom_qty = float_round(move.quantity, precision_rounding=move.product_uom.rounding, rounding_method='HALF-UP')
            precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            qty = float_round(move.quantity, precision_digits=precision_digits, rounding_method='HALF-UP')
            if float_compare(uom_qty, qty, precision_digits=precision_digits) != 0:
                err.append(_("""
The quantity done for the product %(product)s doesn't respect the rounding precision defined on the unit of measure %(unit)s.
Please change the quantity done or the rounding precision of your unit of measure.""",
                             product=move.product_id.display_name, unit=move.product_uom.display_name))
                continue
            delta_qty = move.quantity - move._quantity_sml()
            if float_compare(delta_qty, 0, precision_rounding=move.product_uom.rounding) > 0:
                _process_increase(move, delta_qty)
            elif float_compare(delta_qty, 0, precision_rounding=move.product_uom.rounding) < 0:
                _process_decrease(move, abs(delta_qty))
        if err:
            raise UserError('\n'.join(err))

    def _set_product_qty(self):
        """ The meaning of product_qty field changed lately and is now a functional field computing the quantity
        in the default product UoM. This code has been added to raise an error if a write is made given a value
        for `product_qty`, where the same write should set the `product_uom_qty` field instead, in order to
        detect errors. """
        raise UserError(_('The requested operation cannot be processed because of a programming error setting the `product_qty` field instead of the `product_uom_qty`.'))

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

    @api.depends('product_id', 'product_qty', 'picking_type_id', 'quantity', 'priority', 'state', 'product_uom_qty', 'location_id')
    def _compute_forecast_information(self):
        """ Compute forecasted information of the related product by warehouse."""
        self.forecast_availability = False
        self.forecast_expected_date = False

        # Prefetch product info to avoid fetching all product fields
        self.product_id.fetch(['type', 'uom_id'])

        not_product_moves = self.filtered(lambda move: not move.product_id.is_storable)
        for move in not_product_moves:
            move.forecast_availability = move.product_qty

        product_moves = (self - not_product_moves)

        outgoing_unreserved_moves_per_warehouse = defaultdict(set)
        now = fields.Datetime.now()

        def key_virtual_available(move, incoming=False):
            warehouse_id = move.location_dest_id.warehouse_id.id if incoming else move.location_id.warehouse_id.id
            return warehouse_id, max(move.date or now, now)

        # Prefetch efficiently virtual_available for _is_consuming draft move.
        prefetch_virtual_available = defaultdict(set)
        virtual_available_dict = {}
        for move in product_moves:
            if move._is_consuming() and move.state == 'draft':
                prefetch_virtual_available[key_virtual_available(move)].add(move.product_id.id)
            elif move.picking_type_id.code == 'incoming':
                prefetch_virtual_available[key_virtual_available(move, incoming=True)].add(move.product_id.id)
        for key_context, product_ids in prefetch_virtual_available.items():
            read_res = self.env['product.product'].browse(product_ids).with_context(warehouse_id=key_context[0], to_date=key_context[1]).read(['virtual_available'])
            virtual_available_dict[key_context] = {res['id']: res['virtual_available'] for res in read_res}

        for move in product_moves:
            if move._is_consuming():
                if move.state == 'assigned':
                    move.forecast_availability = move.product_uom._compute_quantity(
                        move.quantity, move.product_id.uom_id, rounding_method='HALF-UP')
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
            moves_per_location = defaultdict(lambda: self.env['stock.move'])
            for move in moves:
                moves_per_location[move.location_id] |= move
            for location, mvs in moves_per_location.items():
                forecast_info = mvs._get_forecast_availability_outgoing(warehouse, location)
                for move in mvs:
                    move.forecast_availability, move.forecast_expected_date = forecast_info[move]

    def _get_moves_to_propagate_date_deadline(self):
        self.ensure_one()
        return self.move_dest_ids | self.move_orig_ids

    def _set_date_deadline(self, new_deadline):
        # Handle the propagation of `date_deadline` fields (up and down stream - only update by up/downstream documents)
        already_propagate_ids = self.env.context.get('date_deadline_propagate_ids', set())
        already_propagate_ids.update(self.ids)
        self = self.with_context(date_deadline_propagate_ids=already_propagate_ids)
        for move in self:
            moves_to_update = move._get_moves_to_propagate_date_deadline()
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

    @api.depends('move_line_ids.lot_id', 'move_line_ids.quantity')
    def _compute_lot_ids(self):
        domain = [('move_id', 'in', self.ids), ('lot_id', '!=', False), ('quantity', '!=', 0.0)]
        lots_by_move_id = self.env['stock.move.line']._read_group(
            domain,
            ['move_id'], ['lot_id:array_agg'],
        )
        lots_by_move_id = {move.id: lot_ids for move, lot_ids in lots_by_move_id}
        for move in self:
            move.lot_ids = lots_by_move_id.get(move._origin.id, [])

    def _set_lot_ids(self):
        for move in self:
            if move.product_id.tracking != 'serial':
                continue
            move_lines_commands = []
            mls = move.move_line_ids
            mls_with_lots = mls.filtered(lambda ml: ml.lot_id)
            mls_without_lots = (mls - mls_with_lots)
            for ml in mls_with_lots:
                if ml.quantity and ml.lot_id not in move.lot_ids:
                    move_lines_commands.append((2, ml.id))
            ls = move.move_line_ids.lot_id
            for lot in move.lot_ids:
                if lot not in ls:
                    if mls_without_lots[:1]:  # Updates an existing line without serial number.
                        move_line = mls_without_lots[:1]
                        move_lines_commands.append(Command.update(move_line.id, {
                            'lot_name': lot.name,
                            'lot_id': lot.id,
                            'product_uom_id': move.product_id.uom_id.id,
                            'quantity': 1,
                        }))
                        mls_without_lots -= move_line
                    else:  # No line without serial number, creates a new one.
                        reserved_quants = self.env['stock.quant']._get_reserve_quantity(move.product_id, move.location_id, 1.0, lot_id=lot)
                        if reserved_quants:
                            move_line_vals = self._prepare_move_line_vals(quantity=0, reserved_quant=reserved_quants[0][0])
                        else:
                            move_line_vals = self._prepare_move_line_vals(quantity=0)
                            move_line_vals['lot_id'] = lot.id
                            move_line_vals['lot_name'] = lot.name
                        move_line_vals['product_uom_id'] = move.product_id.uom_id.id
                        move_line_vals['quantity'] = 1
                        move_lines_commands.append((0, 0, move_line_vals))
                else:
                    move_line = move.move_line_ids.filtered(lambda line: line.lot_id.id == lot.id)
                    move_line.quantity = 1
            move.write({'move_line_ids': move_lines_commands})

    @api.depends('picking_type_id', 'date', 'priority', 'state')
    def _compute_reservation_date(self):
        for move in self:
            if move.picking_type_id.reservation_method == 'by_date' and move.state in ['draft', 'confirmed', 'waiting', 'partially_available']:
                days = move.picking_type_id.reservation_days_before
                if move.priority == '1':
                    days = move.picking_type_id.reservation_days_before_priority
                move.reservation_date = fields.Date.to_date(move.date) - timedelta(days=days)
            elif move.picking_type_id.reservation_method == 'manual':
                move.reservation_date = False

    @api.depends(
        'has_tracking',
        'picking_type_id.use_create_lots',
        'picking_type_id.use_existing_lots',
        'state',
        'origin_returned_move_id',
        'product_id.type',
        'picking_code',
    )
    def _compute_show_info(self):
        for move in self:
            move.show_quant = move.picking_code != 'incoming'\
                           and move.product_id.is_storable
            move.show_lots_text = move.has_tracking != 'none'\
                and move.picking_type_id.use_create_lots\
                and not move.picking_type_id.use_existing_lots\
                and move.state != 'done' \
                and not move.origin_returned_move_id.id
            move.show_lots_m2o = not move.show_quant\
                and not move.show_lots_text\
                and move.has_tracking != 'none'\
                and (move.picking_type_id.use_existing_lots or move.state == 'done' or move.origin_returned_move_id.id)

    @api.constrains('product_uom')
    def _check_uom(self):
        moves_error = self.filtered(lambda move: move.product_id.uom_id.category_id != move.product_uom.category_id)
        if moves_error:
            user_warnings = [
                _('You cannot perform moves because their unit of measure has a different category from their product unit of measure.'),
                *(
                    _('%(product_name)s --> Product UoM is %(product_uom)s (%(product_uom_category)s) - Move UoM is %(move_uom)s (%(move_uom_category)s)',
                      product_name=move.product_id.display_name,
                      product_uom=move.product_id.uom_id.name,
                      product_uom_category=move.product_id.uom_id.category_id.name,
                      move_uom=move.product_uom.name,
                      move_uom_category=move.product_uom.category_id.name)
                    for move in moves_error
                ),
                _('Blocking: %s', ' ,'.join(moves_error.mapped('name')))
            ]
            raise UserError('\n\n'.join(user_warnings))

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
                defaults['additional'] = True
            elif picking_id.state not in ['cancel', 'draft', 'done']:
                defaults['additional'] = True  # to trigger `_autoconfirm_picking`
        return defaults

    @api.depends('picking_id', 'product_id', 'location_id', 'location_dest_id')
    def _compute_display_name(self):
        for move in self:
            move.display_name = '%s%s%s>%s' % (
                move.picking_id.origin and '%s/' % move.picking_id.origin or '',
                move.product_id.code and '%s: ' % move.product_id.code or '',
                move.location_id.name, move.location_dest_id.name)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if (vals.get('quantity') or vals.get('move_line_ids')) and 'lot_ids' in vals:
                vals.pop('lot_ids')
            picking_id = self.env['stock.picking'].browse(vals.get('picking_id'))
            if picking_id.group_id and 'group_id' not in vals:
                vals['group_id'] = picking_id.group_id.id
            if picking_id.state == 'done' and vals.get('state') != 'done':
                vals['state'] = 'done'
            if vals.get('state') == 'done':
                vals['picked'] = True
        return super().create(vals_list)

    def write(self, vals):
        # Handle the write on the initial demand by updating the reserved quantity and logging
        # messages according to the state of the stock.move records.
        receipt_moves_to_reassign = self.env['stock.move']
        move_to_recompute_state = self.env['stock.move']
        move_to_check_location = self.env['stock.move']
        if 'quantity' in vals:
            if any(move.state == 'cancel' for move in self):
                raise UserError(_('You cannot change a cancelled stock move, create a new line instead.'))
        if 'product_uom' in vals and any(move.state == 'done' for move in self):
            raise UserError(_('You cannot change the UoM for a stock move that has been set to \'Done\'.'))
        if 'product_uom_qty' in vals:
            for move in self.filtered(lambda m: m.state not in ('done', 'draft') and m.picking_id):
                if float_compare(vals['product_uom_qty'], move.product_uom_qty, precision_rounding=move.product_uom.rounding):
                    self.env['stock.move.line']._log_message(move.picking_id, move, 'stock.track_move_template', vals)
            if self.env.context.get('do_not_unreserve') is None:
                move_to_unreserve = self.filtered(
                    lambda m: m.state not in ['draft', 'done', 'cancel'] and float_compare(m.quantity, vals.get('product_uom_qty'), precision_rounding=m.product_uom.rounding) == 1
                )
                move_to_unreserve._do_unreserve()
                (self - move_to_unreserve).filtered(lambda m: m.state == 'assigned').write({'state': 'partially_available'})
                # When editing the initial demand, directly run again action assign on receipt moves.
                receipt_moves_to_reassign |= move_to_unreserve.filtered(lambda m: m.location_id.usage == 'supplier')
                receipt_moves_to_reassign |= (self - move_to_unreserve).filtered(
                    lambda m:
                        m.location_id.usage == 'supplier' and
                        m.state in ('partially_available', 'assigned')
                )
                move_to_recompute_state |= self - move_to_unreserve - receipt_moves_to_reassign
        # propagate product_packaging_id changes in the stock move chain
        if 'product_packaging_id' in vals:
            self._propagate_product_packaging(vals['product_packaging_id'])
        if 'date_deadline' in vals:
            self._set_date_deadline(vals.get('date_deadline'))
        if 'move_orig_ids' in vals:
            move_to_recompute_state |= self.filtered(lambda m: m.state not in ['draft', 'cancel', 'done'])
        if 'location_id' in vals:
            move_to_check_location = self.filtered(lambda m: m.location_id.id != vals.get('location_id'))
        if 'picking_id' in vals and 'group_id' not in vals:
            picking = self.env['stock.picking'].browse(vals['picking_id'])
            if picking.group_id:
                vals['group_id'] = picking.group_id.id
        res = super(StockMove, self).write(vals)
        if move_to_recompute_state:
            move_to_recompute_state._recompute_state()
        if move_to_check_location:
            for ml in move_to_check_location.move_line_ids:
                parent_path = [int(loc_id) for loc_id in ml.location_id.parent_path.split('/')[:-1]]
                if move_to_check_location.location_id.id not in parent_path:
                    receipt_moves_to_reassign |= move_to_check_location
                    move_to_check_location.procure_method = 'make_to_stock'
                    move_to_check_location.move_orig_ids = [Command.clear()]
                    ml.unlink()
        if 'location_id' in vals or 'location_dest_id' in vals:
            wh_by_moves = defaultdict(self.env['stock.move'].browse)
            for move in self:
                move_warehouse = move.location_id.warehouse_id or move.location_dest_id.warehouse_id
                if move_warehouse == move.warehouse_id:
                    continue
                wh_by_moves[move_warehouse] |= move
            for warehouse, moves in wh_by_moves.items():
                moves.warehouse_id = warehouse.id
        if receipt_moves_to_reassign:
            receipt_moves_to_reassign._action_assign()
        return res

    def _propagate_product_packaging(self, product_package_id):
        """
        Propagate the product_packaging_id of a move to its destination and origin.
        If there is a bifurcation in the chain we do not propagate the package.
        """
        already_propagated_ids = self.env.context.get('product_packaging_propagation_ids', set()) | set(self.ids)
        self = self.with_context(product_packaging_propagation_ids=already_propagated_ids)
        for move in self:
            # propagate on destination move
            for move_dest in move.move_dest_ids:
                if move_dest.id not in already_propagated_ids and \
                        move_dest.state not in ['cancel', 'done'] and \
                        move_dest.product_packaging_id.id != product_package_id and \
                        move_dest.move_orig_ids == move:  # checks that you are the only parent move of your destination
                    move_dest.product_packaging_id = product_package_id
            # propagate on origin move
            for move_orig in move.move_orig_ids:
                if move_orig.id not in already_propagated_ids and \
                        move_orig.state not in ['cancel', 'done'] and \
                        move_orig.product_packaging_id.id != product_package_id and \
                        move_orig.move_dest_ids == move:  # checks that you are the only child move of your origin
                    move_orig.product_packaging_id = product_package_id

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
        view = self.env.ref('stock.view_stock_move_operations')

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
            ),
        }

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
            action['context']['warehouse_id'] = warehouse.id
        return action

    def _do_unreserve(self):
        moves_to_unreserve = OrderedSet()
        for move in self:
            if move.state == 'cancel' or (move.state == 'done' and move.scrapped) or move.picked:
                # We may have cancelled move in an open picking in a "propagate_cancel" scenario.
                # We may have done move in an open picking in a scrap scenario.
                continue
            elif move.state == 'done':
                raise UserError(_("You cannot unreserve a stock move that has been set to 'Done'."))
            moves_to_unreserve.add(move.id)
        moves_to_unreserve = self.env['stock.move'].browse(moves_to_unreserve)

        ml_to_unlink = OrderedSet()
        moves_not_to_recompute = OrderedSet()
        for ml in moves_to_unreserve.move_line_ids:
            if ml.picked:
                moves_not_to_recompute.add(ml.move_id.id)
                continue
            ml_to_unlink.add(ml.id)
        ml_to_unlink = self.env['stock.move.line'].browse(ml_to_unlink)
        moves_not_to_recompute = self.env['stock.move'].browse(moves_not_to_recompute)

        ml_to_unlink.unlink()
        # `write` on `stock.move.line` doesn't call `_recompute_state` (unlike to `unlink`),
        # so it must be called for each move where no move line has been deleted.
        (moves_to_unreserve - moves_not_to_recompute)._recompute_state()
        return True

    def _generate_serial_numbers(self, next_serial, next_serial_count=False, location_id=False):
        """ This method will generate `lot_name` from a string (field
        `next_serial`) and create a move line for each generated `lot_name`.
        """
        self.ensure_one()
        if not location_id:
            location_id = self.location_dest_id
        count = next_serial_count or self.next_serial_count
        if not count:
            raise ValidationError(_("The number of Serial Numbers to generate must be greater than zero."))
        lot_names = self.env['stock.lot'].generate_lot_names(next_serial, count)
        field_data = [{'lot_name': lot_name['lot_name'], 'quantity': 1} for lot_name in lot_names]
        if self.picking_type_id.use_existing_lots:
            self._create_lot_ids_from_move_line_vals(field_data, self.product_id.id, self.company_id.id)
        move_lines_commands = self._generate_serial_move_line_commands(field_data)
        self.move_line_ids = move_lines_commands
        return True

    def _create_lot_ids_from_move_line_vals(self, vals_list, product_id, company_id=False):
        """ This method will search or create the lot_id from the lot_name and set it in the vals_list
        """
        lot_names = {vals['lot_name'] for vals in vals_list if vals.get('lot_name')}
        lot_ids = self.env['stock.lot'].search([
            ('product_id', '=', product_id),
            '|', ('company_id', '=', company_id), ('company_id', '=', False),
            ('name', 'in', list(lot_names)),
        ])

        lot_names -= set(lot_ids.mapped('name'))  # lot_names not found to create
        lots_to_create_vals = [
            {'product_id': product_id, 'name': lot_name}
            for lot_name in lot_names
        ]
        lot_ids |= self.env['stock.lot'].create(lots_to_create_vals)

        lot_id_by_name = {lot.name: lot.id for lot in lot_ids}
        for vals in vals_list:
            lot_name = vals.get('lot_name', None)
            if not lot_name:
                continue
            vals['lot_id'] = lot_id_by_name[lot_name]
            vals['lot_name'] = False

    @api.model
    def split_lots(self, lots):
        breaking_char = '\n'
        separation_char = '\t'
        options = False

        if not lots:
            return []  # Skip if the `lot_name` doesn't contain multiple values.

        # Checks the lines and prepares the move lines' values.
        split_lines = lots.split(breaking_char)
        split_lines = list(filter(None, split_lines))
        move_lines_vals = []
        for lot_text in split_lines:
            move_line_vals = {
                'lot_name': lot_text,
                'quantity': 1,
            }
            # Semicolons are also used for separation but for convenience we
            # replace them to work only with tabs.
            lot_text_parts = lot_text.replace(';', separation_char).split(separation_char)
            options = options or self._get_formating_options(lot_text_parts[1:])
            for extra_string in lot_text_parts[1:]:
                field_data = self._convert_string_into_field_data(extra_string, options)
                if field_data:
                    lot_text = lot_text_parts[0]
                    if field_data == "ignore":
                        # Got an unusable data for this move, updates only the lot_name part.
                        move_line_vals.update(lot_name=lot_text)
                    else:
                        move_line_vals.update(**field_data, lot_name=lot_text)
                else:
                    # At least this part of the string is erronous and can't be converted,
                    # don't try to guess and simply use the full string as the lot name.
                    move_line_vals['lot_name'] = lot_text
                    break
            move_lines_vals.append(move_line_vals)
        return move_lines_vals

    @api.model
    def action_generate_lot_line_vals(self, context, mode, first_lot, count, lot_text):
        if not context.get('default_product_id'):
            raise UserError(_("No product found to generate Serials/Lots for."))
        assert mode in ('generate', 'import')
        default_vals = {}

        def generate_lot_qty(quantity, qty_per_lot):
            if qty_per_lot <= 0:
                raise UserError(_("The quantity per lot should always be a positive value."))
            line_count = int(quantity // qty_per_lot)
            leftover = quantity % qty_per_lot
            qty_array = [qty_per_lot] * line_count
            if leftover:
                qty_array.append(leftover)
            return qty_array

        # Get default values
        def remove_prefix(text, prefix):
            if text.startswith(prefix):
                return text[len(prefix):]
            return text
        for key in context:
            if key.startswith('default_'):
                default_vals[remove_prefix(key, 'default_')] = context[key]

        if default_vals['tracking'] == 'lot' and mode == 'generate':
            lot_qties = generate_lot_qty(default_vals['quantity'], count)
        else:
            lot_qties = [1] * count

        if mode == 'generate':
            lot_names = self.env['stock.lot'].generate_lot_names(first_lot, len(lot_qties))
        elif mode == 'import':
            lot_names = self.split_lots(lot_text)
            lot_qties = [1] * len(lot_names)

        vals_list = []
        for lot, qty in zip(lot_names, lot_qties):
            if not lot.get('quantity'):
                lot['quantity'] = qty
            loc_dest = self.env['stock.location'].browse(default_vals['location_dest_id'])
            product = self.env['product.product'].browse(default_vals['product_id'])
            loc_dest = loc_dest._get_putaway_strategy(product, lot['quantity'])
            vals_list.append({**default_vals,
                             **lot,
                             'location_dest_id': loc_dest.id,
                             'product_uom_id': product.uom_id.id,
                            })
        if default_vals.get('picking_type_id'):
            picking_type = self.env['stock.picking.type'].browse(default_vals['picking_type_id'])
            if picking_type.use_existing_lots:
                self._create_lot_ids_from_move_line_vals(
                    vals_list, default_vals['product_id'], default_vals['company_id']
                )
        # format many2one values for webclient, id + display_name
        for values in vals_list:
            for key, value in values.items():
                if key in self.env['stock.move.line'] and isinstance(self.env['stock.move.line'][key], models.Model):
                    values[key] = {
                        'id': value,
                        'display_name': self.env['stock.move.line'][key].browse(value).display_name
                    }
        return vals_list

    def _push_apply(self):
        new_moves = []
        for move in self:
            new_move = self.env['stock.move']

            # if the move is a returned move, we don't want to check push rules, as returning a returned move is the only decent way
            # to receive goods without triggering the push rules again (which would duplicate chained operations)
            # first priority goes to the preferred routes defined on the move itself (e.g. coming from a SO line)
            warehouse_id = move.warehouse_id or move.picking_id.picking_type_id.warehouse_id

            ProcurementGroup = self.env['procurement.group']
            if move.location_dest_id.company_id not in self.env.companies:
                ProcurementGroup = self.env['procurement.group'].sudo()
                move = move.with_context(allowed_companies=self.env.user.company_ids.ids)
                warehouse_id = False

            rule = ProcurementGroup._get_push_rule(move.product_id, move.location_dest_id, {
                'route_ids': move.route_ids, 'product_packaging_id': move.product_packaging_id, 'warehouse_id': warehouse_id,
            })

            excluded_rule_ids = []
            while (rule and rule.push_domain and not move.filtered_domain(literal_eval(rule.push_domain))):
                excluded_rule_ids.append(rule.id)
                rule = ProcurementGroup._get_push_rule(move.product_id, move.location_dest_id, {
                    'route_ids': move.route_ids, 'product_packaging_id': move.product_packaging_id, 'warehouse_id': warehouse_id,
                    'domain': [('id', 'not in', excluded_rule_ids)],
                })

            # Make sure it is not returning the return
            if rule and (not move.origin_returned_move_id or move.origin_returned_move_id.location_dest_id.id != rule.location_dest_id.id):
                new_move = rule._run_push(move) or new_move
                if new_move:
                    new_moves.append(new_move)

            move_to_propagate_ids = set()
            move_to_mts_ids = set()
            for m in move.move_dest_ids - new_move:
                if new_move and move.location_final_id and m.location_id == move.location_final_id:
                    move_to_propagate_ids.add(m.id)
                elif not m.location_id._child_of(move.location_dest_id):
                    move_to_mts_ids.add(m.id)
            self.env['stock.move'].browse(move_to_mts_ids)._break_mto_link(move)
            move.move_dest_ids = [Command.unlink(m_id) for m_id in move_to_propagate_ids]
            new_move.move_dest_ids = [Command.link(m_id) for m_id in move_to_propagate_ids]

        new_moves = self.env['stock.move'].concat(*new_moves)
        new_moves = new_moves.sudo()._action_confirm()

        return new_moves

    def _merge_moves_fields(self):
        """ This method will return a dict of stock move’s values that represent the values of all moves in `self` merged. """
        merge_extra = self.env.context.get('merge_extra')
        state = self._get_relevant_state_among_moves()
        origin = '/'.join(set(self.filtered(lambda m: m.origin).mapped('origin')))
        return {
            'product_uom_qty': sum(self.mapped('product_uom_qty')) if not merge_extra else self[0].product_uom_qty,
            'date': min(self.mapped('date')) if all(p.move_type == 'direct' for p in self.picking_id) else max(self.mapped('date')),
            'move_dest_ids': [(4, m.id) for m in self.mapped('move_dest_ids')],
            'move_orig_ids': [(4, m.id) for m in self.mapped('move_orig_ids')],
            'state': state,
            'origin': origin,
        }

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        fields = [
            'product_id', 'price_unit', 'procure_method', 'location_id', 'location_dest_id', 'location_final_id',
            'product_uom', 'restrict_partner_id', 'scrapped', 'origin_returned_move_id',
            'package_level_id', 'propagate_cancel', 'description_picking',
            'product_packaging_id', 'never_product_template_attribute_value_ids',
        ]
        if self.env['ir.config_parameter'].sudo().get_param('stock.merge_only_same_date'):
            fields.append('date')
        if self.env.context.get('merge_extra'):
            fields.pop(fields.index('procure_method'))
        if not self.env['ir.config_parameter'].sudo().get_param('stock.merge_ignore_date_deadline'):
            fields.append('date_deadline')
        return fields

    @api.model
    def _prepare_merge_negative_moves_excluded_distinct_fields(self):
        return ['description_picking']

    def _clean_merged(self):
        """Cleanup hook used when merging moves"""
        self.write({'propagate_cancel': False})

    def _update_candidate_moves_list(self, candidate_moves_set):
        for picking in self.mapped('picking_id'):
            candidate_moves_set.add(picking.move_ids)

    def _merge_move_itemgetter(self, distinct_fields, excluded_fields=None):
        field_names = [
            f_name for f_name in distinct_fields
            if f_name != 'price_unit' and (excluded_fields is None or f_name not in excluded_fields)
        ]
        base_getter = itemgetter(*field_names)

        if 'price_unit' not in distinct_fields:
            return base_getter

        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        currency_prec = self.company_id.currency_id.decimal_places
        price_precision = min(currency_prec, price_unit_prec)

        def _get_formatted_price_unit(move):
            # Round and Cast the price_unit into a string so that rounding errors do not prevent the merge
            rounded_price_unit = float_round(move.price_unit, precision_digits=price_precision)
            return "{:.{p}f}".format(rounded_price_unit, p=price_precision)

        return lambda move: base_getter(move) + (_get_formatted_price_unit(move),)

    def _merge_moves(self, merge_into=False):
        """ This method will, for each move in `self`, go up in their linked picking and try to
        find in their existing moves a candidate into which we can merge the move.
        :return: Recordset of moves passed to this method. If some of the passed moves were merged
        into another existing one, return this one and not the (now unlinked) original.
        """

        candidate_moves_set = set()
        if not merge_into:
            self._update_candidate_moves_list(candidate_moves_set)
        else:
            candidate_moves_set.add(merge_into | self)

        distinct_fields = (self | self.env['stock.move'].concat(*candidate_moves_set))._prepare_merge_moves_distinct_fields()

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
        neg_key = self._merge_move_itemgetter(distinct_fields, excluded_fields)
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')

        for candidate_moves in candidate_moves_set:
            # First step find move to merge.
            candidate_moves = candidate_moves.filtered(lambda m: m.state not in ('done', 'cancel', 'draft')) - neg_qty_moves
            for __, g in groupby(candidate_moves, key=self._merge_move_itemgetter(distinct_fields)):
                moves = self.env['stock.move'].concat(*g)
                # Merge all positive moves together
                if len(moves) > 1:
                    # link all move lines to record 0 (the one we will keep).
                    moves.mapped('move_line_ids').write({'move_id': moves[0].id})
                    # merge move data
                    merge_extra = self.env.context.get('merge_extra') and bool(merge_into)
                    moves[0].write(moves.with_context(merge_extra=merge_extra)._merge_moves_fields())
                    # update merged moves dicts
                    moves_to_unlink |= moves[1:]
                    merged_moves |= moves[0]
                # Add the now single positive move to its limited key record
                moves_by_neg_key[neg_key(moves[0])] |= moves[0]

        for neg_move in neg_qty_moves:
            # Check all the candidates that matches the same limited key, and adjust their quantities to absorb negative moves
            for pos_move in moves_by_neg_key.get(neg_key(neg_move), []):
                new_total_value = pos_move.product_qty * pos_move.price_unit + neg_move.product_qty * neg_move.price_unit
                # If quantity can be fully absorbed by a single move, update its quantity and remove the negative move
                if float_compare(pos_move.product_uom_qty, abs(neg_move.product_uom_qty), precision_rounding=pos_move.product_uom.rounding) >= 0:
                    pos_move.product_uom_qty += neg_move.product_uom_qty
                    pos_move.write({
                        'price_unit': float_round(new_total_value / pos_move.product_qty, precision_digits=price_unit_prec) if pos_move.product_qty else 0,
                        'move_dest_ids': [Command.link(m.id) for m in neg_move.mapped('move_dest_ids') if m.location_id == pos_move.location_dest_id],
                        'move_orig_ids': [Command.link(m.id) for m in neg_move.mapped('move_orig_ids') if m.location_dest_id == pos_move.location_id],
                    })
                    merged_moves |= pos_move
                    moves_to_unlink |= neg_move
                    if float_is_zero(pos_move.product_uom_qty, precision_rounding=pos_move.product_uom.rounding):
                        moves_to_cancel |= pos_move
                    break
                neg_move.product_uom_qty += pos_move.product_uom_qty
                neg_move.price_unit = float_round(new_total_value / neg_move.product_qty, precision_digits=price_unit_prec)
                pos_move.product_uom_qty = 0
                moves_to_cancel |= pos_move

        # We are using propagate to False in order to not cancel destination moves merged in moves[0]
        (moves_to_unlink | moves_to_cancel)._clean_merged()

        if moves_to_unlink:
            moves_to_unlink._action_cancel()
            moves_to_unlink.sudo().unlink()

        if moves_to_cancel:
            moves_to_cancel.filtered(lambda m: not m.picked)._action_cancel()

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
            if all(not m.product_uom_qty for m in moves_todo):
                return 'assigned'
            most_important_move = moves_todo[0]
            if most_important_move.state == 'confirmed':
                return 'confirmed'
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
        quantity = sum(ml.quantity_product_uom for ml in self.move_line_ids.filtered(lambda ml: not ml.lot_id and ml.lot_name))
        quantity += self.product_id.uom_id._compute_quantity(len(self.lot_ids), self.product_uom)
        self.update({'quantity': quantity})

        base_location = self.picking_id.location_id or self.location_id
        quants = self.env['stock.quant'].sudo().search([
            ('product_id', '=', self.product_id.id),
            ('lot_id', 'in', self.lot_ids.ids),
            ('quantity', '!=', 0),
            ('location_id.usage', 'in', ('internal', 'transit', 'customer')),
            ('location_id', 'not any', [('location_id', 'child_of', base_location.id)])
        ])

        if quants:
            sn_to_location = ""
            for quant in quants:
                sn_to_location += _("\n(%(serial_number)s) exists in location %(location)s", serial_number=quant.lot_id.display_name, location=quant.location_id.display_name)
            return {
                'warning': {'title': _('Warning'), 'message': _('Unavailable Serial numbers. Please correct the serial numbers encoded: %(serial_numbers_to_locations)s', serial_numbers_to_locations=sn_to_location)}
            }

    @api.onchange('product_uom')
    def _onchange_product_uom(self):
        if self.product_uom.factor > self.product_id.uom_id.factor:
            return {
                'warning': {
                    'title': _("Unsafe unit of measure"),
                    'message': _("You are using a unit of measure smaller than the one you are using in "
                                 "order to stock your product. This can lead to rounding problem on reserved quantity. "
                                 "You should use the smaller unit of measure possible in order to valuate your stock or "
                                 "change its rounding precision to a smaller value (example: 0.00001)."),
                }
            }

    def _key_assign_picking(self):
        self.ensure_one()
        keys = (self.group_id, self.location_id, self.location_dest_id, self.picking_type_id)
        if self.partner_id and not self.group_id:
            keys += (self.partner_id, )
        return keys

    def _search_picking_for_assignation_domain(self):
        domain = [
            ('group_id', '=', self.group_id.id),
            ('location_id', '=', self.location_id.id),
            ('location_dest_id', '=', (self.location_dest_id.id or self.picking_type_id.default_location_dest_id.id)),
            ('picking_type_id', '=', self.picking_type_id.id),
            ('printed', '=', False),
            ('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])]
        if self.partner_id and not self.group_id:
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
                vals = moves._assign_picking_values(picking)
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

    def _assign_picking_values(self, picking):
        vals = {}
        if any(picking.partner_id != m.partner_id for m in self):
            vals['partner_id'] = False
        if any(picking.origin != m.origin for m in self):
            vals['origin'] = False
        return vals

    def _assign_picking_post_process(self, new=False):
        pass

    def _generate_serial_move_line_commands(self, field_data, location_dest_id=False, origin_move_line=None):
        """Return a list of commands to update the move lines (write on
        existing ones or create new ones).
        Called when user want to create and assign multiple serial numbers in
        one time (using the button/wizard or copy-paste a list in the field).

        :param field_data: A list containing dict with at least `lot_name` and `quantity`
        :type field_data: list
        :param origin_move_line: A move line to duplicate the value from, empty record by default
        :type origin_move_line: record of :class:`stock.move.line`
        :return: A list of commands to create/update :class:`stock.move.line`
        :rtype: list
        """
        self.ensure_one()
        origin_move_line = origin_move_line or self.env['stock.move.line']
        loc_dest = origin_move_line.location_dest_id or location_dest_id
        move_line_vals = {
            'picking_id': self.picking_id.id,
            'location_id': self.location_id.id,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_id.uom_id.id,
        }
        # Select the right move lines depending of the picking type's configuration.
        move_lines = self.move_line_ids.filtered(lambda ml: not ml.lot_id and not ml.lot_name)

        if origin_move_line:
            # Copies `owner_id` and `package_id` if new move lines are created from an existing one.
            move_line_vals.update({
                'owner_id': origin_move_line.owner_id.id,
                'package_id': origin_move_line.package_id.id,
            })

        move_lines_commands = []
        qty_by_location = defaultdict(float)
        for command_vals in field_data:
            quantity = command_vals['quantity']
            # We write the lot name on an existing move line (if we have still one)...
            if move_lines:
                move_lines_commands.append(Command.update(move_lines[0].id, command_vals))
                qty_by_location[move_lines[0].location_dest_id.id] += quantity
                move_lines = move_lines[1:]
            # ... or create a new move line with the serial name.
            else:
                loc = loc_dest or self.location_dest_id._get_putaway_strategy(self.product_id, quantity=quantity, packaging=self.product_packaging_id, additional_qty=qty_by_location)
                new_move_line_vals = {
                    **move_line_vals,
                    **command_vals,
                    'location_dest_id': loc.id
                }
                move_lines_commands.append(Command.create(new_move_line_vals))
                qty_by_location[loc.id] += quantity
        return move_lines_commands

    def _get_formating_options(self, strings):
        return {}

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
        vals = {
            'origin': origin,
            'company_id': self.mapped('company_id').id,
            'user_id': False,
            'group_id': self.mapped('group_id').id,
            'partner_id': partner,
            'picking_type_id': self.mapped('picking_type_id').id,
            'location_id': self.mapped('location_id').id,
        }
        if self.location_dest_id.ids:
            vals['location_dest_id'] = self.location_dest_id.id
        return vals

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
            elif move.procure_method == 'make_to_order':
                move_waiting.add(move.id)
                move_create_proc.add(move.id)
            elif move.rule_id and move.rule_id.procure_method == 'mts_else_mto':
                move_create_proc.add(move.id)
                move_to_confirm.add(move.id)
            else:
                move_to_confirm.add(move.id)
            if move._should_be_assigned():
                key = (move.group_id.id, move.location_id.id, move.location_dest_id.id)
                to_assign[key].add(move.id)

        # create procurements for make to order moves
        procurement_requests = []
        move_create_proc = self.browse(move_create_proc) if not self.env.context.get('bypass_procurement_creation', False) else self.env['stock.move']
        quantities = move_create_proc._prepare_procurement_qty()
        for move, quantity in zip(move_create_proc, quantities):
            values = move._prepare_procurement_values()
            origin = move._prepare_procurement_origin()
            procurement_requests.append(self.env['procurement.group'].Procurement(
                move.product_id, quantity, move.product_uom,
                move.location_id, move.rule_id and move.rule_id.name or "/",
                origin, move.company_id, values))
        self.env['procurement.group'].run(procurement_requests, raise_user_error=not self.env.context.get('from_orderpoint'))

        move_to_confirm, move_waiting = self.browse(move_to_confirm), self.browse(move_waiting)
        move_to_confirm.write({'state': 'confirmed'})
        move_waiting.write({'state': 'waiting'})
        # procure_method sometimes changes with certain workflows so just in case, apply to all moves
        (move_to_confirm | move_waiting).filtered(lambda m: m.picking_type_id.reservation_method == 'at_confirm')\
            .write({'reservation_date': fields.Date.today()})

        # assign picking in batch for all confirmed move that share the same details
        for moves_ids in to_assign.values():
            self.browse(moves_ids).with_context(clean_context(self.env.context))._assign_picking()

        self._check_company()
        moves = self
        if merge:
            moves = self._merge_moves(merge_into=merge_into)

        neg_r_moves = moves.filtered(lambda move: float_compare(
            move.product_uom_qty, 0, precision_rounding=move.product_uom.rounding) < 0)

        # Push remaining quantities to next step
        neg_to_push = neg_r_moves.filtered(lambda move: move.location_final_id and move.location_dest_id != move.location_final_id)
        new_push_moves = self.env['stock.move']
        if neg_to_push:
            new_push_moves = neg_to_push._push_apply()

        # Transform remaining move in returns in case of negative initial demand
        for move in neg_r_moves:
            move.location_id, move.location_dest_id, move.location_final_id = move.location_dest_id, move.location_id, move.location_id
            orig_move_ids, dest_move_ids = [], []
            for m in move.move_orig_ids | move.move_dest_ids:
                from_loc, to_loc = m.location_id, m.location_dest_id
                if float_compare(m.product_uom_qty, 0, precision_rounding=m.product_uom.rounding) < 0:
                    from_loc, to_loc = to_loc, from_loc
                if to_loc == move.location_id:
                    orig_move_ids += m.ids
                elif move.location_dest_id == from_loc:
                    dest_move_ids += m.ids
            move.move_orig_ids, move.move_dest_ids = [Command.set(orig_move_ids)], [Command.set(dest_move_ids)]
            move.product_uom_qty *= -1
            if move.picking_type_id.return_picking_type_id:
                move.picking_type_id = move.picking_type_id.return_picking_type_id
            # We are returning some products, we must take them in the source location
            move.procure_method = 'make_to_stock'
        neg_r_moves._assign_picking()

        # call `_action_assign` on every confirmed move which location_id bypasses the reservation + those expected to be auto-assigned
        moves.filtered(lambda move: move.state in ('confirmed', 'partially_available')
                       and (move._should_bypass_reservation() or move._should_assign_at_confirm()))\
             ._action_assign()
        if new_push_moves:
            neg_push_moves = new_push_moves.filtered(lambda sm: float_compare(sm.product_uom_qty, 0, precision_rounding=sm.product_uom.rounding) < 0)
            (new_push_moves - neg_push_moves).sudo()._action_confirm()
            # Negative moves do not have any picking, so we should try to merge it with their siblings
            neg_push_moves._action_confirm(merge_into=neg_push_moves.move_orig_ids.move_dest_ids)
        return moves

    def _prepare_procurement_origin(self):
        self.ensure_one()
        return self.group_id and self.group_id.name or (self.origin or self.picking_id.name or "/")

    def _prepare_procurement_qty(self):
        quantities = []
        mtso_products_by_locations = defaultdict(list)
        mtso_moves = set()
        for move in self:
            if move.rule_id and move.rule_id.procure_method == 'mts_else_mto':
                mtso_moves.add(move.id)
                mtso_products_by_locations[move.location_id].append(move.product_id.id)

        # Get the forecasted quantity for the `mts_else_mto` procurement.
        forecasted_qties_by_loc = {}
        for location, product_ids in mtso_products_by_locations.items():
            if location.should_bypass_reservation():
                continue
            products = self.env['product.product'].browse(product_ids).with_context(location=location.id)
            forecasted_qties_by_loc[location] = {product.id: product.free_qty for product in products}
        for move in self:
            if move.id not in mtso_moves or float_compare(move.product_qty, 0, precision_rounding=move.product_id.uom_id.rounding) <= 0:
                quantities.append(move.product_uom_qty)
                continue

            if move._should_bypass_reservation():
                quantities.append(move.product_uom_qty)
                continue

            free_qty = max(forecasted_qties_by_loc[move.location_id][move.product_id.id], 0)
            quantity = max(move.product_qty - free_qty, 0)
            product_uom_qty = move.product_id.uom_id._compute_quantity(quantity, move.product_uom, rounding_method='HALF-UP')
            quantities.append(product_uom_qty)
            forecasted_qties_by_loc[move.location_id][move.product_id.id] -= min(move.product_qty, free_qty)

        return quantities

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
        dates_info = {'date_planned': self._get_mto_procurement_date()}
        if self.location_id.warehouse_id and self.location_id.warehouse_id.lot_stock_id.parent_path in self.location_id.parent_path:
            dates_info = self.product_id._get_dates_info(self.date, self.location_id, route_ids=self.route_ids)
        warehouse = self.warehouse_id or self.picking_type_id.warehouse_id
        if not self.location_id.warehouse_id:
            warehouse = self.rule_id.propagate_warehouse_id
        move_dest_ids = False
        if self.procure_method == "make_to_order":
            move_dest_ids = self
        return {
            'product_description_variants': self.description_picking and self.description_picking.replace(product_id._get_description(self.picking_type_id), ''),
            'never_product_template_attribute_value_ids': self.never_product_template_attribute_value_ids,
            'date_planned': dates_info.get('date_planned'),
            'date_order': dates_info.get('date_order'),
            'date_deadline': self.date_deadline,
            'move_dest_ids': move_dest_ids,
            'group_id': group_id,
            'route_ids': self.route_ids,
            'warehouse_id': warehouse,
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
            # TODO could be also move in create/write
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            uom_quantity = self.product_id.uom_id._compute_quantity(quantity, self.product_uom, rounding_method='HALF-UP')
            uom_quantity = float_round(uom_quantity, precision_digits=rounding)
            uom_quantity_back_to_product_uom = self.product_uom._compute_quantity(uom_quantity, self.product_id.uom_id, rounding_method='HALF-UP')
            if float_compare(quantity, uom_quantity_back_to_product_uom, precision_digits=rounding) == 0:
                vals = dict(vals, quantity=uom_quantity)
            else:
                vals = dict(vals, quantity=quantity, product_uom_id=self.product_id.uom_id.id)
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

    def _update_reserved_quantity(self, need, location_id, lot_id=None, package_id=None, owner_id=None, strict=True):
        """ Create or update move lines and reserves quantity from quants
            Expects the need (qty to reserve) and location_id to reserve from.
            `quant_ids` can be passed as an optimization since no search on the database
            is performed and reservation is done on the passed quants set
        """
        self.ensure_one()
        if not lot_id:
            lot_id = self.env['stock.lot']
        if not package_id:
            package_id = self.env['stock.quant.package']
        if not owner_id:
            owner_id = self.env['res.partner']

        quants = self.env['stock.quant']._get_reserve_quantity(
            self.product_id, location_id, need, product_packaging_id=self.product_packaging_id,
            uom_id=self.product_uom, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)

        taken_quantity = 0
        rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        # Find a candidate move line to update or create a new one.
        candidate_lines = {}
        for line in self.move_line_ids:
            if line.result_package_id or line.product_id.tracking == 'serial':
                continue
            candidate_lines[line.location_id, line.lot_id, line.package_id, line.owner_id] = line
        move_line_vals = []
        grouped_quants = {}
        # Handle quants duplication
        for quant, quantity in quants:
            if (quant.location_id, quant.lot_id, quant.package_id, quant.owner_id) not in grouped_quants:
                grouped_quants[quant.location_id, quant.lot_id, quant.package_id, quant.owner_id] = [quant, quantity]
            else:
                grouped_quants[quant.location_id, quant.lot_id, quant.package_id, quant.owner_id][1] += quantity
        for reserved_quant, quantity in grouped_quants.values():
            taken_quantity += quantity
            to_update = candidate_lines.get((reserved_quant.location_id, reserved_quant.lot_id, reserved_quant.package_id, reserved_quant.owner_id))
            if to_update:
                uom_quantity = self.product_id.uom_id._compute_quantity(quantity, to_update.product_uom_id, rounding_method='HALF-UP')
                uom_quantity = float_round(uom_quantity, precision_digits=rounding)
                uom_quantity_back_to_product_uom = to_update.product_uom_id._compute_quantity(uom_quantity, self.product_id.uom_id, rounding_method='HALF-UP')
            if to_update and float_compare(quantity, uom_quantity_back_to_product_uom, precision_digits=rounding) == 0:
                to_update.with_context(reserved_quant=reserved_quant).quantity += uom_quantity
            else:
                if self.product_id.tracking == 'serial' and (self.picking_type_id.use_create_lots or self.picking_type_id.use_existing_lots):
                    vals_list = self._add_serial_move_line_to_vals_list(reserved_quant, quantity)
                    if vals_list:
                        move_line_vals += vals_list
                else:
                    move_line_vals.append(self._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant))
        if move_line_vals:
            self.env['stock.move.line'].create(move_line_vals)
        return taken_quantity

    def _add_serial_move_line_to_vals_list(self, reserved_quant, quantity):
        return [self._prepare_move_line_vals(quantity=1, reserved_quant=reserved_quant) for i in range(int(quantity))]

    def _should_bypass_reservation(self, forced_location=False):
        self.ensure_one()
        location = forced_location or self.location_id
        return location.should_bypass_reservation() or not self.product_id.is_storable

    def _should_assign_at_confirm(self):
        return self._should_bypass_reservation() or self.picking_type_id.reservation_method == 'at_confirm' or (self.reservation_date and self.reservation_date <= fields.Date.today())

    def _get_picked_quantity(self):
        self.ensure_one()
        if self.picked and any(not ml.picked for ml in self.move_line_ids):
            picked_qty = 0
            for ml in self.move_line_ids:
                if not ml.picked:
                    continue
                picked_qty += ml.product_uom_id._compute_quantity(ml.quantity, self.product_uom, round=False)
            return picked_qty
        else:
            return self.quantity

    # necessary hook to be able to override move reservation to a restrict lot, owner, pack, location...
    def _get_available_quantity(self, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, allow_negative=False):
        self.ensure_one()
        if location_id.should_bypass_reservation():
            return self.product_qty
        return self.env['stock.quant']._get_available_quantity(self.product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict, allow_negative=allow_negative)

    def _get_available_move_lines_in(self):
        move_lines_in = self.move_orig_ids.move_dest_ids.move_orig_ids.filtered(lambda m: m.state == 'done').mapped('move_line_ids')

        def _keys_in_groupby(ml):
            return (ml.location_dest_id, ml.lot_id, ml.result_package_id, ml.owner_id)

        grouped_move_lines_in = {}
        for k, g in groupby(move_lines_in, key=_keys_in_groupby):
            quantity = 0
            for ml in g:
                quantity += ml.product_uom_id._compute_quantity(ml.quantity, ml.product_id.uom_id)
            grouped_move_lines_in[k] = quantity

        return grouped_move_lines_in

    def _get_available_move_lines_out(self, assigned_moves_ids, partially_available_moves_ids):
        move_lines_out_done = (self.move_orig_ids.mapped('move_dest_ids') - self)\
            .filtered(lambda m: m.state in ['done'])\
            .mapped('move_line_ids')
        # As we defer the write on the stock.move's state at the end of the loop, there
        # could be moves to consider in what our siblings already took.
        StockMove = self.env['stock.move']
        moves_out_siblings = self.move_orig_ids.mapped('move_dest_ids') - self
        moves_out_siblings_to_consider = moves_out_siblings & (StockMove.browse(assigned_moves_ids) + StockMove.browse(partially_available_moves_ids))
        reserved_moves_out_siblings = moves_out_siblings.filtered(lambda m: m.state in ['partially_available', 'assigned'])
        move_lines_out_reserved = (reserved_moves_out_siblings | moves_out_siblings_to_consider).mapped('move_line_ids')

        def _keys_out_groupby(ml):
            return (ml.location_id, ml.lot_id, ml.package_id, ml.owner_id)

        grouped_move_lines_out = {}
        for k, g in groupby(move_lines_out_done, key=_keys_out_groupby):
            quantity = 0
            for ml in g:
                quantity += ml.product_uom_id._compute_quantity(ml.quantity, ml.product_id.uom_id)
            grouped_move_lines_out[k] = quantity
        for k, g in groupby(move_lines_out_reserved, key=_keys_out_groupby):
            grouped_move_lines_out[k] = sum(self.env['stock.move.line'].concat(*list(g)).mapped('quantity_product_uom'))

        return grouped_move_lines_out

    def _get_available_move_lines(self, assigned_moves_ids, partially_available_moves_ids):
        grouped_move_lines_in = self._get_available_move_lines_in()
        grouped_move_lines_out = self._get_available_move_lines_out(assigned_moves_ids, partially_available_moves_ids)
        available_move_lines = {key: grouped_move_lines_in[key] - grouped_move_lines_out.get(key, 0) for key in grouped_move_lines_in}
        # pop key if the quantity available amount to 0
        rounding = self.product_id.uom_id.rounding
        return dict((k, v) for k, v in available_move_lines.items() if float_compare(v, 0, precision_rounding=rounding) > 0)

    def _action_assign(self, force_qty=False):
        """ Reserve stock moves by creating their stock move lines. A stock move is
        considered reserved once the sum of `reserved_qty` for all its move lines is
        equal to its `product_qty`. If it is less, the stock move is considered
        partially available.
        """
        StockMove = self.env['stock.move']
        assigned_moves_ids = OrderedSet()
        partially_available_moves_ids = OrderedSet()
        # Read the `reserved_availability` field of the moves out of the loop to prevent unwanted
        # cache invalidation when actually reserving the move.
        reserved_availability = {move: move.quantity for move in self}

        roundings = {move: move.product_id.uom_id.rounding for move in self}
        move_line_vals_list = []
        # Once the quantities are assigned, we want to find a better destination location thanks
        # to the putaway rules. This redirection will be applied on moves of `moves_to_redirect`.
        moves_to_redirect = OrderedSet()
        moves_to_assign = self
        if not force_qty:
            moves_to_assign = moves_to_assign.filtered(
                lambda m: not m.picked and m.state in ['confirmed', 'waiting', 'partially_available']
            )
        moves_mto = moves_to_assign.filtered(lambda m: m.move_orig_ids and not m._should_bypass_reservation())
        quants_cache = self.env['stock.quant']._get_quants_by_products_locations(moves_mto.product_id, moves_mto.location_id)
        for move in moves_to_assign:
            move = move.with_company(move.company_id)
            rounding = roundings[move]
            if not force_qty:
                missing_reserved_uom_quantity = move.product_uom_qty - reserved_availability[move]
            else:
                missing_reserved_uom_quantity = force_qty
            if float_compare(missing_reserved_uom_quantity, 0, precision_rounding=rounding) <= 0:
                assigned_moves_ids.add(move.id)
                continue
            missing_reserved_quantity = move.product_uom._compute_quantity(missing_reserved_uom_quantity, move.product_id.uom_id, rounding_method='HALF-UP')
            if move._should_bypass_reservation():
                # create the move line(s) but do not impact quants
                if move.move_orig_ids:
                    available_move_lines = move._get_available_move_lines(assigned_moves_ids, partially_available_moves_ids)
                    for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
                        qty_added = min(missing_reserved_quantity, quantity)
                        move_line_vals = move._prepare_move_line_vals(qty_added)
                        move_line_vals.update({
                            'location_id': location_id.id,
                            'lot_id': lot_id.id,
                            'lot_name': lot_id.name,
                            'owner_id': owner_id.id,
                            'package_id': package_id.id,
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
                                                            not ml.picked and
                                                            not ml.lot_id and
                                                            not ml.result_package_id and
                                                            not ml.package_id and
                                                            not ml.owner_id)
                    if to_update:
                        to_update[0].quantity += move.product_id.uom_id._compute_quantity(
                            missing_reserved_quantity, move.product_uom, rounding_method='HALF-UP')
                    else:
                        move_line_vals_list.append(move._prepare_move_line_vals(quantity=missing_reserved_quantity))
                assigned_moves_ids.add(move.id)
                moves_to_redirect.add(move.id)
            else:
                if float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding) and not force_qty:
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
                    taken_quantity = move._update_reserved_quantity(need, move.location_id, package_id=forced_package_id, strict=False)
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
                    # `quantity` is in `ml.product_uom_id` and, as we will later increase
                    # the reserved quantity on the quants, convert it here in
                    # `product_id.uom_id` (the UOM of the quants is the UOM of the product).
                    available_move_lines = move._get_available_move_lines(assigned_moves_ids, partially_available_moves_ids)
                    if not available_move_lines:
                        continue
                    for move_line in move.move_line_ids.filtered(lambda m: m.quantity_product_uom):
                        if available_move_lines.get((move_line.location_id, move_line.lot_id, move_line.package_id, move_line.owner_id)):
                            available_move_lines[(move_line.location_id, move_line.lot_id, move_line.package_id, move_line.owner_id)] -= move_line.quantity_product_uom
                    for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
                        need = move.product_qty - sum(move.move_line_ids.mapped('quantity_product_uom'))
                        # `quantity` is what is brought by chained done move lines. We double check
                        # here this quantity is available on the quants themselves. If not, this
                        # could be the result of an inventory adjustment that removed totally of
                        # partially `quantity`. When this happens, we chose to reserve the maximum
                        # still available. This situation could not happen on MTS move, because in
                        # this case `quantity` is directly the quantity on the quants themselves.

                        taken_quantity = move.with_context(quants_cache=quants_cache)._update_reserved_quantity(
                            min(quantity, need), location_id, lot_id, package_id, owner_id)
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
        if not self.env.context.get('bypass_entire_pack'):
            self.picking_id._check_entire_pack()
        StockMove.browse(moves_to_redirect).move_line_ids._apply_putaway_strategy()

    def _action_cancel(self):
        if any(move.state == 'done' and not move.scrapped for move in self):
            raise UserError(_('You cannot cancel a stock move that has been set to \'Done\'. Create a return in order to reverse the moves which took place.'))
        moves_to_cancel = self.filtered(lambda m: m.state != 'cancel' and not (m.state == 'done' and m.scrapped))
        moves_to_cancel.picked = False
        # self cannot contain moves that are either cancelled or done, therefore we can safely
        # unlink all associated move_line_ids
        moves_to_cancel._do_unreserve()
        cancel_moves_origin = self.env['ir.config_parameter'].sudo().get_param('stock.cancel_moves_origin')

        moves_to_cancel.state = 'cancel'

        for move in moves_to_cancel:
            siblings_states = (move.move_dest_ids.mapped('move_orig_ids') - move).mapped('state')
            if move.propagate_cancel:
                # only cancel the next move if all my siblings are also cancelled
                if all(state == 'cancel' for state in siblings_states):
                    move.move_dest_ids.filtered(lambda m: m.state != 'done' and move.location_dest_id == m.location_id)._action_cancel()
                    if cancel_moves_origin:
                        move.move_orig_ids.sudo().filtered(lambda m: m.state != 'done')._action_cancel()
            else:
                if all(state in ('done', 'cancel') for state in siblings_states):
                    move_dest_ids = move.move_dest_ids
                    move_dest_ids.write({
                        'procure_method': 'make_to_stock',
                        'move_orig_ids': [Command.unlink(move.id)]
                    })
        moves_to_cancel.write({
            'move_orig_ids': [(5, 0, 0)],
            'procure_method': 'make_to_stock',
        })
        return True

    def _skip_push(self):
        return self.is_inventory or (
            self.move_dest_ids and any(m.location_id._child_of(self.location_dest_id) for m in self.move_dest_ids)
        )

    def _check_quantity(self):
        return self.env['stock.quant'].search([
            ('product_id', 'in', self.product_id.ids),
            ('location_id', 'child_of', self.location_dest_id.ids),
            ('lot_id', 'in', self.lot_ids.ids)
        ]).check_quantity()

    def _action_done(self, cancel_backorder=False):
        moves = self.filtered(
            lambda move: move.state == 'draft')._action_confirm(merge=False)
        moves = (self | moves).exists().filtered(lambda x: x.state not in ('done', 'cancel'))

        # Cancel moves where necessary ; we should do it before creating the extra moves because
        # this operation could trigger a merge of moves.
        ml_ids_to_unlink = OrderedSet()
        for move in moves:
            if move.picked:
                # in theory, we should only have a mix of picked and non-picked mls in the barcode use case
                # where non-scanned mls = not picked => we definitely don't want to validate them
                ml_ids_to_unlink |= move.move_line_ids.filtered(lambda ml: not ml.picked).ids
            if (move.quantity <= 0 or not move.picked) and not move.is_inventory:
                if float_compare(move.product_uom_qty, 0.0, precision_rounding=move.product_uom.rounding) == 0 or cancel_backorder:
                    move._action_cancel()
        self.env['stock.move.line'].browse(ml_ids_to_unlink).unlink()

        moves_todo = moves.filtered(lambda m:
            not (m.state == 'cancel' or (m.quantity <= 0 and not m.is_inventory) or not m.picked)
        )

        moves_todo._check_company()
        if not cancel_backorder:
            moves_todo._create_backorder()
        moves_todo.mapped('move_line_ids').sorted()._action_done()
        # Check the consistency of the result packages; there should be an unique location across
        # the contained quants.
        for result_package in moves_todo\
                .move_line_ids.filtered(lambda ml: ml.picked).mapped('result_package_id')\
                .filtered(lambda p: p.quant_ids and len(p.quant_ids) > 1):
            if len(result_package.quant_ids.filtered(lambda q: float_compare(q.quantity, 0.0, precision_rounding=q.product_uom_id.rounding) > 0).mapped('location_id')) > 1:
                raise UserError(_('You cannot move the same package content more than once in the same transfer or split the same package into two location.'))
        if any(ml.package_id and ml.package_id == ml.result_package_id for ml in moves_todo.move_line_ids):
            self.env['stock.quant']._unlink_zero_quants()
        picking = moves_todo.mapped('picking_id')
        moves_todo.write({'state': 'done', 'date': fields.Datetime.now()})

        move_dests_per_company = defaultdict(lambda: self.env['stock.move'])

        # Break move dest link if move dest and move_dest source are not the same,
        # so that when move_dests._action_assign is called, the move lines are not created with
        # the new location, they should not be created at all.
        moves_to_push = moves_todo.filtered(lambda m: not m._skip_push())
        if moves_to_push:
            moves_to_push._push_apply()
        for move_dest in moves_todo.move_dest_ids:
            move_dests_per_company[move_dest.company_id.id] |= move_dest
        for company_id, move_dests in move_dests_per_company.items():
            move_dests.sudo().with_company(company_id)._action_assign()

        # We don't want to create back order for scrap moves
        # Replace by a kwarg in master
        if self.env.context.get('is_scrap'):
            return moves

        if picking and not cancel_backorder:
            backorder = picking._create_backorder()
            if any([m.state == 'assigned' for m in backorder.move_ids]):
                backorder._check_entire_pack()
        if moves_todo:
            moves_todo._check_quantity()
        return moves_todo

    def _create_backorder(self):
        # Split moves where necessary and move quants
        backorder_moves_vals = []
        for move in self:
            # To know whether we need to create a backorder or not, round to the general product's
            # decimal precision and not the product's UOM.
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(move.quantity, move.product_uom_qty, precision_digits=rounding) < 0:
                # Need to do some kind of conversion here
                qty_split = move.product_uom._compute_quantity(move.product_uom_qty - move.quantity, move.product_id.uom_id, rounding_method='HALF-UP')
                new_move_vals = move._split(qty_split)
                backorder_moves_vals += new_move_vals
        backorder_moves = self.env['stock.move'].create(backorder_moves_vals)
        # The backorder moves are not yet in their own picking. We do not want to check entire packs for those
        # ones as it could messed up the result_package_id of the moves being currently validated
        backorder_moves.with_context(bypass_entire_pack=True, bypass_procurement_creation=True)._action_confirm(merge=False)
        return backorder_moves

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_or_cancel(self):
        if any(move.state not in ('draft', 'cancel') and (move.move_orig_ids or move.move_dest_ids) for move in self):
            raise UserError(_('You can not delete moves linked to another operation'))

    def unlink(self):
        # With the non plannified picking, draft moves could have some move lines.
        self.with_context(prefetch_fields=False).mapped('move_line_ids').unlink()
        return super(StockMove, self).unlink()

    def _prepare_move_split_vals(self, qty):
        vals = {
            'product_uom_qty': qty,
            'procure_method': self.procure_method,
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
            raise UserError(_('You cannot split a stock move that has been set to \'Done\' or \'Cancel\'.'))
        elif self.state == 'draft':
            # we restrict the split of a draft move because if not confirmed yet, it may be replaced by several other moves in
            # case of phantom bom (with mrp module). And we don't want to deal with this complexity by copying the product that will explode.
            raise UserError(_('You cannot split a draft move. It needs to be confirmed first.'))

        if float_is_zero(qty, precision_rounding=self.product_id.uom_id.rounding):
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
        new_product_qty = self.product_id.uom_id._compute_quantity(max(0, self.product_qty - qty), self.product_uom, round=False)
        new_product_qty = float_round(new_product_qty, precision_digits=self.env['decimal.precision'].precision_get('Product Unit of Measure'))
        self.with_context(do_not_unreserve=True).write({'product_uom_qty': new_product_qty})
        return new_move_vals

    def _post_process_created_moves(self):
        # This method is meant to be overriden in order to execute post 
        # creation actions that would be bypassed since the move was 
        # and will probably never be confirmed
        pass

    def _recompute_state(self):
        if self._context.get('preserve_state'):
            return
        moves_state_to_write = defaultdict(set)
        for move in self:
            rounding = move.product_uom.rounding
            if move.state in ('cancel', 'done') or (move.state == 'draft' and not move.quantity):
                continue
            elif float_compare(move.quantity, move.product_uom_qty, precision_rounding=rounding) >= 0:
                moves_state_to_write['assigned'].add(move.id)
            elif move.quantity and float_compare(move.quantity, move.product_uom_qty, precision_rounding=rounding) <= 0:
                moves_state_to_write['partially_available'].add(move.id)
            elif (move.procure_method == 'make_to_order' and not move.move_orig_ids) or\
                 (move.move_orig_ids and any(float_compare(orig.product_uom_qty, 0, precision_rounding=orig.product_uom.rounding) > 0
                                             and orig.state not in ('done', 'cancel') for orig in move.move_orig_ids)):
                # In the process of merging a negative move, we may still have a negative move in the move_orig_ids at that point.
                moves_state_to_write['waiting'].add(move.id)
            else:
                moves_state_to_write['confirmed'].add(move.id)
        for state, moves_ids in moves_state_to_write.items():
            self.browse(moves_ids).filtered(lambda m: m.state != state).state = state

    def _is_consuming(self):
        self.ensure_one()
        from_wh = self.location_id.warehouse_id
        to_wh = self.location_dest_id.warehouse_id
        return self.picking_type_id.code in ('internal', 'outgoing') or (from_wh and to_wh and from_wh != to_wh)

    def _get_lang(self):
        """Determine language to use for translated description"""
        return self.picking_id.partner_id.lang or self.partner_id.lang or self.env.user.lang

    def _get_source_document(self):
        """ Return the move's document, used by `stock.forecasted_product_productt`
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
            ml_qty = ml.quantity
            if float_is_zero(qty, precision_rounding=self.product_uom.rounding):
                res.append((2, ml.id))
                continue
            if float_compare(ml_qty, 0, precision_rounding=ml.product_uom_id.rounding) <= 0:
                continue
            # Convert move line qty into move uom
            if ml.product_uom_id != self.product_uom:
                ml_qty = ml.product_uom_id._compute_quantity(ml_qty, self.product_uom, round=False)

            taken_qty = min(qty, ml_qty)
            # Convert taken qty into move line uom
            if ml.product_uom_id != self.product_uom:
                taken_qty = self.product_uom._compute_quantity(taken_qty, ml.product_uom_id, round=False)

            # Assign qty_done and explicitly round to make sure there is no inconsistency between
            # ml.qty_done and qty.
            taken_qty = float_round(taken_qty, precision_rounding=ml.product_uom_id.rounding)
            res.append((1, ml.id, {'quantity': taken_qty}))
            if ml.product_uom_id != self.product_uom:
                taken_qty = ml.product_uom_id._compute_quantity(taken_qty, self.product_uom, round=False)
            qty -= taken_qty

        if float_compare(qty, 0.0, precision_rounding=self.product_uom.rounding) > 0:
            if self.product_id.tracking != 'serial':
                vals = self._prepare_move_line_vals(quantity=0)
                vals['quantity'] = qty
                res.append((0, 0, vals))
            else:
                uom_qty = self.product_uom._compute_quantity(qty, self.product_id.uom_id)
                for i in range(0, int(uom_qty)):
                    vals = self._prepare_move_line_vals(quantity=0)
                    vals['quantity'] = 1
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

    def _adjust_procure_method(self, picking_type_code=False):
        """ This method will try to apply the procure method MTO on some moves if
        a compatible MTO route is found. Else the procure method will be set to MTS
        picking_type_code (str, optional): Adjusts the procurement method based on
            the specified picking type code. The code to specify the picking type for
            the procurement group. Defaults to False.
        """
        # Prepare the MTSO variables. They are needed since MTSO moves are handled separately.
        # We need 2 dicts:
        # - needed quantity per location per product
        # - forecasted quantity per location per product

        for move in self:
            product_id = move.product_id
            domain = [
                ('location_src_id', '=', move.location_id.id),
                ('location_dest_id', '=', move.location_dest_id.id),
                ('action', '!=', 'push')
            ]
            if picking_type_code:
                domain.append(('picking_type_id.code', '=', picking_type_code))
            rule = self.env['procurement.group']._search_rule(False, move.product_packaging_id, product_id, move.warehouse_id, domain)
            if not rule:
                move.procure_method = 'make_to_stock'
                continue

            move.rule_id = rule.id
            if rule.procure_method in ['make_to_stock', 'make_to_order']:
                move.procure_method = rule.procure_method
            else:
                move.procure_method = 'make_to_stock'

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

        domains = [
            [('product_id', '=', move.product_id.id), ('location_id', '=', move.location_dest_id.id)]
            for move in self
        ]
        static_domain = [('state', 'in', ['confirmed', 'partially_available']),
                         ('procure_method', '=', 'make_to_stock'),
                         '|',
                            ('reservation_date', '<=', fields.Date.today()),
                            ('picking_type_id.reservation_method', '=', 'at_confirm')
                        ]
        moves_to_reserve = self.env['stock.move'].search(expression.AND([static_domain, expression.OR(domains)]),
                                                         order='priority desc, date asc, id asc')
        moves_to_reserve = moves_to_reserve.sorted(key=lambda m: m.group_id.id in self.group_id.ids, reverse=True)
        moves_to_reserve._action_assign()

    def _rollup_move_dests_fetch(self):
        seen = set(self.ids)
        self.fetch(['move_dest_ids'])
        move_dest_ids = set(self.move_dest_ids.ids)
        while not move_dest_ids.issubset(seen):
            seen |= move_dest_ids
            to_visit = self.browse(move_dest_ids)
            to_visit.fetch(['move_dest_ids'])
            move_dest_ids = set(to_visit.move_dest_ids.ids)

    def _rollup_move_origs_fetch(self):
        seen = set(self.ids)
        self.fetch(['move_orig_ids'])
        move_orig_ids = set(self.move_orig_ids.ids)
        while not move_orig_ids.issubset(seen):
            seen |= move_orig_ids
            to_visit = self.browse(move_orig_ids)
            to_visit.fetch(['move_orig_ids'])
            move_orig_ids = set(to_visit.move_orig_ids.ids)

    def _rollup_move_dests(self, seen=False):
        if not seen:
            seen = OrderedSet()
        unseen = OrderedSet(self.ids) - seen
        if not unseen:
            return seen
        seen.update(unseen)
        self.filtered(lambda m: m.id in unseen).move_dest_ids._rollup_move_dests(seen)
        return seen

    def _rollup_move_origs(self, seen=False):
        if not seen:
            seen = OrderedSet()
        unseen = OrderedSet(self.ids) - seen
        if not unseen:
            return seen
        seen.update(unseen)
        self.filtered(lambda m: m.id in unseen).move_orig_ids._rollup_move_origs(seen)
        return seen

    def _get_forecast_availability_outgoing(self, warehouse, location_id=False):
        """ Get forcasted information (sum_qty_expected, max_date_expected) of self for the warehouse's locations.
        :param warehouse: warehouse to search under
        :param  location_id: location source of outgoing moves
        :return: a defaultdict of outgoing moves from warehouse for product_id in self, values are tuple (sum_qty_expected, max_date_expected)
        :rtype: defaultdict
        """
        wh_location_query = self.env['stock.location']._search([('id', 'child_of', warehouse.view_location_id.id)])
        forecast_lines = self.env['stock.forecasted_product_product']._get_report_lines(False, self.product_id.ids, wh_location_query, location_id or warehouse.lot_stock_id, read=False)
        result = defaultdict(lambda: (0.0, False))
        for line in forecast_lines:
            move_out = line.get('move_out')
            if not move_out or not line['quantity']:
                continue
            move_in = line.get('move_in')
            qty_expected = line['quantity'] + result[move_out][0] if line['replenishment_filled'] else -line['quantity']
            date_expected = False
            if move_in:
                date_expected = max(move_in.date, result[move_out][1]) if result[move_out][1] else move_in.date
            result[move_out] = (qty_expected, date_expected)

        return result

    def action_open_reference(self):
        """ Open the form view of the move's reference document, if one exists, otherwise open form view of self
        """
        self.ensure_one()
        source = self.picking_id
        if source and source.browse().has_access('read'):
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

    def _convert_string_into_field_data(self, string, options):
        string = string.replace(',', '.')  # Parsing string as float works only with dot, not comma.
        if regex_findall(r'^([0-9]+\.?[0-9]*|\.[0-9]+)$', string):  # Number => Quantity.
            return {'quantity': float(string)}
        return False

    def _match_searched_availability(self, operator, value, get_comparison_date):
        def get_stock_moves(moves, state):
            if state == 'available':
                return moves.filtered(lambda m: m.forecast_availability == m.product_qty and not m.forecast_expected_date)
            elif state == 'expected':
                return moves.filtered(lambda m: m.forecast_availability == m.product_qty and m.forecast_expected_date and m.forecast_expected_date <= get_comparison_date(m))
            elif state == 'late':
                return moves.filtered(lambda m: m.forecast_availability == m.product_qty and m.forecast_expected_date and m.forecast_expected_date > get_comparison_date(m))
            elif state == 'unavailable':
                return moves if moves.filtered(lambda m: m.forecast_availability < m.product_qty) else self.env['stock.move']
            else:
                raise UserError(_('Selection not supported.'))

        if not value:
            raise UserError(_('Search not supported without a value.'))

        # We consider an operation without any moves as always available since there is no goods to wait.
        if len(self) == 0:
            is_selected_available = any(val == 'available' for val in value) if isinstance(value, list) else value == 'available'
            if is_selected_available == (operator in {'=', 'in'}):
                return True
            return False
        moves = self
        if operator == '=':
            moves = get_stock_moves(moves, value)
        elif operator == '!=':
            moves = moves - get_stock_moves(moves, value)
        elif operator == 'in':
            search_moves = self.env['stock.move']
            for state in value:
                search_moves |= get_stock_moves(moves, state)
            moves = search_moves
        elif operator == 'not in':
            search_moves = self.env['stock.move']
            for state in value:
                search_moves |= get_stock_moves(moves, state)
            moves = self - search_moves
        else:
            raise UserError(_('Operation not supported'))
        return len(moves) == len(self)

    def _break_mto_link(self, parent_move):
        self.move_orig_ids = [Command.unlink(parent_move.id)]
        self.procure_method = 'make_to_stock'
        self._recompute_state()

    def _get_product_catalog_lines_data(self, parent_record=False, **kwargs):
        if not (parent_record and self):
            return {
                'quantity': 0,
            }
        self.product_id.ensure_one()
        return {
            **parent_record._get_product_price_and_data(self.product_id),
            'quantity': sum(
                self.mapped(
                    lambda line: line.product_uom._compute_quantity(
                        qty=line.product_qty,
                        to_unit=line.product_uom,
                    ),
                ),
            ),
            'readOnly': False,
        }

    def _is_incoming(self):
        self.ensure_one()
        return self.location_id.usage in ('customer', 'supplier') or (
            self.location_id.usage == 'transit' and not self.location_id.company_id
        )

    def _is_outgoing(self):
        self.ensure_one()
        return self.location_dest_id.usage in ('customer', 'supplier') or (
            self.location_dest_id.usage == 'transit' and not self.location_dest_id.company_id
        )
