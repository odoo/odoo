# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar

from collections import defaultdict, OrderedDict
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare


class Location(models.Model):
    _name = "stock.location"
    _description = "Inventory Locations"
    _parent_name = "location_id"
    _parent_store = True
    _order = 'complete_name, id'
    _rec_name = 'complete_name'
    _check_company_auto = True

    @api.model
    def default_get(self, fields):
        res = super(Location, self).default_get(fields)
        if 'barcode' in fields and 'barcode' not in res and res.get('complete_name'):
            res['barcode'] = res['complete_name']
        return res

    name = fields.Char('Location Name', required=True)
    complete_name = fields.Char("Full Location Name", compute='_compute_complete_name', recursive=True, store=True)
    active = fields.Boolean('Active', default=True, help="By unchecking the active field, you may hide a location without deleting it.")
    usage = fields.Selection([
        ('supplier', 'Vendor Location'),
        ('view', 'View'),
        ('internal', 'Internal Location'),
        ('customer', 'Customer Location'),
        ('inventory', 'Inventory Loss'),
        ('production', 'Production'),
        ('transit', 'Transit Location')], string='Location Type',
        default='internal', index=True, required=True,
        help="* Vendor Location: Virtual location representing the source location for products coming from your vendors"
             "\n* View: Virtual location used to create a hierarchical structures for your warehouse, aggregating its child locations ; can't directly contain products"
             "\n* Internal Location: Physical locations inside your own warehouses,"
             "\n* Customer Location: Virtual location representing the destination location for products sent to your customers"
             "\n* Inventory Loss: Virtual location serving as counterpart for inventory operations used to correct stock levels (Physical inventories)"
             "\n* Production: Virtual counterpart location for production operations: this location consumes the components and produces finished products"
             "\n* Transit Location: Counterpart location that should be used in inter-company or inter-warehouses operations")
    location_id = fields.Many2one(
        'stock.location', 'Parent Location', index=True, ondelete='cascade', check_company=True,
        help="The parent location that includes this location. Example : The 'Dispatch Zone' is the 'Gate 1' parent location.")
    child_ids = fields.One2many('stock.location', 'location_id', 'Contains')
    child_internal_location_ids = fields.Many2many(
        'stock.location',
        string='Internal locations amoung descendants',
        compute='_compute_child_internal_location_ids',
        recursive=True,
        help='This location (if it\'s internal) and all its descendants filtered by type=Internal.'
    )
    comment = fields.Html('Additional Information')
    posx = fields.Integer('Corridor (X)', default=0, help="Optional localization details, for information purpose only")
    posy = fields.Integer('Shelves (Y)', default=0, help="Optional localization details, for information purpose only")
    posz = fields.Integer('Height (Z)', default=0, help="Optional localization details, for information purpose only")
    parent_path = fields.Char(index=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company, index=True,
        help='Let this field empty if this location is shared between companies')
    scrap_location = fields.Boolean('Is a Scrap Location?', default=False, help='Check this box to allow using this location to put scrapped/damaged goods.')
    return_location = fields.Boolean('Is a Return Location?', help='Check this box to allow using this location as a return location.')
    removal_strategy_id = fields.Many2one(
        'product.removal', 'Removal Strategy',
        help="Defines the default method used for suggesting the exact location (shelf) "
             "where to take the products from, which lot etc. for this location. "
             "This method can be enforced at the product category level, "
             "and a fallback is made on the parent locations if none is set here.\n\n"
             "FIFO: products/lots that were stocked first will be moved out first.\n"
             "LIFO: products/lots that were stocked last will be moved out first.\n"
             "Closet location: products/lots closest to the target location will be moved out first.\n"
             "FEFO: products/lots with the closest removal date will be moved out first "
             "(the availability of this method depends on the \"Expiration Dates\" setting).")
    putaway_rule_ids = fields.One2many('stock.putaway.rule', 'location_in_id', 'Putaway Rules')
    barcode = fields.Char('Barcode', copy=False)
    quant_ids = fields.One2many('stock.quant', 'location_id')
    cyclic_inventory_frequency = fields.Integer("Inventory Frequency (Days)", default=0, help=" When different than 0, inventory count date for products stored at this location will be automatically set at the defined frequency.")
    last_inventory_date = fields.Date("Last Effective Inventory", readonly=True, help="Date of the last inventory at this location.")
    next_inventory_date = fields.Date("Next Expected Inventory", compute="_compute_next_inventory_date", store=True, help="Date for next planned inventory based on cyclic schedule.")
    warehouse_view_ids = fields.One2many('stock.warehouse', 'view_location_id', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', compute='_compute_warehouse_id')
    storage_category_id = fields.Many2one('stock.storage.category', string='Storage Category', check_company=True)
    outgoing_move_line_ids = fields.One2many('stock.move.line', 'location_id', help='Technical: used to compute weight.')
    incoming_move_line_ids = fields.One2many('stock.move.line', 'location_dest_id', help='Technical: used to compute weight.')
    net_weight = fields.Float('Net Weight', compute="_compute_weight")
    forecast_weight = fields.Float('Forecasted Weight', compute="_compute_weight")

    _sql_constraints = [('barcode_company_uniq', 'unique (barcode,company_id)', 'The barcode for a location must be unique per company !'),
                        ('inventory_freq_nonneg', 'check(cyclic_inventory_frequency >= 0)', 'The inventory frequency (days) for a location must be non-negative')]

    @api.depends('outgoing_move_line_ids.product_qty', 'incoming_move_line_ids.product_qty',
                 'outgoing_move_line_ids.state', 'incoming_move_line_ids.state',
                 'outgoing_move_line_ids.product_id.weight', 'outgoing_move_line_ids.product_id.weight',
                 'quant_ids.quantity', 'quant_ids.product_id.weight')
    @api.depends_context('exclude_sml_ids')
    def _compute_weight(self):
        for location in self:
            location.net_weight = 0
            quants = location.quant_ids.filtered(lambda q: q.product_id.type != 'service')
            excluded_sml_ids = self._context.get('exclude_sml_ids', [])
            incoming_move_lines = location.incoming_move_line_ids.filtered(lambda ml: ml.product_id.type != 'service' and ml.state not in ['draft', 'done', 'cancel'] and ml.id not in excluded_sml_ids)
            outgoing_move_lines = location.outgoing_move_line_ids.filtered(lambda ml: ml.product_id.type != 'service' and ml.state not in ['draft', 'done', 'cancel'] and ml.id not in excluded_sml_ids)
            for quant in quants:
                location.net_weight += quant.product_id.weight * quant.quantity
            location.forecast_weight = location.net_weight
            for line in incoming_move_lines:
                location.forecast_weight += line.product_id.weight * line.product_qty
            for line in outgoing_move_lines:
                location.forecast_weight -= line.product_id.weight * line.product_qty

    @api.depends('name', 'location_id.complete_name', 'usage')
    def _compute_complete_name(self):
        for location in self:
            if location.location_id and location.usage != 'view':
                location.complete_name = '%s/%s' % (location.location_id.complete_name, location.name)
            else:
                location.complete_name = location.name

    @api.depends('cyclic_inventory_frequency', 'last_inventory_date', 'usage', 'company_id')
    def _compute_next_inventory_date(self):
        for location in self:
            if location.company_id and location.usage in ['internal', 'transit'] and location.cyclic_inventory_frequency > 0:
                try:
                    if location.last_inventory_date:
                        days_until_next_inventory = location.cyclic_inventory_frequency - (fields.Date.today() - location.last_inventory_date).days
                        if days_until_next_inventory <= 0:
                            location.next_inventory_date = fields.Date.today() + timedelta(days=1)
                        else:
                            location.next_inventory_date = location.last_inventory_date + timedelta(days=location.cyclic_inventory_frequency)
                    else:
                        location.next_inventory_date = fields.Date.today() + timedelta(days=location.cyclic_inventory_frequency)
                except OverflowError:
                    raise UserError(_("The selected Inventory Frequency (Days) creates a date too far into the future."))
            else:
                location.next_inventory_date = False

    @api.depends('warehouse_view_ids')
    def _compute_warehouse_id(self):
        warehouses = self.env['stock.warehouse'].search([('view_location_id', 'parent_of', self.ids)])
        view_by_wh = OrderedDict((wh.view_location_id.id, wh.id) for wh in warehouses)
        self.warehouse_id = False
        for loc in self:
            path = set(int(loc_id) for loc_id in loc.parent_path.split('/')[:-1])
            for view_location_id in view_by_wh:
                if view_location_id in path:
                    loc.warehouse_id = view_by_wh[view_location_id]
                    break

    @api.depends('child_ids.usage', 'child_ids.child_internal_location_ids')
    def _compute_child_internal_location_ids(self):
        # batch reading optimization is not possible because the field has recursive=True
        for loc in self:
            loc.child_internal_location_ids = self.search([('id', 'child_of', loc.id), ('usage', '=', 'internal')])

    @api.onchange('usage')
    def _onchange_usage(self):
        if self.usage not in ('internal', 'inventory'):
            self.scrap_location = False

    def write(self, values):
        if 'company_id' in values:
            for location in self:
                if location.company_id.id != values['company_id']:
                    raise UserError(_("Changing the company of this record is forbidden at this point, you should rather archive it and create a new one."))
        if 'usage' in values and values['usage'] == 'view':
            if self.mapped('quant_ids'):
                raise UserError(_("This location's usage cannot be changed to view as it contains products."))
        if 'usage' in values or 'scrap_location' in values:
            modified_locations = self.filtered(
                lambda l: any(l[f] != values[f] if f in values else False
                              for f in {'usage', 'scrap_location'}))
            reserved_quantities = self.env['stock.move.line'].search_count([
                ('location_id', 'in', modified_locations.ids),
                ('product_qty', '>', 0),
            ])
            if reserved_quantities:
                raise UserError(_(
                    "You cannot change the location type or its use as a scrap"
                    " location as there are products reserved in this location."
                    " Please unreserve the products first."
                ))
        if 'active' in values:
            if values['active'] == False:
                for location in self:
                    warehouses = self.env['stock.warehouse'].search([('active', '=', True), '|', ('lot_stock_id', '=', location.id), ('view_location_id', '=', location.id)])
                    if warehouses:
                        raise UserError(_("You cannot archive the location %s as it is"
                        " used by your warehouse %s") % (location.display_name, warehouses[0].display_name))

            if not self.env.context.get('do_not_check_quant'):
                children_location = self.env['stock.location'].with_context(active_test=False).search([('id', 'child_of', self.ids)])
                internal_children_locations = children_location.filtered(lambda l: l.usage == 'internal')
                children_quants = self.env['stock.quant'].search(['&', '|', ('quantity', '!=', 0), ('reserved_quantity', '!=', 0), ('location_id', 'in', internal_children_locations.ids)])
                if children_quants and values['active'] == False:
                    raise UserError(_('You still have some product in locations %s') %
                        (', '.join(children_quants.mapped('location_id.display_name'))))
                else:
                    super(Location, children_location - self).with_context(do_not_check_quant=True).write({
                        'active': values['active'],
                    })

        res = super(Location, self).write(values)
        self.invalidate_cache(['warehouse_id'])
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self.invalidate_cache(['warehouse_id'])
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """ search full name and barcode """
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        elif operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('barcode', operator, name), ('complete_name', operator, name)]
        else:
            domain = ['|', ('barcode', operator, name), ('complete_name', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    def _get_putaway_strategy(self, product, quantity=0, package=None, packaging=None, additional_qty=None):
        """Returns the location where the product has to be put, if any compliant
        putaway strategy is found. Otherwise returns self.
        The quantity should be in the default UOM of the product, it is used when
        no package is specified.
        """
        # find package type on package or packaging
        package_type = self.env['stock.package.type']
        if package:
            package_type = package.package_type_id
        elif packaging:
            package_type = packaging.package_type_id

        putaway_rules = self.env['stock.putaway.rule']
        putaway_rules |= self.putaway_rule_ids.filtered(lambda x: x.product_id == product and (package_type in x.package_type_ids or package_type == x.package_type_ids))
        categ = product.categ_id
        while categ:
            putaway_rules |= self.putaway_rule_ids.filtered(lambda x: x.category_id == categ and (package_type in x.package_type_ids or package_type == x.package_type_ids))
            categ = categ.parent_id
        if package_type:
            putaway_rules |= self.putaway_rule_ids.filtered(lambda x: not x.product_id and (package_type in x.package_type_ids or package_type == x.package_type_ids))

        putaway_location = None
        locations = self.child_internal_location_ids
        if putaway_rules:
            # get current product qty (qty in current quants and future qty on assigned ml) of all child locations
            qty_by_location = defaultdict(lambda: 0)
            if locations.storage_category_id:
                if package and package.package_type_id:
                    move_line_data = self.env['stock.move.line'].read_group([
                        ('id', 'not in', self._context.get('exclude_sml_ids', [])),
                        ('result_package_id.package_type_id', '=', package_type.id),
                        ('state', 'not in', ['draft', 'cancel', 'done']),
                    ], ['result_package_id:count_distinct'], ['location_dest_id'])
                    quant_data = self.env['stock.quant'].read_group([
                        ('package_id.package_type_id', '=', package_type.id),
                        ('location_id', 'in', locations.ids),
                    ], ['package_id:count_distinct'], ['location_id'])
                    for values in move_line_data:
                        qty_by_location[values['location_dest_id'][0]] = values['result_package_id']
                    for values in quant_data:
                        qty_by_location[values['location_id'][0]] += values['package_id']
                else:
                    move_line_data = self.env['stock.move.line'].read_group([
                        ('id', 'not in', self._context.get('exclude_sml_ids', [])),
                        ('product_id', '=', product.id),
                        ('location_dest_id', 'in', locations.ids),
                        ('state', 'not in', ['draft', 'done', 'cancel'])
                    ], ['location_dest_id', 'product_id', 'product_qty:array_agg', 'qty_done:array_agg', 'product_uom_id:array_agg'], ['location_dest_id'])
                    quant_data = self.env['stock.quant'].read_group([
                        ('product_id', '=', product.id),
                        ('location_id', 'in', locations.ids),
                    ], ['location_id', 'product_id', 'quantity:sum'], ['location_id'])

                    for values in move_line_data:
                        uoms = self.env['uom.uom'].browse(values['product_uom_id'])
                        qty_done = sum(max(ml_uom._compute_quantity(float(qty), product.uom_id), float(qty_reserved))
                                    for qty_reserved, qty, ml_uom in zip(values['product_qty'], values['qty_done'], list(uoms)))
                        qty_by_location[values['location_dest_id'][0]] = qty_done
                    for values in quant_data:
                        qty_by_location[values['location_id'][0]] += values['quantity']
            if additional_qty:
                for location_id, qty in additional_qty.items():
                    qty_by_location[location_id] += qty
            putaway_location = putaway_rules._get_putaway_location(product, quantity, package, packaging, qty_by_location)

        if not putaway_location:
            putaway_location = locations[0] if locations and self.usage == 'view' else self

        return putaway_location

    def _get_next_inventory_date(self):
        """ Used to get the next inventory date for a quant located in this location. It is
        based on:
        1. Does the location have a cyclic inventory set?
        2. If not 1, then is there an annual inventory date set (for its company)?
        3. If not 1 and 2, then quants have no next inventory date."""
        if self.usage not in ['internal', 'transit']:
            return False
        next_inventory_date = False
        if self.next_inventory_date:
            next_inventory_date = self.next_inventory_date
        elif self.company_id.annual_inventory_month:
            today = fields.Date.today()
            annual_inventory_month = int(self.company_id.annual_inventory_month)
            # Manage 0 and negative annual_inventory_day
            annual_inventory_day = max(self.company_id.annual_inventory_day, 1)
            max_day = calendar.monthrange(today.year, annual_inventory_month)[1]
            # Manage annual_inventory_day bigger than last_day
            annual_inventory_day = min(annual_inventory_day, max_day)
            next_inventory_date = today.replace(
                month=annual_inventory_month, day=annual_inventory_day)
            if next_inventory_date <= today:
                # Manage leap year with the february
                max_day = calendar.monthrange(today.year + 1, annual_inventory_month)[1]
                annual_inventory_day = min(annual_inventory_day, max_day)
                next_inventory_date = next_inventory_date.replace(
                    day=annual_inventory_day, year=today.year + 1)
        return next_inventory_date

    def should_bypass_reservation(self):
        self.ensure_one()
        return self.usage in ('supplier', 'customer', 'inventory', 'production') or self.scrap_location or (self.usage == 'transit' and not self.company_id)

    def _check_can_be_used(self, product, quantity=0, package=None, location_qty=0):
        """Check if product/package can be stored in the location. Quantity
        should in the default uom of product, it's only used when no package is
        specified."""
        self.ensure_one()
        if self.storage_category_id:
            # check if enough space
            if package and package.package_type_id:
                # check weight
                package_smls = self.env['stock.move.line'].search([('result_package_id', '=', package.id)])
                if self.storage_category_id.max_weight < self.forecast_weight + sum(package_smls.mapped(lambda sml: sml.product_qty * sml.product_id.weight)):
                    return False
                # check if enough space
                package_capacity = self.storage_category_id.package_capacity_ids.filtered(lambda pc: pc.package_type_id == package.package_type_id)
                if package_capacity and location_qty >= package_capacity.quantity:
                    return False
            else:
                # check weight
                if self.storage_category_id.max_weight < self.forecast_weight + product.weight * quantity:
                    return False
                product_capacity = self.storage_category_id.product_capacity_ids.filtered(lambda pc: pc.product_id == product)
                # To handle new line without quantity in order to avoid suggesting a location already full
                if product_capacity and location_qty >= product_capacity.quantity:
                    return False
                if product_capacity and quantity + location_qty > product_capacity.quantity:
                    return False
            positive_quant = self.quant_ids.filtered(lambda q: float_compare(q.quantity, 0, precision_rounding=q.product_id.uom_id.rounding) > 0)
            # check if only allow new product when empty
            if self.storage_category_id.allow_new_product == "empty" and positive_quant:
                return False
            # check if only allow same product
            if self.storage_category_id.allow_new_product == "same" and positive_quant and positive_quant.product_id != product:
                return False
        return True


class Route(models.Model):
    _name = 'stock.location.route'
    _description = "Inventory Routes"
    _order = 'sequence'
    _check_company_auto = True

    name = fields.Char('Route', required=True, translate=True)
    active = fields.Boolean('Active', default=True, help="If the active field is set to False, it will allow you to hide the route without removing it.")
    sequence = fields.Integer('Sequence', default=0)
    rule_ids = fields.One2many('stock.rule', 'route_id', 'Rules', copy=True)
    product_selectable = fields.Boolean('Applicable on Product', default=True, help="When checked, the route will be selectable in the Inventory tab of the Product form.")
    product_categ_selectable = fields.Boolean('Applicable on Product Category', help="When checked, the route will be selectable on the Product Category.")
    warehouse_selectable = fields.Boolean('Applicable on Warehouse', help="When a warehouse is selected for this route, this route should be seen as the default route when products pass through this warehouse.")
    packaging_selectable = fields.Boolean('Applicable on Packaging', help="When checked, the route will be selectable on the Product Packaging.")
    supplied_wh_id = fields.Many2one('stock.warehouse', 'Supplied Warehouse')
    supplier_wh_id = fields.Many2one('stock.warehouse', 'Supplying Warehouse')
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company, index=True,
        help='Leave this field empty if this route is shared between all companies')
    product_ids = fields.Many2many(
        'product.template', 'stock_route_product', 'route_id', 'product_id',
        'Products', copy=False, check_company=True)
    categ_ids = fields.Many2many('product.category', 'stock_location_route_categ', 'route_id', 'categ_id', 'Product Categories', copy=False)
    packaging_ids = fields.Many2many('product.packaging', 'stock_location_route_packaging', 'route_id', 'packaging_id', 'Packagings', copy=False, check_company=True)
    warehouse_domain_ids = fields.One2many('stock.warehouse', compute='_compute_warehouses')
    warehouse_ids = fields.Many2many(
        'stock.warehouse', 'stock_route_warehouse', 'route_id', 'warehouse_id',
        'Warehouses', copy=False, domain="[('id', 'in', warehouse_domain_ids)]")

    @api.depends('company_id')
    def _compute_warehouses(self):
        for loc in self:
            domain = [('company_id', '=', loc.company_id.id)] if loc.company_id else []
            loc.warehouse_domain_ids = self.env['stock.warehouse'].search(domain)

    @api.onchange('company_id')
    def _onchange_company(self):
        if self.company_id:
            self.warehouse_ids = self.warehouse_ids.filtered(lambda w: w.company_id == self.company_id)

    @api.onchange('warehouse_selectable')
    def _onchange_warehouse_selectable(self):
        if not self.warehouse_selectable:
            self.warehouse_ids = [(5, 0, 0)]

    def toggle_active(self):
        for route in self:
            route.with_context(active_test=False).rule_ids.filtered(lambda ru: ru.active == route.active).toggle_active()
        super(Route, self).toggle_active()
