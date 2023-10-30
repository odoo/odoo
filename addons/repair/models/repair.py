# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero, clean_context
from odoo.tools.misc import format_date, groupby

MAP_REPAIR_TO_PICKING_LOCATIONS = {
    'location_id': 'default_location_src_id',
    'location_dest_id': 'default_location_dest_id',
    'parts_location_id': 'default_remove_location_dest_id',
    'recycle_location_id': 'default_recycle_location_dest_id',
}


class Repair(models.Model):
    """ Repair Orders """
    _name = 'repair.order'
    _description = 'Repair Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, create_date desc'
    _check_company_auto = True

    @api.model
    def _default_picking_type_id(self):
        return self._get_picking_type().get((self.env.company, self.env.user))

    # Common Fields
    name = fields.Char(
        'Repair Reference',
        default='New', index='trigram',
        copy=False, required=True,
        readonly=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        readonly=True, required=True, index=True,
        default=lambda self: self.env.company)
    state = fields.Selection([
        ('draft', 'New'),
        ('confirmed', 'Confirmed'),
        ('under_repair', 'Under Repair'),
        ('done', 'Repaired'),
        ('cancel', 'Cancelled')], string='Status',
        copy=False, default='draft', readonly=True, tracking=True, index=True,
        help="* The \'New\' status is used when a user is encoding a new and unconfirmed repair order.\n"
             "* The \'Confirmed\' status is used when a user confirms the repair order.\n"
             "* The \'Under Repair\' status is used when the repair is ongoing.\n"
             "* The \'Repaired\' status is set when repairing is completed.\n"
             "* The \'Cancelled\' status is used when user cancel repair order.")
    priority = fields.Selection([('0', 'Normal'), ('1', 'Urgent')], default='0', string="Priority")
    partner_id = fields.Many2one(
        'res.partner', 'Customer',
        index=True, check_company=True, change_default=True,
        help='Choose partner for whom the order will be invoiced and delivered. You can find a partner by its Name, TIN, Email or Internal Reference.')
    user_id = fields.Many2one('res.users', string="Responsible", default=lambda self: self.env.user, check_company=True)

    # Specific Fields
    internal_notes = fields.Html('Internal Notes')
    tag_ids = fields.Many2many('repair.tags', string="Tags")
    under_warranty = fields.Boolean(
        'Under Warranty',
        help='If ticked, the sales price will be set to 0 for all products transferred from the repair order.')
    schedule_date = fields.Datetime("Scheduled Date", default=fields.Datetime.now, index=True, required=True, copy=False)

    # Product To Repair
    move_id = fields.Many2one(  # Generated in 'action_repair_done', needed for traceability
        'stock.move', 'Inventory Move',
        copy=False, readonly=True, tracking=True, check_company=True)
    product_id = fields.Many2one(
        'product.product', string='Product to Repair',
        domain="[('type', 'in', ['product', 'consu']), '|', ('company_id', '=', company_id), ('company_id', '=', False), '|', ('id', 'in', picking_product_ids), ('id', '=?', picking_product_id)]",
        check_company=True)
    product_qty = fields.Float(
        'Product Quantity',
        default=1.0, digits='Product Unit of Measure')
    product_uom = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        compute='compute_product_uom', store=True, precompute=True,
        domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    lot_id = fields.Many2one(
        'stock.lot', 'Lot/Serial',
        default=False,
        compute="compute_lot_id", store=True,
        domain="[('product_id','=', product_id), ('company_id', '=', company_id)]", check_company=True,
        help="Products repaired are all belonging to this lot")
    tracking = fields.Selection(string='Product Tracking', related="product_id.tracking", readonly=False)

    # Picking & Locations
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type', copy=True, readonly=False,
        compute='_compute_picking_type_id', store=True,
        default=_default_picking_type_id,
        domain="[('code', '=', 'repair_operation'), ('company_id', '=', company_id)]",
        required=True, precompute=True, check_company=True, index=True)
    procurement_group_id = fields.Many2one(
        'procurement.group', 'Procurement Group',
        copy=False)
    location_id = fields.Many2one(
        'stock.location', 'Location',
        compute="_compute_location_id",
        store=True, readonly=False, required=True, precompute=True,
        index=True, check_company=True,
        help="This is the location where the product to repair is located.")
    location_dest_id = fields.Many2one(
        'stock.location', 'Added Parts Destination Location',
        related="picking_type_id.default_location_dest_id", depends=["picking_type_id"],
        store=True, readonly=True, required=True, precompute=True,
        index=True, check_company=True,
        help="This is the location where the repaired product is located.")
    parts_location_id = fields.Many2one(
        'stock.location', 'Removed Parts Destination Location',
        related="picking_type_id.default_remove_location_dest_id", depends=["picking_type_id"],
        store=True, readonly=True, required=True, precompute=True,
        index=True, check_company=True,
        help="This is the location where the repair parts are located.")
    recycle_location_id = fields.Many2one(
        'stock.location', 'Recycled Parts Destination Location',
        compute="_compute_recycle_location_id",
        store=True, readonly=False, required=True, precompute=True,
        index=True, check_company=True,
        help="This is the location where the repair parts are located.")

    # Parts
    move_ids = fields.One2many(
        'stock.move', 'repair_id', "Parts", check_company=True, copy=True,
        domain=[('repair_line_type', '!=', False)])  # Once RO switch to state done, a binded move is created for the "Product to repair" (move_id), this move appears in 'move_ids' if not filtered
    parts_availability = fields.Char(
        string="Component Status", compute='_compute_parts_availability',
        help="Latest parts availability status for this RO. If green, then the RO's readiness status is ready.")
    parts_availability_state = fields.Selection([
        ('available', 'Available'),
        ('expected', 'Expected'),
        ('late', 'Late')], compute='_compute_parts_availability')
    is_parts_available = fields.Boolean(
        'All Parts are available',
        default=False, store=True, compute='_compute_availability_boolean')
    is_parts_late = fields.Boolean(
        'Any Part is late',
        default=False, store=True, compute='_compute_availability_boolean')

    # Sale Order Binding
    sale_order_id = fields.Many2one(
        'sale.order', 'Sale Order', check_company=True, readonly=True,
        copy=False, help="Sale Order from which the Repair Order comes from.")
    sale_order_line_id = fields.Many2one(
        'sale.order.line', check_company=True, readonly=True,
        copy=False, help="Sale Order Line from which the Repair Order comes from.")
    repair_request = fields.Text(
        related='sale_order_line_id.name',
        string='Repair Request',
        help="Sale Order Line Description.")

    # Return Binding
    picking_id = fields.Many2one(
        'stock.picking', 'Return', check_company=True,
        domain="[('return_id', '!=', False), ('product_id', '=?', product_id)]",
        copy=False, help="Return Order from which the product to be repaired comes from.")
    is_returned = fields.Boolean(
        "Returned", compute='_compute_is_returned',
        help="True if this repair is linked to a Return Order and the order is 'Done'. False otherwise.")
    picking_product_ids = fields.One2many('product.product', compute='compute_picking_product_ids')
    picking_product_id = fields.Many2one(related="picking_id.product_id")
    # UI Fields
    show_set_qty_button = fields.Boolean(compute='_compute_show_qty_button')
    show_clear_qty_button = fields.Boolean(compute='_compute_show_qty_button')
    unreserve_visible = fields.Boolean(
        'Allowed to Unreserve Production', compute='_compute_unreserve_visible',
        help='Technical field to check when we can unreserve')
    reserve_visible = fields.Boolean(
        'Allowed to Reserve Production', compute='_compute_unreserve_visible',
        help='Technical field to check when we can reserve quantities')

    @api.depends('picking_id')
    def compute_picking_product_ids(self):
        for repair in self:
            repair.picking_product_ids = repair.picking_id.move_ids.product_id

    @api.depends('product_id', 'product_id.uom_id.category_id', 'product_uom.category_id')
    def compute_product_uom(self):
        for repair in self:
            if not repair.product_id:
                repair.product_uom = False
            elif not repair.product_uom or repair.product_uom.category_id != repair.product_id.uom_id.category_id:
                repair.product_uom = repair.product_id.uom_id

    @api.depends('product_id', 'lot_id', 'lot_id.product_id')
    def compute_lot_id(self):
        for repair in self:
            if (repair.product_id and repair.lot_id and repair.lot_id.product_id != repair.product_id) or not repair.product_id:
                repair.lot_id = False

    @api.depends('user_id', 'company_id')
    def _compute_picking_type_id(self):
        picking_type_by_company = self._get_picking_type()
        for ro in self:
            ro.picking_type_id = picking_type_by_company.get((ro.company_id, ro.user_id)) or\
                picking_type_by_company.get((ro.company_id, False))

    @api.depends('picking_type_id')
    def _compute_location_id(self):
        for repair in self:
            repair.location_id = repair.picking_type_id.default_location_src_id

    @api.depends('picking_type_id')
    def _compute_recycle_location_id(self):
        for repair in self:
            repair.recycle_location_id = repair.picking_type_id.default_recycle_location_dest_id

    @api.depends('state', 'schedule_date', 'move_ids', 'move_ids.forecast_availability', 'move_ids.forecast_expected_date')
    def _compute_parts_availability(self):
        repairs = self.filtered(lambda ro: ro.state in ('confirmed', 'under_repair'))
        repairs.parts_availability_state = 'available'
        repairs.parts_availability = _('Available')

        other_repairs = self - repairs
        other_repairs.parts_availability = False
        other_repairs.parts_availability_state = False

        all_moves = repairs.move_ids
        # Force to prefetch more than 1000 by 1000
        all_moves._fields['forecast_availability'].compute_value(all_moves)
        for repair in repairs:
            if any(float_compare(move.forecast_availability, move.product_qty, precision_rounding=move.product_id.uom_id.rounding) < 0 for move in repair.move_ids):
                repair.parts_availability = _('Not Available')
                repair.parts_availability_state = 'late'
                continue
            forecast_date = max(repair.move_ids.filtered('forecast_expected_date').mapped('forecast_expected_date'), default=False)
            if not forecast_date:
                continue
            repair.parts_availability = _('Exp %s', format_date(self.env, forecast_date))
            if repair.schedule_date:
                repair.parts_availability_state = 'late' if forecast_date > repair.schedule_date else 'expected'

    @api.depends('parts_availability_state')
    def _compute_availability_boolean(self):
        self.is_parts_available, self.is_parts_late = False, False
        for repair in self:
            if not repair.parts_availability_state:
                continue
            if repair.parts_availability_state == 'available':
                repair.is_parts_available = True
            elif repair.parts_availability_state == 'late':
                repair.is_parts_late = True

    @api.depends('picking_id', 'picking_id.state')
    def _compute_is_returned(self):
        self.is_returned = False
        returned = self.filtered(lambda r: r.picking_id and r.picking_id.state == 'done')
        returned.is_returned = True

    @api.depends('state', 'move_ids.quantity', 'move_ids.product_uom_qty')
    def _compute_show_qty_button(self):
        self.show_set_qty_button = False
        self.show_clear_qty_button = False
        for repair in self.filtered(lambda r: r.state not in ['cancel', 'done']):
            if any(float_is_zero(m.quantity, precision_rounding=m.product_uom.rounding) and not float_is_zero(m.product_uom_qty, precision_rounding=m.product_uom.rounding) for m in repair.move_ids):
                repair.show_set_qty_button = True
            elif any(not float_is_zero(m.quantity, precision_rounding=m.product_uom.rounding) for m in repair.move_ids):
                repair.show_clear_qty_button = True

    @api.depends('move_ids', 'state', 'move_ids.product_uom_qty')
    def _compute_unreserve_visible(self):
        for repair in self:
            already_reserved = repair.state not in ('done', 'cancel') and any(repair.mapped('move_ids.move_line_ids.quantity'))

            repair.unreserve_visible = already_reserved
            repair.reserve_visible = repair.state in ('confirmed', 'under_repair') and any(move.product_uom_qty and move.state in ['confirmed', 'partially_available'] for move in repair.move_ids)

    @api.onchange('product_uom')
    def onchange_product_uom(self):
        res = {}
        if not self.product_id or not self.product_uom:
            return res
        if self.product_uom.category_id != self.product_id.uom_id.category_id:
            res['warning'] = {'title': _('Warning'), 'message': _('The product unit of measure you chose has a different category than the product unit of measure.')}
        return res

    @api.onchange('location_id', 'picking_id')
    def _onchange_location_picking(self):
        location_warehouse = self.location_id.warehouse_id
        picking_warehouse = self.picking_id.location_dest_id.warehouse_id
        if location_warehouse and picking_warehouse and location_warehouse != picking_warehouse:
            return {
                'warning': {'title': _("Warning"), 'message': _("Note that the warehouses of the return and repair locations don't match!")},
            }

    @api.model_create_multi
    def create(self, vals_list):
        # We generate a standard reference
        for vals in vals_list:
            picking_type = self.env['stock.picking.type'].browse(vals.get('picking_type_id', self.default_get('picking_type_id')))
            if 'picking_type_id' not in vals:
                vals['picking_type_id'] = picking_type.id
            if not vals.get('name', False) or vals['name'] == _('New'):
                vals['name'] = picking_type.sequence_id.next_by_id()
            if not vals.get('procurement_group_id'):
                vals['procurement_group_id'] = self.env["procurement.group"].create({'name': vals['name']}).id
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if 'product_id' in vals and self.tracking == 'serial':
            self.write({'product_qty': 1.0})

        for repair in self:
            has_modified_location = any(key in vals for key in MAP_REPAIR_TO_PICKING_LOCATIONS)
            if has_modified_location:
                repair.move_ids._set_repair_locations()
            if 'schedule_date' in vals:
                (repair.move_id + repair.move_ids).filtered(lambda m: m.state not in ('done', 'cancel')).write({'date': repair.schedule_date})
            if 'under_warranty' in vals:
                repair._update_sale_order_line_price()
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        repairs_to_cancel = self.filtered(lambda ro: ro.state not in ('draft', 'cancel'))
        repairs_to_cancel.action_repair_cancel()

    def action_assign(self):
        return self.move_ids._action_assign()

    def action_clear_quantities_to_zero(self):
        return self.move_ids.filtered(lambda m: float_compare(m.quantity, m.reserved_availability, precision_rounding=m.product_uom.rounding) == 0)._clear_quantities_to_zero()

    def action_create_sale_order(self):
        if any(repair.sale_order_id for repair in self):
            concerned_ro = self.filtered('sale_order_id')
            ref_str = "\n".join(ro.name for ro in concerned_ro)
            raise UserError(_("You cannot create a quotation for a repair order that is already linked to an existing sale order.\nConcerned repair order(s) :\n") + ref_str)
        if any(not repair.partner_id for repair in self):
            concerned_ro = self.filtered(lambda ro: not ro.partner_id)
            ref_str = "\n".join(ro.name for ro in concerned_ro)
            raise UserError(_("You need to define a customer for a repair order in order to create an associated quotation.\nConcerned repair order(s) :\n") + ref_str)
        sale_order_values_list = []
        for repair in self:
            sale_order_values_list.append({
                "company_id": self.company_id.id,
                "partner_id": self.partner_id.id,
                "warehouse_id": self.picking_type_id.warehouse_id.id,
                "repair_order_ids": [Command.link(repair.id)],
            })
        self.env['sale.order'].create(sale_order_values_list)
        # Add Sale Order Lines for 'add' move_ids
        self.move_ids._create_repair_sale_order_line()
        return self.action_view_sale_order()

    def action_repair_cancel(self):
        if any(repair.state == 'done' for repair in self):
            raise UserError(_("You cannot cancel a Repair Order that's already been completed"))
        for repair in self:
            if repair.sale_order_id:
                repair.sale_order_line_id.write({'product_uom_qty': 0.0})  # Quantity of the product that generated the RO is set to 0
        self.move_ids._action_cancel()  # Quantity of parts added from the RO to the SO is set to 0
        return self.write({'state': 'cancel'})

    def action_repair_cancel_draft(self):
        if self.filtered(lambda repair: repair.state != 'cancel'):
            self.action_repair_cancel()
        sale_line_to_update = self.move_ids.sale_line_id.filtered(lambda l: l.order_id.state != 'cancel' and float_is_zero(l.product_uom_qty, precision_rounding=l.product_uom.rounding))
        sale_line_to_update.move_ids._update_repair_sale_order_line()
        self.move_ids.state = 'draft'
        self.state = 'draft'
        return True

    def action_repair_done(self):
        """ Creates stock move for final product of repair order.
        Writes move_id and move_ids state to 'done'.
        Writes repair order state to 'Repaired'.
        @return: True
        """
        # Clean the context to get rid of residual default_* keys that could cause issues
        # during the creation of stock.move.
        self = self.with_context(clean_context(self._context))

        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        product_move_vals = []

        # Cancel moves with 0 quantity
        self.move_ids.filtered(lambda m: float_is_zero(m.quantity, precision_rounding=m.product_uom.rounding))._action_cancel()

        no_service_policy = 'service_policy' not in self.env['product.template']
        #SOL qty delivered = repair.move_ids.quantity
        for repair in self:
            if all(not move.picked for move in repair.move_ids):
                repair.move_ids.picked = True
            if repair.sale_order_line_id:
                ro_origin_product = repair.sale_order_line_id.product_template_id
                # TODO: As 'service_policy' only appears with 'sale_project' module, isolate conditions related to this field in a 'sale_project_repair' module if it's worth
                if ro_origin_product.detailed_type == 'service' and (no_service_policy or ro_origin_product.service_policy == 'ordered_prepaid'):
                    repair.sale_order_line_id.qty_delivered = repair.sale_order_line_id.product_uom_qty
            if not repair.product_id:
                continue

            if repair.product_id.product_tmpl_id.tracking != 'none' and not repair.lot_id:
                raise ValidationError(_(
                    "Serial number is required for product to repair : %s",
                    repair.product_id.display_name
                ))

            # Try to create move with the appropriate owner
            owner_id = False
            available_qty_owner = self.env['stock.quant']._get_available_quantity(repair.product_id, repair.location_id, repair.lot_id, owner_id=repair.partner_id, strict=True)
            if float_compare(available_qty_owner, repair.product_qty, precision_digits=precision) >= 0:
                owner_id = repair.partner_id.id

            product_move_vals.append({
                'name': repair.name,
                'product_id': repair.product_id.id,
                'product_uom': repair.product_uom.id or repair.product_id.uom_id.id,
                'product_uom_qty': repair.product_qty,
                'partner_id': repair.partner_id.id,
                'location_id': repair.location_id.id,
                'location_dest_id': repair.location_id.id,
                'picked': True,
                'move_line_ids': [(0, 0, {
                    'product_id': repair.product_id.id,
                    'lot_id': repair.lot_id.id,
                    'product_uom_id': repair.product_uom.id or repair.product_id.uom_id.id,
                    'quantity': repair.product_qty,
                    'package_id': False,
                    'result_package_id': False,
                    'owner_id': owner_id,
                    'location_id': repair.location_id.id,
                    'company_id': repair.company_id.id,
                    'location_dest_id': repair.location_id.id,
                    'consume_line_ids': [(6, 0, repair.move_ids.move_line_ids.ids)]
                })],
                'repair_id': repair.id,
                'origin': repair.name,
                'company_id': repair.company_id.id,
            })

        product_moves = self.env['stock.move'].create(product_move_vals)
        repair_move = {m.repair_id.id: m for m in product_moves}
        for repair in self:
            move_id = repair_move.get(repair.id, False)
            if move_id:
                repair.move_id = move_id
        all_moves = self.move_ids + product_moves
        all_moves._action_done()

        for sale_line in self.move_ids.sale_line_id:
            price_unit = sale_line.price_unit
            sale_line.write({'product_uom_qty': sale_line.qty_delivered, 'price_unit': price_unit})

        self.state = 'done'
        return True

    def action_repair_end(self):
        """ Checks before action_repair_done.
        @return: True
        """
        if self.filtered(lambda repair: repair.state != 'under_repair'):
            raise UserError(_("Repair must be under repair in order to end reparation."))
        if any(float_compare(move.quantity, move.product_uom_qty, precision_rounding=move.product_uom.rounding) < 0 for move in self.move_ids):
            ctx = dict(self.env.context or {})
            ctx['default_repair_ids'] = self.ids
            return {
                'name': _('Uncomplete Move(s)'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [(False, 'form')],
                'res_model': 'repair.warn.uncomplete.move',
                'target': 'new',
                'context': ctx,
            }

        return self.action_repair_done()

    def action_repair_start(self):
        """ Writes repair order state to 'Under Repair'
        """
        if self.filtered(lambda repair: repair.state != 'confirmed'):
            self._action_repair_confirm()
        return self.write({'state': 'under_repair'})

    def action_unreserve(self):
        return self.move_ids.filtered(lambda m: m.state in ('assigned', 'partially_available'))._do_unreserve()

    def action_validate(self):
        self.ensure_one()
        if self.filtered(lambda repair: any(m.product_uom_qty < 0 for m in repair.move_ids)):
            raise UserError(_("You can not enter negative quantities."))
        if not self.product_id or self.product_id.type == 'consu':
            return self._action_repair_confirm()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        available_qty_owner = self.env['stock.quant']._get_available_quantity(self.product_id, self.location_id, self.lot_id, owner_id=self.partner_id, strict=True)
        available_qty_noown = self.env['stock.quant']._get_available_quantity(self.product_id, self.location_id, self.lot_id, strict=True)
        repair_qty = self.product_uom._compute_quantity(self.product_qty, self.product_id.uom_id)
        for available_qty in [available_qty_owner, available_qty_noown]:
            if float_compare(available_qty, repair_qty, precision_digits=precision) >= 0:
                return self._action_repair_confirm()

        return {
            'name': self.product_id.display_name + _(': Insufficient Quantity To Repair'),
            'view_mode': 'form',
            'res_model': 'stock.warn.insufficient.qty.repair',
            'view_id': self.env.ref('repair.stock_warn_insufficient_qty_repair_form_view').id,
            'type': 'ir.actions.act_window',
            'context': {
                'default_product_id': self.product_id.id,
                'default_location_id': self.location_id.id,
                'default_repair_id': self.id,
                'default_quantity': repair_qty,
                'default_product_uom_name': self.product_id.uom_name
            },
            'target': 'new'
        }

    def action_view_sale_order(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": self.sale_order_id.id,
        }

    def print_repair_order(self):
        return self.env.ref('repair.action_report_repair_order').report_action(self)

    def _action_repair_confirm(self):
        """ Repair order state is set to 'Confirmed'.
        @param *arg: Arguments
        @return: True
        """
        repairs_to_confirm = self.filtered(lambda repair: repair.state == 'draft')
        repairs_to_confirm._check_company()
        repairs_to_confirm.move_ids._check_company()
        repairs_to_confirm.move_ids._adjust_procure_method()
        repairs_to_confirm.move_ids._action_confirm()
        repairs_to_confirm.move_ids._trigger_scheduler()
        repairs_to_confirm.write({'state': 'confirmed'})
        return True

    def _get_location(self, field):
        return self.picking_type_id[MAP_REPAIR_TO_PICKING_LOCATIONS[field]]

    def _get_picking_type(self):
        companies = self.company_id or self.env.company
        if not self:
            # default case
            default_warehouse = self.env.user.with_company(companies.id)._get_default_warehouse_id()
            if default_warehouse and default_warehouse.repair_type_id:
                return {(companies, self.env.user): default_warehouse.repair_type_id}

        picking_type_by_company_user = {}
        without_default_warehouse_companies = set()
        for (company, user), dummy in groupby(self, lambda r: (r.company_id, r.user_id)):
            default_warehouse = user.with_company(company.id)._get_default_warehouse_id()
            if default_warehouse and default_warehouse.repair_type_id:
                picking_type_by_company_user[(company, user)] = default_warehouse.repair_type_id
            else:
                without_default_warehouse_companies.add(company.id)

        if not without_default_warehouse_companies:
            return picking_type_by_company_user

        domain = [
            ('code', '=', 'repair_operation'),
            ('warehouse_id.company_id', 'in', list(without_default_warehouse_companies)),
        ]

        picking_types = self.env['stock.picking.type'].search_read(domain, ['company_id'], load=False)
        for picking_type in picking_types:
            if (picking_type.company_id, False) not in picking_type_by_company_user:
                picking_type_by_company_user[(picking_type.company_id, False)] = picking_type
        return picking_type_by_company_user

    def _update_sale_order_line_price(self):
        for repair in self:
            add_moves = repair.move_ids.filtered(lambda m: m.repair_line_type == 'add' and m.sale_line_id)
            if repair.under_warranty:
                add_moves.sale_line_id.write({'price_unit': 0.0})
            else:
                add_moves.sale_line_id._compute_price_unit()

class RepairTags(models.Model):
    """ Tags of Repair's tasks """
    _name = "repair.tags"
    _description = "Repair Tags"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Tag Name', required=True)
    color = fields.Integer(string='Color Index', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists!"),
    ]
