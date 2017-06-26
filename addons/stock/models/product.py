# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round
from datetime import datetime
import operator as py_operator

OPERATORS = {
    '<': py_operator.lt,
    '>': py_operator.gt,
    '<=': py_operator.le,
    '>=': py_operator.ge,
    '=': py_operator.eq,
    '!=': py_operator.ne
}

class Product(models.Model):
    _inherit = "product.product"

    reception_count = fields.Integer('Receipt', compute='_compute_reception_count')
    delivery_count = fields.Integer('Delivery', compute='_compute_delivery_count')
    stock_quant_ids = fields.One2many('stock.quant', 'product_id', help='Technical: used to compute quantities.')
    stock_move_ids = fields.One2many('stock.move', 'product_id', help='Technical: used to compute quantities.')
    qty_available = fields.Float(
        'Quantity On Hand', compute='_compute_quantities', search='_search_qty_available',
        digits=dp.get_precision('Product Unit of Measure'),
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
        'Forecast Quantity', compute='_compute_quantities', search='_search_virtual_available',
        digits=dp.get_precision('Product Unit of Measure'),
        help="Forecast quantity (computed as Quantity On Hand "
             "- Outgoing + Incoming)\n"
             "In a context with a single Stock Location, this includes "
             "goods stored in this location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods stored in the Stock Location of this Warehouse, or any "
             "of its children.\n"
             "Otherwise, this includes goods stored in any Stock Location "
             "with 'internal' type.")
    incoming_qty = fields.Float(
        'Incoming', compute='_compute_quantities', search='_search_incoming_qty',
        digits=dp.get_precision('Product Unit of Measure'),
        help="Quantity of products that are planned to arrive.\n"
             "In a context with a single Stock Location, this includes "
             "goods arriving to this Location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods arriving to the Stock Location of this Warehouse, or "
             "any of its children.\n"
             "Otherwise, this includes goods arriving to any Stock "
             "Location with 'internal' type.")
    outgoing_qty = fields.Float(
        'Outgoing', compute='_compute_quantities', search='_search_outgoing_qty',
        digits=dp.get_precision('Product Unit of Measure'),
        help="Quantity of products that are planned to leave.\n"
             "In a context with a single Stock Location, this includes "
             "goods leaving this Location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods leaving the Stock Location of this Warehouse, or "
             "any of its children.\n"
             "Otherwise, this includes goods leaving any Stock "
             "Location with 'internal' type.")
    # TDE CLEANME: unused except in one test
    orderpoint_ids = fields.One2many('stock.warehouse.orderpoint', 'product_id', 'Minimum Stock Rules')
    nbr_reordering_rules = fields.Integer('Reordering Rules', compute='_compute_nbr_reordering_rules')
    reordering_min_qty = fields.Float(compute='_compute_nbr_reordering_rules')
    reordering_max_qty = fields.Float(compute='_compute_nbr_reordering_rules')

    def _compute_reception_count(self):
        move_data = self.env['stock.move'].read_group([
            ('product_id', 'in', self.ids),
            ('location_id.usage', '!=', 'internal'),
            ('location_dest_id.usage', '=', 'internal'),
            ('state', 'in', ('confirmed', 'assigned', 'pending'))], ['product_id'], ['product_id'])
        res = dict((data['product_id'][0], data['product_id_count']) for data in move_data)
        for move in self:
            move.reception_count = res.get(move.id, 0)

    def _compute_delivery_count(self):
        move_data = self.env['stock.move'].read_group([
            ('product_id', 'in', self.ids),
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '!=', 'internal'),
            ('state', 'in', ('confirmed', 'assigned', 'pending'))], ['product_id'], ['product_id'])
        res = dict((data['product_id'][0], data['product_id_count']) for data in move_data)
        for move in self:
            move.delivery_count = res.get(move.id, 0)

    @api.depends('stock_quant_ids', 'stock_move_ids')
    def _compute_quantities(self):
        res = self._compute_quantities_dict(self._context.get('lot_id'), self._context.get('owner_id'), self._context.get('package_id'), self._context.get('from_date'), self._context.get('to_date'))
        for product in self:
            product.qty_available = res[product.id]['qty_available']
            product.incoming_qty = res[product.id]['incoming_qty']
            product.outgoing_qty = res[product.id]['outgoing_qty']
            product.virtual_available = res[product.id]['virtual_available']

    @api.multi
    def _product_available(self, field_names=None, arg=False):
        """ Compatibility method """
        return self._compute_quantities_dict(self._context.get('lot_id'), self._context.get('owner_id'), self._context.get('package_id'), self._context.get('from_date'), self._context.get('to_date'))

    @api.multi
    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations()
        domain_quant = [('product_id', 'in', self.ids)] + domain_quant_loc
        dates_in_the_past = False
        if to_date and to_date < fields.Datetime.now(): #Only to_date as to_date will correspond to qty_available
            dates_in_the_past = True

        domain_move_in = [('product_id', 'in', self.ids)] + domain_move_in_loc
        domain_move_out = [('product_id', 'in', self.ids)] + domain_move_out_loc
        if lot_id:
            domain_quant += [('lot_id', '=', lot_id)]
        if owner_id:
            domain_quant += [('owner_id', '=', owner_id)]
            domain_move_in += [('restrict_partner_id', '=', owner_id)]
            domain_move_out += [('restrict_partner_id', '=', owner_id)]
        if package_id:
            domain_quant += [('package_id', '=', package_id)]
        if dates_in_the_past:
            domain_move_in_done = list(domain_move_in)
            domain_move_out_done = list(domain_move_out)
        if from_date:
            domain_move_in += [('date', '>=', from_date)]
            domain_move_out += [('date', '>=', from_date)]
        if to_date:
            domain_move_in += [('date', '<=', to_date)]
            domain_move_out += [('date', '<=', to_date)]

        Move = self.env['stock.move']
        Quant = self.env['stock.quant']
        domain_move_in_todo = [('state', 'not in', ('done', 'cancel', 'draft'))] + domain_move_in
        domain_move_out_todo = [('state', 'not in', ('done', 'cancel', 'draft'))] + domain_move_out
        moves_in_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_in_todo, ['product_id', 'product_qty'], ['product_id']))
        moves_out_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_out_todo, ['product_id', 'product_qty'], ['product_id']))
        quants_res = dict((item['product_id'][0], item['qty']) for item in Quant.read_group(domain_quant, ['product_id', 'qty'], ['product_id']))
        if dates_in_the_past:
            # Calculate the moves that were done before now to calculate back in time (as most questions will be recent ones)
            domain_move_in_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_in_done
            domain_move_out_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_out_done
            moves_in_res_past = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_in_done, ['product_id', 'product_qty'], ['product_id']))
            moves_out_res_past = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_out_done, ['product_id', 'product_qty'], ['product_id']))

        res = dict()
        for product in self.with_context(prefetch_fields=False):
            res[product.id] = {}
            if dates_in_the_past:
                qty_available = quants_res.get(product.id, 0.0) - moves_in_res_past.get(product.id, 0.0) + moves_out_res_past.get(product.id, 0.0)
            else:
                qty_available = quants_res.get(product.id, 0.0)
            res[product.id]['qty_available'] = float_round(qty_available, precision_rounding=product.uom_id.rounding)
            res[product.id]['incoming_qty'] = float_round(moves_in_res.get(product.id, 0.0), precision_rounding=product.uom_id.rounding)
            res[product.id]['outgoing_qty'] = float_round(moves_out_res.get(product.id, 0.0), precision_rounding=product.uom_id.rounding)
            res[product.id]['virtual_available'] = float_round(
                qty_available + res[product.id]['incoming_qty'] - res[product.id]['outgoing_qty'],
                precision_rounding=product.uom_id.rounding)

        return res

    def _get_domain_locations(self):
        '''
        Parses the context and returns a list of location_ids based on it.
        It will return all stock locations when no parameters are given
        Possible parameters are shop, warehouse, location, force_company, compute_child
        '''
        # TDE FIXME: clean that brol, context seems overused
        Warehouse = self.env['stock.warehouse']

        location_ids = []
        if self.env.context.get('location', False):
            if isinstance(self.env.context['location'], (int, long)):
                location_ids = [self.env.context['location']]
            elif isinstance(self.env.context['location'], basestring):
                domain = [('complete_name', 'ilike', self.env.context['location'])]
                if self.env.context.get('force_company', False):
                    domain += [('company_id', '=', self.env.context['force_company'])]
                location_ids = self.env['stock.location'].search(domain).ids
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
                    wids = Warehouse.search(domain).ids
                else:
                    wids = self.env.context['warehouse']
            else:
                wids = Warehouse.search([]).ids

            for w in Warehouse.browse(wids):
                location_ids.append(w.view_location_id.id)
        return self._get_domain_locations_new(location_ids, company_id=self.env.context.get('force_company', False), compute_child=self.env.context.get('compute_child', True))

    def _get_domain_locations_new(self, location_ids, company_id=False, compute_child=True):
        operator = compute_child and 'child_of' or 'in'
        domain = company_id and ['&', ('company_id', '=', company_id)] or []
        locations = self.env['stock.location'].browse(location_ids)
        # TDE FIXME: should move the support of child_of + auto_join directly in expression
        # The code has been modified because having one location with parent_left being
        # 0 make the whole domain unusable
        hierarchical_locations = locations.filtered(lambda location: location.parent_left != 0 and operator == "child_of")
        other_locations = locations.filtered(lambda location: location not in hierarchical_locations)  # TDE: set - set ?
        loc_domain = []
        dest_loc_domain = []
        for location in hierarchical_locations:
            loc_domain = loc_domain and ['|'] + loc_domain or loc_domain
            loc_domain += ['&',
                           ('location_id.parent_left', '>=', location.parent_left),
                           ('location_id.parent_left', '<', location.parent_right)]
            dest_loc_domain = dest_loc_domain and ['|'] + dest_loc_domain or dest_loc_domain
            dest_loc_domain += ['&',
                                ('location_dest_id.parent_left', '>=', location.parent_left),
                                ('location_dest_id.parent_left', '<', location.parent_right)]
        if other_locations:
            loc_domain = loc_domain and ['|'] + loc_domain or loc_domain
            loc_domain = loc_domain + [('location_id', operator, [location.id for location in other_locations])]
            dest_loc_domain = dest_loc_domain and ['|'] + dest_loc_domain or dest_loc_domain
            dest_loc_domain = dest_loc_domain + [('location_dest_id', operator, [location.id for location in other_locations])]
        return (
            domain + loc_domain,
            domain + dest_loc_domain + ['!'] + loc_domain if loc_domain else domain + dest_loc_domain,
            domain + loc_domain + ['!'] + dest_loc_domain if dest_loc_domain else domain + loc_domain
        )

    def _search_virtual_available(self, operator, value):
        # TDE FIXME: should probably clean the search methods
        return self._search_product_quantity(operator, value, 'virtual_available')

    def _search_incoming_qty(self, operator, value):
        # TDE FIXME: should probably clean the search methods
        return self._search_product_quantity(operator, value, 'incoming_qty')

    def _search_outgoing_qty(self, operator, value):
        # TDE FIXME: should probably clean the search methods
        return self._search_product_quantity(operator, value, 'outgoing_qty')

    def _search_product_quantity(self, operator, value, field):
        # TDE FIXME: should probably clean the search methods
        # to prevent sql injections
        if field not in ('qty_available', 'virtual_available', 'incoming_qty', 'outgoing_qty'):
            raise UserError(_('Invalid domain left operand %s') % field)
        if operator not in ('<', '>', '=', '!=', '<=', '>='):
            raise UserError(_('Invalid domain operator %s') % operator)
        if not isinstance(value, (float, int)):
            raise UserError(_('Invalid domain right operand %s') % value)

        # TODO: Still optimization possible when searching virtual quantities
        ids = []
        for product in self.search([]):
            if OPERATORS[operator](product[field], value):
                ids.append(product.id)
        return [('id', 'in', ids)]

    def _search_qty_available(self, operator, value):
        # TDE FIXME: should probably clean the search methods
        if value == 0.0 and operator in ('=', '>=', '<='):
            return self._search_product_quantity(operator, value, 'qty_available')
        product_ids = self._search_qty_available_new(operator, value, self._context.get('lot_id'), self._context.get('owner_id'), self._context.get('package_id'))
        return [('id', 'in', product_ids)]

    def _search_qty_available_new(self, operator, value, lot_id=False, owner_id=False, package_id=False):
        # TDE FIXME: should probably clean the search methods
        product_ids = set()
        domain_quant = self._get_domain_locations()[0]
        if lot_id:
            domain_quant.append(('lot_id', '=', lot_id))
        if owner_id:
            domain_quant.append(('owner_id', '=', owner_id))
        if package_id:
            domain_quant.append(('package_id', '=', package_id))
        quants_groupby = self.env['stock.quant'].read_group(domain_quant, ['product_id', 'qty'], ['product_id'])
        for quant in quants_groupby:
            if OPERATORS[operator](quant['qty'], value):
                product_ids.add(quant['product_id'][0])
        return list(product_ids)

    def _compute_nbr_reordering_rules(self):
        read_group_res = self.env['stock.warehouse.orderpoint'].read_group(
            [('product_id', 'in', self.ids)],
            ['product_id', 'product_min_qty', 'product_max_qty'],
            ['product_id'])
        res = {i: {} for i in self.ids}
        for data in read_group_res:
            res[data['product_id'][0]]['nbr_reordering_rules'] = int(data['product_id_count'])
            res[data['product_id'][0]]['reordering_min_qty'] = data['product_min_qty']
            res[data['product_id'][0]]['reordering_max_qty'] = data['product_max_qty']
        for product in self:
            product.nbr_reordering_rules = res[product.id].get('nbr_reordering_rules', 0)
            product.reordering_min_qty = res[product.id].get('reordering_min_qty', 0)
            product.reordering_max_qty = res[product.id].get('reordering_max_qty', 0)

    @api.onchange('tracking')
    def onchange_tracking(self):
        products = self.filtered(lambda self: self.tracking and self.tracking != 'none')
        if products:
            unassigned_quants = self.env['stock.quant'].search_count([('product_id', 'in', products.ids), ('lot_id', '=', False), ('location_id.usage','=', 'internal')])
            if unassigned_quants:
                return {
                    'warning': {
                        'title': _('Warning!'),
                        'message': _("You have products in stock that have no lot number.  You can assign serial numbers by doing an inventory.  ")}}

    @api.model
    def view_header_get(self, view_id, view_type):
        res = super(Product, self).view_header_get(view_id, view_type)
        if not res and self._context.get('active_id') and self._context.get('active_model') == 'stock.location':
            res = '%s%s' % (_('Products: '), self.env['stock.location'].browse(self._context['active_id']).name)
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(Product, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self._context.get('location') and isinstance(self._context['location'], (int, long)):
            location = self.env['stock.location'].browse(self._context['location'])
            fields = res.get('fields')
            if fields:
                if location.usage == 'supplier':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Receipts')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Received Qty')
                elif location.usage == 'internal':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Forecasted Quantity')
                elif location.usage == 'customer':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Deliveries')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Delivered Qty')
                elif location.usage == 'inventory':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future P&L')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('P&L Qty')
                elif location.usage == 'procurement':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Qty')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Unplanned Qty')
                elif location.usage == 'production':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Productions')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Produced Qty')
        return res

    @api.multi
    def action_view_routes(self):
        return self.mapped('product_tmpl_id').action_view_routes()


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    type = fields.Selection(selection_add=[('product', 'Stockable Product')])
    property_stock_procurement = fields.Many2one(
        'stock.location', "Procurement Location",
        company_dependent=True, domain=[('usage', 'like', 'procurement')],
        help="This stock location will be used, instead of the default one, as the source location for stock moves generated by procurements.")
    property_stock_production = fields.Many2one(
        'stock.location', "Production Location",
        company_dependent=True, domain=[('usage', 'like', 'production')],
        help="This stock location will be used, instead of the default one, as the source location for stock moves generated by manufacturing orders.")
    property_stock_inventory = fields.Many2one(
        'stock.location', "Inventory Location",
        company_dependent=True, domain=[('usage', 'like', 'inventory')],
        help="This stock location will be used, instead of the default one, as the source location for stock moves generated when you do an inventory.")
    sale_delay = fields.Float(
        'Customer Lead Time', default=0,
        help="The average delay in days between the confirmation of the customer order and the delivery of the finished products. It's the time you promise to your customers.")
    tracking = fields.Selection([
        ('serial', 'By Unique Serial Number'),
        ('lot', 'By Lots'),
        ('none', 'No Tracking')], string="Tracking", default='none', required=True)
    description_picking = fields.Text('Description on Picking', translate=True)
    qty_available = fields.Float(
        'Quantity On Hand', compute='_compute_quantities', search='_search_qty_available',
        digits=dp.get_precision('Product Unit of Measure'))
    virtual_available = fields.Float(
        'Forecasted Quantity', compute='_compute_quantities', search='_search_virtual_available',
        digits=dp.get_precision('Product Unit of Measure'))
    incoming_qty = fields.Float(
        'Incoming', compute='_compute_quantities', search='_search_incoming_qty',
        digits=dp.get_precision('Product Unit of Measure'))
    outgoing_qty = fields.Float(
        'Outgoing', compute='_compute_quantities', search='_search_outgoing_qty',
        digits=dp.get_precision('Product Unit of Measure'))
    location_id = fields.Many2one('stock.location', 'Location')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    route_ids = fields.Many2many(
        'stock.location.route', 'stock_route_product', 'product_id', 'route_id', 'Routes',
        domain=[('product_selectable', '=', True)],
        help="Depending on the modules installed, this will allow you to define the route of the product: whether it will be bought, manufactured, MTO/MTS,...")
    nbr_reordering_rules = fields.Integer('Reordering Rules', compute='_compute_nbr_reordering_rules')
    # TDE FIXME: really used ?
    reordering_min_qty = fields.Float(compute='_compute_nbr_reordering_rules')
    reordering_max_qty = fields.Float(compute='_compute_nbr_reordering_rules')
    # TDE FIXME: seems only visible in a view - remove me ?
    route_from_categ_ids = fields.Many2many(
        relation="stock.location.route", string="Category Routes",
        related='categ_id.total_route_ids')

    def _compute_quantities(self):
        res = self._compute_quantities_dict()
        for template in self:
            template.qty_available = res[template.id]['qty_available']
            template.virtual_available = res[template.id]['virtual_available']
            template.incoming_qty = res[template.id]['incoming_qty']
            template.outgoing_qty = res[template.id]['outgoing_qty']

    def _product_available(self, name, arg):
        return self._compute_quantities_dict()

    def _compute_quantities_dict(self):
        # TDE FIXME: why not using directly the function fields ?
        variants_available = self.mapped('product_variant_ids')._product_available()
        prod_available = {}
        for template in self:
            qty_available = 0
            virtual_available = 0
            incoming_qty = 0
            outgoing_qty = 0
            for p in template.product_variant_ids:
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

    def _search_qty_available(self, operator, value):
        domain = [('qty_available', operator, value)]
        product_variant_ids = self.env['product.product'].search(domain)
        return [('product_variant_ids', 'in', product_variant_ids.ids)]

    def _search_virtual_available(self, operator, value):
        domain = [('virtual_available', operator, value)]
        product_variant_ids = self.env['product.product'].search(domain)
        return [('product_variant_ids', 'in', product_variant_ids.ids)]

    def _search_incoming_qty(self, operator, value):
        domain = [('incoming_qty', operator, value)]
        product_variant_ids = self.env['product.product'].search(domain)
        return [('product_variant_ids', 'in', product_variant_ids.ids)]

    def _search_outgoing_qty(self, operator, value):
        domain = [('outgoing_qty', operator, value)]
        product_variant_ids = self.env['product.product'].search(domain)
        return [('product_variant_ids', 'in', product_variant_ids.ids)]

    def _compute_nbr_reordering_rules(self):
        res = {k: {'nbr_reordering_rules': 0, 'reordering_min_qty': 0, 'reordering_max_qty': 0} for k in self.ids}
        product_data = self.env['stock.warehouse.orderpoint'].read_group([('product_id.product_tmpl_id', 'in', self.ids)], ['product_id', 'product_min_qty', 'product_max_qty'], ['product_id'])
        for data in product_data:
            product = self.env['product.product'].browse([data['product_id'][0]])
            product_tmpl_id = product.product_tmpl_id.id
            res[product_tmpl_id]['nbr_reordering_rules'] += int(data['product_id_count'])
            res[product_tmpl_id]['reordering_min_qty'] = data['product_min_qty']
            res[product_tmpl_id]['reordering_max_qty'] = data['product_max_qty']
        for template in self:
            template.nbr_reordering_rules = res[template.id]['nbr_reordering_rules']
            template.reordering_min_qty = res[template.id]['reordering_min_qty']
            template.reordering_max_qty = res[template.id]['reordering_max_qty']

    @api.onchange('tracking')
    def onchange_tracking(self):
        return self.mapped('product_variant_ids').onchange_tracking()

    @api.multi
    def write(self, vals):
        if 'uom_id' in vals:
            new_uom = self.env['product.uom'].browse(vals['uom_id'])
            updated = self.filtered(lambda template: template.uom_id != new_uom)
            done_moves = self.env['stock.move'].search([('product_id', 'in', updated.mapped('product_variant_ids').ids)], limit=1)
            if done_moves:
                raise UserError(_("You can not change the unit of measure of a product that has already been used in a done stock move. If you need to change the unit of measure, you may deactivate this product."))
        return super(ProductTemplate, self).write(vals)

    @api.multi
    def action_view_routes(self):
        routes = self.mapped('route_ids') | self.mapped('categ_id').mapped('total_route_ids') | self.env['stock.location.route'].search([('warehouse_selectable', '=', True)])
        action = self.env.ref('stock.action_routes_form').read()[0]
        action['domain'] = [('id', 'in', routes.ids)]
        return action

    @api.multi
    def action_open_quants(self):
        products = self.mapped('product_variant_ids')
        action = self.env.ref('stock.product_open_quants').read()[0]
        action['domain'] = [('product_id', 'in', products.ids)]
        action['context'] = {'search_default_locationgroup': 1, 'search_default_internal_loc': 1}
        return action

    @api.multi
    def action_view_orderpoints(self):
        products = self.mapped('product_variant_ids')
        action = self.env.ref('stock.product_open_orderpoint').read()[0]
        if products and len(products) == 1:
            action['context'] = {'default_product_id': products.ids[0], 'search_default_product_id': products.ids[0]}
        else:
            action['domain'] = [('product_id', 'in', products.ids)]
            action['context'] = {}
        return action

    @api.multi
    def action_view_stock_moves(self):
        products = self.mapped('product_variant_ids')
        action = self.env.ref('stock.act_product_stock_move_open').read()[0]
        if self:
            action['context'] = {'default_product_id': products.ids[0]}
        action['domain'] = [('product_id.product_tmpl_id', 'in', self.ids)]
        return action


class ProductCategory(models.Model):
    _inherit = 'product.category'

    route_ids = fields.Many2many(
        'stock.location.route', 'stock_location_route_categ', 'categ_id', 'route_id', 'Routes',
        domain=[('product_categ_selectable', '=', True)])
    removal_strategy_id = fields.Many2one(
        'product.removal', 'Force Removal Strategy',
        help="Set a specific removal strategy that will be used regardless of the source location for this product category")
    total_route_ids = fields.Many2many(
        'stock.location.route', string='Total routes', compute='_compute_total_route_ids',
        readonly=True)

    @api.one
    def _compute_total_route_ids(self):
        category = self
        routes = self.route_ids
        while category.parent_id:
            category = category.parent_id
            routes |= category.route_ids
        self.total_route_ids = routes
