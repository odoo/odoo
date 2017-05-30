# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval as eval
import openerp.addons.decimal_precision as dp
from openerp.tools.float_utils import float_round
from openerp.exceptions import UserError

class product_product(osv.osv):
    _inherit = "product.product"
        
    def _stock_move_count(self, cr, uid, ids, field_name, arg, context=None):
        res = dict([(id, {'reception_count': 0, 'delivery_count': 0}) for id in ids])
        move_pool=self.pool.get('stock.move')
        moves = move_pool.read_group(cr, uid, [
            ('product_id', 'in', ids),
            ('location_id.usage', '!=', 'internal'),
            ('location_dest_id.usage', '=', 'internal'),
            ('state','in',('confirmed','assigned','pending'))
        ], ['product_id'], ['product_id'])
        for move in moves:
            product_id = move['product_id'][0]
            res[product_id]['reception_count'] = move['product_id_count']
        moves = move_pool.read_group(cr, uid, [
            ('product_id', 'in', ids),
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '!=', 'internal'),
            ('state','in',('confirmed','assigned','pending'))
        ], ['product_id'], ['product_id'])
        for move in moves:
            product_id = move['product_id'][0]
            res[product_id]['delivery_count'] = move['product_id_count']
        return res

    def view_header_get(self, cr, user, view_id, view_type, context=None):
        if context is None:
            context = {}
        res = super(product_product, self).view_header_get(cr, user, view_id, view_type, context)
        if res: return res
        if (context.get('active_id', False)) and (context.get('active_model') == 'stock.location'):
            return _('Products: ')+self.pool.get('stock.location').browse(cr, user, context['active_id'], context).name
        return res

    def _get_domain_locations(self, cr, uid, ids, context=None):
        '''
        Parses the context and returns a list of location_ids based on it.
        It will return all stock locations when no parameters are given
        Possible parameters are shop, warehouse, location, force_company, compute_child
        '''
        context = context or {}

        location_obj = self.pool.get('stock.location')
        warehouse_obj = self.pool.get('stock.warehouse')

        location_ids = []
        if context.get('location', False):
            if isinstance(context['location'], (int, long)):
                location_ids = [context['location']]
            elif isinstance(context['location'], basestring):
                domain = [('complete_name','ilike',context['location'])]
                if context.get('force_company', False):
                    domain += [('company_id', '=', context['force_company'])]
                location_ids = location_obj.search(cr, uid, domain, context=context)
            else:
                location_ids = context['location']
        else:
            if context.get('warehouse', False):
                if isinstance(context['warehouse'], (int, long)):
                    wids = [context['warehouse']]
                elif isinstance(context['warehouse'], basestring):
                    domain = [('name', 'ilike', context['warehouse'])]
                    if context.get('force_company', False):
                        domain += [('company_id', '=', context['force_company'])]
                    wids = warehouse_obj.search(cr, uid, domain, context=context)
                else:
                    wids = context['warehouse']
            else:
                wids = warehouse_obj.search(cr, uid, [], context=context)

            for w in warehouse_obj.browse(cr, uid, wids, context=context):
                location_ids.append(w.view_location_id.id)

        operator = context.get('compute_child', True) and 'child_of' or 'in'
        domain = context.get('force_company', False) and ['&', ('company_id', '=', context['force_company'])] or []
        locations = location_obj.browse(cr, uid, location_ids, context=context)
        if operator == "child_of" and locations and locations[0].parent_left != 0:
            loc_domain = []
            dest_loc_domain = []
            for loc in locations:
                if loc_domain:
                    loc_domain = ['|'] + loc_domain  + ['&', ('location_id.parent_left', '>=', loc.parent_left), ('location_id.parent_left', '<', loc.parent_right)]
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

    def _get_domain_dates(self, cr, uid, ids, context):
        from_date = context.get('from_date', False)
        to_date = context.get('to_date', False)
        domain = []
        if from_date:
            domain.append(('date', '>=', from_date))
        if to_date:
            domain.append(('date', '<=', to_date))
        return domain

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
        ctx = context.copy()
        ctx.update({'prefetch_fields': False})
        for product in self.browse(cr, uid, ids, context=ctx):
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

    def _search_product_quantity(self, cr, uid, obj, name, domain, context):
        res = []
        for field, operator, value in domain:
            #to prevent sql injections
            assert field in ('qty_available', 'virtual_available', 'incoming_qty', 'outgoing_qty'), 'Invalid domain left operand'
            assert operator in ('<', '>', '=', '!=', '<=', '>='), 'Invalid domain operator'
            assert isinstance(value, (float, int)), 'Invalid domain right operand'

            if operator == '=':
                operator = '=='

            ids = []
            if name == 'qty_available' and (value != 0.0 or operator not in  ('==', '>=', '<=')):
                res.append(('id', 'in', self._search_qty_available(cr, uid, operator, value, context)))
            else:
                product_ids = self.search(cr, uid, [], context=context)
                if product_ids:
                    #TODO: Still optimization possible when searching virtual quantities
                    for element in self.browse(cr, uid, product_ids, context=context):
                        if eval(str(element[field]) + operator + str(value)):
                            ids.append(element.id)
                    res.append(('id', 'in', ids))
        return res

    def _search_qty_available(self, cr, uid, operator, value, context):
        domain_quant = []
        if context.get('lot_id'):
            domain_quant.append(('lot_id', '=', context['lot_id']))
        if context.get('owner_id'):
            domain_quant.append(('owner_id', '=', context['owner_id']))
        if context.get('package_id'):
            domain_quant.append(('package_id', '=', context['package_id']))
        domain_quant += self._get_domain_locations(cr, uid, [], context=context)[0]
        quants = self.pool.get('stock.quant').read_group(cr, uid, domain_quant, ['product_id', 'qty'], ['product_id'], context=context)
        quants = dict(map(lambda x: (x['product_id'][0], x['qty']), quants))
        quants = dict((k, v) for k, v in quants.iteritems() if eval(str(v) + operator + str(value)))
        return(list(quants))

    def _product_available_text(self, cr, uid, ids, field_names=None, arg=False, context=None):
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = str(product.qty_available) +  _(" On Hand")
        return res

    def _compute_nbr_reordering_rules(self, cr, uid, ids, field_names=None, arg=None, context=None):
        res = {id : {'nbr_reordering_rules': 0, 'reordering_min_qty': 0, 'reordering_max_qty': 0} for id in ids}
        product_data = self.pool['stock.warehouse.orderpoint'].read_group(cr, uid, [('product_id', 'in', ids)], ['product_id', 'product_min_qty', 'product_max_qty'], ['product_id'], context=context)
        for data in product_data:
            res[data['product_id'][0]]['nbr_reordering_rules'] = int(data['product_id_count'])
            res[data['product_id'][0]]['reordering_min_qty'] = data['product_min_qty']
            res[data['product_id'][0]]['reordering_max_qty'] = data['product_max_qty']
        return res

    _columns = {
        'reception_count': fields.function(_stock_move_count, string="Receipt", type='integer', multi='pickings'),
        'delivery_count': fields.function(_stock_move_count, string="Delivery", type='integer', multi='pickings'),
        'qty_available': fields.function(_product_available, multi='qty_available',
            type='float', digits_compute=dp.get_precision('Product Unit of Measure'),
            string='Quantity On Hand',
            fnct_search=_search_product_quantity,
            help="Current quantity of products.\n"
                 "In a context with a single Stock Location, this includes "
                 "goods stored at this Location, or any of its children.\n"
                 "In a context with a single Warehouse, this includes "
                 "goods stored in the Stock Location of this Warehouse, or any "
                 "of its children.\n"
                 "stored in the Stock Location of the Warehouse of this Shop, "
                 "or any of its children.\n"
                 "Otherwise, this includes goods stored in any Stock Location "
                 "with 'internal' type."),
        'virtual_available': fields.function(_product_available, multi='qty_available',
            type='float', digits_compute=dp.get_precision('Product Unit of Measure'),
            string='Forecast Quantity',
            fnct_search=_search_product_quantity,
            help="Forecast quantity (computed as Quantity On Hand "
                 "- Outgoing + Incoming)\n"
                 "In a context with a single Stock Location, this includes "
                 "goods stored in this location, or any of its children.\n"
                 "In a context with a single Warehouse, this includes "
                 "goods stored in the Stock Location of this Warehouse, or any "
                 "of its children.\n"
                 "Otherwise, this includes goods stored in any Stock Location "
                 "with 'internal' type."),
        'incoming_qty': fields.function(_product_available, multi='qty_available',
            type='float', digits_compute=dp.get_precision('Product Unit of Measure'),
            string='Incoming',
            fnct_search=_search_product_quantity,
            help="Quantity of products that are planned to arrive.\n"
                 "In a context with a single Stock Location, this includes "
                 "goods arriving to this Location, or any of its children.\n"
                 "In a context with a single Warehouse, this includes "
                 "goods arriving to the Stock Location of this Warehouse, or "
                 "any of its children.\n"
                 "Otherwise, this includes goods arriving to any Stock "
                 "Location with 'internal' type."),
        'outgoing_qty': fields.function(_product_available, multi='qty_available',
            type='float', digits_compute=dp.get_precision('Product Unit of Measure'),
            string='Outgoing',
            fnct_search=_search_product_quantity,
            help="Quantity of products that are planned to leave.\n"
                 "In a context with a single Stock Location, this includes "
                 "goods leaving this Location, or any of its children.\n"
                 "In a context with a single Warehouse, this includes "
                 "goods leaving the Stock Location of this Warehouse, or "
                 "any of its children.\n"
                 "Otherwise, this includes goods leaving any Stock "
                 "Location with 'internal' type."),
        'orderpoint_ids': fields.one2many('stock.warehouse.orderpoint', 'product_id', 'Minimum Stock Rules'),
        'nbr_reordering_rules': fields.function(_compute_nbr_reordering_rules, string='Reordering Rules', type='integer', multi=True),
        'reordering_min_qty': fields.function(_compute_nbr_reordering_rules, type='float', multi=True),
        'reordering_max_qty': fields.function(_compute_nbr_reordering_rules, type='float', multi=True),
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(product_product, self).fields_view_get(
            cr, uid, view_id=view_id, view_type=view_type, context=context,
            toolbar=toolbar, submenu=submenu)
        if context is None:
            context = {}
        if context.get('location') and isinstance(context['location'], int):
            location_info = self.pool.get('stock.location').browse(cr, uid, context['location'])
            fields=res.get('fields',{})
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


    def action_view_routes(self, cr, uid, ids, context=None):
        template_obj = self.pool.get("product.template")
        templ_ids = list(set([x.product_tmpl_id.id for x in self.browse(cr, uid, ids, context=context)]))
        return template_obj.action_view_routes(cr, uid, templ_ids, context=context)

    def onchange_tracking(self, cr, uid, ids, tracking, context=None):
        if not tracking or tracking == 'none':
            return {}
        unassigned_quants = self.pool['stock.quant'].search_count(cr, uid, [('product_id','in', ids), ('lot_id','=', False), ('location_id.usage','=', 'internal')], context=context)
        if unassigned_quants:
            return {'warning' : {
                    'title': _('Warning!'),
                    'message' : _("You have products in stock that have no lot number.  You can assign serial numbers by doing an inventory.  ")
            }}
        return {}

    def write(self, cr, uid, ids, vals, context=None):
        res = super(product_product, self).write(cr, uid, ids, vals, context=context)
        products = self.pool['product.product'].browse(cr, uid, ids, context=context)
        if 'active' in vals and not vals['active'] and products.mapped('orderpoint_ids').filtered(lambda r: r.active):
            raise UserError(_('You still have some active reordering rules on this product. Please archive or delete them first.'))
        return res


class product_template(osv.osv):
    _name = 'product.template'
    _inherit = 'product.template'
    
    def _product_available(self, cr, uid, ids, name, arg, context=None):
        prod_available = {}
        product_ids = self.browse(cr, uid, ids, context=context)
        var_ids = []
        for product in product_ids:
            var_ids += [p.id for p in product.product_variant_ids]
        variant_available= self.pool['product.product']._product_available(cr, uid, var_ids, context=context)

        for product in product_ids:
            qty_available = 0
            virtual_available = 0
            incoming_qty = 0
            outgoing_qty = 0
            for p in product.product_variant_ids:
                qty_available += variant_available[p.id]["qty_available"]
                virtual_available += variant_available[p.id]["virtual_available"]
                incoming_qty += variant_available[p.id]["incoming_qty"]
                outgoing_qty += variant_available[p.id]["outgoing_qty"]
            prod_available[product.id] = {
                "qty_available": qty_available,
                "virtual_available": virtual_available,
                "incoming_qty": incoming_qty,
                "outgoing_qty": outgoing_qty,
            }
        return prod_available

    def _search_product_quantity(self, cr, uid, obj, name, domain, context):
        prod = self.pool.get("product.product")
        product_variant_ids = prod.search(cr, uid, domain, context=context)
        return [('product_variant_ids', 'in', product_variant_ids)]

    def _product_available_text(self, cr, uid, ids, field_names=None, arg=False, context=None):
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = str(product.qty_available) +  _(" On Hand")
        return res

    def _compute_nbr_reordering_rules(self, cr, uid, ids, field_names=None, arg=None, context=None):
        res = {id : {'nbr_reordering_rules': 0, 'reordering_min_qty': 0, 'reordering_max_qty': 0} for id in ids}
        product_data = self.pool['stock.warehouse.orderpoint'].read_group(cr, uid, [('product_id.product_tmpl_id', 'in', ids)], ['product_id', 'product_min_qty', 'product_max_qty'], ['product_id'], context=context)
        for data in product_data:
            product_tmpl_id = data['__domain'][1][2][0]
            res[product_tmpl_id]['nbr_reordering_rules'] = res[product_tmpl_id].get('nbr_reordering_rules', 0) + int(data['product_id_count'])
            res[product_tmpl_id]['reordering_min_qty'] = data['product_min_qty']
            res[product_tmpl_id]['reordering_max_qty'] = data['product_max_qty']
        return res

    def _get_product_template_type(self, cr, uid, context=None):
        res = super(product_template, self)._get_product_template_type(cr, uid, context=context)
        if 'product' not in [item[0] for item in res]:
            res.append(('product', _('Stockable Product')))
        return res

    _columns = {
        'property_stock_procurement': fields.property(
            type='many2one',
            relation='stock.location',
            string="Procurement Location",
            domain=[('usage','like','procurement')],
            help="This stock location will be used, instead of the default one, as the source location for stock moves generated by procurements."),
        'property_stock_production': fields.property(
            type='many2one',
            relation='stock.location',
            string="Production Location",
            domain=[('usage','like','production')],
            help="This stock location will be used, instead of the default one, as the source location for stock moves generated by manufacturing orders."),
        'property_stock_inventory': fields.property(
            type='many2one',
            relation='stock.location',
            string="Inventory Location",
            domain=[('usage','like','inventory')],
            help="This stock location will be used, instead of the default one, as the source location for stock moves generated when you do an inventory."),
        'sale_delay': fields.float('Customer Lead Time', help="The average delay in days between the confirmation of the customer order and the delivery of the finished products. It's the time you promise to your customers."),
        'tracking': fields.selection(selection=[('serial', 'By Unique Serial Number'), ('lot', 'By Lots'), ('none', 'No Tracking')], string="Tracking", required=True),
        'description_picking': fields.text('Description on Picking', translate=True),
        # sum of product variant qty
        # 'reception_count': fields.function(_product_available, multi='qty_available',
        #     fnct_search=_search_product_quantity, type='float', string='Quantity On Hand'),
        # 'delivery_count': fields.function(_product_available, multi='qty_available',
        #     fnct_search=_search_product_quantity, type='float', string='Quantity On Hand'),
        'qty_available': fields.function(_product_available, multi='qty_available', digits_compute=dp.get_precision('Product Unit of Measure'),
            fnct_search=_search_product_quantity, type='float', string='Quantity On Hand'),
        'virtual_available': fields.function(_product_available, multi='qty_available', digits_compute=dp.get_precision('Product Unit of Measure'),
            fnct_search=_search_product_quantity, type='float', string='Forecasted Quantity'),
        'incoming_qty': fields.function(_product_available, multi='qty_available', digits_compute=dp.get_precision('Product Unit of Measure'),
            fnct_search=_search_product_quantity, type='float', string='Incoming'),
        'outgoing_qty': fields.function(_product_available, multi='qty_available', digits_compute=dp.get_precision('Product Unit of Measure'),
            fnct_search=_search_product_quantity, type='float', string='Outgoing'),
        'location_id': fields.dummy(string='Location', relation='stock.location', type='many2one'),
        'warehouse_id': fields.dummy(string='Warehouse', relation='stock.warehouse', type='many2one'),
        'route_ids': fields.many2many('stock.location.route', 'stock_route_product', 'product_id', 'route_id', 'Routes', domain=[('product_selectable', '=', True)],
                                    help="Depending on the modules installed, this will allow you to define the route of the product: whether it will be bought, manufactured, MTO/MTS,..."),
        'nbr_reordering_rules': fields.function(_compute_nbr_reordering_rules, string='Reordering Rules', type='integer', multi=True),
        'reordering_min_qty': fields.function(_compute_nbr_reordering_rules, type='float', multi=True),
        'reordering_max_qty': fields.function(_compute_nbr_reordering_rules, type='float', multi=True),
        'route_from_categ_ids': fields.related('categ_id', 'total_route_ids', type="many2many", relation="stock.location.route", string="Category Routes"),
    }

    _defaults = {
        'sale_delay': 7,
        'tracking': 'none',
    }

    def action_view_routes(self, cr, uid, ids, context=None):
        route_obj = self.pool.get("stock.location.route")
        act_obj = self.pool.get('ir.actions.act_window')
        mod_obj = self.pool.get('ir.model.data')
        product_route_ids = set()
        for product in self.browse(cr, uid, ids, context=context):
            product_route_ids |= set([r.id for r in product.route_ids])
            product_route_ids |= set([r.id for r in product.categ_id.total_route_ids])
        route_ids = route_obj.search(cr, uid, ['|', ('id', 'in', list(product_route_ids)), ('warehouse_selectable', '=', True)], context=context)
        result = mod_obj.xmlid_to_res_id(cr, uid, 'stock.action_routes_form', raise_if_not_found=True)
        result = act_obj.read(cr, uid, [result], context=context)[0]
        result['domain'] = "[('id','in',[" + ','.join(map(str, route_ids)) + "])]"
        return result

    def onchange_tracking(self, cr, uid, ids, tracking, context=None):
        if not tracking:
            return {}
        product_product = self.pool['product.product']
        variant_ids = product_product.search(cr, uid, [('product_tmpl_id', 'in', ids)], context=context)
        return product_product.onchange_tracking(cr, uid, variant_ids, tracking, context=context)

    def _get_products(self, cr, uid, ids, context=None):
        products = []
        for prodtmpl in self.browse(cr, uid, ids, context=None):
            products += [x.id for x in prodtmpl.product_variant_ids]
        return products
    
    def _get_act_window_dict(self, cr, uid, name, context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.xmlid_to_res_id(cr, uid, name, raise_if_not_found=True)
        result = act_obj.read(cr, uid, [result], context=context)[0]
        return result

    def action_open_quants(self, cr, uid, ids, context=None):
        products = self._get_products(cr, uid, ids, context=context)
        result = self._get_act_window_dict(cr, uid, 'stock.product_open_quants', context=context)
        result['domain'] = "[('product_id','in',[" + ','.join(map(str, products)) + "])]"
        result['context'] = "{'search_default_locationgroup': 1, 'search_default_internal_loc': 1}"
        return result

    def action_view_orderpoints(self, cr, uid, ids, context=None):
        products = self._get_products(cr, uid, ids, context=context)
        result = self._get_act_window_dict(cr, uid, 'stock.product_open_orderpoint', context=context)
        if len(ids) == 1 and len(products) == 1:
            result['context'] = "{'default_product_id': " + str(products[0]) + ", 'search_default_product_id': " + str(products[0]) + "}"
        else:
            result['domain'] = "[('product_id','in',[" + ','.join(map(str, products)) + "])]"
            result['context'] = "{}"
        return result

    def action_view_stock_moves(self, cr, uid, ids, context=None):
        products = self._get_products(cr, uid, ids, context=context)
        result = self._get_act_window_dict(cr, uid, 'stock.act_product_stock_move_open', context=context)
        if products:
            result['context'] = "{'default_product_id': %d}" % products[0]
        result['domain'] = "[('product_id.product_tmpl_id','in',[" + ','.join(map(str,ids)) + "])]"
        return result

    def write(self, cr, uid, ids, vals, context=None):
        if 'uom_id' in vals:
            new_uom = self.pool.get('product.uom').browse(cr, uid, vals['uom_id'], context=context)
            for product in self.browse(cr, uid, ids, context=context):
                old_uom = product.uom_id
                if old_uom != new_uom:
                    if self.pool.get('stock.move').search(cr, uid, [('product_id', 'in', [x.id for x in product.product_variant_ids]), ('state', '=', 'done')], limit=1, context=context):
                        raise UserError(_("You can not change the unit of measure of a product that has already been used in a done stock move. If you need to change the unit of measure, you may deactivate this product."))
        return super(product_template, self).write(cr, uid, ids, vals, context=context)


class product_removal_strategy(osv.osv):
    _name = 'product.removal'
    _description = 'Removal Strategy'

    _columns = {
        'name': fields.char('Name', required=True),
        'method': fields.char("Method", required=True, help="FIFO, LIFO..."),
    }


class product_putaway_strategy(osv.osv):
    _name = 'product.putaway'
    _description = 'Put Away Strategy'

    def _get_putaway_options(self, cr, uid, context=None):
        return [('fixed', 'Fixed Location')]

    _columns = {
        'name': fields.char('Name', required=True),
        'method': fields.selection(_get_putaway_options, "Method", required=True),
        'fixed_location_ids': fields.one2many('stock.fixed.putaway.strat', 'putaway_id', 'Fixed Locations Per Product Category', help="When the method is fixed, this location will be used to store the products", copy=True),
    }

    _defaults = {
        'method': 'fixed',
    }

    def putaway_apply(self, cr, uid, putaway_strat, product, context=None):
        if putaway_strat.method == 'fixed':
            for strat in putaway_strat.fixed_location_ids:
                categ = product.categ_id
                while categ:
                    if strat.category_id.id == categ.id:
                        return strat.fixed_location_id.id
                    categ = categ.parent_id


class fixed_putaway_strat(osv.osv):
    _name = 'stock.fixed.putaway.strat'
    _order = 'sequence'
    _columns = {
        'putaway_id': fields.many2one('product.putaway', 'Put Away Method', required=True),
        'category_id': fields.many2one('product.category', 'Product Category', required=True),
        'fixed_location_id': fields.many2one('stock.location', 'Location', required=True),
        'sequence': fields.integer('Priority', help="Give to the more specialized category, a higher priority to have them in top of the list."),
    }


class product_category(osv.osv):
    _inherit = 'product.category'

    def calculate_total_routes(self, cr, uid, ids, name, args, context=None):
        res = {}
        for categ in self.browse(cr, uid, ids, context=context):
            categ2 = categ
            routes = [x.id for x in categ.route_ids]
            while categ2.parent_id:
                categ2 = categ2.parent_id
                routes += [x.id for x in categ2.route_ids]
            res[categ.id] = routes
        return res

    _columns = {
        'route_ids': fields.many2many('stock.location.route', 'stock_location_route_categ', 'categ_id', 'route_id', 'Routes', domain=[('product_categ_selectable', '=', True)]),
        'removal_strategy_id': fields.many2one('product.removal', 'Force Removal Strategy', help="Set a specific removal strategy that will be used regardless of the source location for this product category"),
        'total_route_ids': fields.function(calculate_total_routes, relation='stock.location.route', type='many2many', string='Total routes', readonly=True),
    }
