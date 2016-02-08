# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval as eval
import openerp.addons.decimal_precision as dp
from openerp.tools.float_utils import float_round
from openerp.exceptions import UserError
from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.multi
    def _stock_move_count(self):
        self.reception_count = self.delivery_count = 0
        move_pool = self.env['stock.move']
        moves = move_pool.read_group([
            ('product_id', 'in', self.ids),
            ('location_id.usage', '!=', 'internal'),
            ('location_dest_id.usage', '=', 'internal'),
            ('state', 'in', ('confirmed', 'assigned', 'pending'))
        ], ['product_id'], ['product_id'])
        for move in moves:
            self.reception_count = move['product_id_count']
        moves = move_pool.read_group([
            ('product_id', 'in', self.ids),
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '!=', 'internal'),
            ('state', 'in', ('confirmed', 'assigned', 'pending'))
        ], ['product_id'], ['product_id'])
        for move in moves:
            self.delivery_count = move['product_id_count']

    @api.model
    def view_header_get(self, view_id, view_type):
        res = super(ProductProduct, self).view_header_get(view_id, view_type)
        if res:
            return res
        if (self.env.context.get('active_id', False)) and (self.env.context.get('active_model') == 'stock.location'):
            return _('Products: ')+self.env['stock.location'].browse(self.env.context['active_id']).name
        return res

    @api.multi
    def _get_domain_locations(self):
        '''
        Parses the context and returns a list of location_ids based on it.
        It will return all stock locations when no parameters are given
        Possible parameters are shop, warehouse, location, force_company, compute_child
        '''
        location_obj = self.env['stock.location']
        warehouse_obj = self.env['stock.warehouse']

        location_ids = []
        if self.env.context.get('location', False):
            if isinstance(self.env.context['location'], (int, long)):
                location_ids = [self.env.context['location']]
            elif isinstance(self.env.context['location'], basestring):
                domain = [('complete_name', 'ilike', self.env.context['location'])]
                if self.env.context.get('force_company', False):
                    domain += [('company_id', '=', self.env.context['force_company'])]
                location_ids = location_obj.search(domain,)
            else:
                location_ids = self.env.context['location']
        else:
            if self.env.context.get('warehouse', False):
                if isinstance(self.env.context['warehouse'], (int, long)):
                    wids = [self.env.context['warehouse']]
                elif isinstance(self.env.context['warehouse'], basestring):
                    domain = [('name', 'ilike', self.env.context['warehouse'])]
                    if self.env.context.get('force_company', False):
                        domain += [('company_id', '=', self.env.context['force_company'])]
                    wids = warehouse_obj.search(domain)
                else:
                    wids = self.env.context['warehouse']
            else:
                wids = warehouse_obj.search([])

            for w in wids:
                location_ids.append(w.view_location_id.id)

        operator = self.env.context.get('compute_child', True) and 'child_of' or 'in'
        domain = self.env.context.get('force_company', False) and ['&', ('company_id', '=', self.env.context['force_company'])] or []
        locations = location_obj.browse(location_ids)
        if operator == "child_of" and locations and locations[0].parent_left != 0:
            loc_domain = []
            dest_loc_domain = []
            for loc in locations:
                if loc_domain:
                    loc_domain = ['|'] + loc_domain + ['&', ('location_id.parent_left', '>=', loc.parent_left), ('location_id.parent_left', '<', loc.parent_right)]
                    dest_loc_domain = ['|'] + dest_loc_domain + ['&', ('location_dest_id.parent_left', '>=', loc.parent_left), ('location_dest_id.parent_left', '<', loc.parent_right)]
                else:
                    loc_domain += ['&', ('location_id.parent_left', '>=', loc.parent_left), ('location_id.parent_left', '<', loc.parent_right)]
                    dest_loc_domain += ['&', ('location_dest_id.parent_left', '>=', loc.parent_left), ('location_dest_id.parent_left', '<', loc.parent_right)]

            return (
                domain + loc_domain,
                domain + ['&'] + dest_loc_domain + ['!'] + loc_domain,
                domain + ['&'] + loc_domain + ['!'] + dest_loc_domain
            )
        else:
            return (
                domain + [('location_id', operator, location_ids)],
                domain + ['&', ('location_dest_id', operator, location_ids), '!', ('location_id', operator, location_ids)],
                domain + ['&', ('location_id', operator, location_ids), '!', ('location_dest_id', operator, location_ids)]
            )

    @api.multi
    def _get_domain_dates(self):
        from_date = self.env.context.get('from_date', False)
        to_date = self.env.context.get('to_date', False)
        domain = []
        if from_date:
            domain.append(('date', '>=', from_date))
        if to_date:
            domain.append(('date', '<=', to_date))
        return domain

    @api.v7
    def _product_available(self, cr, uid, ids, field_names=None, arg=False, context=None):
        context = context or {}
        field_names = field_names or []

        domain_products = [('product_id', 'in', ids)]
        domain_quant, domain_move_in, domain_move_out = [], [], []
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations(cr, uid, ids, context=context)
        domain_move_in += self._get_domain_dates(cr, uid, ids, context=context) + [('state', 'not in', ('done', 'cancel', 'draft'))] + domain_products
        domain_move_out += self._get_domain_dates(cr, uid, ids, context=context) + [('state', 'not in', ('done', 'cancel', 'draft'))] + domain_products
        domain_quant += domain_products

        if context.get('lot_id'):
            domain_quant.append(('lot_id', '=', context['lot_id']))
        if context.get('owner_id'):
            domain_quant.append(('owner_id', '=', context['owner_id']))
            owner_domain = ('restrict_partner_id', '=', context['owner_id'])
            domain_move_in.append(owner_domain)
            domain_move_out.append(owner_domain)
        if context.get('package_id'):
            domain_quant.append(('package_id', '=', context['package_id']))

        domain_move_in += domain_move_in_loc
        domain_move_out += domain_move_out_loc
        moves_in = self.pool.get('stock.move').read_group(cr, uid, domain_move_in, ['product_id', 'product_qty'], ['product_id'], context=context)
        moves_out = self.pool.get('stock.move').read_group(cr, uid, domain_move_out, ['product_id', 'product_qty'], ['product_id'], context=context)

        domain_quant += domain_quant_loc
        quants = self.pool.get('stock.quant').read_group(cr, uid, domain_quant, ['product_id', 'qty'], ['product_id'], context=context)
        quants = dict(map(lambda x: (x['product_id'][0], x['qty']), quants))

        moves_in = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_in))
        moves_out = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_out))
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            id = product.id
            qty_available = float_round(quants.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            incoming_qty = float_round(moves_in.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            outgoing_qty = float_round(moves_out.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            virtual_available = float_round(quants.get(id, 0.0) + moves_in.get(id, 0.0) - moves_out.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            res[id] = {
                'qty_available': qty_available,
                'incoming_qty': incoming_qty,
                'outgoing_qty': outgoing_qty,
                'virtual_available': virtual_available,
            }
        return res

    @api.v8
    def _product_available(self):
        domain_products = [('product_id', 'in', self.ids)]
        domain_quant, domain_move_in, domain_move_out = [], [], []
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations()
        domain_move_in += self._get_domain_dates() + [('state', 'not in', ('done', 'cancel', 'draft'))] + domain_products
        domain_move_out += self._get_domain_dates() + [('state', 'not in', ('done', 'cancel', 'draft'))] + domain_products
        domain_quant += domain_products
        if self.env.context.get('lot_id'):
            domain_quant.append(('lot_id', '=', self.env.context['lot_id']))
        if self.env.context.get('owner_id'):
            domain_quant.append(('owner_id', '=', self.env.context['owner_id']))
            owner_domain = ('restrict_partner_id', '=', self.env.context['owner_id'])
            domain_move_in.append(owner_domain)
            domain_move_out.append(owner_domain)
        if self.env.context.get('package_id'):
            domain_quant.append(('package_id', '=', self.env.context['package_id']))

        domain_move_in += domain_move_in_loc
        domain_move_out += domain_move_out_loc
        moves_in = self.env['stock.move'].read_group(domain_move_in, ['product_id', 'product_qty'], ['product_id'])
        moves_out = self.env['stock.move'].read_group(domain_move_out, ['product_id', 'product_qty'], ['product_id'])

        domain_quant += domain_quant_loc
        quants = self.env['stock.quant'].read_group(domain_quant, ['product_id', 'qty'], ['product_id'])

        quants = dict(map(lambda x: (x['product_id'][0], x['qty']), quants))

        moves_in = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_in))
        moves_out = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_out))
        for product in self:
            qty_available = float_round(quants.get(product.id, 0.0), precision_rounding=product.uom_id.rounding)
            incoming_qty = float_round(moves_in.get(product.id, 0.0), precision_rounding=product.uom_id.rounding)
            outgoing_qty = float_round(moves_out.get(product.id, 0.0), precision_rounding=product.uom_id.rounding)
            virtual_available = float_round(quants.get(product.id, 0.0) + moves_in.get(product.id, 0.0) - moves_out.get(product.id, 0.0), precision_rounding=product.uom_id.rounding)
            product.qty_available = qty_available
            product.incoming_qty = incoming_qty
            product.outgoing_qty = outgoing_qty
            product.virtual_available = virtual_available

    @api.model
    def _search_product_quantity(self, obj, name, domain):
        res = []
        for field, operator, value in domain:
            #to prevent sql injections
            assert field in ('qty_available', 'virtual_available', 'incoming_qty', 'outgoing_qty'), 'Invalid domain left operand'
            assert operator in ('<', '>', '=', '!=', '<=', '>='), 'Invalid domain operator'
            assert isinstance(value, (float, int)), 'Invalid domain right operand'

            if operator == '=':
                operator = '=='

            ids = []
            if name == 'qty_available' and (value != 0.0 or operator not in ('==', '>=', '<=')):
                res.append(('id', 'in', self._search_qty_available(operator, value)))
            else:
                product_ids = self.search([])
                if product_ids:
                    #TODO: Still optimization possible when searching virtual quantities
                    for element in product_ids:
                        if eval(str(element[field]) + operator + str(value)):
                            ids.append(element.id)
                    res.append(('id', 'in', ids))
        return res

    @api.model
    def _search_qty_available(self, operator, value):
        domain_quant = []
        if self.env.context.get('lot_id'):
            domain_quant.append(('lot_id', '=', self.env.context['lot_id']))
        if self.env.context.get('owner_id'):
            domain_quant.append(('owner_id', '=', self.env.context['owner_id']))
        if self.env.context.get('package_id'):
            domain_quant.append(('package_id', '=', self.env.context['package_id']))
        domain_quant += self._get_domain_locations([])[0]
        quants = self.env['stock.quant'].read_group(domain_quant, ['product_id', 'qty'], ['product_id'])
        quants = dict(map(lambda x: (x['product_id'][0], x['qty']), quants))
        quants = dict((k, v) for k, v in quants.iteritems() if eval(str(v) + operator + str(value)))
        return(list(quants))

    @api.multi
    def _product_available_text(self):
        res = {}
        for product in self:
            res[product.id] = str(product.qty_available) + _(" On Hand")
        return res

    @api.multi
    def _compute_nbr_reordering_rules(self):
        self.nbr_reordering_rules = self.reordering_min_qty = self.reordering_max_qty = 0
        product_data = self.env['stock.warehouse.orderpoint'].read_group([('product_id', 'in', self.ids)], ['product_id', 'product_min_qty', 'product_max_qty'], ['product_id'])
        for data in product_data:
            Product = self.browse(data['product_id'][0])
            Product.nbr_reordering_rules = int(data['product_id_count'])
            Product.reordering_min_qty = data['product_min_qty']
            Product.reordering_max_qty = data['product_max_qty']

    reception_count = fields.Integer(compute="_stock_move_count", string="Receipt")
    delivery_count = fields.Integer(compute="_stock_move_count", string="Delivery")

    qty_available = fields.Float(compute="_product_available",
        digits_compute=dp.get_precision('Product Unit of Measure'),
        string='Quantity On Hand',
        fnct_search="_search_product_quantity",
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
    virtual_available = fields.Float(compute="_product_available",
        digits_compute=dp.get_precision('Product Unit of Measure'),
        string='Forecast Quantity',
        search="_search_product_quantity",
        help="Forecast quantity (computed as Quantity On Hand "
             "- Outgoing + Incoming)\n"
             "In a context with a single Stock Location, this includes "
             "goods stored in this location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods stored in the Stock Location of this Warehouse, or any "
             "of its children.\n"
             "Otherwise, this includes goods stored in any Stock Location "
             "with 'internal' type.")
    incoming_qty = fields.Float(compute="_product_available",
        digits_compute=dp.get_precision('Product Unit of Measure'),
        string='Incoming',
        search="_search_product_quantity",
        help="Quantity of products that are planned to arrive.\n"
             "In a context with a single Stock Location, this includes "
             "goods arriving to this Location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods arriving to the Stock Location of this Warehouse, or "
             "any of its children.\n"
             "Otherwise, this includes goods arriving to any Stock "
             "Location with 'internal' type.")
    outgoing_qty = fields.Float(compute="_product_available",
        digits_compute=dp.get_precision('Product Unit of Measure'),
        string='Outgoing',
        search="_search_product_quantity",
        help="Quantity of products that are planned to leave.\n"
             "In a context with a single Stock Location, this includes "
             "goods leaving this Location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods leaving the Stock Location of this Warehouse, or "
             "any of its children.\n"
             "Otherwise, this includes goods leaving any Stock "
             "Location with 'internal' type.")

    orderpoint_ids = fields.One2many('stock.warehouse.orderpoint', 'product_id', 'Minimum Stock Rules')
    nbr_reordering_rules = fields.Integer(compute="_compute_nbr_reordering_rules", string='Reordering Rules')
    reordering_min_qty = fields.Float(compute="_compute_nbr_reordering_rules")
    reordering_max_qty = fields.Float(compute="_compute_nbr_reordering_rules")

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ProductProduct, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self.env.context.get('location') and isinstance(self.env.context['location'], int):
            location_info = self.pool.get('stock.location').browse(self.env.context['location'])
            fields = res.get('fields', {})
            if fields:
                if location_info.usage == 'supplier':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Receipts')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Received Qty')

                if location_info.usage == 'internal':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Forecasted Quantity')

                if location_info.usage == 'customer':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Deliveries')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Delivered Qty')

                if location_info.usage == 'inventory':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future P&L')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('P&L Qty')

                if location_info.usage == 'procurement':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Qty')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Unplanned Qty')

                if location_info.usage == 'production':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Productions')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Produced Qty')
        return res

    @api.multi
    def action_view_routes(self):
        templ_ids = self.filtered(lambda templ: templ.product_tmpl_id)
        return templ_ids.action_view_routes()

    @api.multi
    def onchange_tracking(self, tracking):
        if not tracking or tracking == 'none':
            return {}
        unassigned_quants = self.env['stock.quant'].search_count([('product_id', 'in', self.ids), ('lot_id', '=', False), ('location_id.usage', '=', 'internal')])
        if unassigned_quants:
            raise Warning(_('Warning!'), _("You have products in stock that have no lot number.  You can assign serial numbers by doing an inventory.  "))
        return {}


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    @api.multi
    def _product_available(self):
        var_ids = []
        for product in self:
            var_ids += [p.id for p in product.product_variant_ids]
        variant_available = self.pool['product.product']._product_available(self.env.cr, self.env.uid, var_ids, context=self.env.context)

        for product in self:
            for p in product.product_variant_ids:
                product.qty_available = variant_available[p.id]["qty_available"] or 0.0
                product.virtual_available = variant_available[p.id]["virtual_available"] or 0.0
                product.incoming_qty = variant_available[p.id]["incoming_qty"] or 0.0
                product.outgoing_qty = variant_available[p.id]["outgoing_qty"] or 0.0

    @api.model
    def _search_product_quantity(self, obj, name, domain):
        prod = self.env["product.product"]
        product_variant_ids = prod.search(domain)
        return [('product_variant_ids', 'in', product_variant_ids.ids)]

    @api.multi
    def _product_available_text(self):
        res = {}
        for product in self:
            res[product.id] = str(product.qty_available) + _(" On Hand")
        return res

    @api.multi
    def _compute_nbr_reordering_rules(self):
        product_data = self.env['stock.warehouse.orderpoint'].read_group([('product_id.product_tmpl_id', 'in', self.ids)], ['product_id', 'product_min_qty', 'product_max_qty'], ['product_id'])
        for data in product_data:
            ProductTempl = self.browse(data['__domain'][1][2][0])
            ProductTempl.nbr_reordering_rules = int(data['product_id_count']) or 0
            ProductTempl.reordering_min_qty = data['product_min_qty'] or 0
            ProductTempl.reordering_max_qty = data['product_max_qty'] or 0

    @api.model
    def _get_product_template_type(self):
        res = super(ProductTemplate, self)._get_product_template_type()
        if 'product' not in [item[0] for item in res]:
            res.append(('product', 'Stockable Product'))
        return res

    property_stock_procurement = fields.Many2one(
        company_dependent=True,
        comodel_name='stock.location',
        string="Procurement Location",
        domain=[('usage', 'like', 'procurement')],
        help="This stock location will be used, instead of the default one, as the source location for stock moves generated by procurements.")
    property_stock_production = fields.Many2one(
        company_dependent=True,
        comodel_name='stock.location',
        string="Production Location",
        domain=[('usage', 'like', 'production')],
        help="This stock location will be used, instead of the default one, as the source location for stock moves generated by manufacturing orders.")
    property_stock_inventory = fields.Many2one(
        company_dependent=True,
        comodel_name='stock.location',
        string="Inventory Location",
        domain=[('usage', 'like', 'inventory')],
        help="This stock location will be used, instead of the default one, as the source location for stock moves generated when you do an inventory.")

    sale_delay = fields.Float('Customer Lead Time', help="The average delay in days between the confirmation of the customer rder and the delivery of the finished products. It's the time you promise to your customers.", default=7)
    tracking = fields.Selection(selection=[('serial', 'By Unique Serial Number'), ('lot', 'By Lots'), ('none', 'No Tracking')], string="Tracking", required=True, default='none')
    description_picking = fields.Text('Description on Picking', translate=True)

    qty_available = fields.Float(compute="_product_available", digits_compute=dp.get_precision('Product Unit of Measure'),
        search="_search_product_quantity", string='Quantity On Hand')
    virtual_available = fields.Float(compute="_product_available", digits_compute=dp.get_precision('Product Unit of Measure'),
        search="_search_product_quantity", string='Forecasted Quantity')
    incoming_qty = fields.Float(compute="_product_available", digits_compute=dp.get_precision('Product Unit of Measure'),
        search="_search_product_quantity", string='Incoming')
    outgoing_qty = fields.Float(compute="_product_available", digits_compute=dp.get_precision('Product Unit of Measure'),
        search="_search_product_quantity", string='Outgoing')

    # sum of product variant qty
    # 'reception_count': fields.function(_product_available, multi='qty_available',
    #     fnct_search=_search_product_quantity, type='float', string='Quantity On Hand'),
    # 'delivery_count': fields.function(_product_available, multi='qty_available',
    #     fnct_search=_search_product_quantity, type='float', string='Quantity On Hand'),
    route_ids = fields.Many2many('stock.location.route', 'stock_route_product', 'product_id', 'route_id', 'Routes', domain="[('product_selectable', '=', True)]",
                                help="Depending on the modules installed, this will allow you to define the route of the product: whether it will be bought, manufactured, MTO/MTS,...")
    nbr_reordering_rules = fields.Integer(compute="_compute_nbr_reordering_rules", string='Reordering Rules')
    reordering_min_qty = fields.Float(compute="_compute_nbr_reordering_rules")
    reordering_max_qty = fields.Float(compute="_compute_nbr_reordering_rules")
    route_from_categ_ids = fields.Many2many(related='categ_id.total_route_ids', comodel_name="stock.location.route", string="Category Routes")

    @api.multi
    def action_view_routes(self):
        route_obj = self.env["stock.location.route"]
        product_route_ids = set()
        for product in self:
            product_route_ids |= set([r.id for r in product.route_ids])
            product_route_ids |= set([r.id for r in product.categ_id.total_route_ids])
        route_ids = route_obj.search(['|', ('id', 'in', list(product_route_ids)), ('warehouse_selectable', '=', True)])

        result = self.env.ref('stock.action_routes_form').read()[0]
        result['domain'] = "[('id','in',[" + ','.join(map(str, route_ids)) + "])]"
        return result

    @api.onchange('tracking')
    def onchange_tracking(self):
        if not self.tracking:
            return {}
        product_product = self.env['product.product']
        variant_ids = product_product.search([('product_tmpl_id', 'in', self.ids)])
        return variant_ids.onchange_tracking(self.tracking)

    @api.multi
    def _get_products(self):
        products = []
        for prodtmpl in self:
            products += [x.id for x in prodtmpl.product_variant_ids]
        return products

    @api.multi
    def _get_act_window_dict(self, name):
        record = self.env.ref(name)
        return record.read()[0]

    @api.multi
    def action_open_quants(self):
        products = self._get_products()
        result = self._get_act_window_dict('stock.product_open_quants')
        result['domain'] = "[('product_id','in',[" + ','.join(map(str, products)) + "])]"
        result['context'] = "{'search_default_locationgroup': 1, 'search_default_internal_loc': 1}"
        return result

    @api.multi
    def action_view_orderpoints(self):
        products = self._get_products()
        result = self._get_act_window_dict('stock.product_open_orderpoint')
        if len(self.ids) == 1 and len(products) == 1:
            result['context'] = "{'default_product_id': " + str(products[0]) + ", 'search_default_product_id': " + str(products[0]) + "}"
        else:
            result['domain'] = "[('product_id','in',[" + ','.join(map(str, products)) + "])]"
            result['context'] = "{}"
        return result

    @api.multi
    def action_view_stock_moves(self):
        products = self._get_products()
        result = self._get_act_window_dict('stock.act_product_stock_move_open')
        if products:
            result['context'] = "{'default_product_id': %d}" % products[0]
        result['domain'] = "[('product_id.product_tmpl_id','in',[" + ','.join(map(str, self.ids)) + "])]"
        return result

    @api.multi
    def write(self, vals):
        if 'uom_id' in vals:
            new_uom = self.env['product.uom'].browse(vals['uom_id'])
            for product in self:
                old_uom = product.uom_id
                if old_uom != new_uom:
                    if self.env['stock.move'].search([('product_id', 'in', [x.id for x in product.product_variant_ids]), ('state', '=', 'done')], limit=1):
                        raise UserError(_("You can not change the unit of measure of a product that has already been used in a done stock move. If you need to change the unit of measure, you may deactivate this product."))
        return super(ProductTemplate, self).write(vals)

class ProductRemovalStrategy(models.Model):
    _name = 'product.removal'
    _description = 'Removal Strategy'

    name = fields.Char(required=True)
    method = fields.Char(required=True, help="FIFO, LIFO...")


class ProductPutawayStrategy(models.Model):
    _name = 'product.putaway'
    _description = 'Put Away Strategy'

    @api.model
    def _get_putaway_options(self):
        return [('fixed', 'Fixed Location')]

    name = fields.Char(required=True)
    method = fields.Selection(_get_putaway_options, required=True, default='fixed')
    fixed_location_ids = fields.One2many('stock.fixed.putaway.strat', 'putaway_id', 'Fixed Locations Per Product Category', help="When the method is fixed, this location will be used to store the products", copy=True)

    @api.model
    def putaway_apply(self, putaway_strat, product):
        if putaway_strat.method == 'fixed':
            for strat in putaway_strat.fixed_location_ids:
                categ = product.categ_id
                while categ:
                    if strat.category_id.id == categ.id:
                        return strat.fixed_location_id.id
                    categ = categ.parent_id

class FixedPutawayStrat(models.Model):
    _name = 'stock.fixed.putaway.strat'
    _order = 'sequence'

    putaway_id = fields.Many2one('product.putaway', 'Put Away Method', required=True)
    category_id = fields.Many2one('product.category', 'Product Category', required=True)
    fixed_location_id = fields.Many2one('stock.location', 'Location', required=True)
    sequence = fields.Integer('Priority', help="Give to the more specialized category, a higher priority to have them in top of the list.")


class ProductCategory(models.Model):
    _inherit = 'product.category'

    @api.multi
    def calculate_total_routes(self):
        for categ in self:
            categ2 = categ
            routes = [x.id for x in categ.route_ids]
            while categ2.parent_id:
                categ2 = categ2.parent_id
                routes += [x.id for x in categ2.route_ids]
            categ.total_route_ids = routes

    route_ids = fields.Many2many('stock.location.route', 'stock_location_route_categ', 'categ_id', 'route_id', 'Routes', domain="[('product_categ_selectable', '=', True)]")
    removal_strategy_id = fields.Many2one('product.removal', 'Force Removal Strategy', help="Set a specific removal strategy that will be used regardless of the source location for this product category")
    total_route_ids = fields.Many2many(compute="calculate_total_routes", comodel_name='stock.location.route', string='Total routes', readonly=True)
