# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil import relativedelta
from itertools import groupby
from operator import itemgetter

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

PROCUREMENT_PRIORITIES = [('0', 'Not urgent'), ('1', 'Normal'), ('2', 'Urgent'), ('3', 'Very Urgent')]


class StockMove(models.Model):
    _name = "stock.move"
    _description = "Stock Move"
    _order = 'picking_id, sequence, id'

    def _default_group_id(self):
        if self.env.context.get('default_picking_id'):
            return self.env['stock.picking'].browse(self.env.context['default_picking_id']).group_id.id
        return False

    name = fields.Char('Description', index=True, required=True)
    sequence = fields.Integer('Sequence', default=10)
    priority = fields.Selection(PROCUREMENT_PRIORITIES, 'Priority', default='1')
    create_date = fields.Datetime('Creation Date', index=True, readonly=True)
    date = fields.Datetime(
        'Date', default=fields.Datetime.now, index=True, required=True,
        states={'done': [('readonly', True)]},
        help="Move date: scheduled date until move is done, then date of actual move processing")
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('stock.move'),
        index=True, required=True)
    date_expected = fields.Datetime(
        'Expected Date', default=fields.Datetime.now, index=True, required=True,
        states={'done': [('readonly', True)]},
        help="Scheduled date for the processing of this move")
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('type', 'in', ['product', 'consu'])], index=True, required=True,
        states={'done': [('readonly', True)]})
    product_qty = fields.Float(
        'Real Quantity', compute='_compute_product_qty', inverse='_set_product_qty',
        digits=0, store=True,
        help='Quantity in the default UoM of the product')
    product_uom_qty = fields.Float(
        'Initial Demand',
        digits=dp.get_precision('Product Unit of Measure'),
        default=0.0, required=True, states={'done': [('readonly', True)]},
        help="This is the quantity of products from an inventory "
             "point of view. For moves in the state 'done', this is the "
             "quantity of products that were actually moved. For other "
             "moves, this is the quantity of product that is planned to "
             "be moved. Lowering this quantity does not generate a "
             "backorder. Changing this quantity on assigned moves affects "
             "the product reservation, and should be done with care.")
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure', required=True)
    # TDE FIXME: make it stored, otherwise group will not work
    product_tmpl_id = fields.Many2one(
        'product.template', 'Product Template',
        related='product_id.product_tmpl_id', readonly=False,
        help="Technical: used in views")
    product_packaging = fields.Many2one(
        'product.packaging', 'Preferred Packaging',
        help="It specifies attributes of packaging like type, quantity of packaging,etc.")
    location_id = fields.Many2one(
        'stock.location', 'Source Location',
        auto_join=True, index=True, required=True,
        help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations.")
    location_dest_id = fields.Many2one(
        'stock.location', 'Destination Location',
        auto_join=True, index=True, required=True,
        help="Location where the system will stock the finished products.")
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
    picking_id = fields.Many2one('stock.picking', 'Transfer Reference', index=True, states={'done': [('readonly', True)]})
    picking_partner_id = fields.Many2one('res.partner', 'Transfer Destination Address', related='picking_id.partner_id', readonly=False)
    note = fields.Text('Notes')
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
    price_unit = fields.Float(
        'Unit Price', help="Technical field used to record the product cost set by the user during a picking confirmation (when costing "
                           "method used is 'average price' or 'real'). Value given in company currency and in product uom.", copy=False)  # as it's a technical field, we intentionally don't provide the digits attribute
    backorder_id = fields.Many2one('stock.picking', 'Back Order of', related='picking_id.backorder_id', index=True, readonly=False)
    origin = fields.Char("Source Document")
    procure_method = fields.Selection([
        ('make_to_stock', 'Default: Take From Stock'),
        ('make_to_order', 'Advanced: Apply Procurement Rules')], string='Supply Method',
        default='make_to_stock', required=True,
        help="By default, the system will take from the stock in the source location and passively wait for availability. "
             "The other possibility allows you to directly create a procurement on the source location (and thus ignore "
             "its current stock) to gather products. If we want to chain moves and have this one to wait for the previous, "
             "this second option should be chosen.")
    scrapped = fields.Boolean('Scrapped', related='location_dest_id.scrap_location', readonly=True, store=True)
    scrap_ids = fields.One2many('stock.scrap', 'move_id')
    group_id = fields.Many2one('procurement.group', 'Procurement Group', default=_default_group_id)
    rule_id = fields.Many2one('stock.rule', 'Stock Rule', ondelete='restrict', help='The stock rule that created this stock move')
    propagate = fields.Boolean(
        'Propagate cancel and split', default=True,
        help='If checked, when this move is cancelled, cancel the linked move too')
    picking_type_id = fields.Many2one('stock.picking.type', 'Operation Type')
    inventory_id = fields.Many2one('stock.inventory', 'Inventory')
    move_line_ids = fields.One2many('stock.move.line', 'move_id')
    move_line_nosuggest_ids = fields.One2many('stock.move.line', 'move_id', domain=[('product_qty', '=', 0.0)])
    origin_returned_move_id = fields.Many2one('stock.move', 'Origin return move', copy=False, help='Move that created the return move')
    returned_move_ids = fields.One2many('stock.move', 'origin_returned_move_id', 'All returned moves', help='Optional: all returned moves created from this move')
    reserved_availability = fields.Float(
        'Quantity Reserved', compute='_compute_reserved_availability',
        digits=dp.get_precision('Product Unit of Measure'),
        readonly=True, help='Quantity that has already been reserved for this move')
    availability = fields.Float(
        'Forecasted Quantity', compute='_compute_product_availability',
        readonly=True, help='Quantity in stock that can still be reserved for this move')
    string_availability_info = fields.Text(
        'Availability', compute='_compute_string_qty_information',
        readonly=True, help='Show various information on stock availability for this move')
    restrict_partner_id = fields.Many2one('res.partner', 'Owner ', help="Technical field used to depict a restriction on the ownership of quants to consider when marking this move as 'done'")
    route_ids = fields.Many2many('stock.location.route', 'stock_location_route_move', 'move_id', 'route_id', 'Destination route', help="Preferred route")
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', help="Technical field depicting the warehouse to consider for the route selection on the next procurement (if any).")
    has_tracking = fields.Selection(related='product_id.tracking', string='Product with Tracking')
    quantity_done = fields.Float('Quantity Done', compute='_quantity_done_compute', digits=dp.get_precision('Product Unit of Measure'), inverse='_quantity_done_set')
    show_operations = fields.Boolean(related='picking_id.picking_type_id.show_operations', readonly=False)
    show_details_visible = fields.Boolean('Details Visible', compute='_compute_show_details_visible')
    show_reserved_availability = fields.Boolean('From Supplier', compute='_compute_show_reserved_availability')
    picking_code = fields.Selection(related='picking_id.picking_type_id.code', readonly=True)
    product_type = fields.Selection(related='product_id.type', readonly=True)
    additional = fields.Boolean("Whether the move was added after the picking's confirmation", default=False)
    is_locked = fields.Boolean(compute='_compute_is_locked', readonly=True)
    is_initial_demand_editable = fields.Boolean('Is initial demand editable', compute='_compute_is_initial_demand_editable')
    is_quantity_done_editable = fields.Boolean('Is quantity done editable', compute='_compute_is_quantity_done_editable')
    reference = fields.Char(compute='_compute_reference', string="Reference", store=True)
    has_move_lines = fields.Boolean(compute='_compute_has_move_lines')
    package_level_id = fields.Many2one('stock.package_level', 'Package Level')
    picking_type_entire_packs = fields.Boolean(related='picking_type_id.show_entire_packs', readonly=True)

    @api.depends('picking_id.is_locked')
    def _compute_is_locked(self):
        for move in self:
            if move.picking_id:
                move.is_locked = move.picking_id.is_locked

    @api.depends('product_id', 'has_tracking')
    def _compute_show_details_visible(self):
        """ According to this field, the button that calls `action_show_details` will be displayed
        to work on a move from its picking form view, or not.
        """
        has_package = self.user_has_groups('stock.group_tracking_lot')
        multi_locations_enabled = self.user_has_groups('stock.group_stock_multi_locations')
        consignment_enabled = self.user_has_groups('stock.group_tracking_owner')

        show_details_visible = multi_locations_enabled or consignment_enabled or has_package

        for move in self:
            if not move.product_id:
                move.show_details_visible = False
            else:
                move.show_details_visible = ((show_details_visible or move.has_tracking != 'none') and
                                             (move.state != 'draft' or (move.picking_id.immediate_transfer and move.state == 'draft')) and
                                             move.picking_id.picking_type_id.show_operations is False)

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

    @api.multi
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
    def _compute_has_move_lines(self):
        for move in self:
            move.has_move_lines = bool(move.move_line_ids)

    @api.one
    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_product_qty(self):
        rounding_method = self._context.get('rounding_method', 'UP')
        self.product_qty = self.product_uom._compute_quantity(self.product_uom_qty, self.product_id.uom_id, rounding_method=rounding_method)

    def _get_move_lines(self):
        """ This will return the move lines to consider when applying _quantity_done_compute on a stock.move. 
        In some context, such as MRP, it is necessary to compute quantity_done on filtered sock.move.line."""
        self.ensure_one()
        return self.move_line_ids or self.move_line_nosuggest_ids

    @api.depends('move_line_ids.qty_done', 'move_line_ids.product_uom_id', 'move_line_nosuggest_ids.qty_done')
    def _quantity_done_compute(self):
        """ This field represents the sum of the move lines `qty_done`. It allows the user to know
        if there is still work to do.

        We take care of rounding this value at the general decimal precision and not the rounding
        of the move's UOM to make sure this value is really close to the real sum, because this
        field will be used in `_action_done` in order to know if the move will need a backorder or
        an extra move.
        """
        for move in self:
            quantity_done = 0
            for move_line in move._get_move_lines():
                quantity_done += move_line.product_uom_id._compute_quantity(move_line.qty_done, move.product_uom, round=False)
            move.quantity_done = quantity_done

    def _quantity_done_set(self):
        quantity_done = self[0].quantity_done  # any call to create will invalidate `move.quantity_done`
        for move in self:
            move_lines = move._get_move_lines()
            if not move_lines:
                if quantity_done:
                    # do not impact reservation here
                    move_line = self.env['stock.move.line'].create(dict(move._prepare_move_line_vals(), qty_done=quantity_done))
                    move.write({'move_line_ids': [(4, move_line.id)]})
            elif len(move_lines) == 1:
                move_lines[0].qty_done = quantity_done
            else:
                raise UserError(_("Cannot set the done quantity from this stock move, work directly with the move lines."))

    def _set_product_qty(self):
        """ The meaning of product_qty field changed lately and is now a functional field computing the quantity
        in the default product UoM. This code has been added to raise an error if a write is made given a value
        for `product_qty`, where the same write should set the `product_uom_qty` field instead, in order to
        detect errors. """
        raise UserError(_('The requested operation cannot be processed because of a programming error setting the `product_qty` field instead of the `product_uom_qty`.'))

    @api.multi
    @api.depends('move_line_ids.product_qty')
    def _compute_reserved_availability(self):
        """ Fill the `availability` field on a stock move, which is the actual reserved quantity
        and is represented by the aggregated `product_qty` on the linked move lines. If the move
        is force assigned, the value will be 0.
        """
        result = {data['move_id'][0]: data['product_qty'] for data in 
            self.env['stock.move.line'].read_group([('move_id', 'in', self.ids)], ['move_id','product_qty'], ['move_id'])}
        for rec in self:
            rec.reserved_availability = rec.product_id.uom_id._compute_quantity(result.get(rec.id, 0.0), rec.product_uom, rounding_method='HALF-UP')

    @api.one
    @api.depends('state', 'product_id', 'product_qty', 'location_id')
    def _compute_product_availability(self):
        """ Fill the `availability` field on a stock move, which is the quantity to potentially
        reserve. When the move is done, `availability` is set to the quantity the move did actually
        move.
        """
        if self.state == 'done':
            self.availability = self.product_qty
        else:
            total_availability = self.env['stock.quant']._get_available_quantity(self.product_id, self.location_id)
            self.availability = min(self.product_qty, total_availability)

    def _compute_string_qty_information(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        void_moves = self.filtered(lambda move: move.state in ('draft', 'done', 'cancel') or move.location_id.usage != 'internal')
        other_moves = self - void_moves
        for move in void_moves:
            move.string_availability_info = ''  # 'not applicable' or 'n/a' could work too
        for move in other_moves:
            total_available = min(move.product_qty, move.reserved_availability + move.availability)
            total_available = move.product_id.uom_id._compute_quantity(total_available, move.product_uom, round=False)
            total_available = float_round(total_available, precision_digits=precision)
            info = str(total_available)
            if self.user_has_groups('uom.group_uom'):
                info += ' ' + move.product_uom.name
            if move.reserved_availability:
                if move.reserved_availability != total_available:
                    # some of the available quantity is assigned and some are available but not reserved
                    reserved_available = move.product_id.uom_id._compute_quantity(move.reserved_availability, move.product_uom, round=False)
                    reserved_available = float_round(reserved_available, precision_digits=precision)
                    info += _(' (%s reserved)') % str(reserved_available)
                else:
                    # all available quantity is assigned
                    info += _(' (reserved)')
            move.string_availability_info = info

    @api.constrains('product_uom')
    def _check_uom(self):
        moves_error = self.filtered(lambda move: move.product_id.uom_id.category_id != move.product_uom.category_id)
        if moves_error:
            user_warning = _('You cannot perform the move because the unit of measure has a different category as the product unit of measure.')
            for move in moves_error:
                user_warning += _('\n\n%s --> Product UoM is %s (%s) - Move UoM is %s (%s)') % (move.product_id.display_name, move.product_id.uom_id.name, move.product_id.uom_id.category_id.name, move.product_uom.name, move.product_uom.category_id.name)
            user_warning += _('\n\nBlocking: %s') % ' ,'.join(moves_error.mapped('name'))
            raise UserError(user_warning)

    @api.model_cr
    def init(self):
        self._cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_move_product_location_index',))
        if not self._cr.fetchone():
            self._cr.execute('CREATE INDEX stock_move_product_location_index ON stock_move (product_id, location_id, location_dest_id, company_id, state)')

    @api.model
    def default_get(self, fields_list):
        # We override the default_get to make stock moves created after the picking was confirmed
        # directly as available. This allows to create extra move lines in
        # the fp view.
        defaults = super(StockMove, self).default_get(fields_list)
        if self.env.context.get('default_picking_id'):
            picking_id = self.env['stock.picking'].browse(self.env.context['default_picking_id'])
            if picking_id.state == 'done':
                defaults['state'] = 'done'
                defaults['product_uom_qty'] = 0.0
                defaults['additional'] = True
            elif picking_id.state not in ['draft', 'confirmed']:
                defaults['state'] = 'assigned'
                defaults['product_uom_qty'] = 0.0
                defaults['additional'] = True
        return defaults

    def name_get(self):
        res = []
        for move in self:
            res.append((move.id, '%s%s%s>%s' % (
                move.picking_id.origin and '%s/' % move.picking_id.origin or '',
                move.product_id.code and '%s: ' % move.product_id.code or '',
                move.location_id.name, move.location_dest_id.name)))
        return res

    @api.model_create_multi
    def create(self, vals_list):
        # TDE CLEANME: why doing this tracking on picking here ? seems weird
        tracking = []
        for vals in vals_list:
            if not self.env.context.get('mail_notrack') and vals.get('picking_id'):
                picking = self.env['stock.picking'].browse(vals['picking_id'])
                initial_values = {picking.id: {'state': picking.state}}
                tracking.append((picking, initial_values))
        res = super(StockMove, self).create(vals_list)
        for picking, initial_values in tracking:
            picking.message_track(picking.fields_get(['state']), initial_values)
        return res

    def write(self, vals):
        # FIXME: pim fix your crap
        receipt_moves_to_reassign = self.env['stock.move']
        if 'product_uom_qty' in vals:
            for move in self.filtered(lambda m: m.state not in ('done', 'draft') and m.picking_id):
                if vals['product_uom_qty'] != move.product_uom_qty:
                    self.env['stock.move.line']._log_message(move.picking_id, move, 'stock.track_move_template', vals)
            if self.env.context.get('do_not_unreserve') is None:
                move_to_unreserve = self.filtered(lambda m: m.state not in ['draft', 'done', 'cancel'] and m.reserved_availability > vals.get('product_uom_qty'))
                move_to_unreserve._do_unreserve()
                (self - move_to_unreserve).filtered(lambda m: m.state == 'assigned').write({'state': 'partially_available'})
                # When editing the initial demand, directly run again action assign on receipt moves.
                receipt_moves_to_reassign |= move_to_unreserve.filtered(lambda m: m.location_id.usage == 'supplier')
                receipt_moves_to_reassign |= (self - move_to_unreserve).filtered(lambda m: m.location_id.usage == 'supplier' and m.state in ('partially_available', 'assigned'))

        # TDE CLEANME: it is a gros bordel + tracking
        Picking = self.env['stock.picking']

        propagated_changes_dict = {}
        #propagation of expected date:
        propagated_date_field = False
        if vals.get('date_expected'):
            #propagate any manual change of the expected date
            propagated_date_field = 'date_expected'
        elif (vals.get('state', '') == 'done' and vals.get('date')):
            #propagate also any delta observed when setting the move as done
            propagated_date_field = 'date'

        if not self._context.get('do_not_propagate', False) and (propagated_date_field or propagated_changes_dict):
            #any propagation is (maybe) needed
            for move in self:
                if move.move_dest_ids and move.propagate:
                    if 'date_expected' in propagated_changes_dict:
                        propagated_changes_dict.pop('date_expected')
                    if propagated_date_field:
                        current_date = move.date_expected
                        new_date = fields.Datetime.from_string(vals.get(propagated_date_field))
                        delta_days = (new_date - current_date).total_seconds() / 86400
                        if abs(delta_days) >= move.company_id.propagation_minimum_delta:
                            old_move_date = move.move_dest_ids[0].date_expected
                            new_move_date = (old_move_date + relativedelta.relativedelta(days=delta_days or 0)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                            propagated_changes_dict['date_expected'] = new_move_date
                    #For pushed moves as well as for pulled moves, propagate by recursive call of write().
                    #Note that, for pulled moves we intentionally don't propagate on the procurement.
                    if propagated_changes_dict:
                        move.move_dest_ids.filtered(lambda m: m.state not in ('done', 'cancel')).write(propagated_changes_dict)
        track_pickings = not self._context.get('mail_notrack') and any(field in vals for field in ['state', 'picking_id', 'partially_available'])
        if track_pickings:
            to_track_picking_ids = set([move.picking_id.id for move in self if move.picking_id])
            if vals.get('picking_id'):
                to_track_picking_ids.add(vals['picking_id'])
            to_track_picking_ids = list(to_track_picking_ids)
            pickings = Picking.browse(to_track_picking_ids)
            initial_values = dict((picking.id, {'state': picking.state}) for picking in pickings)
        res = super(StockMove, self).write(vals)
        if track_pickings:
            pickings.message_track(pickings.fields_get(['state']), initial_values)
        if receipt_moves_to_reassign:
            receipt_moves_to_reassign._action_assign()
        return res

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
        if self.picking_id.picking_type_id.show_reserved:
            view = self.env.ref('stock.view_stock_move_operations')
        else:
            view = self.env.ref('stock.view_stock_move_nosuggest_operations')

        return {
            'name': _('Detailed Operations'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.move',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.id,
            'context': dict(
                self.env.context,
                show_lots_m2o=self.has_tracking != 'none' and (self.picking_type_id.use_existing_lots or self.state == 'done' or self.origin_returned_move_id.id),  # able to create lots, whatever the value of ` use_create_lots`.
                show_lots_text=self.has_tracking != 'none' and self.picking_type_id.use_create_lots and not self.picking_type_id.use_existing_lots and self.state != 'done' and not self.origin_returned_move_id.id,
                show_source_location=self.location_id.child_ids and self.picking_type_id.code != 'incoming',
                show_destination_location=self.location_dest_id.child_ids and self.picking_type_id.code != 'outgoing',
                show_package=not self.location_id.usage == 'supplier',
                show_reserved_quantity=self.state != 'done'
            ),
        }

    def _do_unreserve(self):
        moves_to_unreserve = self.env['stock.move']
        for move in self:
            if move.state == 'cancel':
                # We may have cancelled move in an open picking in a "propagate_cancel" scenario.
                continue
            if move.state == 'done':
                if move.scrapped:
                    # We may have done move in an open picking in a scrap scenario.
                    continue
                else:
                    raise UserError(_('You cannot unreserve a stock move that has been set to \'Done\'.'))
            moves_to_unreserve |= move
        moves_to_unreserve.mapped('move_line_ids').unlink()
        return True

    def _push_apply(self):
        for move in self:
            # if the move is already chained, there is no need to check push rules
            if move.move_dest_ids:
                continue
            # if the move is a returned move, we don't want to check push rules, as returning a returned move is the only decent way
            # to receive goods without triggering the push rules again (which would duplicate chained operations)
            domain = [('location_src_id', '=', move.location_dest_id.id), ('action', 'in', ('push', 'pull_push'))]
            # first priority goes to the preferred routes defined on the move itself (e.g. coming from a SO line)
            warehouse_id = move.warehouse_id or move.picking_id.picking_type_id.warehouse_id
            rules = self.env['procurement.group']._search_rule(move.route_ids, move.product_id, warehouse_id, domain)

            # Make sure it is not returning the return
            if rules and (not move.origin_returned_move_id or move.origin_returned_move_id.location_dest_id.id != rules.location_id.id):
                rules._run_push(move)

    def _merge_moves_fields(self):
        """ This method will return a dict of stock move’s values that represent the values of all moves in `self` merged. """
        state = self._get_relevant_state_among_moves()
        origin = '/'.join(set(self.filtered(lambda m: m.origin).mapped('origin')))
        return {
            'product_uom_qty': sum(self.mapped('product_uom_qty')),
            'date': min(self.mapped('date')),
            'date_expected': min(self.mapped('date_expected')) if self.mapped('picking_id').move_type == 'direct' else max(self.mapped('date_expected')),
            'move_dest_ids': [(4, m.id) for m in self.mapped('move_dest_ids')],
            'move_orig_ids': [(4, m.id) for m in self.mapped('move_orig_ids')],
            'state': state,
            'origin': origin,
        }

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        return [
            'product_id', 'price_unit', 'product_packaging', 'procure_method',
            'product_uom', 'restrict_partner_id', 'scrapped', 'origin_returned_move_id',
            'package_level_id'
        ]

    @api.model
    def _prepare_merge_move_sort_method(self, move):
        move.ensure_one()
        return [
            move.product_id.id, move.price_unit, move.product_packaging.id, move.procure_method, 
            move.product_uom.id, move.restrict_partner_id.id, move.scrapped, move.origin_returned_move_id.id,
            move.package_level_id.id
        ]

    def _clean_merged(self):
        """Cleanup hook used when merging moves"""
        self.write({'propagate': False})

    def _merge_moves(self, merge_into=False):
        """ This method will, for each move in `self`, go up in their linked picking and try to
        find in their existing moves a candidate into which we can merge the move.
        :return: Recordset of moves passed to this method. If some of the passed moves were merged
        into another existing one, return this one and not the (now unlinked) original.
        """
        distinct_fields = self._prepare_merge_moves_distinct_fields()

        candidate_moves_list = []
        if not merge_into:
            for picking in self.mapped('picking_id'):
                candidate_moves_list.append(picking.move_lines)
        else:
            candidate_moves_list.append(merge_into | self)

        # Move removed after merge
        moves_to_unlink = self.env['stock.move']
        moves_to_merge = []
        for candidate_moves in candidate_moves_list:
            # First step find move to merge.
            candidate_moves = candidate_moves.with_context(prefetch_fields=False)
            for k, g in groupby(sorted(candidate_moves, key=self._prepare_merge_move_sort_method), key=itemgetter(*distinct_fields)):
                moves = self.env['stock.move'].concat(*g).filtered(lambda m: m.state not in ('done', 'cancel', 'draft'))
                # If we have multiple records we will merge then in a single one.
                if len(moves) > 1:
                    moves_to_merge.append(moves)

        # second step merge its move lines, initial demand, ...
        for moves in moves_to_merge:
            # link all move lines to record 0 (the one we will keep).
            moves.mapped('move_line_ids').write({'move_id': moves[0].id})
            # merge move data
            moves[0].write(moves._merge_moves_fields())
            # update merged moves dicts
            moves_to_unlink |= moves[1:]

        if moves_to_unlink:
            # We are using propagate to False in order to not cancel destination moves merged in moves[0]
            moves_to_unlink._clean_merged()
            moves_to_unlink._action_cancel()
            moves_to_unlink.sudo().unlink()
        return (self | self.env['stock.move'].concat(*moves_to_merge)) - moves_to_unlink

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
            .filtered(lambda move: move.state not in ['cancel', 'done'])\
            .sorted(key=lambda move: (sort_map.get(move.state, 0), move.product_uom_qty))
        # The picking should be the same for all moves.
        if moves_todo[0].picking_id and moves_todo[0].picking_id.move_type == 'one':
            most_important_move = moves_todo[0]
            if most_important_move.state == 'confirmed':
                return 'confirmed' if most_important_move.product_uom_qty else 'assigned'
            elif most_important_move.state == 'partially_available':
                return 'confirmed'
            else:
                return moves_todo[0].state or 'draft'
        elif moves_todo[0].state != 'assigned' and any(move.state in ['assigned', 'partially_available'] for move in moves_todo):
            return 'partially_available'
        else:
            least_important_move = moves_todo[-1]
            if least_important_move.state == 'confirmed' and least_important_move.product_uom_qty == 0:
                return 'assigned'
            else:
                return moves_todo[-1].state or 'draft'

    @api.onchange('product_id', 'product_qty')
    def onchange_quantity(self):
        if not self.product_id or self.product_qty < 0.0:
            self.product_qty = 0.0
        if self.product_qty < self._origin.product_qty:
            warning_mess = {
                'title': _('Quantity decreased!'),
                'message' : _("By changing this quantity here, you accept the "
                              "new quantity as complete: Odoo will not "
                              "automatically generate a back order."),
            }
            return {'warning': warning_mess}

    @api.onchange('product_id')
    def onchange_product_id(self):
        product = self.product_id.with_context(lang=self.partner_id.lang or self.env.user.lang)
        self.name = product.partner_ref
        self.product_uom = product.uom_id.id
        return {'domain': {'product_uom': [('category_id', '=', product.uom_id.category_id.id)]}}

    @api.onchange('date_expected')
    def onchange_date(self):
        if self.date_expected:
            self.date = self.date_expected

    @api.onchange('product_uom')
    def onchange_product_uom(self):
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

    def _search_picking_for_assignation(self):
        self.ensure_one()
        picking = self.env['stock.picking'].search([
                ('group_id', '=', self.group_id.id),
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_dest_id.id),
                ('picking_type_id', '=', self.picking_type_id.id),
                ('printed', '=', False),
                ('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])], limit=1)
        return picking

    def _assign_picking(self):
        """ Try to assign the moves to an existing picking that has not been
        reserved yet and has the same procurement group, locations and picking
        type (moves should already have them identical). Otherwise, create a new
        picking to assign them to. """
        Picking = self.env['stock.picking']
        for move in self:
            recompute = False
            picking = move._search_picking_for_assignation()
            if picking:
                if picking.partner_id.id != move.partner_id.id or picking.origin != move.origin:
                    # If a picking is found, we'll append `move` to its move list and thus its
                    # `partner_id` and `ref` field will refer to multiple records. In this
                    # case, we chose to  wipe them.
                    picking.write({
                        'partner_id': False,
                        'origin': False,
                    })
            else:
                recompute = True
                picking = Picking.create(move._get_new_picking_values())
            move.write({'picking_id': picking.id})
            move._assign_picking_post_process(new=recompute)
            # If this method is called in batch by a write on a one2many and
            # at some point had to create a picking, some next iterations could
            # try to find back the created picking. As we look for it by searching
            # on some computed fields, we have to force a recompute, else the
            # record won't be found.
            if recompute:
                move.recompute()
        return True

    def _assign_picking_post_process(self, new=False):
        pass

    def _get_new_picking_values(self):
        """ Prepares a new picking for this move as it could not be assigned to
        another picking. This method is designed to be inherited. """
        return {
            'origin': self.origin,
            'company_id': self.company_id.id,
            'move_type': self.group_id and self.group_id.move_type or 'direct',
            'partner_id': self.partner_id.id,
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
        }

    def _should_be_assigned(self):
        self.ensure_one()
        return bool(not self.picking_id and self.picking_type_id)

    def _action_confirm(self, merge=True, merge_into=False):
        """ Confirms stock move or put it in waiting if it's linked to another move.
        :param: merge: According to this boolean, a newly confirmed move will be merged
        in another move of the same picking sharing its characteristics.
        """
        move_create_proc = self.env['stock.move']
        move_to_confirm = self.env['stock.move']
        move_waiting = self.env['stock.move']

        to_assign = {}
        for move in self:
            # if the move is preceeded, then it's waiting (if preceeding move is done, then action_assign has been called already and its state is already available)
            if move.move_orig_ids:
                move_waiting |= move
            else:
                if move.procure_method == 'make_to_order':
                    move_create_proc |= move
                else:
                    move_to_confirm |= move
            if move._should_be_assigned():
                key = (move.group_id.id, move.location_id.id, move.location_dest_id.id)
                if key not in to_assign:
                    to_assign[key] = self.env['stock.move']
                to_assign[key] |= move

        # create procurements for make to order moves
        for move in move_create_proc:
            values = move._prepare_procurement_values()
            origin = (move.group_id and move.group_id.name or (move.origin or move.picking_id.name or "/"))
            self.env['procurement.group'].run(move.product_id, move.product_uom_qty, move.product_uom, move.location_id, move.rule_id and move.rule_id.name or "/", origin,
                                              values)

        move_to_confirm.write({'state': 'confirmed'})
        (move_waiting | move_create_proc).write({'state': 'waiting'})

        # assign picking in batch for all confirmed move that share the same details
        for moves in to_assign.values():
            moves._assign_picking()
        self._push_apply()
        if merge:
            return self._merge_moves(merge_into=merge_into)
        return self

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
        return {
            'company_id': self.company_id,
            'date_planned': self.date_expected,
            'move_dest_ids': self,
            'group_id': group_id,
            'route_ids': self.route_ids,
            'warehouse_id': self.warehouse_id or self.picking_id.picking_type_id.warehouse_id or self.picking_type_id.warehouse_id,
            'priority': self.priority,
        }

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        self.ensure_one()
        # apply putaway
        location_dest_id = self.location_dest_id.get_putaway_strategy(self.product_id).id or self.location_dest_id.id
        vals = {
            'move_id': self.id,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'location_id': self.location_id.id,
            'location_dest_id': location_dest_id,
            'picking_id': self.picking_id.id,
        }
        if quantity:
            uom_quantity = self.product_id.uom_id._compute_quantity(quantity, self.product_uom, rounding_method='HALF-UP')
            uom_quantity_back_to_product_uom = self.product_uom._compute_quantity(uom_quantity, self.product_id.uom_id, rounding_method='HALF-UP')
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(quantity, uom_quantity_back_to_product_uom, precision_digits=rounding) == 0:
                vals = dict(vals, product_uom_qty=uom_quantity)
            else:
                vals = dict(vals, product_uom_qty=quantity, product_uom_id=self.product_id.uom_id.id)
        if reserved_quant:
            vals = dict(
                vals,
                location_id=reserved_quant.location_id.id,
                lot_id=reserved_quant.lot_id.id or False,
                package_id=reserved_quant.package_id.id or False,
                owner_id =reserved_quant.owner_id.id or False,
            )
        return vals

    def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None, owner_id=None, strict=True):
        """ Create or update move lines.
        """
        self.ensure_one()

        if not lot_id:
            lot_id = self.env['stock.production.lot']
        if not package_id:
            package_id = self.env['stock.quant.package']
        if not owner_id:
            owner_id = self.env['res.partner']

        taken_quantity = min(available_quantity, need)

        # `taken_quantity` is in the quants unit of measure. There's a possibility that the move's
        # unit of measure won't be respected if we blindly reserve this quantity, a common usecase
        # is if the move's unit of measure's rounding does not allow fractional reservation. We chose
        # to convert `taken_quantity` to the move's unit of measure with a down rounding method and
        # then get it back in the quants unit of measure with an half-up rounding_method. This
        # way, we'll never reserve more than allowed. We do not apply this logic if
        # `available_quantity` is brought by a chained move line. In this case, `_prepare_move_line_vals`
        # will take care of changing the UOM to the UOM of the product.
        if not strict:
            taken_quantity_move_uom = self.product_id.uom_id._compute_quantity(taken_quantity, self.product_uom, rounding_method='DOWN')
            taken_quantity = self.product_uom._compute_quantity(taken_quantity_move_uom, self.product_id.uom_id, rounding_method='HALF-UP')

        quants = []

        if self.product_id.tracking == 'serial':
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(taken_quantity, int(taken_quantity), precision_digits=rounding) != 0:
                taken_quantity = 0

        try:
            if not float_is_zero(taken_quantity, precision_rounding=self.product_id.uom_id.rounding):
                quants = self.env['stock.quant']._update_reserved_quantity(
                    self.product_id, location_id, taken_quantity, lot_id=lot_id,
                    package_id=package_id, owner_id=owner_id, strict=strict
                )
        except UserError:
            taken_quantity = 0

        # Find a candidate move line to update or create a new one.
        for reserved_quant, quantity in quants:
            to_update = self.move_line_ids.filtered(lambda m: m.product_id.tracking != 'serial' and
                                                    m.location_id.id == reserved_quant.location_id.id and m.lot_id.id == reserved_quant.lot_id.id and m.package_id.id == reserved_quant.package_id.id and m.owner_id.id == reserved_quant.owner_id.id)
            if to_update:
                to_update[0].with_context(bypass_reservation_update=True).product_uom_qty += self.product_id.uom_id._compute_quantity(quantity, to_update[0].product_uom_id, rounding_method='HALF-UP')
            else:
                if self.product_id.tracking == 'serial':
                    for i in range(0, int(quantity)):
                        self.env['stock.move.line'].create(self._prepare_move_line_vals(quantity=1, reserved_quant=reserved_quant))
                else:
                    self.env['stock.move.line'].create(self._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant))
        return taken_quantity

    def _action_assign(self):
        """ Reserve stock moves by creating their stock move lines. A stock move is
        considered reserved once the sum of `product_qty` for all its move lines is
        equal to its `product_qty`. If it is less, the stock move is considered
        partially available.
        """
        assigned_moves = self.env['stock.move']
        partially_available_moves = self.env['stock.move']
        for move in self.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available']):
            missing_reserved_uom_quantity = move.product_uom_qty - move.reserved_availability
            missing_reserved_quantity = move.product_uom._compute_quantity(missing_reserved_uom_quantity, move.product_id.uom_id, rounding_method='HALF-UP')
            if move.location_id.should_bypass_reservation()\
                    or move.product_id.type == 'consu':
                # create the move line(s) but do not impact quants
                if move.product_id.tracking == 'serial' and (move.picking_type_id.use_create_lots or move.picking_type_id.use_existing_lots):
                    for i in range(0, int(missing_reserved_quantity)):
                        self.env['stock.move.line'].create(move._prepare_move_line_vals(quantity=1))
                else:
                    to_update = move.move_line_ids.filtered(lambda ml: ml.product_uom_id == move.product_uom and
                                                            ml.location_id == move.location_id and
                                                            ml.location_dest_id == move.location_dest_id and
                                                            ml.picking_id == move.picking_id and
                                                            not ml.lot_id and
                                                            not ml.package_id and
                                                            not ml.owner_id)
                    if to_update:
                        to_update[0].product_uom_qty += missing_reserved_uom_quantity
                    else:
                        self.env['stock.move.line'].create(move._prepare_move_line_vals(quantity=missing_reserved_quantity))
                assigned_moves |= move
            else:
                if not move.move_orig_ids:
                    if move.procure_method == 'make_to_order':
                        continue
                    # If we don't need any quantity, consider the move assigned.
                    need = missing_reserved_quantity
                    if float_is_zero(need, precision_rounding=move.product_id.uom_id.rounding):
                        assigned_moves |= move
                        continue
                    # Reserve new quants and create move lines accordingly.
                    forced_package_id = move.package_level_id.package_id or None
                    available_quantity = self.env['stock.quant']._get_available_quantity(move.product_id, move.location_id, package_id=forced_package_id)
                    if available_quantity <= 0:
                        continue
                    taken_quantity = move._update_reserved_quantity(need, available_quantity, move.location_id, package_id=forced_package_id, strict=False)
                    if float_is_zero(taken_quantity, precision_rounding=move.product_id.uom_id.rounding):
                        continue
                    if need == taken_quantity:
                        assigned_moves |= move
                    else:
                        partially_available_moves |= move
                else:
                    # Check what our parents brought and what our siblings took in order to
                    # determine what we can distribute.
                    # `qty_done` is in `ml.product_uom_id` and, as we will later increase
                    # the reserved quantity on the quants, convert it here in
                    # `product_id.uom_id` (the UOM of the quants is the UOM of the product).
                    move_lines_in = move.move_orig_ids.filtered(lambda m: m.state == 'done').mapped('move_line_ids')
                    keys_in_groupby = ['location_dest_id', 'lot_id', 'result_package_id', 'owner_id']

                    def _keys_in_sorted(ml):
                        return (ml.location_dest_id.id, ml.lot_id.id, ml.result_package_id.id, ml.owner_id.id)

                    grouped_move_lines_in = {}
                    for k, g in groupby(sorted(move_lines_in, key=_keys_in_sorted), key=itemgetter(*keys_in_groupby)):
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
                    moves_out_siblings_to_consider = moves_out_siblings & (assigned_moves + partially_available_moves)
                    reserved_moves_out_siblings = moves_out_siblings.filtered(lambda m: m.state in ['partially_available', 'assigned'])
                    move_lines_out_reserved = (reserved_moves_out_siblings | moves_out_siblings_to_consider).mapped('move_line_ids')
                    keys_out_groupby = ['location_id', 'lot_id', 'package_id', 'owner_id']

                    def _keys_out_sorted(ml):
                        return (ml.location_id.id, ml.lot_id.id, ml.package_id.id, ml.owner_id.id)

                    grouped_move_lines_out = {}
                    for k, g in groupby(sorted(move_lines_out_done, key=_keys_out_sorted), key=itemgetter(*keys_out_groupby)):
                        qty_done = 0
                        for ml in g:
                            qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
                        grouped_move_lines_out[k] = qty_done
                    for k, g in groupby(sorted(move_lines_out_reserved, key=_keys_out_sorted), key=itemgetter(*keys_out_groupby)):
                        grouped_move_lines_out[k] = sum(self.env['stock.move.line'].concat(*list(g)).mapped('product_qty'))
                    available_move_lines = {key: grouped_move_lines_in[key] - grouped_move_lines_out.get(key, 0) for key in grouped_move_lines_in.keys()}
                    # pop key if the quantity available amount to 0
                    available_move_lines = dict((k, v) for k, v in available_move_lines.items() if v)

                    if not available_move_lines:
                        continue
                    for move_line in move.move_line_ids.filtered(lambda m: m.product_qty):
                        if available_move_lines.get((move_line.location_id, move_line.lot_id, move_line.result_package_id, move_line.owner_id)):
                            available_move_lines[(move_line.location_id, move_line.lot_id, move_line.result_package_id, move_line.owner_id)] -= move_line.product_qty
                    for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
                        need = move.product_qty - sum(move.move_line_ids.mapped('product_qty'))
                        # `quantity` is what is brought by chained done move lines. We double check
                        # here this quantity is available on the quants themselves. If not, this
                        # could be the result of an inventory adjustment that removed totally of
                        # partially `quantity`. When this happens, we chose to reserve the maximum
                        # still available. This situation could not happen on MTS move, because in
                        # this case `quantity` is directly the quantity on the quants themselves.
                        available_quantity = self.env['stock.quant']._get_available_quantity(
                            move.product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True)
                        if float_is_zero(available_quantity, precision_rounding=move.product_id.uom_id.rounding):
                            continue
                        taken_quantity = move._update_reserved_quantity(need, min(quantity, available_quantity), location_id, lot_id, package_id, owner_id)
                        if float_is_zero(taken_quantity, precision_rounding=move.product_id.uom_id.rounding):
                            continue
                        if need - taken_quantity == 0.0:
                            assigned_moves |= move
                            break
                        partially_available_moves |= move
        partially_available_moves.write({'state': 'partially_available'})
        assigned_moves.write({'state': 'assigned'})
        self.mapped('picking_id')._check_entire_pack()

    def _action_cancel(self):
        if any(move.state == 'done' for move in self):
            raise UserError(_('You cannot cancel a stock move that has been set to \'Done\'.'))
        for move in self:
            if move.state == 'cancel':
                continue
            move._do_unreserve()
            siblings_states = (move.move_dest_ids.mapped('move_orig_ids') - move).mapped('state')
            if move.propagate:
                # only cancel the next move if all my siblings are also cancelled
                if all(state == 'cancel' for state in siblings_states):
                    move.move_dest_ids.filtered(lambda m: m.state != 'done')._action_cancel()
            else:
                if all(state in ('done', 'cancel') for state in siblings_states):
                    move.move_dest_ids.write({'procure_method': 'make_to_stock'})
                    move.move_dest_ids.write({'move_orig_ids': [(3, move.id, 0)]})
        self.write({'state': 'cancel', 'move_orig_ids': [(5, 0, 0)]})
        return True

    def _prepare_extra_move_vals(self, qty):
        vals = {
            'origin_returned_move_id': self.origin_returned_move_id.id,
            'product_uom_qty': qty,
            'picking_id': self.picking_id.id,
            'price_unit': self.price_unit,
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
            extra_move = self.copy(default=extra_move_vals)
            if extra_move.picking_id:
                extra_move = extra_move._action_confirm(merge_into=self)
            else:
                extra_move = extra_move._action_confirm()

            # link it to some move lines. We don't need to do it for move since they should be merged.
            if self.exists() and not self.picking_id:
                for move_line in self.move_line_ids.filtered(lambda ml: ml.qty_done):
                    if float_compare(move_line.qty_done, extra_move_quantity, precision_rounding=rounding) <= 0:
                        # move this move line to our extra move
                        move_line.move_id = extra_move.id
                        extra_move_quantity -= move_line.qty_done
                    else:
                        # split this move line and assign the new part to our extra move
                        quantity_split = float_round(
                            move_line.qty_done - extra_move_quantity,
                            precision_rounding=self.product_uom.rounding,
                            rounding_method='UP')
                        move_line.qty_done = quantity_split
                        move_line.copy(default={'move_id': extra_move.id, 'qty_done': extra_move_quantity, 'product_uom_qty': 0})
                        extra_move_quantity -= extra_move_quantity
                    if extra_move_quantity == 0.0:
                        break
        return extra_move

    def _unreserve_initial_demand(self, new_move):
        pass

    def _action_done(self, cancel_backorder=False):
        self.filtered(lambda move: move.state == 'draft')._action_confirm()  # MRP allows scrapping draft moves
        moves = self.exists().filtered(lambda x: x.state not in ('done', 'cancel'))
        moves_todo = self.env['stock.move']

        # Cancel moves where necessary ; we should do it before creating the extra moves because
        # this operation could trigger a merge of moves.
        for move in moves:
            if move.quantity_done <= 0:
                if float_compare(move.product_uom_qty, 0.0, precision_rounding=move.product_uom.rounding) == 0:
                    move._action_cancel()

        # Create extra moves where necessary
        for move in moves:
            if move.state == 'cancel' or move.quantity_done <= 0:
                continue
            # extra move will not be merged in mrp
            if not move.picking_id:
                moves_todo |= move
            moves_todo |= move._create_extra_move()

        # Split moves where necessary and move quants
        for move in moves_todo:
            # To know whether we need to create a backorder or not, round to the general product's
            # decimal precision and not the product's UOM.
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(move.quantity_done, move.product_uom_qty, precision_digits=rounding) < 0:
                # Need to do some kind of conversion here
                qty_split = move.product_uom._compute_quantity(move.product_uom_qty - move.quantity_done, move.product_id.uom_id, rounding_method='HALF-UP')
                new_move = move._split(qty_split)
                for move_line in move.move_line_ids:
                    if move_line.product_qty and move_line.qty_done:
                        # FIXME: there will be an issue if the move was partially available
                        # By decreasing `product_qty`, we free the reservation.
                        # FIXME: if qty_done > product_qty, this could raise if nothing is in stock
                        try:
                            move_line.write({'product_uom_qty': move_line.qty_done})
                        except UserError:
                            pass
                move._unreserve_initial_demand(new_move)
                if cancel_backorder:
                    self.env['stock.move'].browse(new_move)._action_cancel()
        moves_todo.mapped('move_line_ids')._action_done()
        # Check the consistency of the result packages; there should be an unique location across
        # the contained quants.
        for result_package in moves_todo\
                .mapped('move_line_ids.result_package_id')\
                .filtered(lambda p: p.quant_ids and len(p.quant_ids) > 1):
            if len(result_package.quant_ids.mapped('location_id')) > 1:
                raise UserError(_('You cannot move the same package content more than once in the same transfer or split the same package into two location.'))
        picking = moves_todo and moves_todo[0].picking_id or False
        moves_todo.write({'state': 'done', 'date': fields.Datetime.now()})
        moves_todo.mapped('move_dest_ids')._action_assign()

        # We don't want to create back order for scrap moves
        if all(move_todo.scrapped for move_todo in moves_todo):
            return moves_todo

        if picking and not cancel_backorder:
            picking._create_backorder()
        return moves_todo

    def unlink(self):
        if any(move.state not in ('draft', 'cancel') for move in self):
            raise UserError(_('You can only delete draft moves.'))
        # With the non plannified picking, draft moves could have some move lines.
        self.mapped('move_line_ids').unlink()
        return super(StockMove, self).unlink()

    def _prepare_move_split_vals(self, qty):
        vals = {
            'product_uom_qty': qty,
            'procure_method': 'make_to_stock',
            'move_dest_ids': [(4, x.id) for x in self.move_dest_ids if x.state not in ('done', 'cancel')],
            'move_orig_ids': [(4, x.id) for x in self.move_orig_ids],
            'origin_returned_move_id': self.origin_returned_move_id.id,
            'price_unit': self.price_unit,
        }
        if self.env.context.get('force_split_uom_id'):
            vals['product_uom'] = self.env.context['force_split_uom_id']
        return vals

    def _split(self, qty, restrict_partner_id=False):
        """ Splits qty from move move into a new move

        :param qty: float. quantity to split (given in product UoM)
        :param restrict_partner_id: optional partner that can be given in order to force the new move to restrict its choice of quants to the ones belonging to this partner.
        :param context: dictionay. can contains the special key 'source_location_id' in order to force the source location when copying the move
        :returns: id of the backorder move created """
        self = self.with_prefetch() # This makes the ORM only look for one record and not 300 at a time, which improves performance
        if self.state in ('done', 'cancel'):
            raise UserError(_('You cannot split a stock move that has been set to \'Done\'.'))
        elif self.state == 'draft':
            # we restrict the split of a draft move because if not confirmed yet, it may be replaced by several other moves in
            # case of phantom bom (with mrp module). And we don't want to deal with this complexity by copying the product that will explode.
            raise UserError(_('You cannot split a draft move. It needs to be confirmed first.'))
        if float_is_zero(qty, precision_rounding=self.product_id.uom_id.rounding) or self.product_qty <= qty:
            return self.id

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
        new_move = self.with_context(rounding_method='HALF-UP').copy(defaults)

        # FIXME: pim fix your crap
        # Update the original `product_qty` of the move. Use the general product's decimal
        # precision and not the move's UOM to handle case where the `quantity_done` is not
        # compatible with the move's UOM.
        new_product_qty = self.product_id.uom_id._compute_quantity(self.product_qty - qty, self.product_uom, round=False)
        new_product_qty = float_round(new_product_qty, precision_digits=self.env['decimal.precision'].precision_get('Product Unit of Measure'))
        self.with_context(do_not_propagate=True, do_not_unreserve=True, rounding_method='HALF-UP').write({'product_uom_qty': new_product_qty})
        new_move = new_move._action_confirm(merge=False)
        return new_move.id

    def _recompute_state(self):
        for move in self:
            if move.reserved_availability == move.product_uom_qty:
                move.state = 'assigned'
            elif move.reserved_availability and move.reserved_availability <= move.product_uom_qty:
                move.state = 'partially_available'
            else:
                if move.procure_method == 'make_to_order' and not move.move_orig_ids:
                    move.state = 'waiting'
                elif move.move_orig_ids and not all(orig.state in ('done', 'cancel') for orig in move.move_orig_ids):
                    move.state = 'waiting'
                else:
                    move.state = 'confirmed'

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
            return [(self.picking_id, self.product_id.responsible_id, visited)]

    def _set_quantity_done(self, qty):
        """
        Set the given quantity as quantity done on the move through the move lines. The method is
        able to handle move lines with a different UoM than the move (but honestly, this would be
        looking for trouble...).
        @param qty: quantity in the UoM of move.product_uom
        """
        for ml in self.move_line_ids:
            # Convert move line qty into move uom
            ml_qty = ml.product_uom_qty - ml.qty_done
            if ml.product_uom_id != self.product_uom:
                ml_qty = ml.product_uom_id._compute_quantity(ml_qty, self.product_uom, round=False)

            taken_qty = min(qty, ml_qty)
            # Convert taken qty into move line uom
            if ml.product_uom_id != self.product_uom:
                taken_qty = self.product_uom._compute_quantity(ml_qty, ml.product_uom_id, round=False)

            # Assign qty_done and explicitly round to make sure there is no inconsistency between
            # ml.qty_done and qty.
            taken_qty = float_round(taken_qty, precision_rounding=ml.product_uom_id.rounding)
            ml.qty_done += taken_qty
            if ml.product_uom_id != self.product_uom:
                taken_qty = ml.product_uom_id._compute_quantity(ml_qty, self.product_uom, round=False)
            qty -= taken_qty

            if float_compare(qty, 0.0,  precision_rounding=self.product_uom.rounding) <= 0:
                break
        if float_compare(qty, 0.0,  precision_rounding=self.product_uom.rounding) > 0:
            vals = self._prepare_move_line_vals(quantity=0)
            vals['qty_done'] = qty
            ml = self.env['stock.move.line'].create(vals)
