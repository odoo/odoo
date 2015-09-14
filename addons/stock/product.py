# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.tools.safe_eval import safe_eval as eval
import openerp.addons.decimal_precision as dp
from openerp.tools.float_utils import float_round
from openerp.exceptions import UserError

class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.multi
    @api.depends("reception_count", "delivery_count")
    def _stock_move_count(self, ids, field_name, arg):
        res = dict([(id, {'reception_count': 0, 'delivery_count': 0}) for id in ids])
        move_pool = self.env['stock.move']
        moves = move_pool.read_group([
            ('product_id', 'in', ids),
            ('location_id.usage', '!=', 'internal'),
            ('location_dest_id.usage', '=', 'internal'),
            ('state', 'in', ('confirmed', 'assigned', 'pending'))
        ], ['product_id'], ['product_id'])
        for move in moves:
            product_id = move['product_id'][0]
            res[product_id]['reception_count'] = move['product_id_count']
        moves = move_pool.read_group([
            ('product_id', 'in', ids),
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '!=', 'internal'),
            ('state', 'in', ('confirmed', 'assigned', 'pending'))
        ], ['product_id'], ['product_id'])
        for move in moves:
            product_id = move['product_id'][0]
            res[product_id]['delivery_count'] = move['product_id_count']
        return res

    @api.model
    def view_header_get(self, view_id, view_type):
        res = super(ProductProduct, self).view_header_get(view_id, view_type)
        if res:
            return res
        if (self._context.get('active_id', False)) and (self._context.get('active_model') == 'stock.location'):
            return _('Products: ')+self.env['stock.location'].browse(self._context['active_id']).name
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
        if self._context.get('location'):
            if isinstance(self._context['location'], (int, long)):
                location_ids = [self._context['location']]
            elif isinstance(self._context['location'], basestring):
                domain = [('complete_name', 'ilike', self._context['location'])]
                if self._context.get('force_company'):
                    domain += [('company_id', '=', self._context['force_company'])]
                location_ids = location_obj.search(domain)
            else:
                location_ids = self._context['location']
        else:
            if self._context.get('warehouse'):
                if isinstance(self._context['warehouse'], (int, long)):
                    wids = [self._context['warehouse']]
                elif isinstance(self._context['warehouse'], basestring):
                    domain = [('name', 'ilike', self._context['warehouse'])]
                    if self._context.get('force_company'):
                        domain += [('company_id', '=', self._context['force_company'])]
                    wids = warehouse_obj.search(domain)
                else:
                    wids = self._context['warehouse']
            else:
                wids = warehouse_obj.search([])

            for w in wids:
                location_ids.append(w.view_location_id.id)

        operator = self._context.get('compute_child', True) and 'child_of' or 'in'
        domain = self._context.get('force_company') and ['&', ('company_id', '=', self._context['force_company'])] or []
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
        from_date = self._context.get('from_date')
        to_date = self._context.get('to_date')
        domain = []
        if from_date:
            domain.append(('date', '>=', from_date))
        if to_date:
            domain.append(('date', '<=', to_date))
        return domain

    @api.multi
    def _product_available(self):
        domain_products = [('product_id', 'in', self.ids)]
        domain_quant, domain_move_in, domain_move_out = [], [], []
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations()
        domain_move_in += self._get_domain_dates() + [('state', 'not in', ('done', 'cancel', 'draft'))] + domain_products
        domain_move_out += self._get_domain_dates() + [('state', 'not in', ('done', 'cancel', 'draft'))] + domain_products
        domain_quant += domain_products

        if self._context.get('lot_id'):
            domain_quant.append(('lot_id', '=', self._context['lot_id']))
        if self._context.get('owner_id'):
            domain_quant.append(('owner_id', '=', self._context['owner_id']))
            owner_domain = ('restrict_partner_id', '=', self._context['owner_id'])
            domain_move_in.append(owner_domain)
            domain_move_out.append(owner_domain)
        if self._context.get('package_id'):
            domain_quant.append(('package_id', '=', self._context['package_id']))

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
            product.qty_available = float_round(quants.get(product.id, 0.0), precision_rounding=product.uom_id.rounding)
            product.incoming_qty = float_round(moves_in.get(product.id, 0.0), precision_rounding=product.uom_id.rounding)
            product.outgoing_qty = float_round(moves_out.get(product.id, 0.0), precision_rounding=product.uom_id.rounding)
            product.virtual_available = float_round(quants.get(product.id, 0.0) + moves_in.get(product.id, 0.0) - moves_out.get(product.id, 0.0), precision_rounding=product.uom_id.rounding)

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
        if self._context.get('lot_id'):
            domain_quant.append(('lot_id', '=', self._context['lot_id']))
        if self._context.get('owner_id'):
            domain_quant.append(('owner_id', '=', self._context['owner_id']))
        if self._context.get('package_id'):
            domain_quant.append(('package_id', '=', self._context['package_id']))
        domain_quant += self._get_domain_locations([])[0]
        quants = self.env['stock.quant'].read_group(domain_quant, ['product_id', 'qty'], ['product_id'])
        quants = dict(map(lambda x: (x['product_id'][0], x['qty']), quants))
        quants = dict((k, v) for k, v in quants.iteritems() if eval(str(v) + operator + str(value)))
        return(list(quants))

    @api.multi
    def _product_available_text(self, field_names=None, arg=False):
        res = {}
        for product in self:
            res[product.id] = str(product.qty_available) + _(" On Hand")
        return res

    @api.multi
    @api.depends("nbr_reordering_rules", "reordering_min_qty", "reordering_max_qty")
    def _compute_nbr_reordering_rules(self, field_names=None, arg=None):
        res = dict.fromkeys(self.ids, {'nbr_reordering_rules': 0, 'reordering_min_qty': 0, 'reordering_max_qty': 0})
        product_data = self.env['stock.warehouse.orderpoint'].read_group([('product_id', 'in', self.ids)], ['product_id', 'product_min_qty', 'product_max_qty'], ['product_id'])
        for data in product_data:
            res[data['product_id'][0]]['nbr_reordering_rules'] = int(data['product_id_count'])
            res[data['product_id'][0]]['reordering_min_qty'] = data['product_min_qty']
            res[data['product_id'][0]]['reordering_max_qty'] = data['product_max_qty']
        return res

    reception_count = fields.Integer(compute='_stock_move_count', string="Receipt")
    delivery_count = fields.Integer(compute='_stock_move_count', string="Delivery")
    qty_available = fields.Float(compute='_product_available', digits_compute=dp.get_precision('Product Unit of Measure'), multi='qty_available',
        string='Quantity On Hand',
        search='_search_qty_available',
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
    virtual_available = fields.Float(compute='_product_available', digits=dp.get_precision('Product Unit of Measure'), multi='qty_available',
        string='Forecast Quantity',
        search='_search_virtual_available',
        help="Forecast quantity (computed as Quantity On Hand "
             "- Outgoing + Incoming)\n"
             "In a context with a single Stock Location, this includes "
             "goods stored in this location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods stored in the Stock Location of this Warehouse, or any "
             "of its children.\n"
             "Otherwise, this includes goods stored in any Stock Location "
             "with 'internal' type.")
    incoming_qty = fields.Float(compute='_product_available',
        digits=dp.get_precision('Product Unit of Measure'),
        string='Incoming', multi='qty_available',
        search='_search_incoming_quantity',
        help="Quantity of products that are planned to arrive.\n"
             "In a context with a single Stock Location, this includes "
             "goods arriving to this Location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods arriving to the Stock Location of this Warehouse, or "
             "any of its children.\n"
             "Otherwise, this includes goods arriving to any Stock "
             "Location with 'internal' type.")
    outgoing_qty = fields.Float(compute='_product_available', digits=dp.get_precision('Product Unit of Measure'), multi='qty_available',
        string='Outgoing',
        search='_search_outgoing_quantity',
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
    def fields_view_get(self, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(ProductProduct, self).fields_view_get(view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu)
        if context is None:
            context = {}
        if context.get('location') and isinstance(context['location'], int):
            location_info = self.env['stock.location'].browse(self._context['location'])
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

    @api.model
    def action_view_routes(self, ids):
        template_obj = self.env["product.template"]
        templ_ids = list(set([x.product_tmpl_id.id for x in self.browse(ids)]))
        return template_obj.action_view_routes(templ_ids)

    @api.model
    def onchange_tracking(self, ids, tracking):
        if not tracking or tracking == 'none':
            return {}
        unassigned_quants = self.pool['stock.quant'].search_count([('product_id', 'in', ids), ('lot_id', '=', False), ('location_id.usage', '=', 'internal')])
        if unassigned_quants:
            return {'warning': {
                    'title': _('Warning!'),
                    'message': _("You have products in stock that have no lot number.  You can assign serial numbers by doing an inventory.  ")}}
        return {}


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    @api.depends('qty_available', 'virtual_available', 'outgoing_qty', 'outgoing_qty')
    def _product_available(self):
        var_ids = []
        for product in self:
            var_ids += [p.id for p in product.product_variant_ids]
        variant_available = self.product_variant_ids._product_available()

        for product in self:
            for p in product.product_variant_ids:
                p.qty_available += variant_available[p.id]["qty_available"] or 0
                p.virtual_available += variant_available[p.id]["virtual_available"] or 0
                p.incoming_qty += variant_available[p.id]["incoming_qty"] or 0
                p.outgoing_qty += variant_available[p.id]["outgoing_qty"] or 0

    @api.model
    def _search_product_quantity(self, obj, name, domain):
        prod = self.env["product.product"]
        product_variant_ids = prod.search(domain)
        return [('product_variant_ids', 'in', product_variant_ids)]

    @api.multi
    def _product_available_text(self, field_names=None, arg=False):
        res = {}
        for product in self:
            res[product.id] = str(product.qty_available) + _(" On Hand")
        return res

    @api.depends('nbr_reordering_rules', 'reordering_min_qty', 'route_from_categ_ids')
    def _compute_nbr_reordering_rules(self):
        res = dict.fromkeys(self.ids, {'nbr_reordering_rules': 0, 'reordering_min_qty': 0, 'reordering_max_qty': 0})
        product_data = self.env['stock.warehouse.orderpoint'].read_group([('product_id.product_tmpl_id', 'in', self.ids)], ['product_id', 'product_min_qty', 'product_max_qty'], ['product_id'])
        for data in product_data:
            product_tmpl_id = data['__domain'][1][2][0]
            res[product_tmpl_id]['nbr_reordering_rules'] = int(data['product_id_count'])
            res[product_tmpl_id]['reordering_min_qty'] = data['product_min_qty']
            res[product_tmpl_id]['reordering_max_qty'] = data['product_max_qty']
        return res

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
    sale_delay = fields.Float('Customer Lead Time', help="The average delay in days between the confirmation of the customer order and the delivery of the finished products. It's the time you promise to your customers.", default=7)
    tracking = fields.Selection(selection=[('serial', 'By Unique Serial Number'), ('lot', 'By Lots'), ('none', 'No Tracking')], string="Tracking", required=True, default='none')
    description_picking = fields.Text('Description on Picking', translate=True)
    # sum of product variant qty
    # 'reception_count': fields.function(_product_available, multi='qty_available',
    #     fnct_search=_search_product_quantity, type='float', string='Quantity On Hand'),
    # 'delivery_count': fields.function(_product_available, multi='qty_available',
    #     fnct_search=_search_product_quantity, type='float', string='Quantity On Hand'),
    qty_available = fields.Float(compute="_product_available",
        search="_search_product_quantity", string='Quantity On Hand')
    virtual_available = fields.Float(compute="_product_available",
        search="_search_product_quantity", string='Forecasted Quantity')
    incoming_qty = fields.Float(compute="_product_available",
        search="_search_product_quantity", string='Incoming')
    outgoing_qty = fields.Float(compute="_product_available",
        search="_search_product_quantity", string='Outgoing')
    location_id = fields.Many2one(string='Location', comodel_name='stock.location')
    warehouse_id = fields.Many2one(string='Warehouse', comodel_name='stock.warehouse')
    route_ids = fields.Many2many('stock.location.route', 'stock_route_product', 'product_id', 'route_id', 'Routes', domain="[('product_selectable', '=', True)]",
                                help="Depending on the modules installed, this will allow you to define the route of the product: whether it will be bought, manufactured, MTO/MTS,...")
    nbr_reordering_rules = fields.Integer(compute="_compute_nbr_reordering_rules", string='Reordering Rules')
    reordering_min_qty = fields.Float(compute="_compute_nbr_reordering_rules")
    reordering_max_qty = fields.Float(compute="_compute_nbr_reordering_rules")
    route_from_categ_ids = fields.Many2many(related='categ_id.total_route_ids', comodel_name="stock.location.route", string="Category Routes")

    @api.multi
    def action_view_routes(self):
        route_obj = self.Env["stock.location.route"]
        act_obj = self.env['ir.actions.act_window']
        mod_obj = self.env['ir.model.data']
        product_route_ids = set()
        for product in self:
            product_route_ids |= set([r.id for r in product.route_ids])
            product_route_ids |= set([r.id for r in product.categ_id.total_route_ids])
        route_ids = route_obj.search(['|', ('id', 'in', list(product_route_ids)), ('warehouse_selectable', '=', True)])
        result = mod_obj.xmlid_to_res_id('stock.action_routes_form', raise_if_not_found=True)
        result = act_obj.read([result])[0]
        result['domain'] = "[('id','in',[" + ','.join(map(str, route_ids)) + "])]"
        return result

    @api.onchange('tracking')
    def onchange_tracking(self):
        if self.tracking:
            product_product = self.env['product.product']
            variant_ids = product_product.search([('product_tmpl_id', 'in', self.ids)])
            return product_product.onchange_tracking(variant_ids, self.tracking)

    @api.model
    def _get_products(self):
        products = []
        for prodtmpl in self:
            products += [x.id for x in prodtmpl.product_variant_ids]
        return products

    @api.model
    def _get_act_window_dict(self, name):
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']
        result = mod_obj.xmlid_to_res_id(name, raise_if_not_found=True)
        result = act_obj.read([result])[0]
        return result

    @api.multi
    def action_view_orderpoints(self):
        products = self._get_products()
        result = self._get_act_window_dict('stock.product_open_orderpoint')
        if len(self.ids) == 1 and len(products) == 1:
            result.with_context({'default_product_id': str(products[0]), 'search_default_product_id': str(products[0])})
        else:
            result['domain'] = "[('product_id','in',[" + ','.join(map(str, products)) + "])]"
            result.with_context({})
        return result

    @api.multi
    def action_view_stock_moves(self):
        products = self._get_products()
        result = self._get_act_window_dict('stock.act_product_stock_move_open')
        if products:
            result.with_context({'default_product_id': products[0]})
        result['domain'] = "[('product_id.product_tmpl_id','in',[" + ','.join(map(str, self.ids)) + "])]"
        return result

    @api.multi
    def write(self, vals):
        if 'uom_id' in vals:
            new_uom = self.env['product.uom'].browse(vals['uom_id'])
            for product in self:
                old_uom = product.uom_id
                if old_uom != new_uom:
                    if self.env['stock.move'].search([('product_id', 'in', product.product_variant_ids.ids), ('state', '=', 'done')], limit=1):
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
    fixed_location_ids = fields.One2many('stock.fixed.putaway.strat', 'putaway_id', string='Fixed Locations Per Product Category', help="When the method is fixed, this location will be used to store the products", copy=True)

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

    putaway_id = fields.Many2one(comodel_name='product.putaway', string='Put Away Method', required=True)
    category_id = fields.Many2one(comodel_name='product.category', string='Product Category', required=True)
    fixed_location_id = fields.Many2one(comodel_name='stock.location', string='Location', required=True)
    sequence = fields.Integer(string='Priority', help="Give to the more specialized category, a higher priority to have them in top of the list.")


class ProductCategory(models.Model):
    _inherit = 'product.category'

    @api.one
    @api.depends('route_ids', 'parent_id')
    def calculate_total_routes(self):
        res = {}
        for categ in self:
            categ2 = categ
            routes = [x.id for x in categ.route_ids]
            while categ2.parent_id:
                categ2 = categ2.parent_id
                routes += [x.id for x in categ2.route_ids]
            res[categ.id] = routes
        return res

    route_ids = fields.Many2many('stock.location.route', 'stock_location_route_categ', 'categ_id', 'route_id', string='Routes', domain="[('product_categ_selectable', '=', True)]")
    removal_strategy_id = fields.Many2one('product.removal', string='Force Removal Strategy', help="Set a specific removal strategy that will be used regardless of the source location for this product category")
    total_route_ids = fields.Many2many('stock.location.route', compute="calculate_total_routes", string='Total routes', readonly=True)

