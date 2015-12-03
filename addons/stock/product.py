# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval as eval
import openerp.addons.decimal_precision as dp
from openerp.tools.float_utils import float_round
from openerp.exceptions import UserError
from openerp import api, fields, models

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

    @api.multi
    def _compute_nbr_reordering_rules(self):
        self.nbr_reordering_rules = self.reordering_min_qty = self.reordering_max_qty = 0
        product_data = self.env['stock.warehouse.orderpoint'].read_group([('product_id', 'in', self.ids)], ['product_id', 'product_min_qty', 'product_max_qty'], ['product_id'])
        for data in product_data:
            self.nbr_reordering_rules = int(data['product_id_count'])
            self.reordering_min_qty = data['product_min_qty']
            self.reordering_max_qty = data['product_max_qty']

    reception_count = fields.Integer(compute="_stock_move_count", string="Receipt")
    delivery_count = fields.Integer(compute="_stock_move_count", string="Delivery")

    orderpoint_ids = fields.One2many('stock.warehouse.orderpoint', 'product_id', 'Minimum Stock Rules')
    nbr_reordering_rules = fields.Integer(compute="_compute_nbr_reordering_rules", string='Reordering Rules')
    reordering_min_qty = fields.Float(compute="_compute_nbr_reordering_rules")
    reordering_max_qty = fields.Float(compute="_compute_nbr_reordering_rules")

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
