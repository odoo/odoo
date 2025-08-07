# Part of Odoo. See LICENSE file for full copyright and licensing details.

import operator as py_operator
from ast import literal_eval
from collections import defaultdict
from collections.abc import Iterable
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools.barcode import check_barcode_encoding
from odoo.tools.float_utils import float_compare
from odoo.tools.mail import html2plaintext, is_html_empty

PY_OPERATORS = {
    '<': py_operator.lt,
    '>': py_operator.gt,
    '<=': py_operator.le,
    '>=': py_operator.ge,
    '=': py_operator.eq,
    '!=': py_operator.ne,
    'in': lambda elem, container: elem in container,
    'not in': lambda elem, container: elem not in container,
}

SERIAL_PREFIX_FORMAT_HELP_TEXT = """
    If multiple products share the same prefix, they will share the same sequence, otherwise the sequence will be dedicated to the product.

    * Legend (for prefix):
    - Current Year with Century: %(year)s
    - Current Year without Century: %(y)s
    - Month: %(month)s
    - Day: %(day)s
    - Day of the Year: %(doy)s
    - Week of the Year: %(woy)s
    - Day of the Week (0:Monday): %(weekday)s
    - Hour 00->24: %(h24)s
    - Hour 00->12: %(h12)s
    - Minute: %(min)s
    - Second: %(sec)s
"""


class ProductProduct(models.Model):
    _inherit = "product.product"

    stock_quant_ids = fields.One2many('stock.quant', 'product_id') # used to compute quantities
    stock_move_ids = fields.One2many('stock.move', 'product_id') # used to compute quantities
    qty_available = fields.Float(
        'Quantity On Hand', compute='_compute_quantities', search='_search_qty_available',
        inverse='_inverse_qty_available', digits='Product Unit', compute_sudo=False,
        help="Current quantity of products.\n"
             "In a context with a single Stock Location, this includes "
             "goods stored at this Location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods stored in the Stock Location of this Warehouse, or any "
             "of its children.\n"
             "stored in the Stock Location of the Warehouse of this Shop, "
             "or any of its children.\n"
             "Otherwise, this includes goods stored in any Stock Location "
             "with 'internal' type.")
    virtual_available = fields.Float(
        'Forecasted Quantity', compute='_compute_quantities', search='_search_virtual_available',
        digits='Product Unit', compute_sudo=False,
        help="Forecast quantity (computed as Quantity On Hand "
             "- Outgoing + Incoming)\n"
             "In a context with a single Stock Location, this includes "
             "goods stored in this location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods stored in the Stock Location of this Warehouse, or any "
             "of its children.\n"
             "Otherwise, this includes goods stored in any Stock Location "
             "with 'internal' type.")
    free_qty = fields.Float(
        'Free To Use Quantity ', compute='_compute_quantities', search='_search_free_qty',
        digits='Product Unit', compute_sudo=False,
        help="Available quantity (computed as Quantity On Hand "
             "- reserved quantity)\n"
             "In a context with a single Stock Location, this includes "
             "goods stored in this location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods stored in the Stock Location of this Warehouse, or any "
             "of its children.\n"
             "Otherwise, this includes goods stored in any Stock Location "
             "with 'internal' type.")
    incoming_qty = fields.Float(
        'Incoming', compute='_compute_quantities', search='_search_incoming_qty',
        digits='Product Unit', compute_sudo=False,
        help="Quantity of planned incoming products.\n"
             "In a context with a single Stock Location, this includes "
             "goods arriving to this Location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods arriving to the Stock Location of this Warehouse, or "
             "any of its children.\n"
             "Otherwise, this includes goods arriving to any Stock "
             "Location with 'internal' type.")
    outgoing_qty = fields.Float(
        'Outgoing', compute='_compute_quantities', search='_search_outgoing_qty',
        digits='Product Unit', compute_sudo=False,
        help="Quantity of planned outgoing products.\n"
             "In a context with a single Stock Location, this includes "
             "goods leaving this Location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods leaving the Stock Location of this Warehouse, or "
             "any of its children.\n"
             "Otherwise, this includes goods leaving any Stock "
             "Location with 'internal' type.")

    orderpoint_ids = fields.One2many('stock.warehouse.orderpoint', 'product_id', 'Minimum Stock Rules')
    nbr_moves_in = fields.Integer(compute='_compute_nbr_moves', compute_sudo=False, help="Number of incoming stock moves in the past 12 months")
    nbr_moves_out = fields.Integer(compute='_compute_nbr_moves', compute_sudo=False, help="Number of outgoing stock moves in the past 12 months")
    nbr_reordering_rules = fields.Integer('Reordering Rules',
        compute='_compute_nbr_reordering_rules', compute_sudo=False)
    reordering_min_qty = fields.Float(
        compute='_compute_nbr_reordering_rules', compute_sudo=False)
    reordering_max_qty = fields.Float(
        compute='_compute_nbr_reordering_rules', compute_sudo=False)
    putaway_rule_ids = fields.One2many('stock.putaway.rule', 'product_id', 'Putaway Rules')
    storage_category_capacity_ids = fields.One2many('stock.storage.category.capacity', 'product_id', 'Storage Category Capacity')
    show_on_hand_qty_status_button = fields.Boolean(compute='_compute_show_qty_status_button')
    show_forecasted_qty_status_button = fields.Boolean(compute='_compute_show_qty_status_button')
    show_qty_update_button = fields.Boolean(compute='_compute_show_qty_update_button')
    valid_ean = fields.Boolean('Barcode is valid EAN', compute='_compute_valid_ean')
    lot_properties_definition = fields.PropertiesDefinition('Lot Properties')

    @api.depends('product_tmpl_id')
    def _compute_show_qty_status_button(self):
        for product in self:
            product.show_on_hand_qty_status_button = product.product_tmpl_id.show_on_hand_qty_status_button
            product.show_forecasted_qty_status_button = product.product_tmpl_id.show_forecasted_qty_status_button

    @api.depends('product_tmpl_id')
    def _compute_show_qty_update_button(self):
        for product in self:
            product.show_qty_update_button = (
                product.product_tmpl_id._should_open_product_quants()
                or product.tracking != 'none'
            )

    @api.depends('barcode')
    def _compute_valid_ean(self):
        self.valid_ean = False
        for product in self:
            if product.barcode:
                product.valid_ean = check_barcode_encoding(product.barcode.rjust(14, '0'), 'gtin14')

    @api.depends('stock_move_ids.product_qty', 'stock_move_ids.state', 'stock_move_ids.quantity')
    @api.depends_context(
        'lot_id', 'owner_id', 'package_id', 'from_date', 'to_date',
        'location', 'warehouse_id', 'allowed_company_ids', 'is_storable'
    )
    def _compute_quantities(self):
        products = self.with_context(prefetch_fields=False).filtered(lambda p: p.type != 'service').with_context(prefetch_fields=True)
        res = products._compute_quantities_dict(self.env.context.get('lot_id'), self.env.context.get('owner_id'), self.env.context.get('package_id'), self.env.context.get('from_date'), self.env.context.get('to_date'))
        for product in products:
            product.with_context(skip_qty_available_update=True).update(res[product.id])
        # Services need to be set with 0.0 for all quantities
        services = self - products
        services.qty_available = 0.0
        services.incoming_qty = 0.0
        services.outgoing_qty = 0.0
        services.virtual_available = 0.0
        services.free_qty = 0.0

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations()
        domain_quant = [('product_id', 'in', self.ids)] + domain_quant_loc
        dates_in_the_past = False
        # only to_date as to_date will correspond to qty_available
        to_date = fields.Datetime.to_datetime(to_date)
        if to_date and to_date < fields.Datetime.now():
            dates_in_the_past = True

        domain_move_in = [('product_id', 'in', self.ids)] + domain_move_in_loc
        domain_move_out = [('product_id', 'in', self.ids)] + domain_move_out_loc
        if lot_id is not None:
            domain_quant += [('lot_id', '=', lot_id)]
        if owner_id is not None:
            domain_quant += [('owner_id', '=', owner_id)]
            domain_move_in += [('restrict_partner_id', '=', owner_id)]
            domain_move_out += [('restrict_partner_id', '=', owner_id)]
        if package_id is not None:
            domain_quant += [('package_id', '=', package_id)]
        if dates_in_the_past:
            domain_move_in_done = list(domain_move_in)
            domain_move_out_done = list(domain_move_out)
        if from_date:
            date_date_expected_domain_from = [('date', '>=', from_date)]
            domain_move_in += date_date_expected_domain_from
            domain_move_out += date_date_expected_domain_from
        if to_date:
            date_date_expected_domain_to = [('date', '<=', to_date)]
            domain_move_in += date_date_expected_domain_to
            domain_move_out += date_date_expected_domain_to
        Move = self.env['stock.move'].with_context(active_test=False)
        Quant = self.env['stock.quant'].with_context(active_test=False)
        domain_move_in_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_in
        domain_move_out_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_out
        moves_in_res = {product.id: product_qty for product, product_qty in Move._read_group(domain_move_in_todo, ['product_id'], ['product_qty:sum'])}
        moves_out_res = {product.id: product_qty for product, product_qty in Move._read_group(domain_move_out_todo, ['product_id'], ['product_qty:sum'])}
        quants_res = {product.id: (quantity, reserved_quantity) for product, quantity, reserved_quantity in Quant._read_group(domain_quant, ['product_id'], ['quantity:sum', 'reserved_quantity:sum'])}
        expired_unreserved_quants_res = {}
        if self.env.context.get('with_expiration'):
            domain_quant += [('removal_date', '<=', self.env.context['with_expiration'])]
            expired_unreserved_quants_res = {product.id: quantity - reserved_quantity for product, quantity, reserved_quantity in Quant._read_group(domain_quant, ['product_id'], ['quantity:sum', 'reserved_quantity:sum'])}
        if dates_in_the_past:
            # Calculate the moves that were done before now to calculate back in time (as most questions will be recent ones)
            domain_move_in_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_in_done
            domain_move_out_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_out_done

            groupby = ['product_id', 'product_uom']
            moves_in_res_past = defaultdict(float)
            for product, uom, quantity in Move._read_group(domain_move_in_done, groupby, ['quantity:sum']):
                moves_in_res_past[product.id] += uom._compute_quantity(quantity, product.uom_id)

            moves_out_res_past = defaultdict(float)
            for product, uom, quantity in Move._read_group(domain_move_out_done, groupby, ['quantity:sum']):
                moves_out_res_past[product.id] += uom._compute_quantity(quantity, product.uom_id)

        res = dict()
        for product in self.with_context(prefetch_fields=False):
            origin_product_id = product._origin.id
            product_id = product.id
            if not origin_product_id:
                res[product_id] = dict.fromkeys(
                    ['qty_available', 'free_qty', 'incoming_qty', 'outgoing_qty', 'virtual_available'],
                    0.0,
                )
                continue
            res[product_id] = {}
            if dates_in_the_past:
                qty_available = quants_res.get(origin_product_id, [0.0])[0] - moves_in_res_past.get(origin_product_id, 0.0) + moves_out_res_past.get(origin_product_id, 0.0)
            else:
                qty_available = quants_res.get(origin_product_id, [0.0])[0]
            reserved_quantity = quants_res.get(origin_product_id, [False, 0.0])[1]
            expired_unreserved_qty = expired_unreserved_quants_res.get(origin_product_id, 0.0)
            res[product_id]['qty_available'] = product.uom_id.round(qty_available)
            res[product_id]['free_qty'] = product.uom_id.round(qty_available - reserved_quantity - expired_unreserved_qty)
            res[product_id]['incoming_qty'] = product.uom_id.round(moves_in_res.get(origin_product_id, 0.0))
            res[product_id]['outgoing_qty'] = product.uom_id.round(moves_out_res.get(origin_product_id, 0.0))
            res[product_id]['virtual_available'] = product.uom_id.round(
                qty_available + res[product_id]['incoming_qty'] - res[product_id]['outgoing_qty'] - expired_unreserved_qty,
            )

        return res

    def _inverse_qty_available(self):
        """
        Inverse method for the 'qty_available' field, enabling manual adjustment of stock on hand quantity
        in the product form. To prevent the automatic creation of stock quants when the
        'compute_quantities' method is triggered, this method skips quant creation by custom context key.
        """
        if self.env.context.get('skip_qty_available_update', False):
            return
        for product in self:
            if (
                product.type == "consu" and product.is_storable and float_compare(product.qty_available,
                     0.0, precision_rounding=product.uom_id.rounding) >= 0
            ):
                warehouse = self.env['stock.warehouse'].search(
                    [('company_id', '=', self.env.company.id)], limit=1
                )
                self.env['stock.quant'].with_context(inventory_mode=True, from_inverse_qty=True).create({
                    'product_id': product.id,
                    'location_id': warehouse.lot_stock_id.id,
                    'inventory_quantity': product.qty_available,
                })._apply_inventory()

    def _compute_nbr_moves(self):
        incoming_moves = self.env['stock.move.line']._read_group([
                ('product_id', 'in', self.ids),
                ('state', '=', 'done'),
                ('picking_code', '=', 'incoming'),
                ('date', '>=', fields.Datetime.now() - relativedelta(years=1))
            ], ['product_id'], ['__count'])
        outgoing_moves = self.env['stock.move.line']._read_group([
                ('product_id', 'in', self.ids),
                ('state', '=', 'done'),
                ('picking_code', '=', 'outgoing'),
                ('date', '>=', fields.Datetime.now() - relativedelta(years=1))
            ], ['product_id'], ['__count'])
        res_incoming = {product.id: count for product, count in incoming_moves}
        res_outgoing = {product.id: count for product, count in outgoing_moves}
        for product in self:
            product.nbr_moves_in = res_incoming.get(product.id, 0)
            product.nbr_moves_out = res_outgoing.get(product.id, 0)

    def get_components(self):
        self.ensure_one()
        return self.ids

    def _get_description(self, picking_type_id):
        """
            Return product description based on the picking type:
            * For outgoing pickings, we always use the product name.
            * For all other pickings, we try to use the product description (if one has been set),
              otherwise we fall back to the product name.
        """
        self.ensure_one()
        if picking_type_id.code == 'outgoing':
            return self.display_name
        return html2plaintext(self.description) if not is_html_empty(self.description) else self.display_name

    def _get_picking_description(self, picking_type_id):
        """
        Return product receipt/delivery/picking description depending on picking type passed as argument.
        """
        return {
            'incoming': self.description_pickingin,
            'outgoing': self.description_pickingout,
            'internal': self.description_picking
        }.get(picking_type_id.code, '')

    def _get_domain_locations(self):
        '''
        Parses the context and returns a list of location_ids based on it.
        It will return all stock locations when no parameters are given
        Possible parameters are shop, warehouse, location, compute_child
        '''
        Location = self.env['stock.location']
        Warehouse = self.env['stock.warehouse']

        def _search_ids(model, values):
            ids = set()
            domains = []
            for item in values:
                if isinstance(item, int):
                    ids.add(item)
                else:
                    domains.append(Domain(self.env[model]._rec_name, 'ilike', item))
            if domains:
                ids |= set(self.env[model].search(Domain.OR(domains)).ids)
            return ids

        # We may receive a location or warehouse from the context, either by explicit
        # python code or by the use of dummy fields in the search view.
        # Normalize them into a list.
        location = self.env.context.get('location') or self.env.context.get('search_location')
        if location and not isinstance(location, list):
            location = [location]
        warehouse = self.env.context.get('warehouse_id') or self.env.context.get('search_warehouse')
        if warehouse and not isinstance(warehouse, list):
            warehouse = [warehouse]
        # filter by location and/or warehouse
        if warehouse:
            w_ids = set(Warehouse.browse(_search_ids('stock.warehouse', warehouse)).mapped('view_location_id').ids)
            if location:
                l_ids = _search_ids('stock.location', location)
                parents = Location.browse(w_ids).mapped("parent_path")
                location_ids = {
                    loc.id
                    for loc in Location.browse(l_ids)
                    if any(loc.parent_path.startswith(parent) for parent in parents)
                }
            else:
                location_ids = w_ids
        else:
            if location:
                location_ids = _search_ids('stock.location', location)
            else:
                location_ids = set(Warehouse.search(
                    [('company_id', 'in', self.env.companies.ids)]
                ).mapped('view_location_id').ids)

        return self._get_domain_locations_new(location_ids)

    def _get_domain_locations_new(self, location_ids) -> tuple[Domain, Domain, Domain]:
        if not location_ids:
            return (Domain.FALSE,) * 3
        locations = self.env['stock.location'].browse(location_ids)
        # TDE FIXME: should move the support of child_of + bypass_search_access directly in expression
        # this optimizes [('location_id', 'child_of', locations.ids)]
        # by avoiding the ORM to search for children locations and injecting a
        # lot of location ids into the main query
        if self.env.context.get('strict'):
            loc_domain = Domain('location_id', 'in', locations.ids)
            dest_loc_domain = Domain('location_dest_id', 'in', locations.ids)
            dest_loc_domain_out = Domain('location_dest_id', 'in', locations.ids)
        elif locations:
            paths_domain = Domain.OR(Domain('parent_path', '=like', loc.parent_path + '%') for loc in locations)
            loc_domain = Domain('location_id', 'any', paths_domain)
            # The condition should be split for done and not-done moves as the final_dest_id only make sense
            # for the part of the move chain that is not done yet.
            dest_loc_domain_done = Domain('location_dest_id', 'any', paths_domain)
            dest_loc_domain_in_progress = Domain([
                '|',
                    '&', ('location_final_id', '!=', False), ('location_final_id', 'any', paths_domain),
                    '&', ('location_final_id', '=', False), ('location_dest_id', 'any', paths_domain),
            ])
            dest_loc_domain = Domain([
                '|',
                    '&', ('state', '=', 'done'), dest_loc_domain_done,
                    '&', ('state', '!=', 'done'), dest_loc_domain_in_progress,
            ])
            dest_loc_domain_out = Domain([
                '|',
                    '&', ('state', '=', 'done'), ~dest_loc_domain_done,
                    '&', ('state', '!=', 'done'), ~dest_loc_domain_in_progress,
            ])

        # returns: (domain_quant_loc, domain_move_in_loc, domain_move_out_loc)
        return (
            loc_domain,
            dest_loc_domain & ~loc_domain,
            loc_domain & dest_loc_domain_out,
        )

    def _search_qty_available(self, operator, value):
        # In the very specific case we want to retrieve products with stock available, we only need
        # to use the quants, not the stock moves. Therefore, we bypass the usual
        # '_search_product_quantity' method and call '_search_qty_available_new' instead. This
        # allows better performances.
        if not ({'from_date', 'to_date'} & set(self.env.context.keys())):
            product_ids = self._search_qty_available_new(
                operator, value, self.env.context.get('lot_id'), self.env.context.get('owner_id'),
                self.env.context.get('package_id')
            )
            return [('id', 'in', product_ids)]
        return self._search_product_quantity(operator, value, 'qty_available')

    def _search_virtual_available(self, operator, value):
        # TDE FIXME: should probably clean the search methods
        return self._search_product_quantity(operator, value, 'virtual_available')

    def _search_incoming_qty(self, operator, value):
        # TDE FIXME: should probably clean the search methods
        return self._search_product_quantity(operator, value, 'incoming_qty')

    def _search_outgoing_qty(self, operator, value):
        # TDE FIXME: should probably clean the search methods
        return self._search_product_quantity(operator, value, 'outgoing_qty')

    def _search_free_qty(self, operator, value):
        return self._search_product_quantity(operator, value, 'free_qty')

    def _search_product_quantity(self, operator, value, field):
        # Order the search on `id` to prevent the default order on the product name which slows
        # down the search.
        ids = self.with_context(prefetch_fields=False).search_fetch([], [field], order='id').filtered_domain([(field, operator, value)]).ids
        return [('id', 'in', ids)]

    def _search_qty_available_new(self, operator, value, lot_id=False, owner_id=False, package_id=False):
        ''' Optimized method which doesn't search on stock.moves, only on stock.quants. '''
        op = PY_OPERATORS.get(operator)
        if not op:
            return NotImplemented
        if isinstance(value, Iterable) and not isinstance(value, str):
            value = {float(v) for v in value}
        else:
            value = float(value)

        product_ids = set()
        domain_quant = self._get_domain_locations()[0]
        if lot_id:
            domain_quant.append(('lot_id', '=', lot_id))
        if owner_id:
            domain_quant.append(('owner_id', '=', owner_id))
        if package_id:
            domain_quant.append(('package_id', '=', package_id))
        quants_groupby = self.env['stock.quant']._read_group(domain_quant, ['product_id'], ['quantity:sum'])

        # check if we need include zero values in result
        include_zero = op(0.0, value)

        processed_product_ids = set()
        for product, quantity_sum in quants_groupby:
            product_id = product.id
            if include_zero:
                processed_product_ids.add(product_id)
            if op(quantity_sum, value):
                product_ids.add(product_id)

        if include_zero:
            products_without_quants_in_domain = self.env['product.product'].search([
                ('is_storable', '=', True),
                ('id', 'not in', list(processed_product_ids))],
                order='id'
            )
            product_ids |= set(products_without_quants_in_domain.ids)
        return list(product_ids)

    def _compute_nbr_reordering_rules(self):
        read_group_res = self.env['stock.warehouse.orderpoint']._read_group(
            [('product_id', 'in', self.ids)],
            ['product_id'],
            ['__count', 'product_min_qty:sum', 'product_max_qty:sum'])
        mapped_res = {product: aggregates for product, *aggregates in read_group_res}
        for product in self:
            count, product_min_qty_sum, product_max_qty_sum = mapped_res.get(product._origin, (0, 0, 0))
            product.nbr_reordering_rules = count
            product.reordering_min_qty = product_min_qty_sum
            product.reordering_max_qty = product_max_qty_sum

    @api.onchange('tracking')
    def _onchange_tracking(self):
        if any(product.tracking != 'none' and product.qty_available > 0 for product in self):
            return {
                'warning': {
                    'title': _('Warning!'),
                    'message': _("You have product(s) in stock that have no lot/serial number. You can assign lot/serial numbers by doing an inventory adjustment.")}}

    @api.model
    def view_header_get(self, view_id, view_type):
        res = super().view_header_get(view_id, view_type)
        if not res and self.env.context.get('active_id') and self.env.context.get('active_model') == 'stock.location':
            return _(
                'Products: %(location)s',
                location=self.env['stock.location'].browse(self.env.context['active_id']).name,
            )
        return res

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        context_location = self.env.context.get('location') or self.env.context.get('search_location')
        if context_location and isinstance(context_location, int):
            location = self.env['stock.location'].browse(context_location)
            if location.usage == 'supplier':
                if res.get('virtual_available'):
                    res['virtual_available']['string'] = _('Future Receipts')
                if res.get('qty_available'):
                    res['qty_available']['string'] = _('Received Qty')
            elif location.usage == 'internal':
                if res.get('virtual_available'):
                    res['virtual_available']['string'] = _('Forecasted Quantity')
            elif location.usage == 'customer':
                if res.get('virtual_available'):
                    res['virtual_available']['string'] = _('Future Deliveries')
                if res.get('qty_available'):
                    res['qty_available']['string'] = _('Delivered Qty')
            elif location.usage == 'inventory':
                if res.get('virtual_available'):
                    res['virtual_available']['string'] = _('Future P&L')
                if res.get('qty_available'):
                    res['qty_available']['string'] = _('P&L Qty')
            elif location.usage == 'production':
                if res.get('virtual_available'):
                    res['virtual_available']['string'] = _('Future Productions')
                if res.get('qty_available'):
                    res['qty_available']['string'] = _('Produced Qty')
        return res

    def action_view_orderpoints(self):
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_orderpoint")
        action['context'] = literal_eval(action.get('context'))
        action['context'].pop('search_default_trigger', False)
        action['context'].update({
            'search_default_filter_not_snoozed': True,
        })
        if self and len(self) == 1:
            action['context'].update({
                'default_product_id': self.ids[0],
                'search_default_product_id': self.ids[0]
            })
        else:
            action['domain'] = Domain(action.get('domain') or Domain.TRUE) & Domain('product_id', 'in', self.ids)
        return action

    def action_view_routes(self):
        return self.mapped('product_tmpl_id').action_view_routes()

    def action_view_stock_move_lines(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.stock_move_line_action")
        action['domain'] = [('product_id', '=', self.id)]
        return action

    def action_view_related_putaway_rules(self):
        self.ensure_one()
        domain = [
            '|',
                ('product_id', '=', self.id),
                ('category_id', '=', self.product_tmpl_id.categ_id.id),
        ]
        return self.env['product.template']._get_action_view_related_putaway_rules(domain)

    def action_view_storage_category_capacity(self):
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_storage_category_capacity")
        action['context'] = {
            'hide_package_type': True,
        }
        if len(self) == 1:
            action['context'].update({
                'default_product_id': self.id,
            })
        action['domain'] = [('product_id', 'in', self.ids)]
        return action

    def action_open_product_lot(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_product_production_lot_form")
        action['domain'] = [
            ('product_id', '=', self.id),
            '|', ('location_id', '=', False),
                 ('location_id', 'any', self.env['stock.location']._check_company_domain(self.env.context['allowed_company_ids']))
        ]
        action['context'] = {
            'default_product_id': self.id,
            'set_product_readonly': True,
            'search_default_group_by_location': True,
        }
        return action

    # Be aware that the exact same function exists in product.template
    def action_open_quants(self):
        hide_location = not self.env.user.has_group('stock.group_stock_multi_locations')
        hide_lot = all(product.tracking == 'none' for product in self)
        self = self.with_context(
            hide_location=hide_location, hide_lot=hide_lot,
            no_at_date=True, search_default_on_hand=True,
        )

        # If user have rights to write on quant, we define the view as editable.
        if self.env.user.has_group('stock.group_stock_manager'):
            self = self.with_context(inventory_mode=True)
            # Set default location id if multilocations is inactive
            if not self.env.user.has_group('stock.group_stock_multi_locations'):
                user_company = self.env.company
                warehouse = self.env['stock.warehouse'].search(
                    [('company_id', '=', user_company.id)], limit=1
                )
                if warehouse:
                    self = self.with_context(default_location_id=warehouse.lot_stock_id.id)
        # Set default product id if quants concern only one product
        if len(self) == 1:
            self = self.with_context(
                default_product_id=self.id,
                single_product=True
            )
        else:
            self = self.with_context(product_tmpl_ids=self.product_tmpl_id.ids)
        action = self.env['stock.quant'].action_view_quants()
        # note that this action is used by different views w/varying customizations
        if not self.env.context.get('is_stock_report'):
            action['domain'] = [('product_id', 'in', self.ids)]
            action["name"] = _('Update Quantity')
        return action

    def action_product_forecast_report(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.stock_forecasted_product_product_action")
        return action

    def write(self, vals):
        if 'active' in vals:
            self.filtered(lambda p: p.active != vals['active']).with_context(active_test=False).orderpoint_ids.write({
                'active': vals['active']
            })
        return super().write(vals)

    def _get_quantity_in_progress(self, location_ids=False, warehouse_ids=False):
        return defaultdict(float), defaultdict(float)

    def _get_rules_from_location(self, location, route_ids=False, seen_rules=False):
        if not seen_rules:
            seen_rules = self.env['stock.rule']
        warehouse = location.warehouse_id
        if not warehouse and seen_rules:
            warehouse = seen_rules[-1].propagate_warehouse_id
        rule = self.env['procurement.group'].with_context(active_test=True)._get_rule(self, location, {
            'route_ids': route_ids,
            'warehouse_id': warehouse,
        })
        if rule in seen_rules:
            raise UserError(_("Invalid rule's configuration, the following rule causes an endless loop: %s", rule.display_name))
        if not rule:
            return seen_rules
        if rule.procure_method == 'make_to_stock' or rule.action not in ('pull_push', 'pull'):
            return seen_rules | rule
        else:
            return self._get_rules_from_location(rule.location_src_id, seen_rules=seen_rules | rule)

    def _get_dates_info(self, date, location, route_ids=False):
        rules = self._get_rules_from_location(location, route_ids=route_ids)
        delays, _ = rules.with_context(bypass_delay_description=True)._get_lead_days(self)
        return {
            'date_planned': date - relativedelta(days=delays['security_lead_days']),
            'date_order': date - relativedelta(days=delays['security_lead_days'] + delays['purchase_delay']),
        }

    def _get_only_qty_available(self):
        """ Get only quantities available, it is equivalent to read qty_available
        but avoid fetching other qty fields (avoid costly read group on moves)

        :rtype: defaultdict(float)
        """
        domain_quant = Domain.AND([self._get_domain_locations()[0], [('product_id', 'in', self.ids)]])
        quants_groupby = self.env['stock.quant']._read_group(domain_quant, ['product_id'], ['quantity:sum'])
        currents = defaultdict(float)
        currents.update({product.id: quantity for product, quantity in quants_groupby})
        return currents

    def _filter_to_unlink(self):
        domain = [('product_id', 'in', self.ids)]
        lines = self.env['stock.lot']._read_group(domain, ['product_id'])
        linked_product_ids = [product.id for [product] in lines]
        return super(ProductProduct, self - self.browse(linked_product_ids))._filter_to_unlink()

    @api.model
    def _count_returned_sn_products(self, sn_lot):
        domain = self._count_returned_sn_products_domain(sn_lot, or_domains=[])
        if not domain:
            return 0
        return self.env['stock.move.line'].search_count(domain)

    @api.model
    def _count_returned_sn_products_domain(self, sn_lot, or_domains):
        if not or_domains:
            return None
        return Domain([
            ('lot_id', '=', sn_lot.id),
            ('quantity', '=', 1),
            ('state', '=', 'done'),
        ]) & Domain.OR(or_domains)

    def _update_uom(self, to_uom_id):
        for uom, product, moves in self.env['stock.move']._read_group(
            [('product_id', 'in', self.ids)],
            ['product_uom', 'product_id'],
            ['id:recordset'],
        ):
            if uom != product.product_tmpl_id.uom_id:
                raise UserError(_('As other units of measure (ex : %(problem_uom)s) '
                'than %(uom)s have already been used for this product, the change of unit of measure can not be done.'
                'If you want to change it, please archive the product and create a new one.',
                problem_uom=uom.name, uom=product.product_tmpl_id.uom_id.name))
            moves.product_uom = to_uom_id

        for uom, product, move_lines in self.env['stock.move.line']._read_group(
            [('product_id', 'in', self.ids)],
            ['product_uom_id', 'product_id'],
            ['id:recordset'],
        ):
            if uom != product.product_tmpl_id.uom_id:
                raise UserError(_('As other units of measure (ex : %(problem_uom)s) '
                'than %(uom)s have already been used for this product, the change of unit of measure can not be done.'
                'If you want to change it, please archive the product and create a new one.',
                problem_uom=uom.name, uom=product.product_tmpl_id.uom_id.name))
            move_lines.product_uom_id = to_uom_id
        return super()._update_uom(to_uom_id)

    def filter_has_routes(self):
        """ Return products with route_ids
            or whose categ_id has total_route_ids.
        """
        products_with_routes = self.env['product.product']
        # retrieve products with route_ids
        products_with_routes += self.search([('id', 'in', self.ids), ('route_ids', '!=', False)])
        # retrive products with categ_ids having routes
        products_with_routes += self.search([('id', 'in', (self - products_with_routes).ids), ('categ_id.total_route_ids', '!=', False)])
        return products_with_routes

    def _trigger_uom_warning(self):
        res = super()._trigger_uom_warning()
        if res:
            return res
        moves = self.env['stock.move'].sudo().search_count(
            [('product_id', 'in', self.ids)], limit=1
        )
        return bool(moves)


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _check_company_auto = True

    is_storable = fields.Boolean(
        'Track Inventory', store=True, compute='compute_is_storable', readonly=False,
        default=False, precompute=True, tracking=True, help='A storable product is a product for which you manage stock.')
    responsible_id = fields.Many2one(
        'res.users', string='Responsible', default=lambda self: self.env.uid, company_dependent=True, check_company=True,
        help="This user will be responsible of the next activities related to logistic operations for this product.")
    property_stock_production = fields.Many2one(
        'stock.location', "Production Location",
        company_dependent=True, check_company=True, domain="[('usage', '=', 'production'), '|', ('company_id', '=', False), ('company_id', '=', allowed_company_ids[0])]",
        help="This stock location will be used, instead of the default one, as the source location for stock moves generated by manufacturing orders.")
    property_stock_inventory = fields.Many2one(
        'stock.location', "Inventory Location",
        company_dependent=True, check_company=True, domain="[('usage', '=', 'inventory'), '|', ('company_id', '=', False), ('company_id', '=', allowed_company_ids[0])]",
        help="This stock location will be used, instead of the default one, as the source location for stock moves generated when you do an inventory.")
    sale_delay = fields.Integer(
        'Customer Lead Time', default=0,
        help="Delivery lead time, in days. It's the number of days, promised to the customer, between the confirmation of the sales order and the delivery.")
    tracking = fields.Selection([
        ('serial', 'By Unique Serial Number'),
        ('lot', 'By Lots'),
        ('none', 'By Quantity')],
        string="Tracking", required=True, default='none', # Not having a default value here causes issues when migrating.
        compute='_compute_tracking', store=True, readonly=False, precompute=True,
        help="Ensure the traceability of a storable product in your warehouse.")
    lot_sequence_id = fields.Many2one(
        'ir.sequence', 'Serial/Lot Numbers Sequence', default=lambda self: self.env.ref('stock.sequence_production_lots', raise_if_not_found=False),
        help='Technical Field: The Ir.Sequence record that is used to generate serial/lot numbers for this product')
    serial_prefix_format = fields.Char(
        'Custom Lot/Serial', compute='_compute_serial_prefix_format', inverse='_inverse_serial_prefix_format',
        help=SERIAL_PREFIX_FORMAT_HELP_TEXT)
    next_serial = fields.Char(compute='_compute_next_serial')
    description_picking = fields.Text('Description on Picking', translate=True)
    description_pickingout = fields.Text('Description on Delivery Orders', translate=True)
    description_pickingin = fields.Text('Description on Receptions', translate=True)
    qty_available = fields.Float(
        'Quantity On Hand', compute='_compute_quantities', search='_search_qty_available',
        inverse='_inverse_qty_available',compute_sudo=False, digits='Product Unit')
    virtual_available = fields.Float(
        'Forecasted Quantity', compute='_compute_quantities', search='_search_virtual_available',
        compute_sudo=False, digits='Product Unit')
    incoming_qty = fields.Float(
        'Incoming', compute='_compute_quantities', search='_search_incoming_qty',
        compute_sudo=False, digits='Product Unit')
    outgoing_qty = fields.Float(
        'Outgoing', compute='_compute_quantities', search='_search_outgoing_qty',
        compute_sudo=False, digits='Product Unit')
    # The goal of these fields is to be able to put some keys in context from search view in order
    # to influence computed field.
    location_id = fields.Many2one('stock.location', 'Location', store=False)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', store=False)
    has_available_route_ids = fields.Boolean(
        'Routes can be selected on this product', compute='_compute_has_available_route_ids',
        default=lambda self: self.env['stock.route'].search_count([('product_selectable', '=', True)]))
    route_ids = fields.Many2many(
        'stock.route', 'stock_route_product', 'product_id', 'route_id', 'Routes',
        domain=[('product_selectable', '=', True)], depends_context=['company', 'allowed_companies'],
        help="Depending on the modules installed, this will allow you to define the route of the product: whether it will be bought, manufactured, replenished on order, etc.")
    nbr_moves_in = fields.Integer(compute='_compute_nbr_moves', compute_sudo=False, help="Number of incoming stock moves in the past 12 months")
    nbr_moves_out = fields.Integer(compute='_compute_nbr_moves', compute_sudo=False, help="Number of outgoing stock moves in the past 12 months")
    nbr_reordering_rules = fields.Integer('Reordering Rules',
        compute='_compute_nbr_reordering_rules', compute_sudo=False)
    reordering_min_qty = fields.Float(
        compute='_compute_nbr_reordering_rules', compute_sudo=False)
    reordering_max_qty = fields.Float(
        compute='_compute_nbr_reordering_rules', compute_sudo=False)
    # TDE FIXME: seems only visible in a view - remove me ?
    route_from_categ_ids = fields.Many2many(
        string="Category Routes", related='categ_id.total_route_ids', related_sudo=False)
    show_on_hand_qty_status_button = fields.Boolean(compute='_compute_show_qty_status_button')
    show_forecasted_qty_status_button = fields.Boolean(compute='_compute_show_qty_status_button')
    show_qty_update_button = fields.Boolean(compute='_compute_show_qty_update_button')

    @api.depends('type')
    def compute_is_storable(self):
        self.filtered(lambda t: t.type != 'consu' and t.is_storable).is_storable = False

    @api.depends('lot_sequence_id', 'lot_sequence_id.prefix')
    def _compute_serial_prefix_format(self):
        for template in self:
            template.serial_prefix_format = template.lot_sequence_id.prefix or ""

    def _inverse_serial_prefix_format(self):
        valid_sequences = self.env['ir.sequence'].search([('prefix', 'in', self.mapped('serial_prefix_format'))])
        sequences_by_prefix = {seq.prefix: seq for seq in valid_sequences}
        for template in self:
            if template.serial_prefix_format:
                if template.serial_prefix_format in sequences_by_prefix:
                    template.lot_sequence_id = sequences_by_prefix[template.serial_prefix_format]
                else:
                    new_sequence = self.env['ir.sequence'].create({
                        'name': f'{template.name} Serial Sequence',
                        'code': 'stock.lot.serial',
                        'prefix': template.serial_prefix_format,
                        'padding': 7,
                        'company_id': False,
                    })
                    template.lot_sequence_id = new_sequence
                    sequences_by_prefix[template.serial_prefix_format] = new_sequence
            else:
                template.lot_sequence_id = self.env.ref('stock.sequence_production_lots', raise_if_not_found=False)

    @api.depends('serial_prefix_format', 'lot_sequence_id')
    def _compute_next_serial(self):
        for template in self:
            if template.lot_sequence_id:
                template.next_serial = '{:0{}d}{}'.format(
                    template.lot_sequence_id.number_next_actual,
                    template.lot_sequence_id.padding,
                    template.lot_sequence_id.suffix or ""
                )
            else:
                template.next_serial = '0000001'

    @api.depends('is_storable')
    def _compute_show_qty_status_button(self):
        for template in self:
            template.show_on_hand_qty_status_button = template.is_storable
            template.show_forecasted_qty_status_button = template.is_storable

    @api.depends('is_storable')
    def _compute_has_available_route_ids(self):
        self.has_available_route_ids = self.env['stock.route'].search_count([('product_selectable', '=', True)])

    @api.depends('product_variant_count', 'tracking')
    def _compute_show_qty_update_button(self):
        for product in self:
            product.show_qty_update_button = (
                product._should_open_product_quants()
                or product.product_variant_count > 1
                or product.tracking != 'none'
            )

    @api.depends(
        'product_variant_ids.qty_available',
        'product_variant_ids.virtual_available',
        'product_variant_ids.incoming_qty',
        'product_variant_ids.outgoing_qty',
        'tracking',
    )
    @api.depends_context('warehouse_id')
    def _compute_quantities(self):
        res = self._compute_quantities_dict()
        for template in self.with_context(skip_qty_available_update=True):
            template.qty_available = res[template.id]['qty_available']
            template.virtual_available = res[template.id]['virtual_available']
            template.incoming_qty = res[template.id]['incoming_qty']
            template.outgoing_qty = res[template.id]['outgoing_qty']

    def _compute_quantities_dict(self):
        variants_available = {
            p['id']: p for p in self.product_variant_ids._origin.read(['qty_available', 'virtual_available', 'incoming_qty', 'outgoing_qty'])
        }
        prod_available = {}
        for template in self:
            qty_available = 0
            virtual_available = 0
            incoming_qty = 0
            outgoing_qty = 0
            for p in template.product_variant_ids._origin:
                qty_available += variants_available[p.id]["qty_available"]
                virtual_available += variants_available[p.id]["virtual_available"]
                incoming_qty += variants_available[p.id]["incoming_qty"]
                outgoing_qty += variants_available[p.id]["outgoing_qty"]
            prod_available[template.id] = {
                "qty_available": qty_available,
                "virtual_available": virtual_available,
                "incoming_qty": incoming_qty,
                "outgoing_qty": outgoing_qty,
            }
        return prod_available

    def _compute_nbr_moves(self):
        res = defaultdict(lambda: {'moves_in': 0, 'moves_out': 0})
        incoming_moves = self.env['stock.move.line']._read_group([
                ('product_id.product_tmpl_id', 'in', self.ids),
                ('state', '=', 'done'),
                ('picking_code', '=', 'incoming'),
                ('date', '>=', fields.Datetime.now() - relativedelta(years=1))
            ], ['product_id'], ['__count'])
        outgoing_moves = self.env['stock.move.line']._read_group([
                ('product_id.product_tmpl_id', 'in', self.ids),
                ('state', '=', 'done'),
                ('picking_code', '=', 'outgoing'),
                ('date', '>=', fields.Datetime.now() - relativedelta(years=1))
            ], ['product_id'], ['__count'])
        for product, count in incoming_moves:
            product_tmpl_id = product.product_tmpl_id.id
            res[product_tmpl_id]['moves_in'] += count
        for product, count in outgoing_moves:
            product_tmpl_id = product.product_tmpl_id.id
            res[product_tmpl_id]['moves_out'] += count
        for template in self:
            template.nbr_moves_in = res[template.id]['moves_in']
            template.nbr_moves_out = res[template.id]['moves_out']

    def _inverse_qty_available(self):
        if self.env.context.get('skip_qty_available_update', False):
            return
        for template in self:
            if template.qty_available and not template.product_variant_id:
                raise UserError(_("Save the product form before updating the Quantity On Hand."))
            else:
                template.product_variant_id.qty_available = template.qty_available

    @api.model
    def _get_action_view_related_putaway_rules(self, domain):
        return {
            'name': _('Putaway Rules'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.putaway.rule',
            'view_mode': 'list',
            'domain': domain,
        }

    def _search_qty_available(self, operator, value):
        domain = [('qty_available', operator, value)]
        product_variant_query = self.env['product.product']._search(domain)
        return [('product_variant_ids', 'in', product_variant_query)]

    def _search_virtual_available(self, operator, value):
        domain = [('virtual_available', operator, value)]
        product_variant_query = self.env['product.product']._search(domain)
        return [('product_variant_ids', 'in', product_variant_query)]

    def _search_incoming_qty(self, operator, value):
        domain = [('incoming_qty', operator, value)]
        product_variant_query = self.env['product.product']._search(domain)
        return [('product_variant_ids', 'in', product_variant_query)]

    def _search_outgoing_qty(self, operator, value):
        domain = [('outgoing_qty', operator, value)]
        product_variant_query = self.env['product.product']._search(domain)
        return [('product_variant_ids', 'in', product_variant_query)]

    def _compute_nbr_reordering_rules(self):
        res = {k: {'nbr_reordering_rules': 0, 'reordering_min_qty': 0, 'reordering_max_qty': 0} for k in self.ids}
        product_data = self.env['stock.warehouse.orderpoint']._read_group([('product_id.product_tmpl_id', 'in', self.ids)], ['product_id'], ['__count', 'product_min_qty:sum', 'product_max_qty:sum'])
        for product, count, product_min_qty, product_max_qty in product_data:
            product_tmpl_id = product.product_tmpl_id.id
            res[product_tmpl_id]['nbr_reordering_rules'] += count
            res[product_tmpl_id]['reordering_min_qty'] = product_min_qty
            res[product_tmpl_id]['reordering_max_qty'] = product_max_qty
        for template in self:
            if not template.id:
                template.nbr_reordering_rules = 0
                template.reordering_min_qty = 0
                template.reordering_max_qty = 0
                continue
            template.nbr_reordering_rules = res[template.id]['nbr_reordering_rules']
            template.reordering_min_qty = res[template.id]['reordering_min_qty']
            template.reordering_max_qty = res[template.id]['reordering_max_qty']

    @api.onchange('tracking')
    def _onchange_tracking(self):
        return self.mapped('product_variant_ids')._onchange_tracking()

    @api.depends('is_storable')
    def _compute_tracking(self):
        self.filtered(lambda t: not t.is_storable and t.tracking != 'none').tracking = 'none'

    @api.onchange('type')
    def _onchange_type(self):
        # Return a warning when trying to change the product type
        res = super()._onchange_type()
        if self.ids and self.product_variant_ids.ids and self.env['stock.move.line'].sudo().search_count([
            ('product_id', 'in', self.product_variant_ids.ids), ('state', '!=', 'cancel')
        ]):
            res['warning'] = {
                'title': _('Warning!'),
                'message': _(
                    'This product has been used in at least one inventory movement. '
                    'It is not advised to change the Product Type since it can lead to inconsistencies. '
                    'A better solution could be to archive the product and create a new one instead.'
                )
            }
        return res

    @api.model_create_multi
    def create(self, vals_list):
        product_tmpl_quantities = [
            vals.pop('qty_available', 0) for vals in vals_list
        ]

        product_templates = super().create(vals_list)

        if any(product_tmpl_quantities):
            for product_tmpl, qty in zip(product_templates, product_tmpl_quantities):
                if qty > 0 and product_tmpl.tracking == 'none':
                    product_tmpl.product_variant_id.qty_available = qty
        return product_templates

    def write(self, vals):
        if 'company_id' in vals and vals['company_id']:
            products_changing_company = self.filtered(lambda product: product.company_id.id != vals['company_id'])
            if products_changing_company:
                move = self.env['stock.move'].sudo().search([
                    ('product_id', 'in', products_changing_company.product_variant_ids.ids),
                    ('company_id', 'not in', [vals['company_id'], False]),
                ], order=None, limit=1)
                if move:
                    raise UserError(_("This product's company cannot be changed as long as there are stock moves of it belonging to another company."))

                # Forbid changing a product's company when quant(s) exist in another company.
                quant = self.env['stock.quant'].sudo().search([
                    ('product_id', 'in', products_changing_company.product_variant_ids.ids),
                    ('company_id', 'not in', [vals['company_id'], False]),
                    ('quantity', '!=', 0),
                ], order=None, limit=1)
                if quant:
                    raise UserError(_("This product's company cannot be changed as long as there are quantities of it belonging to another company."))

        clean_inventory = False
        if 'is_storable' in vals and any(vals['is_storable'] != prod_tmpl.is_storable and not prod_tmpl.is_storable for prod_tmpl in self):
            clean_inventory = True

        res = super().write(vals)
        if clean_inventory:
            self.env['stock.quant'].sudo()._clean_reservations()
        return res

    def copy(self, default=None):
        new_products = super().copy(default=default)
        # Since we don't copy product variants directly, we need to match the newly
        # created product variants with the old one, and copy the storage category
        # capacity from them.
        new_product_dict = {}
        for product in new_products.product_variant_ids:
            product_attribute_value = product.product_template_attribute_value_ids.product_attribute_value_id
            new_product_dict[product_attribute_value] = product.id
        storage_category_capacity_vals = []
        for storage_category_capacity in self.product_variant_ids.storage_category_capacity_ids:
            product_attribute_value = storage_category_capacity.product_id.product_template_attribute_value_ids.product_attribute_value_id
            storage_category_capacity_vals.append(storage_category_capacity.copy_data({'product_id': new_product_dict[product_attribute_value]})[0])
        self.env['stock.storage.category.capacity'].create(storage_category_capacity_vals)
        return new_products

    def _should_open_product_quants(self):
        self.ensure_one()
        advanced_option_groups = [
            'stock.group_stock_multi_locations',
            'stock.group_tracking_owner',
            'stock.group_tracking_lot',
        ]
        return (
            any(self.env.user.has_group(g) for g in advanced_option_groups)
            or self.tracking != "none"
        )

    # Be aware that the exact same function exists in product.product
    def action_open_quants(self):
        if 'product_variant' in self.env.context:
            return self.env['product.product'].browse(self.env.context['default_product_id']).action_open_quants()
        return self.product_variant_ids.filtered(lambda p: p.active or p.qty_available != 0).action_open_quants()

    def action_view_related_putaway_rules(self):
        self.ensure_one()
        domain = [
            '|',
                ('product_id.product_tmpl_id', '=', self.id),
                ('category_id', '=', self.categ_id.id),
        ]
        return self._get_action_view_related_putaway_rules(domain)

    def action_view_storage_category_capacity(self):
        self.ensure_one()
        return self.product_variant_ids.action_view_storage_category_capacity()

    def action_view_orderpoints(self):
        return self.product_variant_ids.action_view_orderpoints()

    def action_view_stock_move_lines(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.stock_move_line_action")
        action['domain'] = [('product_id.product_tmpl_id', 'in', self.ids)]
        return action

    def action_open_product_lot(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_product_production_lot_form")
        action['domain'] = [
            ('product_id.product_tmpl_id', '=', self.id),
            '|', ('location_id', '=', False),
                 ('location_id', 'any', self.env['stock.location']._check_company_domain(self.env.context['allowed_company_ids']))
        ]
        action['context'] = {
            'default_product_tmpl_id': self.id,
            'search_default_group_by_location': True,
        }
        if self.product_variant_count == 1:
            action['context'].update({
                'default_product_id': self.product_variant_id.id,
            })
        return action

    def action_open_routes_diagram(self):
        products = False
        if self.env.context.get('default_product_id'):
            products = self.env['product.product'].browse(self.env.context['default_product_id'])
        if not products and self.env.context.get('default_product_tmpl_id'):
            products = self.env['product.template'].browse(self.env.context['default_product_tmpl_id']).product_variant_ids
        if not self.env.user.has_group('stock.group_stock_multi_warehouses') and len(products) == 1:
            company = products.company_id or self.env.company
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
            return self.env.ref('stock.action_report_stock_rule').report_action(None, data={
                'product_id': products.id,
                'warehouse_ids': warehouse.ids,
            }, config=False)
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_stock_rules_report")
        action['context'] = self.env.context
        return action

    def action_product_tmpl_forecast_report(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id('stock.stock_forecasted_product_template_action')
        return action


class ProductCategory(models.Model):
    _inherit = 'product.category'

    route_ids = fields.Many2many(
        'stock.route', 'stock_route_categ', 'categ_id', 'route_id', 'Routes',
        domain=[('product_categ_selectable', '=', True)])
    removal_strategy_id = fields.Many2one(
        'product.removal', 'Force Removal Strategy',
        help="Set a specific removal strategy that will be used regardless of the source location for this product category.\n\n"
             "FIFO: products/lots that were stocked first will be moved out first.\n"
             "LIFO: products/lots that were stocked last will be moved out first.\n"
             "Closest location: products/lots closest to the target location will be moved out first.\n"
             "FEFO: products/lots with the closest removal date will be moved out first "
             "(the availability of this method depends on the \"Expiration Dates\" setting).\n"
             "Least Packages: FIFO but with the least number of packages possible when there are several packages containing the same product.",
        tracking=True,
    )
    parent_route_ids = fields.Many2many(
        'stock.route', string='Parent Routes', compute='_compute_parent_route_ids')
    total_route_ids = fields.Many2many(
        'stock.route', string='Total routes', compute='_compute_total_route_ids', search='_search_total_route_ids',
        readonly=True)
    putaway_rule_ids = fields.One2many('stock.putaway.rule', 'category_id', 'Putaway Rules')
    packaging_reserve_method = fields.Selection([
        ('full', 'Reserve Only Full Packagings'),
        ('partial', 'Reserve Partial Packagings'),], string="Reserve Packagings", default='partial',
        help="Reserve Only Full Packagings: will not reserve partial packagings. If customer orders 2 pallets of 1000 units each and you only have 1600 in stock, then only 1000 will be reserved\n"
             "Reserve Partial Packagings: allow reserving partial packagings. If customer orders 2 pallets of 1000 units each and you only have 1600 in stock, then 1600 will be reserved")
    filter_for_stock_putaway_rule = fields.Boolean('stock.putaway.rule', store=False, search='_search_filter_for_stock_putaway_rule')

    @api.depends('parent_id')
    def _compute_parent_route_ids(self):
        for category in self:
            base_cat = category
            routes = self.env['stock.route']
            while base_cat.parent_id:
                base_cat = base_cat.parent_id
                routes |= base_cat.route_ids
            category.parent_route_ids = routes - category.route_ids

    def _search_total_route_ids(self, operator, value):
        categories = self.with_context(active_test=False).search([])
        categ_ids = categories.filtered_domain([('total_route_ids', operator, value)]).ids
        return [('id', 'in', categ_ids)]

    @api.depends('route_ids', 'parent_route_ids')
    def _compute_total_route_ids(self):
        for category in self:
            category.total_route_ids = category.route_ids | category.parent_route_ids

    def _search_filter_for_stock_putaway_rule(self, operator, value):
        if operator != 'in':
            return NotImplemented

        domain = Domain.TRUE
        active_model = self.env.context.get('active_model')
        if active_model in ('product.template', 'product.product') and self.env.context.get('active_id'):
            product = self.env[active_model].browse(self.env.context.get('active_id'))
            product = product.exists()
            if product:
                domain = Domain('id', '=', product.categ_id.id)
        return domain


class UomUom(models.Model):
    _inherit = 'uom.uom'

    package_type_id = fields.Many2one('stock.package.type', string='Package Type')
    route_ids = fields.Many2many(related='package_type_id.route_ids', string='Routes', help='Routes propagated from the package type')

    def write(self, vals):
        # Users can not update the factor if open stock moves are based on it
        keys_to_protect = {'factor', 'relative_factor', 'relative_uom_id'}
        if any(key in vals for key in keys_to_protect):
            changed = self.filtered(
                lambda u: any(
                    f in vals and u[f] != vals[f]
                    for f in ('factor', 'relative_factor')
                ) or ('relative_uom_id' in vals and u.relative_uom_id.id != int(vals['relative_uom_id']))
            )
            if changed:
                error_msg = _(
                    "You cannot change the ratio of this unit of measure"
                    " as some products with this UoM have already been moved"
                    " or are currently reserved."
                )
                if self.env['stock.move'].sudo().search_count([
                    ('product_uom', 'in', changed.ids),
                    ('state', 'not in', ('cancel', 'done'))
                ]):
                    raise UserError(error_msg)
                if self.env['stock.move.line'].sudo().search_count([
                    ('product_uom_id', 'in', changed.ids),
                    ('state', 'not in', ('cancel', 'done')),
                ]):
                    raise UserError(error_msg)
                if self.env['stock.quant'].sudo().search_count([
                    ('product_id.product_tmpl_id.uom_id', 'in', changed.ids),
                    ('quantity', '!=', 0),
                ]):
                    raise UserError(error_msg)
        return super().write(vals)

    def _adjust_uom_quantities(self, qty, quant_uom):
        """ This method adjust the quantities of a procurement if its UoM isn't the same
        as the one of the quant and the parameter 'propagate_uom' is not set.
        """
        procurement_uom = self
        computed_qty = qty
        get_param = self.env['ir.config_parameter'].sudo().get_param
        if get_param('stock.propagate_uom') != '1':
            computed_qty = self._compute_quantity(qty, quant_uom, rounding_method='HALF-UP')
            procurement_uom = quant_uom
        else:
            computed_qty = self._compute_quantity(qty, procurement_uom, rounding_method='HALF-UP')
        return (computed_qty, procurement_uom)
