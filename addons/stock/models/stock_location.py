# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar

from collections import defaultdict, OrderedDict
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare


class StockLocation(models.Model):
    _name = 'stock.location'
    _description = "Inventory Locations"
    _parent_name = "location_id"
    _parent_store = True
    _order = 'complete_name, id'
    _rec_name = 'complete_name'
    _rec_names_search = ['complete_name', 'barcode']
    _check_company_auto = True

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
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
        'stock.location', 'Parent Location', index=True, check_company=True,
        help="The parent location that includes this location. Example : The 'Dispatch Zone' is the 'Gate 1' parent location.")
    child_ids = fields.One2many('stock.location', 'location_id', 'Contains')
    child_internal_location_ids = fields.Many2many(
        'stock.location',
        string='Internal locations among descendants',
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
    replenish_location = fields.Boolean('Replenish Location', copy=False, compute="_compute_replenish_location", readonly=False, store=True,
                                        help='Activate this function to get all quantities to replenish at this particular location')
    removal_strategy_id = fields.Many2one(
        'product.removal', 'Removal Strategy',
        help="Defines the default method used for suggesting the exact location (shelf) "
             "where to take the products from, which lot etc. for this location. "
             "This method can be enforced at the product category level, "
             "and a fallback is made on the parent locations if none is set here.\n\n"
             "FIFO: products/lots that were stocked first will be moved out first.\n"
             "LIFO: products/lots that were stocked last will be moved out first.\n"
             "Closest Location: products/lots closest to the target location will be moved out first.\n"
             "Least Packages: products/lots that were stocked in package with least amount of qty will be moved out first.\n"
             "FEFO: products/lots with the closest removal date will be moved out first "
             "(the availability of this method depends on the \"Expiration Dates\" setting).")
    putaway_rule_ids = fields.One2many('stock.putaway.rule', 'location_in_id', 'Putaway Rules')
    barcode = fields.Char('Barcode', copy=False)
    quant_ids = fields.One2many('stock.quant', 'location_id')
    cyclic_inventory_frequency = fields.Integer("Inventory Frequency", default=0, help=" When different than 0, inventory count date for products stored at this location will be automatically set at the defined frequency.")
    last_inventory_date = fields.Date("Last Inventory", readonly=True, help="Date of the last inventory at this location.")
    next_inventory_date = fields.Date("Next Expected", compute="_compute_next_inventory_date", store=True, help="Date for next planned inventory based on cyclic schedule.")
    warehouse_view_ids = fields.One2many('stock.warehouse', 'view_location_id', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', compute='_compute_warehouse_id', store=True)
    storage_category_id = fields.Many2one('stock.storage.category', string='Storage Category', check_company=True)
    outgoing_move_line_ids = fields.One2many('stock.move.line', 'location_id') # used to compute weight
    incoming_move_line_ids = fields.One2many('stock.move.line', 'location_dest_id') # used to compute weight
    net_weight = fields.Float('Net Weight', compute="_compute_weight")
    forecast_weight = fields.Float('Forecasted Weight', compute="_compute_weight")
    is_empty = fields.Boolean('Is Empty', compute='_compute_is_empty', search='_search_is_empty')

    _barcode_company_uniq = models.Constraint(
        'unique (barcode,company_id)',
        'The barcode for a location must be unique per company!',
    )
    _inventory_freq_nonneg = models.Constraint(
        'check(cyclic_inventory_frequency >= 0)',
        'The inventory frequency (days) for a location must be non-negative',
    )

    @api.depends('outgoing_move_line_ids.quantity_product_uom', 'incoming_move_line_ids.quantity_product_uom',
                 'outgoing_move_line_ids.state', 'incoming_move_line_ids.state',
                 'outgoing_move_line_ids.product_id.weight', 'outgoing_move_line_ids.product_id.weight',
                 'quant_ids.quantity', 'quant_ids.product_id.weight')
    def _compute_weight(self):
        weight_by_location = self._get_weight()
        for location in self:
            location.net_weight = weight_by_location[location]['net_weight']
            location.forecast_weight = weight_by_location[location]['forecast_weight']

    @api.depends('name', 'location_id.complete_name', 'usage')
    def _compute_complete_name(self):
        for location in self:
            if location.location_id and location.usage != 'view':
                location.complete_name = '%s/%s' % (location.location_id.complete_name, location.name)
            else:
                location.complete_name = location.name

    def _compute_is_empty(self):
        groups = self.env['stock.quant']._read_group(
            [('location_id.usage', 'in', ('internal', 'transit')),
             ('location_id', 'in', self.ids)],
            ['location_id'], ['quantity:sum'])
        groups = dict(groups)
        for location in self:
            location.is_empty = groups.get(location, 0) <= 0

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

    @api.depends('warehouse_view_ids', 'location_id')
    def _compute_warehouse_id(self):
        warehouses = self.env['stock.warehouse'].search([('view_location_id', 'parent_of', self.ids)])
        warehouses = warehouses.sorted(lambda w: w.view_location_id.parent_path, reverse=True)
        view_by_wh = OrderedDict((wh.view_location_id.id, wh.id) for wh in warehouses)
        self.warehouse_id = False
        for loc in self:
            if not loc.parent_path:
                continue
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

    @api.depends('usage')
    def _compute_replenish_location(self):
        for loc in self:
            if loc.usage != 'internal':
                loc.replenish_location = False

    @api.constrains('replenish_location', 'location_id', 'usage')
    def _check_replenish_location(self):
        for loc in self:
            if loc.replenish_location:
                # cannot have parent/child location set as replenish as well
                replenish_wh_location = self.search([('id', '!=', loc.id), ('replenish_location', '=', True), '|', ('location_id', 'child_of', loc.id), ('location_id', 'parent_of', loc.id)], limit=1)
                if replenish_wh_location:
                    raise ValidationError(_('Another parent/sub replenish location %s exists, if you wish to change it, uncheck it first', replenish_wh_location.name))

    @api.constrains('scrap_location')
    def _check_scrap_location(self):
        for record in self:
            if record.scrap_location and self.env['stock.picking.type'].search_count([('code', '=', 'mrp_operation'), ('default_location_dest_id', '=', record.id)], limit=1):
                raise ValidationError(_("You cannot set a location as a scrap location when it is assigned as a destination location for a manufacturing type operation."))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_data(self):
        inter_company_location = self.env.ref('stock.stock_location_inter_company')
        if inter_company_location in self:
            raise ValidationError(_('The %s location is required by the Inventory app and cannot be deleted, but you can archive it.', inter_company_location.name))

    def _search_is_empty(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise NotImplementedError(_(
                "The search does not support the %(operator)s operator or %(value)s value.",
                operator=operator,
                value=value,
            ))
        groups = self.env['stock.quant']._read_group([
            ('location_id.usage', 'in', ['internal', 'transit'])],
            ['location_id'], ['quantity:sum'])
        location_ids = {loc.id for loc, quantity in groups if quantity >= 0}
        if value and operator == '=' or not value and operator == '!=':
            return [('id', 'not in', list(location_ids))]
        return [('id', 'in', list(location_ids))]

    def write(self, values):
        if 'company_id' in values:
            for location in self:
                if location.company_id.id != values['company_id']:
                    raise UserError(_("Changing the company of this record is forbidden at this point, you should rather archive it and create a new one."))
        if 'usage' in values and values['usage'] == 'view':
            if self.quant_ids:
                raise UserError(_("This location's usage cannot be changed to view as it contains products."))
        if 'usage' in values or 'scrap_location' in values:
            modified_locations = self.filtered(
                lambda l: any(l[f] != values[f] if f in values else False
                              for f in {'usage', 'scrap_location'}))
            reserved_quantities = self.env['stock.quant'].search_count([
                ('location_id', 'in', modified_locations.ids),
                ('quantity', '>', 0),
                ],
                limit=1)
            if reserved_quantities:
                raise UserError(_(
                    "Internal locations having stock can't be converted"
                ))
        if 'active' in values:
            if not values['active']:
                for location in self:
                    warehouses = self.env['stock.warehouse'].search([('active', '=', True), '|', ('lot_stock_id', '=', location.id), ('view_location_id', '=', location.id)], limit=1)
                    if warehouses:
                        raise UserError(_(
                            "You cannot archive location %(location)s because it is used by warehouse %(warehouse)s",
                            location=location.display_name, warehouse=warehouses.display_name))

            if not self.env.context.get('do_not_check_quant'):
                children_location = self.env['stock.location'].with_context(active_test=False).search([('id', 'child_of', self.ids)])
                internal_children_locations = children_location.filtered(lambda l: l.usage == 'internal')
                children_quants = self.env['stock.quant'].search(['&', '|', ('quantity', '!=', 0), ('reserved_quantity', '!=', 0), ('location_id', 'in', internal_children_locations.ids)])
                if children_quants and not values['active']:
                    raise UserError(_(
                        "You can't disable locations %s because they still contain products.",
                        ', '.join(children_quants.location_id.mapped('display_name'))))
                else:
                    super(StockLocation, children_location - self).with_context(do_not_check_quant=True).write({
                        'active': values['active'],
                    })

        res = super().write(values)
        self.invalidate_model(['warehouse_id'])
        return res

    def unlink(self):
        return super(StockLocation, self.search([('id', 'child_of', self.ids)])).unlink()

    @api.model
    def name_create(self, name):
        if name:
            name_split = name.split('/')
            parent_location = self.env['stock.location'].search([
                ('complete_name', '=', '/'.join(name_split[:-1])),
            ], limit=1)
            new_location = self.create({
                'name': name.split('/')[-1],
                'location_id': parent_location.id if parent_location else False,
            })
            return new_location.id, new_location.display_name
        return super().name_create(name)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self.invalidate_model(['warehouse_id'])
        return res

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if 'name' not in default:
            for location, vals in zip(self, vals_list):
                vals['name'] = _("%s (copy)", location.name)
        return vals_list

    def _get_putaway_strategy(self, product, quantity=0, package=None, packaging=None, additional_qty=None):
        """Returns the location where the product has to be put, if any compliant
        putaway strategy is found. Otherwise returns self.
        The quantity should be in the default UOM of the product, it is used when
        no package is specified.
        """
        self = self._check_access_putaway()
        products = self.env.context.get('products', self.env['product.product'])
        products |= product
        # find package type on package or packaging
        package_type = self.env['stock.package.type']
        if package:
            package_type = package.package_type_id
        elif packaging:
            package_type = packaging.package_type_id

        categ = products.categ_id if len(products.categ_id) == 1 else self.env['product.category']
        categs = categ
        while categ.parent_id:
            categ = categ.parent_id
            categs |= categ

        putaway_rules = self.putaway_rule_ids.filtered(lambda rule:
                                                       (not rule.product_id or rule.product_id in products) and
                                                       (not rule.category_id or rule.category_id in categs) and
                                                       (not rule.package_type_ids or package_type in rule.package_type_ids))

        putaway_rules = putaway_rules.sorted(lambda rule: (rule.package_type_ids,
                                                           rule.product_id,
                                                           rule.category_id == categs[:1],  # same categ, not a parent
                                                           rule.category_id),
                                             reverse=True)

        putaway_location = None
        locations = self.child_internal_location_ids
        if putaway_rules:
            # get current product qty (qty in current quants and future qty on assigned ml) of all child locations
            qty_by_location = defaultdict(lambda: 0)
            if locations.storage_category_id:
                if package and package.package_type_id:
                    move_line_data = self.env['stock.move.line']._read_group([
                        ('id', 'not in', list(self._context.get('exclude_sml_ids', set()))),
                        ('result_package_id.package_type_id', '=', package_type.id),
                        ('state', 'not in', ['draft', 'cancel', 'done']),
                    ], ['location_dest_id'], ['result_package_id:count_distinct'])
                    quant_data = self.env['stock.quant']._read_group([
                        ('package_id.package_type_id', '=', package_type.id),
                        ('location_id', 'in', locations.ids),
                    ], ['location_id'], ['package_id:count_distinct'])
                    qty_by_location.update({location_dest.id: count for location_dest, count in move_line_data})
                    for location, count in quant_data:
                        qty_by_location[location.id] += count
                else:
                    move_line_data = self.env['stock.move.line']._read_group([
                        ('id', 'not in', list(self._context.get('exclude_sml_ids', set()))),
                        ('product_id', '=', product.id),
                        ('location_dest_id', 'in', locations.ids),
                        ('state', 'not in', ['draft', 'done', 'cancel'])
                    ], ['location_dest_id'], ['quantity:array_agg', 'product_uom_id:recordset'])
                    quant_data = self.env['stock.quant']._read_group([
                        ('product_id', '=', product.id),
                        ('location_id', 'in', locations.ids),
                    ], ['location_id'], ['quantity:sum'])

                    qty_by_location.update({location.id: quantity_sum for location, quantity_sum in quant_data})
                    for location_dest, quantity_list, uoms in move_line_data:
                        current_qty = sum(ml_uom._compute_quantity(float(qty), product.uom_id) for qty, ml_uom in zip(quantity_list, uoms))
                        qty_by_location[location_dest.id] += current_qty

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
        return self.usage in ('supplier', 'customer', 'inventory', 'production') or self.scrap_location

    def _check_access_putaway(self):
        return self

    def _check_can_be_used(self, product, quantity=0, package=None, location_qty=0):
        """Check if product/package can be stored in the location. Quantity
        should in the default uom of product, it's only used when no package is
        specified."""
        self.ensure_one()
        if self.storage_category_id:
            forecast_weight = self._get_weight(self.env.context.get('exclude_sml_ids', set()))[self]['forecast_weight']
            # check if enough space
            if package and package.package_type_id:
                # check weight
                package_smls = self.env['stock.move.line'].search([('result_package_id', '=', package.id), ('state', 'not in', ['done', 'cancel'])])
                if self.storage_category_id.max_weight < forecast_weight + sum(package_smls.mapped(lambda sml: sml.quantity_product_uom * sml.product_id.weight)):
                    return False
                # check if enough space
                package_capacity = self.storage_category_id.package_capacity_ids.filtered(lambda pc: pc.package_type_id == package.package_type_id)
                if package_capacity and location_qty >= package_capacity.quantity:
                    return False
            else:
                # check weight
                if self.storage_category_id.max_weight < forecast_weight + product.weight * quantity:
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
            if self.storage_category_id.allow_new_product == "same":
                # In case it's a package, `product` is not defined, so try to get
                # the package products from the context
                product = product or self._context.get('products')
                if (positive_quant and positive_quant.product_id != product) or len(product) > 1:
                    return False
                if self.env['stock.move.line'].search_count([
                    ('product_id', '!=', product.id),
                    ('state', 'not in', ('done', 'cancel')),
                    ('location_dest_id', '=', self.id),
                ], limit=1):
                    return False
        return True

    def _child_of(self, other_location):
        self.ensure_one()
        return self.parent_path.startswith(other_location.parent_path)

    def _is_outgoing(self):
        self.ensure_one()
        if self.usage == 'customer':
            return True
        # Can also be True if location is inter-company transit
        inter_comp_location = self.env.ref('stock.stock_location_inter_company', raise_if_not_found=False)
        return self._child_of(inter_comp_location)

    def _get_weight(self, excluded_sml_ids=False):
        """Returns a dictionary with the net and forecasted weight of the location.
        param excluded_sml_ids: set of stock.move.line ids to exclude from the computation
        """
        if not excluded_sml_ids:
            excluded_sml_ids = set()
        Product = self.env['product.product']
        StockMoveLine = self.env['stock.move.line']

        quants = self.env['stock.quant']._read_group(
            [('location_id', 'in', self.ids)],
            groupby=['location_id', 'product_id'], aggregates=['quantity:sum'],
        )
        base_domain = [('state', 'not in', ['draft', 'done', 'cancel']), ('id', 'not in', tuple(excluded_sml_ids))]
        outgoing_move_lines = StockMoveLine._read_group(
            expression.AND([[('location_id', 'in', self.ids)], base_domain]),
            groupby=['location_id', 'product_id'], aggregates=['quantity_product_uom:sum'],
        )
        incoming_move_lines = StockMoveLine._read_group(
            expression.AND([[('location_dest_id', 'in', self.ids)], base_domain]),
            groupby=['location_dest_id', 'product_id'], aggregates=['quantity_product_uom:sum']
        )

        products = Product.union(*(product for __, product, __ in quants + outgoing_move_lines + incoming_move_lines))
        products.fetch(['weight'])

        result = defaultdict(lambda: defaultdict(float))
        for loc, product, quantity_sum in quants:
            weight = quantity_sum * product.weight
            result[loc]['net_weight'] += weight
            result[loc]['forecast_weight'] += weight

        for loc, product, quantity_product_uom_sum in outgoing_move_lines:
            result[loc]['forecast_weight'] -= quantity_product_uom_sum * product.weight

        for dest_loc, product, quantity_product_uom_sum in incoming_move_lines:
            result[dest_loc]['forecast_weight'] += quantity_product_uom_sum * product.weight

        return result


class StockRoute(models.Model):
    _name = 'stock.route'
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
    categ_ids = fields.Many2many('product.category', 'stock_route_categ', 'route_id', 'categ_id', 'Product Categories', copy=False)
    packaging_ids = fields.Many2many('product.packaging', 'stock_route_packaging', 'route_id', 'packaging_id', 'Packagings', copy=False, check_company=True)
    warehouse_domain_ids = fields.One2many('stock.warehouse', compute='_compute_warehouses')
    warehouse_ids = fields.Many2many(
        'stock.warehouse', 'stock_route_warehouse', 'route_id', 'warehouse_id',
        'Warehouses', copy=False, domain="[('id', 'in', warehouse_domain_ids)]")

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if 'name' not in default:
            for route, vals in zip(self, vals_list):
                vals['name'] = _("%s (copy)", route.name)
        return vals_list

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

    def write(self, vals):
        if 'active' in vals:
            rules = self.with_context(active_test=False).rule_ids
            if vals['active']:
                rules.action_unarchive()
            else:
                rules.action_archive()
        return super().write(vals)

    @api.constrains('company_id')
    def _check_company_consistency(self):
        for route in self:
            if not route.company_id:
                continue

            for rule in route.rule_ids:
                if route.company_id.id != rule.company_id.id:
                    raise ValidationError(_(
                        "Rule %(rule)s belongs to %(rule_company)s while the route belongs to %(route_company)s.",
                        rule=rule.display_name,
                        rule_company=rule.company_id.display_name,
                        route_company=route.company_id.display_name,
                    ))
