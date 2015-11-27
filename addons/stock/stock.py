# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from dateutil import relativedelta
import json
import time
import sets

from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import fields, models, api
from openerp import SUPERUSER_ID
import openerp.addons.decimal_precision as dp
from openerp.addons.procurement import procurement
import logging
from openerp.exceptions import UserError


_logger = logging.getLogger(__name__)
#----------------------------------------------------------
# Incoterms
#----------------------------------------------------------
class StockIncoterms(models.Model):
    _name = "stock.incoterms"
    _description = "Incoterms"

    name = fields.Char(required=True, help="Incoterms are series of sales terms. They are used to divide transaction costs and responsibilities between buyer and seller and reflect state-of-the-art transportation practices.")
    code = fields.Char(size=3, required=True, help="Incoterm Standard Code")
    active = fields.Boolean(help="By unchecking the active field, you may hide an INCOTERM you will not use.", default=True)

#----------------------------------------------------------
# Stock Location
#----------------------------------------------------------

class StockLocation(models.Model):
    _name = "stock.location"
    _description = "Inventory Locations"
    _parent_name = "location_id"
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left'
    _rec_name = 'complete_name'

    @api.model
    def _location_owner(self, location):
        ''' Return the company owning the location if any '''
        return location and (location.usage == 'internal') and location.company_id or False

    @api.multi
    def _complete_name(self):
        """ Forms complete name of location from parent location to child location.
        @return: Dictionary of values
        """
        for m in self:
            if m.location_id:
                m.complete_name = m.location_id.name + ' / ' + m.name
            m.complete_name = m.name

    @api.multi
    @api.depends('name', 'location_id', 'active')
    def _get_sublocations(self):
        """ return all sublocations of the given stock locations (included) """
        self.with_context({'active_test': False})
        return self.search([('id', 'child_of', self.ids)])

    # def _name_get(self):
    #     name = self.name
    #     if self.location_id and self.usage != 'view':
    #         name = self.location_id.name + '/' + self.name
    #     return name

    # @api.multi
    # def name_get(self):
    #     for location in self:
    #         location.name = location._name_get()

    name = fields.Char('Location Name', required=True, translate=True)
    active = fields.Boolean('Active', help="By unchecking the active field, you may hide a location without deleting it.", default=True)
    usage = fields.Selection([
                    ('supplier', 'Vendor Location'),
                    ('view', 'View'),
                    ('internal', 'Internal Location'),
                    ('customer', 'Customer Location'),
                    ('inventory', 'Inventory Loss'),
                    ('procurement', 'Procurement'),
                    ('production', 'Production'),
                    ('transit', 'Transit Location')],
            'Location Type', required=True,
            help="""* Vendor Location: Virtual location representing the source location for products coming from your vendors
                   \n* View: Virtual location used to create a hierarchical structures for your warehouse, aggregating its child locations ; can't directly contain products
                   \n* Internal Location: Physical locations inside your own warehouses,
                   \n* Customer Location: Virtual location representing the destination location for products sent to your customers
                   \n* Inventory Loss: Virtual location serving as counterpart for inventory operations used to correct stock levels (Physical inventories)
                   \n* Procurement: Virtual location serving as temporary counterpart for procurement operations when the source (vendor or production) is not known yet. This location should be empty when the procurement scheduler has finished running.
                   \n* Production: Virtual counterpart location for production operations: this location consumes the raw material and produces finished products
                   \n* Transit Location: Counterpart location that should be used in inter-companies or inter-warehouses operations
                  """, select=True, default='internal')
    complete_name = fields.Char(compute="_complete_name", string="Full Location Name")
    location_id = fields.Many2one('stock.location', 'Parent Location', select=True, ondelete='cascade')
    child_ids = fields.One2many('stock.location', 'location_id', 'Contains')

    partner_id = fields.Many2one('res.partner', 'Owner', help="Owner of the location if not internal")

    comment = fields.Text('Additional Information')
    posx = fields.Integer('Corridor (X)', help="Optional localization details, for information purpose only", default=0)
    posy = fields.Integer('Shelves (Y)', help="Optional localization details, for information purpose only", default=0)
    posz = fields.Integer('Height (Z)', help="Optional localization details, for information purpose only", default=0)

    parent_left = fields.Integer('Left Parent', select=1)
    parent_right = fields.Integer('Right Parent', select=1)

    company_id = fields.Many2one('res.company', 'Company', select=1, help='Let this field empty if this location is shared between companies', default=lambda self: self.env.user.company_id)
    scrap_location = fields.Boolean('Is a Scrap Location?', help='Check this box to allow using this location to put scrapped/damaged goods.', default=False)
    return_location = fields.Boolean('Is a Return Location?', help='Check this box to allow using this location as a return location.')
    removal_strategy_id = fields.Many2one('product.removal', 'Removal Strategy', help="Defines the default method used for suggesting the exact location (shelf) where to take the products from, which lot etc. for this location. This method can be enforced at the product category level, and a fallback is made on the parent locations if none is set here.")
    putaway_strategy_id = fields.Many2one('product.putaway', 'Put Away Strategy', help="Defines the default method used for suggesting the exact location (shelf) where to store the products. This method can be enforced at the product category level, and a fallback is made on the parent locations if none is set here.")
    barcode = fields.Char('Barcode', copy=False, oldname='loc_barcode')

    _sql_constraints = [('barcode_company_uniq', 'unique (barcode,company_id)', 'The barcode for a location must be unique per company !')]

    @api.model
    def create(self, default):
        if not default.get('barcode'):
            default.update({'barcode': default.get('complete_name')})
        return super(StockLocation, self).create(default)

    @api.model
    def get_putaway_strategy(self, location, product):
        ''' Returns the location where the product has to be put, if any compliant putaway strategy is found. Otherwise returns None.'''
        putaway_obj = self.env['product.putaway']
        while location:
            if location.putaway_strategy_id:
                res = putaway_obj.putaway_apply(location.putaway_strategy_id, product)
                if res:
                    return res
            location = location.location_id

    @api.model
    def _default_removal_strategy(self):
        return 'fifo'

    @api.model
    def get_removal_strategy(self, qty, move, ops=False):
        ''' Returns the removal strategy to consider for the given move/ops
            :rtype: char
        '''
        product = move.product_id
        location = move.location_id
        if product.categ_id.removal_strategy_id:
            return product.categ_id.removal_strategy_id.method
        while location:
            if location.removal_strategy_id:
                return location.removal_strategy_id.method
            location = location.location_id
        return self._default_removal_strategy()

    @api.model
    def get_warehouse(self, location):
        """
            Returns warehouse id of warehouse that contains location
            :param location: browse record (stock.location)
        """
        whs = self.env["stock.warehouse"].search([('view_location_id.parent_left', '<=', location.parent_left), ('view_location_id.parent_right', '>=', location.parent_left)])
        return whs and whs.ids[0] or False

#----------------------------------------------------------
# Routes
#----------------------------------------------------------
class StockLocationRoute(models.Model):
    _name = 'stock.location.route'
    _description = "Inventory Routes"
    _order = 'sequence'

    name = fields.Char('Route Name', required=True, translate=True)
    sequence = fields.Integer(default=lambda self: 0)
    pull_ids = fields.One2many('procurement.rule', 'route_id', 'Procurement Rules', copy=True)
    active = fields.Boolean(help="If the active field is set to False, it will allow you to hide the route without removing it.", default=True)
    push_ids = fields.One2many('stock.location.path', 'route_id', 'Push Rules', copy=True)
    product_selectable = fields.Boolean('Applicable on Product', help="When checked, the route will be selectable in the Inventory tab of the Product form.  It will take priority over the Warehouse route. ", default=True)
    product_categ_selectable = fields.Boolean('Applicable on Product Category', help="When checked, the route will be selectable on the Product Category.  It will take priority over the Warehouse route. ")
    warehouse_selectable = fields.Boolean('Applicable on Warehouse', help="When a warehouse is selected for this route, this route should be seen as the default route when products pass through this warehouse.  This behaviour can be overridden by the routes on the Product/Product Categories or by the Preferred Routes on the Procurement")
    supplied_wh_id = fields.Many2one('stock.warehouse', 'Supplied Warehouse')
    supplier_wh_id = fields.Many2one('stock.warehouse', 'Supplying Warehouse')
    company_id = fields.Many2one('res.company', 'Company', select=1, help='Leave this field empty if this route is shared between all companies', default=lambda self: self.env.user.company_id)
    product_ids = fields.Many2many('product.template', 'stock_route_product', 'route_id', 'product_id', 'Products')
    categ_ids = fields.Many2many('product.category', 'stock_location_route_categ', 'route_id', 'categ_id', 'Product Categories')
    warehouse_ids = fields.Many2many('stock.warehouse', 'stock_route_warehouse', 'route_id', 'warehouse_id', 'Warehouses')

    @api.multi
    def write(self, vals):
        '''when a route is deactivated, deactivate also its pull and push rules'''
        res = super(StockLocationRoute, self).write(vals)
        if 'active' in vals:
            push_ids = []
            pull_ids = []
            for route in self:
                if route.push_ids:
                    push_ids.append(route.push_ids(lambda route: route.active != vals['active']))
                    # push_ids += [r for r in route.push_ids if r.active != vals['active']]
                if route.pull_ids:
                    pull_ids.append(route.pull_ids(lambda route: route.active != vals['active']))
                    # pull_ids += [r for r in route.pull_ids if r.active != vals['active']]
            if push_ids:
                push_ids[0].write({'active': vals['active']})
            if pull_ids:
                pull_ids[0].write({'active': vals['active']})
        return res

    @api.multi
    def view_product_ids(self):
        return {
            'name': _('Products'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'product.template',
            'type': 'ir.actions.act_window',
            'domain': [('route_ids', 'in', self.ids[0])],
        }

    @api.multi
    def view_categ_ids(self):
        return {
            'name': _('Product Categories'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'product.category',
            'type': 'ir.actions.act_window',
            'domain': [('route_ids', 'in', self.ids[0])],
        }


#----------------------------------------------------------
# Quants
#----------------------------------------------------------


class StockQuant(models.Model):
    """
    Quants are the smallest unit of stock physical instances
    """
    _name = "stock.quant"
    _description = "Quants"

    @api.multi
    def _get_quant_name(self):
        """ Forms complete name of location from parent location to child location.
        @return: Dictionary of values
        """
        for q in self:
            q.name = q.product_id.code or ''
            if q.lot_id:
                q.name = q.lot_id.name
            q.name += ': ' + str(q.qty) + q.product_id.uom_id.name

    @api.multi
    def _calc_inventory_value(self):
        uid_company_id = self.env.user.company_id.id
        for quant in self:
            # self._context.pop('force_company')
            if quant.company_id.id != uid_company_id:
                #if the company of the quant is different than the current user company, force the company in the context
                #then re-do a browse to read the property fields for the good company.
                self._context['force_company'] = quant.company_id.id
            quant.inventory_value = quant._get_inventory_value()

    @api.multi
    def _get_inventory_value(self):
        return self.product_id.standard_price * self.qty

    name = fields.Char(compute="_get_quant_name", string='Identifier')
    product_id = fields.Many2one('product.product', 'Product', required=True, ondelete="restrict", readonly=True, select=True)
    location_id = fields.Many2one('stock.location', 'Location', required=True, ondelete="restrict", readonly=True, select=True, auto_join=True)
    qty = fields.Float('Quantity', required=True, help="Quantity of products in this quant, in the default unit of measure of the product", readonly=True, select=True)
    product_uom_id = fields.Many2one(related='product_id.uom_id', relation="product.uom", string='Unit of Measure', readonly=True)
    package_id = fields.Many2one('stock.quant.package', string='Package', help="The package containing this quant", readonly=True, select=True)
    packaging_type_id = fields.Many2one(related='package_id.packaging_id', relation='product.packaging', string='Type of packaging', readonly=True, store=True)
    reservation_id = fields.Many2one('stock.move', 'Reserved for Move', help="The move the quant is reserved for", readonly=True, select=True)
    lot_id = fields.Many2one('stock.production.lot', 'Lot', readonly=True, select=True, ondelete="restrict")
    cost = fields.Float('Unit Cost')
    owner_id = fields.Many2one('res.partner', 'Owner', help="This is the owner of the quant", readonly=True, select=True)
    create_date = fields.Datetime('Creation Date', readonly=True)
    in_date = fields.Datetime('Incoming Date', readonly=True, select=True)
    history_ids = fields.Many2many('stock.move', 'stock_quant_move_rel', 'quant_id', 'move_id', 'Moves', help='Moves that operate(d) on this quant', copy=False)
    company_id = fields.Many2one('res.company', 'Company', help="The company to which the quants belong", required=True, readonly=True, select=True, default=lambda self: self.env.user.company_id)
    inventory_value = fields.Float(compute="_calc_inventory_value", string="Inventory Value", readonly=True)
    # Used for negative quants to reconcile after compensated by a new positive one
    propagated_from_id = fields.Many2one('stock.quant', 'Linked Quant', help='The negative quant this is coming from', readonly=True, select=True)
    negative_move_id = fields.Many2one('stock.move', 'Move Negative Quant', help='If this is a negative quant, this will be the move that caused this negative quant.', readonly=True)
    negative_dest_location_id = fields.Many2one(related='negative_move_id.location_dest_id', relation='stock.location', string="Negative Destination Location", readonly=True, help="Technical field used to record the destination location of a move that created a negative quant")

    @api.v7
    def init(self, cr):
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_quant_product_location_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX stock_quant_product_location_index ON stock_quant (product_id, location_id, company_id, qty, in_date, reservation_id)')

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        ''' Overwrite the read_group in order to sum the function field 'inventory_value' in group by'''
        res = super(StockQuant, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        if 'inventory_value' in fields:
            for line in res:
                if '__domain' in line:
                    lines = self.search(line['__domain'])
                    inv_value = 0.0
                    for line2 in lines:
                        inv_value += line2.inventory_value
                    line['inventory_value'] = inv_value
        return res

    @api.multi
    def action_view_quant_history(self):
        '''
        This function returns an action that display the history of the quant, which
        mean all the stock moves that lead to this quant creation with this quant quantity.
        '''
        # mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']

        # result = mod_obj.get_object_reference(cr, uid, 'stock', 'action_move_form2')
        result = self.env.ref('stock.action_move_form2')
        id = result and result.id or False
        result = act_obj.read([id])[0]

        move_ids = []
        for quant in self:
            move_ids += [move.id for move in quant.history_ids]

        result['domain'] = "[('id','in',[" + ','.join(map(str, move_ids)) + "])]"
        return result

    @api.model
    def quants_reserve(self, quants, move, link=False):
        '''This function reserves quants for the given move (and optionally given link). If the total of quantity reserved is enough, the move's state
        is also set to 'assigned'
        '''
        toreserve = []
        reserved_availability = move.reserved_availability
        #split quants if needed
        for quant, qty in quants:
            if qty <= 0.0 or (quant and quant.qty <= 0.0):
                raise UserError(_('You can not reserve a negative quantity or a negative quant.'))
            if not quant:
                continue
            self._quant_split(quant, qty)
            toreserve.append(quant.id)
            reserved_availability += quant.qty
        #reserve quants
        if toreserve:
            toreserve_obj = self.browse(toreserve)
            toreserve_obj.sudo().write({'reservation_id': move.id})
        #check if move'state needs to be set as 'assigned'
        rounding = move.product_id.uom_id.rounding
        if float_compare(reserved_availability, move.product_qty, precision_rounding=rounding) == 0 and move.state in ('confirmed', 'waiting'):
            move.write({'state': 'assigned'})
        elif float_compare(reserved_availability, 0, precision_rounding=rounding) > 0 and not move.partially_available:
            move.write({'partially_available': True})

    @api.model
    def quants_move(self, quants, move, location_to, location_from=False, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False, entire_pack=False):
        """Moves all given stock.quant in the given destination location.  Unreserve from current move.
        """
        quants_reconcile = []
        to_move_quants = []
        self._check_location(location_to)
        for quant, qty in quants:
            if not quant:
                #If quant is None, we will create a quant to move (and potentially a negative counterpart too)
                quant = self._quant_create(qty, move, lot_id=lot_id, owner_id=owner_id, src_package_id=src_package_id, dest_package_id=dest_package_id, force_location_from=location_from, force_location_to=location_to)
            else:
                self._quant_split(quant, qty)
                to_move_quants.append(quant)
            quants_reconcile.append(quant)
        if to_move_quants:
            to_recompute_move_ids = [x.reservation_id.id for x in to_move_quants if x.reservation_id and x.reservation_id.id != move.id]
            self.move_quants_write(to_move_quants, move, location_to, dest_package_id, lot_id=lot_id, entire_pack=entire_pack)
            self.pool['stock.move'].recalculate_move_state(self._cr, self._uid, to_recompute_move_ids, context=self._context)
            # self.env['stock.move'].recalculate_move_state(to_recompute_move_ids)
        if location_to.usage == 'internal':
            # Do manual search for quant to avoid full table scan (order by id)
            self._cr.execute("""
                SELECT 0 FROM stock_quant, stock_location WHERE product_id = %s AND stock_location.id = stock_quant.location_id AND
                ((stock_location.parent_left >= %s AND stock_location.parent_left < %s) OR stock_location.id = %s) AND qty < 0.0 LIMIT 1
            """, (move.product_id.id, location_to.parent_left, location_to.parent_right, location_to.id))
            if self._cr.fetchone():
                for quant in quants_reconcile:
                    self._quant_reconcile_negative(quant, move)

    @api.model
    def move_quants_write(self, quants, move, location_dest_id, dest_package_id, lot_id=False, entire_pack=False):
        if len(quants) > 1:
                quant = [quants[0] + x for x in quants[1:]][0]
        else:
            quant = quants[0]
        vals = {'location_id': location_dest_id.id,
                'history_ids': [(4, move.id)],
                'reservation_id': False}
        if lot_id and any(x.id for x in quants if not x.lot_id.id):
            vals['lot_id'] = lot_id
        if not entire_pack:
            vals.update({'package_id': dest_package_id})
        quant.sudo().write(vals)

    @api.model
    def quants_get_preferred_domain(self, qty, move, ops=False, lot_id=False, domain=None, preferred_domain_list=[]):
        ''' This function tries to find quants for the given domain and move/ops, by trying to first limit
            the choice on the quants that match the first item of preferred_domain_list as well. But if the qty requested is not reached
            it tries to find the remaining quantity by looping on the preferred_domain_list (tries with the second item and so on).
            Make sure the quants aren't found twice => all the domains of preferred_domain_list should be orthogonal
        '''
        domain = domain or [('qty', '>', 0.0)]
        quants = [(None, qty)]
        if ops:
            restrict_lot_id = lot_id
            location = ops.location_id
            domain += [('owner_id', '=', ops.owner_id.id)]
            if ops.package_id and not ops.product_id:
                domain += [('package_id', 'child_of', ops.package_id.id)]
            else:
                domain += [('package_id', '=', ops.package_id.id)]
            domain += [('location_id', '=', ops.location_id.id)]
        else:
            restrict_lot_id = move.restrict_lot_id.id
            location = move.location_id
            domain += [('owner_id', '=', move.restrict_partner_id.id)]
            domain += [('location_id', 'child_of', move.location_id.id)]
        if self._context.get('force_company'):
            domain += [('company_id', '=', self._context['force_company'])]
        else:
            domain += [('company_id', '=', move.company_id.id)]
        removal_strategy = self.env['stock.location'].get_removal_strategy(qty, move, ops=ops)
        product = move.product_id
        domain += [('product_id', '=', move.product_id.id)]

        #don't look for quants in location that are of type production, supplier or inventory.
        if location.usage in ['inventory', 'production', 'supplier']:
            return quants
        res_qty = qty
        if restrict_lot_id:
            if not preferred_domain_list:
                preferred_domain_list = [[('lot_id', '=', restrict_lot_id)], [('lot_id', '=', False)]]
            else:
                lot_list = []
                no_lot_list = []
                for pref_domain in preferred_domain_list:
                    pref_lot_domain = pref_domain + [('lot_id', '=', restrict_lot_id)]
                    pref_no_lot_domain = pref_domain + [('lot_id', '=', False)]
                    lot_list.append(pref_lot_domain)
                    no_lot_list.append(pref_no_lot_domain)
                preferred_domain_list = lot_list + no_lot_list

        if not preferred_domain_list:
            return self.quants_get(qty, move, ops=ops, domain=domain, removal_strategy=removal_strategy)
        for preferred_domain in preferred_domain_list:
            res_qty_cmp = float_compare(res_qty, 0, precision_rounding=product.uom_id.rounding)
            if res_qty_cmp > 0:
                #try to replace the last tuple (None, res_qty) with something that wasn't chosen at first because of the preferred order
                quants.pop()
                tmp_quants = self.quants_get(res_qty, move, ops=ops, domain=domain + preferred_domain,
                                             removal_strategy=removal_strategy)
                for quant in tmp_quants:
                    if quant[0]:
                        res_qty -= quant[1]
                quants += tmp_quants
        return quants

    @api.model
    def quants_get(self, qty, move, ops=False, domain=None, removal_strategy='fifo'):
        """
        Use the removal strategies of product to search for the correct quants
        If you inherit, put the super at the end of your method.
        """
        domain = domain or [('qty', '>', 0.0)]
        return self.apply_removal_strategy(qty, move, ops=ops, domain=domain, removal_strategy=removal_strategy)

    @api.model
    def apply_removal_strategy(self, quantity, move, ops=False, domain=None, removal_strategy='fifo'):
        if removal_strategy == 'fifo':
            order = 'in_date, id'
            return self._quants_get_order(quantity, move, ops=ops, domain=domain, orderby=order)
        elif removal_strategy == 'lifo':
            order = 'in_date desc, id desc'
            return self._quants_get_order(quantity, move, ops=ops, domain=domain, orderby=order)
        raise UserError(_('Removal strategy %s not implemented.' % (removal_strategy,)))

    @api.model
    def _quant_create(self, qty, move, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False,
                      force_location_from=False, force_location_to=False):
        '''Create a quant in the destination location and create a negative quant in the source location if it's an internal location.
        '''
        price_unit = self.env['stock.move'].get_price_unit(move)
        location = force_location_to or move.location_dest_id
        rounding = move.product_id.uom_id.rounding
        vals = {
            'product_id': move.product_id.id,
            'location_id': location.id,
            'qty': float_round(qty, precision_rounding=rounding),
            'cost': price_unit,
            'history_ids': [(4, move.id)],
            'in_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'company_id': move.company_id.id,
            'lot_id': lot_id,
            'owner_id': owner_id,
            'package_id': dest_package_id,
        }
        if move.location_id.usage == 'internal':
            #if we were trying to move something from an internal location and reach here (quant creation),
            #it means that a negative quant has to be created as well.
            negative_vals = vals.copy()
            negative_vals['location_id'] = force_location_from and force_location_from.id or move.location_id.id
            negative_vals['qty'] = float_round(-qty, precision_rounding=rounding)
            negative_vals['cost'] = price_unit
            negative_vals['negative_move_id'] = move.id
            negative_vals['package_id'] = src_package_id
            negative_quant_id = self.sudo().create(negative_vals)
            vals.update({'propagated_from_id': negative_quant_id.id})

        # In case of serial tracking, check if the product does not exist somewhere internally already
        picking_type = move.picking_id and move.picking_id.picking_type_id or False
        if lot_id and move.product_id.tracking == 'serial' and (not picking_type or (picking_type.use_create_lots or picking_type.use_existing_lots)):
            if qty != 1.0:
                raise UserError(_('You should only receive by the piece with the same serial number'))
            other_quants = self.search([('product_id', '=', move.product_id.id), ('lot_id', '=', lot_id),
                                                 ('qty', '>', 0.0), ('location_id.usage', '=', 'internal')])
            if other_quants:
                lot_name = self.env['stock.production.lot'].browse(lot_id).name
                raise UserError(_('The serial number %s is already in stock') % lot_name)

        #create the quant as superuser, because we want to restrict the creation of quant manually: we should always use this method to create quants
        quant_id = self.sudo().create(vals)
        return quant_id

    @api.model
    def _quant_split(self, quant, qty):
        rounding = quant.product_id.uom_id.rounding
        if float_compare(abs(quant.qty), abs(qty), precision_rounding=rounding) <= 0:  # if quant <= qty in abs, take it entirely
            return False
        qty_round = float_round(qty, precision_rounding=rounding)
        new_qty_round = float_round(quant.qty - qty, precision_rounding=rounding)
        # Fetch the history_ids manually as it will not do a join with the stock moves then (=> a lot faster)
        self._cr.execute("""SELECT move_id FROM stock_quant_move_rel WHERE quant_id = %s""", (quant.id,))
        res = self._cr.fetchall()
        new_quant = quant.sudo().copy(default={'qty': new_qty_round, 'history_ids': [(4, x[0]) for x in res]})
        quant.sudo().write({'qty': qty_round})
        return new_quant

    @api.model
    def _get_latest_move(self, quant):
        move = False
        for m in quant.history_ids:
            if not move or m.date > move.date:
                move = m
        return move

    @api.model
    def _quants_merge(self, solved_quant_ids, solving_quant):
        path = []
        for move in solving_quant.history_ids:
            path.append((4, move.id))
        self.browse(solved_quant_ids).sudo().write({'history_ids': path})

    @api.model
    def _search_quants_to_reconcile(self, quant):
        """
            Searches negative quants to reconcile for where the quant to reconcile is put
        """
        dom = [('qty', '<', 0)]
        order = 'in_date'
        dom += [('location_id', 'child_of', quant.location_id.id), ('product_id', '=', quant.product_id.id),
                ('owner_id', '=', quant.owner_id.id)]
        if quant.package_id.id:
            dom += [('package_id', '=', quant.package_id.id)]
        if quant.lot_id:
            dom += ['|', ('lot_id', '=', False), ('lot_id', '=', quant.lot_id.id)]
            order = 'lot_id, in_date'
        # Do not let the quant eat itself, or it will kill its history (e.g. returns / Stock -> Stock)
        dom += [('id', '!=', quant.propagated_from_id.id)]
        quants_search = self.search(dom, order=order)
        product = quant.product_id
        quants = []
        quantity = quant.qty
        for quant in quants_search:
            rounding = product.uom_id.rounding
            if float_compare(quantity, abs(quant.qty), precision_rounding=rounding) >= 0:
                quants += [(quant, abs(quant.qty))]
                quantity -= abs(quant.qty)
            elif float_compare(quantity, 0.0, precision_rounding=rounding) != 0:
                quants += [(quant, quantity)]
                quantity = 0
                break
        return quants

    @api.model
    def _quant_reconcile_negative(self, quant, move):
        """
            When new quant arrive in a location, try to reconcile it with
            negative quants. If it's possible, apply the cost of the new
            quant to the counterpart of the negative quant.
        """
        solving_quant = quant
        quants = self._search_quants_to_reconcile(quant)
        product_uom_rounding = quant.product_id.uom_id.rounding
        for quant_neg, qty in quants:
            if not quant_neg or not solving_quant:
                continue
            to_solve_quant_ids = self.search([('propagated_from_id', '=', quant_neg.id)])
            if not to_solve_quant_ids:
                continue
            solving_qty = qty
            solved_quant_ids = []
            for to_solve_quant in to_solve_quant_ids:
                if float_compare(solving_qty, 0, precision_rounding=product_uom_rounding) <= 0:
                    continue
                solved_quant_ids.append(to_solve_quant.id)
                self._quant_split(to_solve_quant, min(solving_qty, to_solve_quant.qty))
                solving_qty -= min(solving_qty, to_solve_quant.qty)
            remaining_solving_quant = self._quant_split(solving_quant, qty)
            remaining_neg_quant = self._quant_split(quant_neg, -qty)
            #if the reconciliation was not complete, we need to link together the remaining parts
            if remaining_neg_quant:
                remaining_to_solve_quant_ids = self.search([('propagated_from_id', '=', quant_neg.id), ('id', 'not in', solved_quant_ids)])
                if remaining_to_solve_quant_ids:
                    remaining_to_solve_quant_ids.sudo().write({'propagated_from_id': remaining_neg_quant.id})
            solved_quant = self.browse(solved_quant_ids)
            if solving_quant.propagated_from_id and solved_quant_ids:
                solved_quant.sudo().write({'propagated_from_id': solving_quant.propagated_from_id.id})
            #delete the reconciled quants, as it is replaced by the solved quants
            quant_neg.sudo().unlink()
            if solved_quant_ids:
                #price update + accounting entries adjustments
                solved_quant._price_update(solving_quant.cost)
                #merge history (and cost?)
                self._quants_merge(solved_quant_ids, solving_quant)
            solving_quant.sudo().unlink()
            solving_quant = remaining_solving_quant

    @api.multi
    def _price_update(self, newprice):
        self.sudo().write({'cost': newprice})

    @api.model
    def quants_unreserve(self, move):
        if move.reserved_quant_ids:
            #if move has a picking_id, write on that picking that pack_operation might have changed and need to be recomputed
            if move.partially_available:
                move.write({'partially_available': False})
            move.reserved_quant_ids.sudo().write({'reservation_id': False})

    @api.model
    def _quants_get_order(self, quantity, move, ops=False, domain=[], orderby='in_date'):
        ''' Implementation of removal strategies
            If it can not reserve, it will return a tuple (None, qty)
        '''
        product = move.product_id
        res = []
        offset = 0
        while float_compare(quantity, 0, precision_rounding=product.uom_id.rounding) > 0:
            quants = self.search(domain, order=orderby, limit=10, offset=offset)
            if not quants:
                res.append((None, quantity))
                break
            for quant in quants:
                rounding = product.uom_id.rounding
                if float_compare(quantity, abs(quant.qty), precision_rounding=rounding) >= 0:
                    res += [(quant, abs(quant.qty))]
                    quantity -= abs(quant.qty)
                elif float_compare(quantity, 0.0, precision_rounding=rounding) != 0:
                    res += [(quant, quantity)]
                    quantity = 0
                    break
            offset += 10
        return res

    @api.model
    def _check_location(self, location_to):
        if location_to.usage == 'view':
            raise UserError(_('You cannot move to a location of type view %s.') % (location_to.name))
        return True

#----------------------------------------------------------
# Stock Picking
#----------------------------------------------------------
class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ['mail.thread']
    _description = "Transfer"
    _order = "priority desc, date asc, id desc"

    def _set_min_date(self):
        move_ids = self.mapped('move_lines')
        move_ids.write({'date_expected': self.min_date})

    def _set_priority(self):
        move_ids = self.mapped('move_lines')
        move_ids.write({'priority': self.priority})

    @api.multi
    # @api.depends('move_lines.date_expected', 'move_lines.picking_id', 'move_lines.priority')
    def get_min_max_date(self):
        """ Finds minimum and maximum dates for picking.
        @return: Dictionary of values
        """
        if self.ids:
            self.env.cr.execute("""select
                    picking_id,
                    min(date_expected),
                    max(date_expected),
                    max(priority)
                from
                    stock_move
                where
                    picking_id IN %s
                group by
                    picking_id""", (tuple(self.ids),))
            for pick, dt1, dt2, prio in self.env.cr.fetchall():
                picking = self.browse(pick)
                picking.min_date = dt1
                picking.max_date = dt2
                picking.priority = prio
        else:
            self.min_date = False
            self.max_date = False
            self.priority = '1'

    @api.multi
    def _get_pack_operation_exist(self):
        for pick in self:
            pick.pack_operation_exist = False
            if pick.pack_operation_ids:
                pick.pack_operation_exist = True

    @api.multi
    def _get_quant_reserved_exist(self):
        for pick in self:
            pick.quant_reserved_exist = False
            for move in pick.move_lines:
                if move.reserved_quant_ids:
                    pick.quant_reserved_exist = True
                    continue

    def _default_location_destination(self):
        # retrieve picking type from context; if none this returns an empty recordset
        picking_type_id = self.env.context.get('default_picking_type_id')
        picking_type = self.env['stock.picking.type'].browse(picking_type_id)
        return picking_type.default_location_dest_id

    def _default_location_source(self):
        # retrieve picking type from context; if none this returns an empty recordset
        picking_type_id = self.env.context.get('default_picking_type_id')
        picking_type = self.env['stock.picking.type'].browse(picking_type_id)
        return picking_type.default_location_src_id

    name = fields.Char('Reference', select=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, copy=False, default='/')
    origin = fields.Char('Source Document', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, help="Reference of the document", select=True)
    backorder_id = fields.Many2one('stock.picking', 'Back Order of', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, help="If this shipment was split, then this field links to the shipment which contains the already processed part.", select=True, copy=False)
    note = fields.Text('Notes')
    move_type = fields.Selection([('direct', 'Partial'), ('one', 'All at once')], 'Delivery Method', required=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, help="It specifies goods to be deliver partially or all at once", default='direct')

    location_id = fields.Many2one('stock.location', required=True, string="Source Location Zone",
                                      default=_default_location_source, readonly=True, states={'draft': [('readonly', False)]})
    location_dest_id = fields.Many2one('stock.location', required=True, string="Destination Location Zone",
                                           default=_default_location_destination, readonly=True, states={'draft': [('readonly', False)]})
    move_lines = fields.One2many('stock.move', 'picking_id', string="Stock Moves", copy=True)
    move_lines_related = fields.One2many(related='move_lines', comodel_name='stock.move', string="Move Lines")

    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, required=True)
    picking_type_code = fields.Selection(related='picking_type_id.code', selection=[('incoming', 'Suppliers'), ('outgoing', 'Customers'), ('internal', 'Internal')])
    picking_type_entire_packs = fields.Boolean(related='picking_type_id.show_entire_packs')

    priority = fields.Selection(inverse="_set_priority", selection=procurement.PROCUREMENT_PRIORITIES, string='Priority', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, select=1, help="Priority for this picking. Setting manually a value here would set it as priority for all the moves", track_visibility='onchange', required=True, default='1')
    min_date = fields.Datetime(compute="get_min_max_date", inverse="_set_min_date",
                  states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, string='Scheduled Date', select=1, help="Scheduled time for the first part of the shipment to be processed. Setting manually a value here would set it as expected date for all the stock moves.", track_visibility='onchange')
    max_date = fields.Datetime(compute="get_min_max_date", string='Max. Expected Date', select=2, help="Scheduled time for the last part of the shipment to be processed")

    date = fields.Datetime('Creation Date', help="Creation Date, usually the time of the order", select=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, track_visibility='onchange', default=fields.Datetime.now)
    date_done = fields.Datetime('Date of Transfer', help="Completion Date of Transfer", readonly=True, copy=False)
    quant_reserved_exist = fields.Boolean(compute="_get_quant_reserved_exist", string='Has quants already reserved', help='Check the existance of quants linked to this picking')
    partner_id = fields.Many2one('res.partner', 'Partner', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    company_id = fields.Many2one('res.company', 'Company', required=True, select=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, default=lambda self: self.env['res.company']._company_default_get('stock.picking'))
    pack_operation_ids = fields.One2many('stock.pack.operation', 'picking_id', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, string='Related Packing Operations')
    pack_operation_product_ids = fields.One2many('stock.pack.operation', 'picking_id', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, domain=[('product_id', '!=', False)], string='Non pack')
    pack_operation_pack_ids = fields.One2many('stock.pack.operation', 'picking_id', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, domain=[('product_id', '=', False)], string='Pack')
    pack_operation_exist = fields.Boolean(compute="_get_pack_operation_exist", string='Has Pack Operations', help='Check the existance of pack operation on the picking')
    owner_id = fields.Many2one('res.partner', 'Owner', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, help="Default Owner")
        # Used to search on pickings
    product_id = fields.Many2one(related='move_lines.product_id', comodel_name='product.product', string='Product')
    recompute_pack_op = fields.Boolean('Recompute pack operation?', help='True if reserved quants changed, which mean we might need to recompute the package operations', copy=False, default=False)
    launch_pack_operations = fields.Boolean("Launch Pack Operations", copy=False, default=False)

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per company!'),
    ]

    @api.model
    def create(self, vals):
        if ('name' not in vals) or (vals.get('name') in ('/', False)):
            ptype_id = vals.get('picking_type_id', self.env.context.get('default_picking_type_id'))
            sequence_id = self.env['stock.picking.type'].browse(ptype_id).sequence_id
            vals['name'] = sequence_id.next_by_id()
        # As the on_change in one2many list is WIP, we will overwrite the locations on the stock moves here
        # As it is a create the format will be a list of (0, 0, dict)
        if vals.get('move_lines') and vals.get('location_id') and vals.get('location_dest_id'):
            for move in vals['move_lines']:
                if len(move) == 3:
                    move[2]['location_id'] = vals['location_id']
                    move[2]['location_dest_id'] = vals['location_dest_id']
        return super(StockPicking, self).create(vals)

    @api.multi
    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        after_vals = {}
        if vals.get('location_id'):
            after_vals['location_id'] = vals['location_id']
        if vals.get('location_dest_id'):
            after_vals['location_dest_id'] = vals['location_dest_id']
        # Change locations of moves if those of the picking change
        if after_vals:
            moves = self.move_lines.filtered(lambda x: not x.scrapped)
            # moves = None
            # for pick in self:
            #     moves += [x.id for x in pick.move_lines if not x.scrapped]
            if moves:
                moves.write(after_vals)
        return res

    @api.multi
    def do_print_picking(self):
        '''This function prints the picking list'''
        self.with_context(active_ids=self.ids)
        return self.env["report"].get_action(self.ids, 'stock.report_picking')

    @api.multi
    def launch_packops(self):
        self.write({'launch_pack_operations': True})

    @api.multi
    def action_confirm(self):
        todo = []
        todo_force_assign = []
        for picking in self:
            if not picking.move_lines:
                picking.launch_packops()
            if picking.location_id.usage in ('supplier', 'inventory', 'production'):
                todo_force_assign.append(picking.id)
            for r in picking.move_lines:
                if r.state == 'draft':
                    todo.append(r.id)
        if len(todo):
            self.env['stock.move'].browse(todo).action_confirm()

        if todo_force_assign:
            self.browse(todo_force_assign).force_assign()
        return True

    @api.multi
    def action_assign(self):
        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """
        for pick in self:
            if pick.state == 'draft':
                pick.action_confirm()
            #skip the moves that don't need to be checked
            move_ids = pick.move_lines.filtered(lambda x: x.state not in ('draft', 'cancel', 'done'))
            # move_ids = [x.id for x in pick.move_lines if x.state not in ('draft', 'cancel', 'done')]
            if not move_ids.ids:
                raise UserError(_('Nothing to check the availability for.'))
            move_ids.action_assign()
        return True

    @api.multi
    def force_assign(self):
        """ Changes state of picking to available if moves are confirmed or waiting.
        @return: True
        """
        for pick in self:
            move_ids = pick.move_lines.filtered(lambda x: x.state in ['confirmed', 'waiting'])
            move_ids.force_assign()
        return True

    @api.multi
    def action_cancel(self):
        for pick in self:
            pick.move_lines.action_cancel()
        return True

    @api.multi
    def action_done(self):
        """Changes picking state to done by processing the Stock Moves of the Picking

        Normally that happens when the button "Done" is pressed on a Picking view.
        @return: True
        """
        for pick in self:
            todo = []
            for move in pick.move_lines:
                if move.state == 'draft':
                    todo.extend(move.action_confirm())
                elif move.state in ('assigned', 'confirmed'):
                    todo.append(move.id)
            if len(todo):
                self.env['stock.move'].browse(todo).action_done()
        return True

    @api.multi
    def unlink(self):
        #on picking deletion, cancel its move then unlink them too
        for pick in self:
            pick.move_lines.action_cancel()
            pick.move_lines.unlink()
        return super(StockPicking, self).unlink()

    @api.model
    def _create_backorder(self, picking, backorder_moves=[]):
        """ Move all non-done lines into a new backorder picking. If the key 'do_only_split' is given in the context, then move all lines not in context.get('split', []) instead of all non-done lines.
        """
        if not backorder_moves:
            backorder_moves = picking.move_lines
        backorder_move_ids = [x.id for x in backorder_moves if x.state not in ('done', 'cancel')]
        if 'do_only_split' in self.env.context and self.env.context['do_only_split']:
            backorder_move_ids = [x.id for x in backorder_moves if x.id not in self.env.context.get('split', [])]

        if backorder_move_ids:
            backorder = picking.copy({
                'name': '/',
                'move_lines': [],
                'pack_operation_ids': [],
                'backorder_id': picking.id,
            })
            # backorder = self.browse(cr, uid, backorder_id, context=context)
            picking.message_post(body=_("Back order <em>%s</em> <b>created</b>.") % (backorder.name))
            self.env["stock.move"].browse(backorder_move_ids).write({'picking_id': backorder.id})

            if not picking.date_done:
                picking.write({'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
            backorder.action_confirm()
            backorder.action_assign()
            return backorder
        return False

    @api.multi
    def recheck_availability(self):
        self.action_assign()
        self.do_prepare_partial()

    @api.model
    def _get_top_level_packages(self, quants_suggested_locations):
        """This method searches for the higher level packages that can be moved as a single operation, given a list of quants
           to move and their suggested destination, and returns the list of matching packages.
        """
        # Try to find as much as possible top-level packages that can be moved
        quant_obj = self.env["stock.quant"]
        top_lvl_packages = set()
        quants_to_compare = quants_suggested_locations.keys()
        for pack in list(set([x.package_id for x in quants_suggested_locations.keys() if x and x.package_id])):
            loop = True
            test_pack = pack
            good_pack = False
            pack_destination = False
            while loop:
                pack_quants = test_pack.get_content()
                all_in = True
                for quant in quant_obj.browse(pack_quants):
                    # If the quant is not in the quants to compare and not in the common location
                    if not quant in quants_to_compare:
                        all_in = False
                        break
                    else:
                        #if putaway strat apply, the destination location of each quant may be different (and thus the package should not be taken as a single operation)
                        if not pack_destination:
                            pack_destination = quants_suggested_locations[quant]
                        elif pack_destination != quants_suggested_locations[quant]:
                            all_in = False
                            break
                if all_in:
                    good_pack = test_pack
                    if test_pack.parent_id:
                        test_pack = test_pack.parent_id
                    else:
                        #stop the loop when there's no parent package anymore
                        loop = False
                else:
                    #stop the loop when the package test_pack is not totally reserved for moves of this picking
                    #(some quants may be reserved for other picking or not reserved at all)
                    loop = False
            if good_pack:
                top_lvl_packages.add(good_pack)
        return list(top_lvl_packages)

    @api.model
    def _prepare_pack_ops(self, picking, quants, forced_qties):
        """ returns a list of dict, ready to be used in create() of stock.pack.operation.

        :param picking: browse record (stock.picking)
        :param quants: browse record list (stock.quant). List of quants associated to the picking
        :param forced_qties: dictionary showing for each product (keys) its corresponding quantity (value) that is not covered by the quants associated to the picking
        """
        def _picking_putaway_apply(product):
            location = False
            # Search putaway strategy
            if product_putaway_strats.get(product.id):
                location = product_putaway_strats[product.id]
            else:
                location = self.env['stock.location'].get_putaway_strategy(picking.location_dest_id, product)
                product_putaway_strats[product.id] = location
            return location or picking.location_dest_id.id

        # If we encounter an UoM that is smaller than the default UoM or the one already chosen, use the new one instead.
        product_uom = {}  # Determines UoM used in pack operations
        location_dest_id = None
        location_id = None
        for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
            if not product_uom.get(move.product_id.id):
                product_uom[move.product_id.id] = move.product_id.uom_id
            if move.product_uom.id != move.product_id.uom_id.id and move.product_uom.factor > product_uom[move.product_id.id].factor:
                product_uom[move.product_id.id] = move.product_uom
            if not move.scrapped:
                if location_dest_id and move.location_dest_id.id != location_dest_id:
                    raise UserError(_('The destination location must be the same for all the moves of the picking.'))
                location_dest_id = move.location_dest_id.id
                if location_id and move.location_id.id != location_id:
                    raise UserError(_('The source location must be the same for all the moves of the picking.'))
                location_id = move.location_id.id

        quant_obj = self.env["stock.quant"]
        vals = []
        qtys_grouped = {}
        lots_grouped = {}
        #for each quant of the picking, find the suggested location
        quants_suggested_locations = {}
        product_putaway_strats = {}
        for quant in quants:
            if quant.qty <= 0:
                continue
            suggested_location_id = _picking_putaway_apply(quant.product_id)
            quants_suggested_locations[quant] = suggested_location_id

        #find the packages we can movei as a whole
        top_lvl_packages = self._get_top_level_packages(quants_suggested_locations)
        # and then create pack operations for the top-level packages found
        for pack in top_lvl_packages:
            pack_quant_ids = pack.get_content()
            pack_quants = quant_obj.browse(pack_quant_ids)
            vals.append({
                    'picking_id': picking.id,
                    'package_id': pack.id,
                    'product_qty': 1.0,
                    'location_id': pack.location_id.id,
                    'location_dest_id': quants_suggested_locations[pack_quants[0]],
                    'owner_id': pack.owner_id.id,
                })
            #remove the quants inside the package so that they are excluded from the rest of the computation
            for quant in pack_quants:
                del quants_suggested_locations[quant]
        # Go through all remaining reserved quants and group by product, package, owner, source location and dest location
        # Lots will go into pack operation lot object
        for quant, dest_location_id in quants_suggested_locations.items():
            key = (quant.product_id.id, quant.package_id.id, quant.owner_id.id, quant.location_id.id, dest_location_id)
            if qtys_grouped.get(key):
                qtys_grouped[key] += quant.qty
            else:
                qtys_grouped[key] = quant.qty
            if quant.product_id.tracking != 'none' and quant.lot_id:
                lots_grouped.setdefault(key, {}).setdefault(quant.lot_id.id, 0.0)
                lots_grouped[key][quant.lot_id.id] += quant.qty

        # Do the same for the forced quantities (in cases of force_assign or incomming shipment for example)
        for product, qty in forced_qties.items():
            if qty <= 0:
                continue
            suggested_location_id = _picking_putaway_apply(product)
            key = (product.id, False, picking.owner_id.id, picking.location_id.id, suggested_location_id)
            if qtys_grouped.get(key):
                qtys_grouped[key] += qty
            else:
                qtys_grouped[key] = qty

        # Create the necessary operations for the grouped quants and remaining qtys
        uom_obj = self.env['product.uom']
        prevals = {}
        for key, qty in qtys_grouped.items():
            product = self.env["product.product"].browse(key[0])
            uom_id = product.uom_id.id
            qty_uom = qty
            if product_uom.get(key[0]):
                uom_id = product_uom[key[0]].id
                qty_uom = uom_obj._compute_qty(product.uom_id.id, qty, uom_id)
            pack_lot_ids = []
            if lots_grouped.get(key):
                for lot in lots_grouped[key].keys():
                    pack_lot_ids += [(0, 0, {'lot_id': lot, 'qty': 0.0, 'qty_todo': lots_grouped[key][lot]})]
            val_dict = {
                'picking_id': picking.id,
                'product_qty': qty_uom,
                'product_id': key[0],
                'package_id': key[1],
                'owner_id': key[2],
                'location_id': key[3],
                'location_dest_id': key[4],
                'product_uom_id': uom_id,
                'pack_lot_ids': pack_lot_ids,
            }
            if key[0] in prevals:
                prevals[key[0]].append(val_dict)
            else:
                prevals[key[0]] = [val_dict]
        # prevals var holds the operations in order to create them in the same order than the picking stock moves if possible
        processed_products = set()
        for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
            if move.product_id.id not in processed_products:
                vals += prevals.get(move.product_id.id, [])
                processed_products.add(move.product_id.id)
        return vals

    @api.multi
    def do_prepare_partial(self):
        pack_operation_obj = self.env['stock.pack.operation']

        #get list of existing operations and delete them
        existing_package_ids = pack_operation_obj.search([('picking_id', 'in', self.ids)])
        if existing_package_ids:
            existing_package_ids.unlink()
        for picking in self:
            forced_qties = {}  # Quantity remaining after calculating reserved quants
            picking_quants = []
            #Calculate packages, reserved quants, qtys of this picking's moves
            for move in picking.move_lines:
                if move.state not in ('assigned', 'confirmed', 'waiting'):
                    continue
                move_quants = move.reserved_quant_ids
                picking_quants += move_quants
                forced_qty = (move.state == 'assigned') and move.product_qty - sum([x.qty for x in move_quants]) or 0
                #if we used force_assign() on the move, or if the move is incoming, forced_qty > 0
                if float_compare(forced_qty, 0, precision_rounding=move.product_id.uom_id.rounding) > 0:
                    if forced_qties.get(move.product_id):
                        forced_qties[move.product_id] += forced_qty
                    else:
                        forced_qties[move.product_id] = forced_qty
            for vals in self._prepare_pack_ops(picking, picking_quants, forced_qties):
                vals['fresh_record'] = False
                pack_operation_obj.create(vals)
        #recompute the remaining quantities all at once
        self.do_recompute_remaining_quantities()
        self.write({'recompute_pack_op': False})

    @api.multi
    def do_unreserve(self):
        """
          Will remove all quants for picking in picking_ids
        """
        moves_to_unreserve = []
        pack_line_to_unreserve = []
        for picking in self:
            moves_to_unreserve += [m.id for m in picking.move_lines if m.state not in ('done', 'cancel')]
            pack_line_to_unreserve += [p.id for p in picking.pack_operation_ids]
        if moves_to_unreserve:
            if pack_line_to_unreserve:
                self.env['stock.pack.operation'].browse(pack_line_to_unreserve).unlink()
            self.env['stock.move'].browse(moves_to_unreserve).do_unreserve()

    @api.model
    def recompute_remaining_qty(self, picking, done_qtys=False):
        def _create_link_for_index(operation_id, index, product_id, qty_to_assign, quant_id=False):
            move_dict = prod2move_ids[product_id][index]
            qty_on_link = min(move_dict['remaining_qty'], qty_to_assign)
            self.env['stock.move.operation.link'].create({'move_id': move_dict['move'].id, 'operation_id': operation_id, 'qty': qty_on_link, 'reserved_quant_id': quant_id})
            if move_dict['remaining_qty'] == qty_on_link:
                prod2move_ids[product_id].pop(index)
            else:
                move_dict['remaining_qty'] -= qty_on_link
            return qty_on_link

        def _create_link_for_quant(operation_id, quant, qty):
            """create a link for given operation and reserved move of given quant, for the max quantity possible, and returns this quantity"""
            if not quant.reservation_id.id:
                return _create_link_for_product(operation_id, quant.product_id.id, qty)
            qty_on_link = 0
            for i in range(0, len(prod2move_ids[quant.product_id.id])):
                if prod2move_ids[quant.product_id.id][i]['move'].id != quant.reservation_id.id:
                    continue
                qty_on_link = _create_link_for_index(operation_id, i, quant.product_id.id, qty, quant_id=quant.id)
                break
            return qty_on_link

        def _create_link_for_product(operation_id, product_id, qty):
            '''method that creates the link between a given operation and move(s) of given product, for the given quantity.
            Returns True if it was possible to create links for the requested quantity (False if there was not enough quantity on stock moves)'''
            qty_to_assign = qty
            prod_obj = self.env["product.product"]
            product = prod_obj.browse(product_id)
            rounding = product.uom_id.rounding
            qtyassign_cmp = float_compare(qty_to_assign, 0.0, precision_rounding=rounding)
            if prod2move_ids.get(product_id):
                while prod2move_ids[product_id] and qtyassign_cmp > 0:
                    qty_on_link = _create_link_for_index(operation_id, 0, product_id, qty_to_assign, quant_id=False)
                    qty_to_assign -= qty_on_link
                    qtyassign_cmp = float_compare(qty_to_assign, 0.0, precision_rounding=rounding)
            return qtyassign_cmp == 0

        uom_obj = self.env['product.uom']
        package_obj = self.env['stock.quant.package']
        quant_obj = self.env['stock.quant']
        link_obj = self.env['stock.move.operation.link']
        quants_in_package_done = set()
        prod2move_ids = {}
        still_to_do = []
        #make a dictionary giving for each product, the moves and related quantity that can be used in operation links
        for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
            if not prod2move_ids.get(move.product_id.id):
                prod2move_ids[move.product_id.id] = [{'move': move, 'remaining_qty': move.product_qty}]
            else:
                prod2move_ids[move.product_id.id].append({'move': move, 'remaining_qty': move.product_qty})

        need_rereserve = False
        #sort the operations in order to give higher priority to those with a package, then a serial number
        operations = picking.pack_operation_ids
        operations = sorted(operations, key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))
        #delete existing operations to start again from scratch
        links = link_obj.search([('operation_id', 'in', [x.id for x in operations])])
        if links:
            links.unlink()
        #1) first, try to create links when quants can be identified without any doubt
        for ops in operations:
            lot_qty = {}
            for packlot in ops.pack_lot_ids:
                lot_qty[packlot.lot_id.id] = uom_obj._compute_qty(ops.product_uom_id.id, packlot.qty, ops.product_id.uom_id.id)
            #for each operation, create the links with the stock move by seeking on the matching reserved quants,
            #and deffer the operation if there is some ambiguity on the move to select
            if ops.package_id and not ops.product_id and (not done_qtys or ops.qty_done):
                #entire package
                quant_ids = ops.package_id.get_content()
                for quant in quant_obj.browse(quant_ids):
                    remaining_qty_on_quant = quant.qty
                    if quant.reservation_id:
                        #avoid quants being counted twice
                        quants_in_package_done.add(quant.id)
                        qty_on_link = _create_link_for_quant(ops.id, quant, quant.qty)
                        remaining_qty_on_quant -= qty_on_link
                    if remaining_qty_on_quant:
                        still_to_do.append((ops, quant.product_id.id, remaining_qty_on_quant))
                        need_rereserve = True
            elif ops.product_id.id:
                #Check moves with same product
                product_qty = ops.qty_done if done_qtys else ops.product_qty
                qty_to_assign = uom_obj._compute_qty_obj(ops.product_uom_id, product_qty, ops.product_id.uom_id)
                for move_dict in prod2move_ids.get(ops.product_id.id, []):
                    move = move_dict['move']
                    for quant in move.reserved_quant_ids:
                        if not qty_to_assign > 0:
                            break
                        if quant.id in quants_in_package_done:
                            continue

                        #check if the quant is matching the operation details
                        if ops.package_id:
                            flag = quant.package_id and bool(package_obj.search([('id', 'child_of', [ops.package_id.id])])) or False
                        else:
                            flag = not quant.package_id.id
                        flag = flag and (ops.owner_id.id == quant.owner_id.id)
                        if flag:
                            if not lot_qty:
                                max_qty_on_link = min(quant.qty, qty_to_assign)
                                qty_on_link = _create_link_for_quant(ops.id, quant, max_qty_on_link)
                                qty_to_assign -= qty_on_link
                            else:
                                if lot_qty.get(quant.lot_id.id):  # if there is still some qty left
                                    max_qty_on_link = min(quant.qty, qty_to_assign, lot_qty[quant.lot_id.id])
                                    qty_on_link = _create_link_for_quant(ops.id, quant, max_qty_on_link)
                                    qty_to_assign -= qty_on_link
                                    lot_qty[quant.lot_id.id] -= qty_on_link

                qty_assign_cmp = float_compare(qty_to_assign, 0, precision_rounding=ops.product_id.uom_id.rounding)
                if qty_assign_cmp > 0:
                    #qty reserved is less than qty put in operations. We need to create a link but it's deferred after we processed
                    #all the quants (because they leave no choice on their related move and needs to be processed with higher priority)
                    still_to_do += [(ops, ops.product_id.id, qty_to_assign)]
                    need_rereserve = True

        #2) then, process the remaining part
        all_op_processed = True
        for ops, product_id, remaining_qty in still_to_do:
            all_op_processed = _create_link_for_product(ops.id, product_id, remaining_qty) and all_op_processed
        return (need_rereserve, all_op_processed)

    @api.model
    def picking_recompute_remaining_quantities(self, picking, done_qtys=False):
        need_rereserve = False
        all_op_processed = True
        if picking.pack_operation_ids:
            need_rereserve, all_op_processed = self.recompute_remaining_qty(picking, done_qtys=done_qtys)
        return need_rereserve, all_op_processed

    @api.multi
    def do_recompute_remaining_quantities(self, done_qtys=False):
        for picking in self:
            if picking.pack_operation_ids:
                self.recompute_remaining_qty(picking, done_qtys=done_qtys)

    @api.model
    def _prepare_values_extra_move(self, op, product, remaining_qty):
        """
        Creates an extra move when there is no corresponding original move to be copied
        """
        uom_obj = self.env["product.uom"]
        uom_id = product.uom_id.id
        qty = remaining_qty
        if op.product_id and op.product_uom_id and op.product_uom_id.id != product.uom_id.id:
            if op.product_uom_id.factor > product.uom_id.factor:  # If the pack operation's is a smaller unit
                uom_id = op.product_uom_id.id
                #HALF-UP rounding as only rounding errors will be because of propagation of error from default UoM
                qty = uom_obj._compute_qty_obj(product.uom_id, remaining_qty, op.product_uom_id, rounding_method='HALF-UP')
        picking = op.picking_id
        ref = product.default_code
        name = '[' + ref + ']' + ' ' + product.name if ref else product.name
        res = {
            'picking_id': picking.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'product_id': product.id,
            'product_uom': uom_id,
            'product_uom_qty': qty,
            'name': _('Extra Move: ') + name,
            'state': 'draft',
            'restrict_partner_id': op.owner_id,
            'group_id': picking.group_id.id,
            }
        return res

    @api.model
    def _create_extra_moves(self, picking):
        '''This function creates move lines on a picking, at the time of do_transfer, based on
        unexpected product transfers (or exceeding quantities) found in the pack operations.
        '''
        move_obj = self.env['stock.move']
        operation_obj = self.env['stock.pack.operation']
        moves = []
        for op in picking.pack_operation_ids:
            for product_id, remaining_qty in operation_obj._get_remaining_prod_quantities(op).items():
                product = self.env['product.product'].browse(product_id)
                if float_compare(remaining_qty, 0, precision_rounding=product.uom_id.rounding) > 0:
                    vals = self._prepare_values_extra_move(op, product, remaining_qty)
                    moves.append(move_obj.create(vals).id)
        if moves:
            move_list = move_obj.browse(moves)
            move_list.action_confirm()
        return moves

    @api.multi
    def rereserve_pick(self):
        """
        This can be used to provide a button that rereserves taking into account the existing pack operations
        """
        for pick in self:
            self.rereserve_quants(pick, move_ids=pick.move_lines.ids)

    @api.model
    def rereserve_quants(self, picking, move_ids=[]):
        """ Unreserve quants then try to reassign quants."""
        stock_move_obj = self.env['stock.move']
        if not move_ids:
            picking.do_unreserve()
            picking.action_assign()
        else:
            stock_move_obj.browse(move_ids).do_unreserve()
            stock_move_obj.browse(move_ids).action_assign(no_prepare=True)

    @api.multi
    def do_new_transfer(self):
        pack_op_obj = self.env['stock.pack.operation']
        for pick in self:
            to_delete = []
            if not pick.move_lines and not pick.pack_operation_ids:
                raise UserError(_('Please create some Initial Demand or Mark as Todo and create some Operations. '))
            # In draft or with no pack operations edited yet, ask if we can just do everything
            if pick.state == 'draft' or all([x.qty_done == 0.0 for x in pick.pack_operation_ids]):
                # If no lots when needed, raise error
                picking_type = pick.picking_type_id
                if (picking_type.use_create_lots or picking_type.use_existing_lots):
                    for pack in pick.pack_operation_ids:
                        if pack.product_id and pack.product_id.tracking != 'none':
                            raise UserError(_('Some products require lots, so you need to specify those first!'))

                view = self.env.ref('stock.view_immediate_transfer').id
                # view = data_obj.xmlid_to_res_id(cr, uid, 'stock.view_immediate_transfer')
                wiz_id = self.env['stock.immediate.transfer'].create({'pick_id': pick.id})
                return {
                        'name': _('Immediate Transfer?'),
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'stock.immediate.transfer',
                        'views': [(view, 'form')],
                        'view_id': view,
                        'target': 'new',
                        'res_id': wiz_id.id,
                        'context': self.env.context,
                    }

            # Check backorder should check for other barcodes
            if self.check_backorder(pick):
                view = self.env.ref('stock.view_backorder_confirmation').id
                # view = data_obj.xmlid_to_res_id(cr, uid, 'stock.view_backorder_confirmation')
                wiz_id = self.env['stock.backorder.confirmation'].create({'pick_id': pick.id})
                return {
                        'name': _('Create Backorder?'),
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'stock.backorder.confirmation',
                        'views': [(view, 'form')],
                        'view_id': view,
                        'target': 'new',
                        'res_id': wiz_id.id,
                        'context': self.env.context,
                        }
            for operation in pick.pack_operation_ids:
                if operation.qty_done < 0:
                    raise UserError(_('No negative quantities allowed'))
                if operation.qty_done > 0:
                    operation.write({'product_qty': operation.qty_done})
                else:
                    to_delete.append(operation.id)
            if to_delete:
                pack_op_obj.browse(to_delete).unlink()
        self.do_transfer()
        return

    @api.model
    def check_backorder(self, picking):
        need_rereserve, all_op_processed = self.picking_recompute_remaining_quantities(picking, done_qtys=True)
        for move in picking.move_lines:
            if float_compare(move.remaining_qty, 0, precision_rounding=move.product_id.uom_id.rounding) != 0:
                return True
        return False

    @api.multi
    def create_lots_for_picking(self):
        lot_obj = self.env['stock.production.lot']
        opslot_obj = self.env['stock.pack.operation.lot']
        to_unlink = []
        for picking in self:
            for ops in picking.pack_operation_ids:
                for opslot in ops.pack_lot_ids:
                    if not opslot.lot_id:
                        lot_id = lot_obj.create({'name': opslot.lot_name, 'product_id': ops.product_id.id})
                        opslot.write({'lot_id': lot_id.id})
                #Unlink pack operations where qty = 0
                to_unlink += [x.id for x in ops.pack_lot_ids if x.qty == 0.0]
        opslot_obj.browse(to_unlink).unlink()

    @api.multi
    def do_transfer(self):
        """
            If no pack operation, we do simple action_done of the picking
            Otherwise, do the pack operations
        """
        stock_move_obj = self.env['stock.move']
        self.create_lots_for_picking()
        for picking in self:
            if not picking.pack_operation_ids:
                picking.action_done()
                continue
            else:
                need_rereserve, all_op_processed = self.picking_recompute_remaining_quantities(picking)
                #create extra moves in the picking (unexpected product moves coming from pack operations)
                todo_move_ids = []
                if not all_op_processed:
                    todo_move_ids += self._create_extra_moves(picking)

                #split move lines if needed
                toassign_move_ids = []
                for move in picking.move_lines:
                    remaining_qty = move.remaining_qty
                    if move.state in ('done', 'cancel'):
                        #ignore stock moves cancelled or already done
                        continue
                    elif move.state == 'draft':
                        toassign_move_ids.append(move.id)
                    if float_compare(remaining_qty, 0,  precision_rounding=move.product_id.uom_id.rounding) == 0:
                        if move.state in ('draft', 'assigned', 'confirmed'):
                            todo_move_ids.append(move.id)
                    elif float_compare(remaining_qty,0, precision_rounding=move.product_id.uom_id.rounding) > 0 and \
                                float_compare(remaining_qty, move.product_qty, precision_rounding=move.product_id.uom_id.rounding) < 0:
                        new_move = stock_move_obj.split(move, remaining_qty)
                        todo_move_ids.append(move.id)
                        #Assign move as it was assigned before
                        toassign_move_ids.append(new_move)
                if need_rereserve or not all_op_processed:
                    if not picking.location_id.usage in ("supplier", "production", "inventory"):
                        self.rereserve_quants(picking, move_ids=todo_move_ids)
                    picking.do_recompute_remaining_quantities()
                if todo_move_ids and not self.env.context.get('do_only_split'):
                    self.env['stock.move'].browse(todo_move_ids).action_done()
                elif self.env.context.get('do_only_split'):
                    self.with_context(split=todo_move_ids)
            self._create_backorder(picking)
        return True

    @api.model
    def do_split(self, picking_ids):
        """ just split the picking (create a backorder) without making it 'done' """
        self.with_context(do_only_split=True)
        return picking_ids.do_transfer()

    @api.multi
    def put_in_pack(self):
        stock_operation_obj = self.env["stock.pack.operation"]
        package_obj = self.env["stock.quant.package"]
        package_id = False
        for pick in self:
            operations = [x for x in pick.pack_operation_ids if x.qty_done > 0 and (not x.result_package_id)]
            pack_operation_ids = []
            for operation in operations:
                #If we haven't done all qty in operation, we have to split into 2 operation
                op = operation
                if operation.qty_done < operation.product_qty:
                    new_operation = operation.copy({'product_qty': operation.qty_done, 'qty_done': operation.qty_done})

                    operation.write({'product_qty': operation.product_qty - operation.qty_done, 'qty_done': 0})
                    if operation.pack_lot_ids:
                        packlots_transfer = [(4, x.id) for x in operation.pack_lot_ids]
                        new_operation.write({'pack_lot_ids': packlots_transfer})

                    op = new_operation
                pack_operation_ids.append(op.id)
            if operations:
                stock_operation_obj.browse(pack_operation_ids).check_tracking()
                package_id = package_obj.create({})
                stock_operation_obj.browse(pack_operation_ids).write({'result_package_id': package_id})
            else:
                raise UserError(_('Please process some quantities to put in the pack first!'))
        return package_id.id

class StockProductionLot(models.Model):
    _name = 'stock.production.lot'
    _inherit = ['mail.thread']
    _description = 'Lot/Serial'

    name = fields.Char('Serial Number', required=True, help="Unique Serial Number", default=lambda x: x.env['ir.sequence'].next_by_code('stock.lot.serial'))
    ref = fields.Char('Internal Reference', help="Internal reference number in case it differs from the manufacturer's serial number")
    product_id = fields.Many2one('product.product', 'Product', required=True, domain=[('type', 'in', ['product', 'consu'])], default=lambda x: x._context.get('product_id'))
    quant_ids = fields.One2many('stock.quant', 'lot_id', 'Quants', readonly=True)
    create_date = fields.Datetime('Creation Date')

    _sql_constraints = [
        ('name_ref_uniq', 'unique (name, product_id)', 'The combination of serial number and product must be unique !'),
    ]

    @api.multi
    def action_traceability(self):
        """ It traces the information of lots
        @param self: The object pointer.
        @return: A dictionary of values
        """
        quants = self.env["stock.quant"].search([('lot_id', 'in', self.ids)])
        moves = set()
        for quant in quants:
            moves |= {move.id for move in quant.history_ids}
        if moves:
            return {
                'domain': "[('id','in',[" + ','.join(map(str, list(moves))) + "])]",
                'name': _('Traceability'),
                'view_mode': 'tree,form',
                'view_type': 'form',
                'context': {'tree_view_ref': 'stock.view_move_tree'},
                'res_model': 'stock.move',
                'type': 'ir.actions.act_window',
                    }
        return False

# ----------------------------------------------------
# Move
# ----------------------------------------------------
class StockMove(models.Model):
    _name = "stock.move"
    _description = "Stock Move"
    _order = 'picking_id, sequence, id'
    _log_create = False

    @api.model
    def get_price_unit(self, move):
        """ Returns the unit price to store on the quant """
        return move.price_unit or move.product_id.standard_price

    @api.multi
    def name_get(self):
        res = []
        for line in self:
            name = line.location_id.name + ' > ' + line.location_dest_id.name
            if line.product_id.code:
                name = line.product_id.code + ': ' + name
            if line.picking_id.origin:
                name = line.picking_id.origin + '/ ' + name
            res.append((line.id, name))
        return res

    @api.multi
    def _get_move(self):
        res = set()
        for quant in self:
            if quant.reservation_id:
                res.add(quant.reservation_id.id)
        return list(res)

    @api.multi
    def _get_move_ids(self):
        res = []
        for picking in self:
            res += [x.id for x in picking.move_lines]
        return res

    @api.multi
    def _get_moves_from_prod(self):
        if self.ids:
            return self.search([('product_id', 'in', self.ids)])
        return []

    @api.multi
    def _get_remaining_qty(self):
        for move in self:
            qty = move.product_qty
            for record in move.linked_move_operation_ids:
                qty -= record.qty
            # Keeping in product default UoM
            move.remaining_qty = float_round(qty, precision_rounding=move.product_id.uom_id.rounding)

    @api.multi
    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _quantity_normalize(self):
        for m in self:
            m.product_qty = self.env['product.uom']._compute_qty_obj(m.product_uom, m.product_uom_qty, m.product_id.uom_id)

    @api.multi
    def _get_product_availability(self):
        for move in self:
            if move.state == 'done':
                move.availability = move.product_qty
            else:
                sublocation_ids = self.env['stock.location'].search([('id', 'child_of', [move.location_id.id])])
                quant_ids = self.env['stock.quant'].search([('location_id', 'in', sublocation_ids.ids), ('product_id', '=', move.product_id.id), ('reservation_id', '=', False)])
                availability = 0
                for quant in quant_ids:
                    availability += quant.qty
                move.availability = min(move.product_qty, availability)

    @api.multi
    def _get_lot_ids(self):
        for move in self:
            if move.state == 'done':
                move.lot_ids = [q.lot_id.id for q in move.quant_ids if q.lot_id]
            else:
                move.lot_ids = [q.lot_id.id for q in move.reserved_quant_ids if q.lot_id]

    @api.multi
    def _get_string_qty_information(self):
        uom_obj = self.env['product.uom']
        # res = dict.fromkeys(ids, '')
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for move in self:
            if move.state in ('draft', 'done', 'cancel') or move.location_id.usage != 'internal':
                move.string_availability_info = ''  # 'not applicable' or 'n/a' could work too
                continue
            total_available = min(move.product_qty, move.reserved_availability + move.availability)
            total_available = uom_obj._compute_qty_obj(move.product_id.uom_id, total_available, move.product_uom, round=False)
            total_available = float_round(total_available, precision_digits=precision)
            info = str(total_available)
            #look in the settings if we need to display the UoM name or not
            config_ids = self.env['stock.config.settings'].search([], limit=1, order='id DESC')
            if config_ids:
                stock_settings = config_ids
                if stock_settings.group_uom:
                    info += ' ' + move.product_uom.name
            if move.reserved_availability:
                if move.reserved_availability != total_available:
                    #some of the available quantity is assigned and some are available but not reserved
                    reserved_available = uom_obj._compute_qty_obj(move.product_id.uom_id, move.reserved_availability, move.product_uom, round=False)
                    reserved_available = float_round(reserved_available, precision_digits=precision)
                    info += _(' (%s reserved)') % str(reserved_available)
                else:
                    #all available quantity is assigned
                    info += _(' (reserved)')
            move.string_availability_info = info

    @api.multi
    def _get_reserved_availability(self):
        for move in self:
            move.reserved_availability = sum([quant.qty for quant in move.reserved_quant_ids])

    @api.model
    def _default_destination_address(self):
        return False

    @api.model
    def _default_group_id(self):
        if self.env.context.get('default_picking_id', False):
            picking = self.env['stock.picking'].browse(self.env.context['default_picking_id'])
            return picking.group_id.id
        return False

    @api.multi
    def _set_product_qty(self):
        """ The meaning of product_qty field changed lately and is now a functional field computing the quantity
            in the default product UoM. This code has been added to raise an error if a write is made given a value
            for `product_qty`, where the same write should set the `product_uom_qty` field instead, in order to
            detect errors.
        """
        raise UserError(_('The requested operation cannot be processed because of a programming error setting the `product_qty` field instead of the `product_uom_qty`.'))

    sequence = fields.Integer(default=10)
    name = fields.Char('Description', required=True, select=True)
    priority = fields.Selection(procurement.PROCUREMENT_PRIORITIES, default='1')
    create_date = fields.Datetime('Creation Date', readonly=True, select=True)
    date = fields.Datetime(required=True, select=True, help="Move date: scheduled date until move is done, then date of actual move processing", states={'done': [('readonly', True)]}, default=fields.Datetime.now)
    date_expected = fields.Datetime('Expected Date', states={'done': [('readonly', True)]}, required=True, select=True, help="Scheduled date for the processing of this move", default=fields.Datetime.now)
    product_id = fields.Many2one('product.product', 'Product', required=True, select=True, domain=[('type', 'in', ['product', 'consu'])], states={'done': [('readonly', True)]})
    product_qty = fields.Float(compute="_quantity_normalize", inverse='_set_product_qty', store=True, digits=0,
        string='Quantity', help='Quantity in the default UoM of the product')
    product_uom_qty = fields.Float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'),
        required=True, states={'done': [('readonly', True)]}, default=1.0,
        help="This is the quantity of products from an inventory "
            "point of view. For moves in the state 'done', this is the "
            "quantity of products that were actually moved. For other "
            "moves, this is the quantity of product that is planned to "
            "be moved. Lowering this quantity does not generate a "
            "backorder. Changing this quantity on assigned moves affects "
            "the product reservation, and should be done with care."
    )
    product_uom = fields.Many2one('product.uom', 'Unit of Measure', required=True, states={'done': [('readonly', True)]})
    product_tmpl_id = fields.Many2one(related='product_id.product_tmpl_id', relation='product.template', string='Product Template')
    product_packaging = fields.Many2one('product.packaging', 'preferred Packaging', help="It specifies attributes of packaging like type, quantity of packaging,etc.")
    location_id = fields.Many2one('stock.location', 'Source Location', required=True, select=True, auto_join=True, states={'done': [('readonly', True)]}, help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations.")
    location_dest_id = fields.Many2one('stock.location', 'Destination Location', required=True, states={'done': [('readonly', True)]}, select=True, auto_join=True, help="Location where the system will stock the finished products.")
    partner_id = fields.Many2one('res.partner', 'Destination Address ', states={'done': [('readonly', True)]}, help="Optional address where goods are to be delivered, specifically used for allotment", default=_default_destination_address)
    move_dest_id = fields.Many2one('stock.move', 'Destination Move', help="Optional: next stock move when chaining them", select=True, copy=False)
    move_orig_ids = fields.One2many('stock.move', 'move_dest_id', 'Original Move', help="Optional: previous stock move when chaining them", select=True)
    picking_id = fields.Many2one('stock.picking', 'Transfer Reference', select=True, states={'done': [('readonly', True)]})
    note = fields.Text('Notes')
    state = fields.Selection([('draft', 'New'),
                           ('cancel', 'Cancelled'),
                           ('waiting', 'Waiting Another Move'),
                           ('confirmed', 'Waiting Availability'),
                           ('assigned', 'Available'),
                           ('done', 'Done'),
                           ], 'Status', readonly=True, select=True, copy=False,
            help= "* New: When the stock move is created and not yet confirmed.\n"\
               "* Waiting Another Move: This state can be seen when a move is waiting for another one, for example in a chained flow.\n"\
               "* Waiting Availability: This state is reached when the procurement resolution is not straight forward. It may need the scheduler to run, a component to me manufactured...\n"\
               "* Available: When products are reserved, it is set to \'Available\'.\n"\
               "* Done: When the shipment is processed, the state is \'Done\'.", default='draft')
    partially_available = fields.Boolean('Partially Available', readonly=True, help="Checks if the move has some stock reserved", copy=False, default=False)
    price_unit = fields.Float('Unit Price', help="Technical field used to record the product cost set by the user during a picking confirmation (when costing method used is 'average price' or 'real'). Value given in company currency and in product uom.")  # as it's a technical field, we intentionally don't provide the digits attribute
    company_id = fields.Many2one('res.company', 'Company', required=True, select=True, default=lambda self: self.env.user.company_id)
    split_from = fields.Many2one('stock.move', string="Move Split From", help="Technical field used to track the origin of a split move, which can be useful in case of debug", copy=False)
    backorder_id = fields.Many2one(related='picking_id.backorder_id', relation="stock.picking", string="Back Order of", select=True)
    origin = fields.Char("Source Document")
    procure_method = fields.Selection([('make_to_stock', 'Default: Take From Stock'), ('make_to_order', 'Advanced: Apply Procurement Rules')], 'Supply Method', required=True,
        help="""By default, the system will take from the stock in the source location and passively wait for availability. The other possibility allows you to directly create a procurement on the source location (and thus ignore its current stock) to gather products. If we want to chain moves and have this one to wait for the previous, this second option should be chosen.""",
        default='make_to_stock')
    # used for colors in tree views:
    scrapped = fields.Boolean(related='location_dest_id.scrap_location', relation='stock.location', readonly=True, default=False)
    quant_ids = fields.Many2many('stock.quant', 'stock_quant_move_rel', 'move_id', 'quant_id', 'Moved Quants', copy=False)
    reserved_quant_ids = fields.One2many('stock.quant', 'reservation_id', 'Reserved quants')
    linked_move_operation_ids = fields.One2many('stock.move.operation.link', 'move_id', string='Linked Operations', readonly=True, help='Operations that impact this move for the computation of the remaining quantities')
    remaining_qty = fields.Float(compute="_get_remaining_qty", string='Remaining Quantity', digits=0, states={'done': [('readonly', True)]},
        help="Remaining Quantity in default UoM according to operations matched with this move")
    procurement_id = fields.Many2one('procurement.order', 'Procurement')
    group_id = fields.Many2one('procurement.group', 'Procurement Group', default=_default_group_id)
    rule_id = fields.Many2one('procurement.rule', 'Procurement Rule', help='The procurement rule that created this stock move')
    push_rule_id = fields.Many2one('stock.location.path', 'Push Rule', help='The push rule that created this stock move')
    propagate = fields.Boolean('Propagate cancel and split', help='If checked, when this move is cancelled, cancel the linked move too', default=True)
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type')
    inventory_id = fields.Many2one('stock.inventory', 'Inventory')
    lot_ids = fields.Many2many(compute="_get_lot_ids", comodel_name='stock.production.lot', string='Lots')
    origin_returned_move_id = fields.Many2one('stock.move', 'Origin return move', help='move that created the return move', copy=False)
    returned_move_ids = fields.One2many('stock.move', 'origin_returned_move_id', 'All returned moves', help='Optional: all returned moves created from this move')
    reserved_availability = fields.Float(compute="_get_reserved_availability", string='Quantity Reserved', readonly=True, help='Quantity that has already been reserved for this move')
    availability = fields.Float(compute="_get_product_availability", string='Forecasted Quantity', readonly=True, help='Quantity in stock that can still be reserved for this move')
    string_availability_info = fields.Text(compute="_get_string_qty_information", string='Availability', readonly=True, help='Show various information on stock availability for this move')
    restrict_lot_id = fields.Many2one('stock.production.lot', 'Lot', help="Technical field used to depict a restriction on the lot of quants to consider when marking this move as 'done'")
    restrict_partner_id = fields.Many2one('res.partner', 'Owner ', help="Technical field used to depict a restriction on the ownership of quants to consider when marking this move as 'done'")
    route_ids = fields.Many2many('stock.location.route', 'stock_location_route_move', 'move_id', 'route_id', 'Destination route', help="Preferred route to be followed by the procurement order")
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', help="Technical field depicting the warehouse to consider for the route selection on the next procurement (if any).")

    @api.multi
    @api.constrains('product_uom')
    def _check_uom(self):
        for move in self:
            if move.product_id.uom_id.category_id.id != move.product_uom.category_id.id:
                raise UserError('You try to move a product using a UoM that is not compatible with the UoM of the product moved. Please use an UoM in the same UoM category.')

    @api.v7
    def init(self, cr):
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_move_product_location_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX stock_move_product_location_index ON stock_move (product_id, location_id, location_dest_id, company_id, state)')

    @api.multi
    def do_unreserve(self):
        quant_obj = self.env["stock.quant"]
        for move in self:
            if move.state in ('done', 'cancel'):
                raise UserError(_('Cannot unreserve a done move'))
            quant_obj.quants_unreserve(move)
            if self.find_move_ancestors(move):
                move.write({'state': 'waiting'})
            else:
                move.write({'state': 'confirmed'})

    @api.model
    def _prepare_procurement_from_move(self, move):
        origin = (move.group_id and (move.group_id.name + ":") or "") + (move.rule_id and move.rule_id.name or move.origin or move.picking_id.name or "/")
        group_id = move.group_id and move.group_id.id or False
        if move.rule_id:
            if move.rule_id.group_propagation_option == 'fixed' and move.rule_id.group_id:
                group_id = move.rule_id.group_id.id
            elif move.rule_id.group_propagation_option == 'none':
                group_id = False
        return {
            'name': move.rule_id and move.rule_id.name or "/",
            'origin': origin,
            'company_id': move.company_id and move.company_id.id or False,
            'date_planned': move.date,
            'product_id': move.product_id.id,
            'product_qty': move.product_uom_qty,
            'product_uom': move.product_uom.id,
            'location_id': move.location_id.id,
            'move_dest_id': move.id,
            'group_id': group_id,
            'route_ids': [(4, x.id) for x in move.route_ids],
            'warehouse_id': move.warehouse_id.id or (move.picking_type_id and move.picking_type_id.warehouse_id.id or False),
            'priority': move.priority,
        }

    @api.model
    def _push_apply(self, moves):
        push_obj = self.env["stock.location.path"]
        for move in moves:
            #1) if the move is already chained, there is no need to check push rules
            #2) if the move is a returned move, we don't want to check push rules, as returning a returned move is the only decent way
            #   to receive goods without triggering the push rules again (which would duplicate chained operations)
            if not move.move_dest_id:
                domain = [('location_from_id', '=', move.location_dest_id.id)]
                #priority goes to the route defined on the product and product category
                route_ids = [x.id for x in move.product_id.route_ids + move.product_id.categ_id.total_route_ids]
                rules = push_obj.search(domain + [('route_id', 'in', route_ids)], order='route_sequence, sequence')
                if not rules:
                    #then we search on the warehouse if a rule can apply
                    wh_route_ids = []
                    if move.warehouse_id:
                        wh_route_ids = [x.id for x in move.warehouse_id.route_ids]
                    elif move.picking_type_id and move.picking_type_id.warehouse_id:
                        wh_route_ids = [x.id for x in move.picking_type_id.warehouse_id.route_ids]
                    if wh_route_ids:
                        rules = push_obj.search(domain + [('route_id', 'in', wh_route_ids)], order='route_sequence, sequence')
                    if not rules:
                        #if no specialized push rule has been found yet, we try to find a general one (without route)
                        rules = push_obj.search(domain + [('route_id', '=', False)], order='sequence')
                if rules:
                    rule = rules[0]
                    # Make sure it is not returning the return
                    if (not move.origin_returned_move_id or move.origin_returned_move_id.location_id.id != rule.location_dest_id.id):
                        push_obj._apply(rule, move)
        return True

    @api.model
    def _create_procurement(self, move):
        """ This will create a procurement order """
        return self.env["procurement.order"].create(self._prepare_procurement_from_move(move)).id

    @api.model
    def _create_procurements(self, moves):
        res = []
        for move in moves:
            res.append(self._create_procurement(move))
        return res

    @api.multi
    def write(self, vals):
        # Check that we do not modify a stock.move which is done
        frozen_fields = set(['product_qty', 'product_uom', 'location_id', 'location_dest_id', 'product_id'])
        for move in self:
            if move.state == 'done':
                if frozen_fields.intersection(vals):
                    raise UserError(_('Quantities, Units of Measure, Products and Locations cannot be modified on stock moves that have already been processed (except by the Administrator).'))
        propagated_changes_dict = {}
        #propagation of quantity change
        if vals.get('product_uom_qty'):
            propagated_changes_dict['product_uom_qty'] = vals['product_uom_qty']
        if vals.get('product_uom_id'):
            propagated_changes_dict['product_uom_id'] = vals['product_uom_id']
        #propagation of expected date:
        propagated_date_field = False
        if vals.get('date_expected'):
            #propagate any manual change of the expected date
            propagated_date_field = 'date_expected'
        elif (vals.get('state', '') == 'done' and vals.get('date')):
            #propagate also any delta observed when setting the move as done
            propagated_date_field = 'date'

        if not self.env.context.get('do_not_propagate', False) and (propagated_date_field or propagated_changes_dict):
            #any propagation is (maybe) needed
            for move in self:
                if move.move_dest_id and move.propagate:
                    if 'date_expected' in propagated_changes_dict:
                        propagated_changes_dict.pop('date_expected')
                    if propagated_date_field:
                        current_date = datetime.strptime(move.date_expected, DEFAULT_SERVER_DATETIME_FORMAT)
                        new_date = datetime.strptime(vals.get(propagated_date_field), DEFAULT_SERVER_DATETIME_FORMAT)
                        delta = new_date - current_date
                        if abs(delta.days) >= move.company_id.propagation_minimum_delta:
                            old_move_date = datetime.strptime(move.move_dest_id.date_expected, DEFAULT_SERVER_DATETIME_FORMAT)
                            new_move_date = (old_move_date + relativedelta.relativedelta(days=delta.days or 0)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                            propagated_changes_dict['date_expected'] = new_move_date
                    #For pushed moves as well as for pulled moves, propagate by recursive call of write().
                    #Note that, for pulled moves we intentionally don't propagate on the procurement.
                    if propagated_changes_dict:
                        move.move_dest_id.write(propagated_changes_dict)
        return super(StockMove, self).write(vals)

# on_change="onchange_quantity(product_id, product_uom_qty, product_uom)"
    # def onchange_quantity(self, cr, uid, ids, product_id, product_qty, product_uom):
    @api.onchange('product_id', 'product_uom_qty', 'product_uom')
    def onchange_quantity(self):
        """ On change of product quantity finds UoM
        """
        warning = {}
        if (not self.product_id) or (self.product_uom_qty <= 0.0):
            self.product_qty = 0.0
            return

        # Warn if the quantity was decreased
        if self.ids:
            for move in self.read(['product_qty']):
                if self.product_uom_qty < move['product_qty']:
                    warning.update({
                        'title': _('Information'),
                        'message': _("By changing this quantity here, you accept the "
                                "new quantity as complete: Odoo will not "
                                "automatically generate a back order.")})
                break
        return {'warning': warning}

# on_change="onchange_product_id(product_id,location_id,location_dest_id, False)"
    # def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False, loc_dest_id=False, partner_id=False):
    @api.onchange('product_id', 'location_id', 'location_dest_id', 'partner_id')
    def onchange_product_id(self):
        """ On change of product id, if finds UoM, quantity
        """
        if not self.product_id:
            return {'domain': {'product_uom': []}}
        user = self.env.user
        lang = user and user.lang or False
        if self.partner_id:
            addr_rec = self.partner_id
            if addr_rec:
                lang = addr_rec and addr_rec.lang or False
        self.with_context(lang=lang)
        product = self.env['product.product'].browse(self.product_id.ids)[0]
        self.name = product.partner_ref
        self.product_uom = product.uom_id.id
        self.product_uom_qty = 1.00
        if self.location_id:
            self.location_id = self.location_id
        if self.location_dest_id:
            self.location_dest_id = self.location_dest_id
        res = {'domain': {'product_uom': [('category_id', '=', product.uom_id.category_id.id)]}}
        return res

    @api.model
    def _prepare_picking_assign(self, move):
        """ Prepares a new picking for this move as it could not be assigned to
        another picking. This method is designed to be inherited.
        """
        values = {
            'origin': move.origin,
            'company_id': move.company_id and move.company_id.id or False,
            'move_type': move.group_id and move.group_id.move_type or 'direct',
            'partner_id': move.partner_id.id or False,
            'picking_type_id': move.picking_type_id and move.picking_type_id.id or False,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
        }
        return values

    @api.multi
    def _picking_assign(self):
        """Try to assign the moves to an existing picking
        that has not been reserved yet and has the same
        procurement group, locations and picking type  (moves should already have them identical)
         Otherwise, create a new picking to assign them to.
        """
        move = self[0]
        pick_obj = self.env["stock.picking"]
        picks = pick_obj.search([
                ('group_id', '=', move.group_id.id),
                ('location_id', '=', move.location_id.id),
                ('location_dest_id', '=', move.location_dest_id.id),
                ('picking_type_id', '=', move.picking_type_id.id),
                ('state', 'in', ['draft', 'confirmed', 'waiting'])], limit=1)
        if picks:
            pick = picks[0]
        else:
            values = self._prepare_picking_assign(move)
            pick = pick_obj.create(values)
        return self.write({'picking_id': pick.id})

    @api.onchange('date', 'date_expected')
    def onchange_date(self):
        """ On change of Scheduled Date gives a Move date.
        @param date_expected: Scheduled Date
        @param date: Move Date
        @return: Move Date
        """
        if not self.date_expected:
            self.date_expected = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.date = self.date_expected

    @api.model
    def attribute_price(self, move):
        """
            Attribute price to move, important in inter-company moves or receipts with only one partner
        """
        if not move.price_unit:
            price = move.product_id.standard_price
            move.write({'price_unit': price})

class StockInventory(models.Model):
    _name = "stock.inventory"
    _description = "Inventory"

    @api.multi
    def _get_move_ids_exist(self):
        res = {}
        for inv in self:
            res[inv.id] = False
            if inv.move_ids:
                res[inv.id] = True
        return res

    @api.model
    def _get_available_filters(self):
        """
           This function will return the list of filter allowed according to the options checked
           in 'Settings\Warehouse'.

           :rtype: list of tuple
        """
        #default available choices
        res_filter = [('none', _('All products')), ('partial', _('Select products manually')), ('product', _('One product only'))]
        settings_obj = self.env['stock.config.settings']
        config_ids = settings_obj.search([], limit=1, order='id DESC').ids
        #If we don't have updated config until now, all fields are by default false and so should be not dipslayed
        if not config_ids:
            return res_filter

        stock_settings = settings_obj.browse(config_ids)
        if stock_settings.group_stock_tracking_owner:
            res_filter.append(('owner', _('One owner only')))
            res_filter.append(('product_owner', _('One product for a specific owner')))
        if stock_settings.group_stock_tracking_lot:
            res_filter.append(('lot', _('One Lot/Serial Number')))
        if stock_settings.group_stock_packaging:
            res_filter.append(('pack', _('A Pack')))
        return res_filter

    @api.multi
    def _get_total_qty(self):
        for inv in self:
            inv.total_qty = sum([x.product_qty for x in inv.line_ids])

    @api.model
    def _default_stock_location(self):
        try:
            warehouse = self.env.ref('stock.warehouse0')
            return warehouse.lot_stock_id.id
        except:
            return False

    INVENTORY_STATE_SELECTION = [
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirm', 'In Progress'),
        ('done', 'Validated'),
    ]

    name = fields.Char('Inventory Reference', required=True, readonly=True, states={'draft': [('readonly', False)]}, help="Inventory Name.")
    date = fields.Datetime('Inventory Date', required=True, readonly=True, help="The date that will be used for the stock level check of the products and the validation of the stock move related to this inventory.", default=fields.Datetime.now)
    line_ids = fields.One2many('stock.inventory.line', 'inventory_id', 'Inventories', readonly=False, states={'done': [('readonly', True)]}, help="Inventory Lines.", copy=True)
    move_ids = fields.One2many('stock.move', 'inventory_id', 'Created Moves', help="Inventory Moves.", states={'done': [('readonly', True)]})
    state = fields.Selection(INVENTORY_STATE_SELECTION, 'Status', readonly=True, select=True, copy=False, default='draft')
    company_id = fields.Many2one('res.company', 'Company', required=True, select=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.user.company_id)
    location_id = fields.Many2one('stock.location', 'Inventoried Location', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=_default_stock_location)
    product_id = fields.Many2one('product.product', 'Inventoried Product', readonly=True, states={'draft': [('readonly', False)]}, help="Specify Product to focus your inventory on a particular Product.")
    package_id = fields.Many2one('stock.quant.package', 'Inventoried Pack', readonly=True, states={'draft': [('readonly', False)]}, help="Specify Pack to focus your inventory on a particular Pack.")
    partner_id = fields.Many2one('res.partner', 'Inventoried Owner', readonly=True, states={'draft': [('readonly', False)]}, help="Specify Owner to focus your inventory on a particular Owner.")
    lot_id = fields.Many2one('stock.production.lot', 'Inventoried Lot/Serial Number', readonly=True, states={'draft': [('readonly', False)]}, help="Specify Lot/Serial Number to focus your inventory on a particular Lot/Serial Number.", copy=False)
    # technical field for attrs in view
    move_ids_exist = fields.Boolean(compute="get_move_ids_exist", string='Has Stock Moves', help='Check the existance of stock moves linked to this inventory')
    filter = fields.Selection(_get_available_filters, string='Inventory of', required=True, default='none',
        help="If you do an entire inventory, you can choose 'All Products' and it will prefill the inventory with the current stock.  If you only do some products  "\
        "(e.g. Cycle Counting) you can choose 'Manual Selection of Products' and the system won't propose anything.  You can also let the "\
        "system propose for a single product / lot /... ")
    total_qty = fields.Float(compute="_get_total_qty")

    @api.multi
    def reset_real_qty(self):
        self.line_ids.write({'product_qty': 0})
        return True

    @api.multi
    def action_done(self):
        """ Finish the inventory
        @return: True
        """
        for inv in self:
            for inventory_line in inv.line_ids:
                if inventory_line.product_qty < 0 and inventory_line.product_qty != inventory_line.theoretical_qty:
                    raise UserError(_('You cannot set a negative product quantity in an inventory line:\n\t%s - qty: %s' % (inventory_line.product_id.name, inventory_line.product_qty)))
            inv.action_check()
            inv.write({'state': 'done'})
            self.post_inventory(inv)
        return True

    @api.model
    def post_inventory(self, inv):
        inv.move_ids.filtered(lambda x: x.state != 'done').action_done()

    @api.multi
    def action_check(self):
        """ Checks the inventory and computes the stock move to do
        @return: True
        """
        for inventory in self:
            #first remove the existing stock moves linked to this inventory
            inventory.move_ids.unlink()
            for line in inventory.line_ids:
                #compare the checked quantities on inventory lines to the theorical one
                # self.env['stock.inventory.line']._resolve_inventory_line(line)
                line._resolve_inventory_line()

    @api.multi
    def action_cancel_draft(self):
        """ Cancels the stock move and change inventory state to draft.
        @return: True
        """
        for inv in self:
            inv.write({'line_ids': [(5,)]})
            inv.move_ids.action_cancel()
            inv.write({'state': 'draft'})
        return True

    @api.multi
    def action_cancel_inventory(self):
        self.action_cancel_draft()

    @api.multi
    def prepare_inventory(self):
        inventory_line_obj = self.env['stock.inventory.line']
        for inventory in self:
            # If there are inventory lines already (e.g. from import), respect those and set their theoretical qty
            line_ids = [line.id for line in inventory.line_ids]
            if not line_ids and inventory.filter != 'partial':
                #compute the inventory lines and create them
                vals = inventory._get_inventory_lines()
                for product_line in vals:
                    inventory_line_obj.create(product_line)
        return self.write({'state': 'confirm', 'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})

    @api.multi
    def _get_inventory_lines(self):
        location_obj = self.env['stock.location']
        product_obj = self.env['product.product']
        location_ids = location_obj.search([('id', 'child_of', [self.location_id.ids])]).ids
        domain = ' location_id in %s'
        args = (tuple(location_ids),)
        if self.partner_id:
            domain += ' and owner_id = %s'
            args += (self.partner_id.id,)
        if self.lot_id:
            domain += ' and lot_id = %s'
            args += (self.lot_id.id,)
        if self.product_id:
            domain += ' and product_id = %s'
            args += (self.product_id.id,)
        if self.package_id:
            domain += ' and package_id = %s'
            args += (self.package_id.id,)

        self.env.cr.execute('''
           SELECT product_id, sum(qty) as product_qty, location_id, lot_id as prod_lot_id, package_id, owner_id as partner_id
           FROM stock_quant WHERE''' + domain + '''
           GROUP BY product_id, location_id, lot_id, package_id, partner_id
        ''', args)
        vals = []
        for product_line in self.env.cr.dictfetchall():
            #replace the None the dictionary by False, because falsy values are tested later on
            for key, value in product_line.items():
                if not value:
                    product_line[key] = False
            product_line['inventory_id'] = self.id
            product_line['theoretical_qty'] = product_line['product_qty']
            if product_line['product_id']:
                product = product_obj.browse(product_line['product_id'])
                product_line['product_uom_id'] = product.uom_id.id
            vals.append(product_line)
        return vals

    @api.multi
    @api.constrains('filter', 'product_id', 'lot_id', 'partner_id', 'package_id')
    def _check_filter_product(self):
        for inventory in self:
            if inventory.filter == 'none' and inventory.product_id and inventory.location_id and inventory.lot_id:
                raise ValueError("The selected inventory options are not coherent.")
            if inventory.filter not in ('product', 'product_owner') and inventory.product_id:
                raise ValueError("The selected inventory options are not coherent.")
            if inventory.filter != 'lot' and inventory.lot_id:
                raise ValueError("The selected inventory options are not coherent.")
            if inventory.filter not in ('owner', 'product_owner') and inventory.partner_id:
                raise ValueError("The selected inventory options are not coherent.")
            if inventory.filter != 'pack' and inventory.package_id:
                raise ValueError("The selected inventory options are not coherent.")

    @api.onchange('filter')
    def onchange_filter(self):
        if self.filter not in ('product', 'product_owner'):
            self.product_id = False
        if self.filter != 'lot':
            self.lot = False
        if self.filter not in ('owner', 'product_owner'):
            self.partner_id = False
        if self.filter != 'pack':
            self.package_id = False

class StockInventoryLine(models.Model):
    _name = "stock.inventory.line"
    _description = "Inventory Line"
    _order = "inventory_id, location_name, product_code, product_name, prodlot_name"

    @api.multi
    @api.depends('product_id.name', 'product_id.default_code')
    def _get_product_name_change(self):
        return self.env['stock.inventory.line'].search([('product_id', 'in', self.ids)]).ids

    @api.multi
    @api.depends('location_id.name', 'location_id.active')
    def _get_location_change(self):
        return self.env['stock.inventory.line'].search([('location_id', 'in', self.ids)]).ids

    @api.multi
    @api.depends('prod_lot_id.name')
    def _get_prodlot_change(self):
        return self.env['stock.inventory.line'].search([('prod_lot_id', 'in', self.ids)]).ids

    @api.depends('product_uom_id')
    def _get_theoretical_qty(self):
        for line in self:
            quant_ids = line._get_quants()
            tot_qty = sum([x.qty for x in quant_ids])
            if line.product_uom_id and line.product_id.uom_id.id != line.product_uom_id.id:
                tot_qty = self.env["product.uom"]._compute_qty_obj(line.product_id.uom_id, tot_qty, line.product_uom_id)
            line.theoretical_qty = tot_qty

    inventory_id = fields.Many2one('stock.inventory', 'Inventory', ondelete='cascade', select=True)
    location_id = fields.Many2one('stock.location', 'Location', required=True, select=True)
    product_id = fields.Many2one('product.product', 'Product', required=True, select=True)
    package_id = fields.Many2one('stock.quant.package', 'Pack', select=True)
    product_uom_id = fields.Many2one('product.uom', 'Product Unit of Measure', required=True, default=lambda self=None: self.env.ref('product.product_uom_unit').id)
    product_qty = fields.Float('Checked Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), default=0)
    company_id = fields.Many2one(related='inventory_id.company_id', relation='res.company', string='Company', store=True, select=True, readonly=True)
    prod_lot_id = fields.Many2one('stock.production.lot', 'Serial Number', domain="[('product_id','=',product_id)]")
    state = fields.Selection(related='inventory_id.state', string='Status', readonly=True)
    theoretical_qty = fields.Float(compute="_get_theoretical_qty", digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True, string="Theoretical Quantity")
    partner_id = fields.Many2one('res.partner', 'Owner')
    product_name = fields.Char(related='product_id.name', string='Product Name', store=True)
    product_code = fields.Char(related='product_id.default_code', string='Product Code', store=True)
    # location_name = fields.Char(related='location_id.name', string='Location Name', store=True)
    location_name = fields.Char(related='location_id.complete_name', string='Location Name', store=True)
    prodlot_name = fields.Char(related='prod_lot_id.name', string='Serial Number Name', store=True)

    @api.model
    def create(self, values):
        product_obj = self.env['product.product']
        if 'product_id' in values and not 'product_uom_id' in values:
            values['product_uom_id'] = product_obj.browse(values.get('product_id')).uom_id.id
        return super(StockInventoryLine, self).create(values)

    @api.multi
    def _get_quants(self):
        quant_obj = self.env["stock.quant"]
        dom = [('company_id', '=', self.company_id.id), ('location_id', '=', self.location_id.id), ('lot_id', '=', self.prod_lot_id.id),
                        ('product_id', '=', self.product_id.id), ('owner_id', '=', self.partner_id.id), ('package_id', '=', self.package_id.id)]
        quants = quant_obj.search(dom)
        return quants

    @api.multi
    def onchange_createline(self, location_id=False, product_id=False, uom_id=False, package_id=False, prod_lot_id=False, partner_id=False, company_id=False):
        quant_obj = self.env["stock.quant"]
        uom_obj = self.env["product.uom"]
        res = {'value': {}}
        # If no UoM already put the default UoM of the product
        if product_id:
            product = self.env['product.product'].browse(product_id)
            uom = self.env['product.uom'].browse(uom_id)
            if product.uom_id.category_id.id != uom.category_id.id:
                res['value']['product_uom_id'] = product.uom_id.id
                res['domain'] = {'product_uom_id': [('category_id', '=', product.uom_id.category_id.id)]}
                uom_id = product.uom_id.id
        # Calculate theoretical quantity by searching the quants as in quants_get
        if product_id and location_id:
            product = self.env['product.product'].browse(product_id)
            if not company_id:
                company_id = self.env.user.company_id.id
            dom = [('company_id', '=', company_id), ('location_id', '=', location_id), ('lot_id', '=', prod_lot_id),
                        ('product_id', '=', product_id), ('owner_id', '=', partner_id), ('package_id', '=', package_id)]
            quants = quant_obj.search(dom)
            th_qty = sum([x.qty for x in quants])
            if product_id and uom_id and product.uom_id.id != uom_id:
                th_qty = uom_obj._compute_qty(product.uom_id.id, th_qty, uom_id)
            res['value']['theoretical_qty'] = th_qty
            res['value']['product_qty'] = th_qty
        return res

    @api.multi
    def _resolve_inventory_line(self):
        stock_move_obj = self.env['stock.move']
        quant_obj = self.env['stock.quant']
        diff = self.theoretical_qty - self.product_qty
        if not diff:
            return
        #each theorical_lines where difference between theoretical and checked quantities is not 0 is a line for which we need to create a stock move
        vals = {
            'name': _('INV:') + (self.inventory_id.name or ''),
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'date': self.inventory_id.date,
            'company_id': self.inventory_id.company_id.id,
            'inventory_id': self.inventory_id.id,
            'state': 'confirmed',
            'restrict_lot_id': self.prod_lot_id.id,
            'restrict_partner_id': self.partner_id.id,
        }
        inventory_location_id = self.product_id.property_stock_inventory.id
        if diff < 0:
            #found more than expected
            vals['location_id'] = inventory_location_id
            vals['location_dest_id'] = self.location_id.id
            vals['product_uom_qty'] = -diff
        else:
            #found less than expected
            vals['location_id'] = self.location_id.id
            vals['location_dest_id'] = inventory_location_id
            vals['product_uom_qty'] = diff
        move = stock_move_obj.create(vals)
        # move = stock_move_obj.browse(cr, uid, move_id, context=context)
        if diff > 0:
            domain = [('qty', '>', 0.0), ('package_id', '=', self.package_id.id), ('lot_id', '=', self.prod_lot_id.id), ('location_id', '=', self.location_id.id)]
            preferred_domain_list = [[('reservation_id', '=', False)], [('reservation_id.inventory_id', '!=', self.inventory_id.id)]]
            quants = quant_obj.quants_get_preferred_domain(move.product_qty, move, domain=domain, preferred_domain_list=preferred_domain_list)
            quant_obj.quants_reserve(quants, move)
        elif self.package_id:
            move.action_done()
            quants = move.quant_ids
            quants.write({'package_id': self.package_id.id})
            res = quant_obj.search([('qty', '<', 0.0), ('product_id', '=', move.product_id.id),
                                    ('location_id', '=', move.location_dest_id.id), ('package_id', '!=', False)], limit=1)
            if res:
                for quant in move.quant_ids:
                    if quant.location_id.id == move.location_dest_id.id:  # To avoid we take a quant that was reconcile already
                        quant_obj._quant_reconcile_negative(quant, move)
        return move

    # Should be left out in next version
    @api.multi
    @api.onchange('theoretical_qty')
    def restrict_change(self):
        return {}

    @api.multi
    @api.onchange('product_id', 'theoretical_qty', 'product_uom_id')
    def on_change_product_id(self):
        """ Changes UoM
        @param location_id: Location id
        @param product: Changed product_id
        @param uom: UoM product
        @return:  Dictionary of changed values
        """
        if not self.product_id:
            return {'value': {'product_uom_id': False}}
        return {'value': {'product_uom_id': self.product_uom_id or self.product_id.uom_id.id}}



#----------------------------------------------------------
# Stock Warehouse
#----------------------------------------------------------
class StockWarehouse(models.Model):
    _name = "stock.warehouse"
    _description = "Warehouse"

    name = fields.Char('Warehouse Name', required=True, select=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, readonly=True, select=True, default=lambda self: self.env.user.company_id)
    partner_id = fields.Many2one('res.partner', 'Address')
    view_location_id = fields.Many2one('stock.location', 'View Location', required=True, domain=[('usage', '=', 'view')])
    lot_stock_id = fields.Many2one('stock.location', 'Location Stock', domain=[('usage', '=', 'internal')], required=True)
    code = fields.Char('Short Name', size=5, required=True, help="Short name used to identify your warehouse")
    route_ids = fields.Many2many('stock.location.route', 'stock_route_warehouse', 'warehouse_id', 'route_id', 'Routes', domain="[('warehouse_selectable', '=', True)]", help='Defaults routes through the warehouse')
    reception_steps = fields.Selection([
        ('one_step', 'Receive goods directly in stock (1 step)'),
        ('two_steps', 'Unload in input location then go to stock (2 steps)'),
        ('three_steps', 'Unload in input location, go through a quality control before being admitted in stock (3 steps)')], 'Incoming Shipments',
        help="Default incoming route to follow", required=True, default='one_step')
    delivery_steps = fields.Selection([
        ('ship_only', 'Ship directly from stock (Ship only)'),
        ('pick_ship', 'Bring goods to output location before shipping (Pick + Ship)'),
        ('pick_pack_ship', 'Make packages into a dedicated location, then bring them to the output location for shipping (Pick + Pack + Ship)')], 'Outgoing Shippings',
        help="Default outgoing route to follow", required=True, default='ship_only')
    wh_input_stock_loc_id = fields.Many2one('stock.location', 'Input Location')
    wh_qc_stock_loc_id = fields.Many2one('stock.location', 'Quality Control Location')
    wh_output_stock_loc_id = fields.Many2one('stock.location', 'Output Location')
    wh_pack_stock_loc_id = fields.Many2one('stock.location', 'Packing Location')
    mto_pull_id = fields.Many2one('procurement.rule', 'MTO rule')
    pick_type_id = fields.Many2one('stock.picking.type', 'Pick Type')
    pack_type_id = fields.Many2one('stock.picking.type', 'Pack Type')
    out_type_id = fields.Many2one('stock.picking.type', 'Out Type')
    in_type_id = fields.Many2one('stock.picking.type', 'In Type')
    int_type_id = fields.Many2one('stock.picking.type', 'Internal Type')
    crossdock_route_id = fields.Many2one('stock.location.route', 'Crossdock Route')
    reception_route_id = fields.Many2one('stock.location.route', 'Receipt Route')
    delivery_route_id = fields.Many2one('stock.location.route', 'Delivery Route')
    resupply_from_wh = fields.Boolean('Resupply From Other Warehouses', help='Unused field')
    resupply_wh_ids = fields.Many2many('stock.warehouse', 'stock_wh_resupply_table', 'supplied_wh_id', 'supplier_wh_id', 'Resupply Warehouses')
    resupply_route_ids = fields.One2many('stock.location.route', 'supplied_wh_id', 'Resupply Routes',
        help="Routes will be created for these resupply warehouses and you can select them on products and product categories")
    default_resupply_wh_id = fields.Many2one('stock.warehouse', 'Default Resupply Warehouse', help="Goods will always be resupplied from this warehouse")

    @api.multi
    @api.onchange('default_resupply_wh_id', 'resupply_wh_ids')
    def onchange_filter_default_resupply_wh_id(self):
        resupply_wh_ids = set([x['id'] for x in (self.resolve_2many_commands('resupply_wh_ids', self.resupply_wh_ids, ['id']))])
        if self.default_resupply_wh_id:  # If we are removing the default resupply, we don't have default_resupply_wh_id
            resupply_wh_ids.add(self.default_resupply_wh_id)
        resupply_wh_ids = list(resupply_wh_ids)
        return {'value': {'resupply_wh_ids': resupply_wh_ids}}

    @api.multi
    def _get_external_transit_location(self):
        ''' returns browse record of inter company transit location, if found'''
        try:
            inter_wh_loc = self.env.ref('stock.stock_location_inter_wh')
        except:
            return False
        return inter_wh_loc

    @api.multi
    def _get_inter_wh_route(self, wh):
        return {
            'name': _('%s: Supply Product from %s') % (self.name, wh.name),
            'warehouse_selectable': False,
            'product_selectable': True,
            'product_categ_selectable': True,
            'supplied_wh_id': self.id,
            'supplier_wh_id': wh.id,
        }

    @api.multi
    def _create_resupply_routes(self, supplier_warehouses, default_resupply_wh):
        route_obj = self.env['stock.location.route']
        pull_obj = self.env['procurement.rule']
        # warehouse
        #create route selectable on the product to resupply the warehouse from another one
        external_transit_location = self._get_external_transit_location()
        internal_transit_location = self.company_id.internal_transit_location_id
        input_loc = self.wh_input_stock_loc_id
        if self.reception_steps == 'one_step':
            input_loc = self.lot_stock_id
        for wh in supplier_warehouses:
            transit_location = wh.company_id.id == self.company_id.id and internal_transit_location or external_transit_location
            if transit_location:
                output_loc = wh.wh_output_stock_loc_id
                if wh.delivery_steps == 'ship_only':
                    output_loc = wh.lot_stock_id
                    # Create extra MTO rule (only for 'ship only' because in the other cases MTO rules already exists)
                    mto_pull_vals = wh._get_mto_pull_rule([(output_loc, transit_location, wh.out_type_id.id)])[0]
                    pull_obj.create(mto_pull_vals)
                inter_wh_route_vals = self._get_inter_wh_route(wh)
                inter_wh_route_id = route_obj.create(vals=inter_wh_route_vals)
                values = [(output_loc, transit_location, wh.out_type_id.id, wh), (transit_location, input_loc, self.in_type_id.id, self)]
                pull_rules_list = wh._get_supply_pull_rules(values, inter_wh_route_id)
                for pull_rule in pull_rules_list:
                    pull_obj.create(vals=pull_rule)
                #if the warehouse is also set as default resupply method, assign this route automatically to the warehouse
                if default_resupply_wh and default_resupply_wh.id == wh.id:
                    self.write({'route_ids': [(4, inter_wh_route_id.id)]})
                    wh.write({'route_ids': [(4, inter_wh_route_id.id)]})

    _sql_constraints = [
        ('warehouse_name_uniq', 'unique(name, company_id)', 'The name of the warehouse must be unique per company!'),
        ('warehouse_code_uniq', 'unique(code, company_id)', 'The code of the warehouse must be unique per company!'),
    ]

    @api.multi
    def _get_partner_locations(self):
        ''' returns a tuple made of the browse record of customer location and the browse record of supplier location'''
        location_obj = self.env['stock.location']
        try:
            customer_loc = self.env.ref('stock.stock_location_customers').id
            supplier_loc = self.env.ref('stock.stock_location_suppliers').id
        except:
            customer_loc = location_obj.search([('usage', '=', 'customer')])
            customer_loc = customer_loc and customer_loc[0] or False
            supplier_loc = location_obj.search([('usage', '=', 'supplier')])
            supplier_loc = supplier_loc and supplier_loc[0] or False
        if not (customer_loc and supplier_loc):
            raise UserError(_('Can\'t find any customer or supplier location.'))
        return location_obj.browse([customer_loc, supplier_loc])

    @api.model
    def _location_used(self, location_id, warehouse):
        pull_obj = self.env['procurement.rule']
        push_obj = self.env['stock.location.path']

        domain = ['&', ('route_id', 'not in', [x.id for x in warehouse.route_ids]),
                       '|', ('location_src_id', '=', location_id),                      # noqa
                            ('location_id', '=', location_id)
                  ]
        pulls = pull_obj.search_count(domain)

        domain = ['&', ('route_id', 'not in', [x.id for x in warehouse.route_ids]),
                       '|', ('location_from_id', '=', location_id),                     # noqa
                            ('location_dest_id', '=', location_id)
                  ]
        pushs = push_obj.search_count(domain)
        if pulls or pushs:
            return True
        return False

    @api.multi
    def switch_location(self, warehouse, new_reception_step=False, new_delivery_step=False):
        new_reception_step = new_reception_step or warehouse.reception_steps
        new_delivery_step = new_delivery_step or warehouse.delivery_steps
        if warehouse.reception_steps != new_reception_step:
            if not self._location_used(warehouse.wh_input_stock_loc_id.id, warehouse):
                warehouse.wh_input_stock_loc_id.write({'active': False})
                warehouse.wh_qc_stock_loc_id.write({'active': False})
            if new_reception_step != 'one_step':
                warehouse.wh_input_stock_loc_id.write({'active': True})
            if new_reception_step == 'three_steps':
                warehouse.wh_qc_stock_loc_id.write({'active': True})

        if warehouse.delivery_steps != new_delivery_step:
            if not self._location_used(warehouse.wh_output_stock_loc_id.id, warehouse):
                warehouse.wh_output_stock_loc_id.write({'active': False})
            if not self._location_used(warehouse.wh_pack_stock_loc_id.id, warehouse):
                warehouse.wh_pack_stock_loc_id.write({'active': False})
            if new_delivery_step != 'ship_only':
                warehouse.wh_output_stock_loc_id.write({'active': True})
            if new_delivery_step == 'pick_pack_ship':
                warehouse.wh_pack_stock_loc_id.write({'active': True})
        return True

    @api.model
    def _get_reception_delivery_route(self, warehouse, route_name):
        return {
            'name': self._format_routename(warehouse, route_name),
            'product_categ_selectable': True,
            'product_selectable': False,
            'sequence': 10,
        }

    @api.multi
    def _get_supply_pull_rules(self, values, new_route_id):
        pull_rules_list = []
        for from_loc, dest_loc, pick_type_id, warehouse in values:
            pull_rules_list.append({
                'name': warehouse._format_rulename(from_loc, dest_loc),
                'location_src_id': from_loc.id,
                'location_id': dest_loc.id,
                'route_id': new_route_id.id,
                'action': 'move',
                'picking_type_id': pick_type_id,
                'procure_method': warehouse.lot_stock_id.id != from_loc.id and 'make_to_order' or 'make_to_stock',  # first part of the resuply route is MTS
                'warehouse_id': warehouse.id,
                'propagate_warehouse_id': self.id,
            })
        return pull_rules_list

    @api.multi
    def _get_push_pull_rules(self, active, values, new_route_id):
        first_rule = True
        push_rules_list = []
        pull_rules_list = []
        for from_loc, dest_loc, pick_type_id in values:
            push_rules_list.append({
                'name': self._format_rulename(from_loc, dest_loc),
                'location_from_id': from_loc.id,
                'location_dest_id': dest_loc.id,
                'route_id': new_route_id.id,
                'auto': 'manual',
                'picking_type_id': pick_type_id,
                'active': active,
                'warehouse_id': self.id,
            })
            pull_rules_list.append({
                'name': self._format_rulename(from_loc, dest_loc),
                'location_src_id': from_loc.id,
                'location_id': dest_loc.id,
                'route_id': new_route_id.id,
                'action': 'move',
                'picking_type_id': pick_type_id,
                'procure_method': first_rule is True and 'make_to_stock' or 'make_to_order',
                'active': active,
                'warehouse_id': self.id,
            })
            first_rule = False
        return push_rules_list, pull_rules_list

    @api.model
    def _get_mto_route(self):
        route_obj = self.env['stock.location.route']
        try:
            mto_route_id = self.env.ref('stock.route_warehouse0_mto').id
        except:
            mto_route_id = route_obj.search([('name', 'like', _('Make To Order'))])
            mto_route_id = mto_route_id and mto_route_id[0] or False
        if not mto_route_id:
            raise UserError(_('Can\'t find any generic Make To Order route.'))
        return mto_route_id

    @api.multi
    def _check_remove_mto_resupply_rules(self):
        """ Checks that the moves from the different """
        pull_obj = self.env['procurement.rule']
        mto_route_id = self._get_mto_route()
        rules = pull_obj.search(['&', ('location_src_id', '=', self.lot_stock_id.id), ('location_id.usage', '=', 'transit')])
        rules.unlink()

    @api.multi
    def _get_mto_pull_rule(self, values):
        mto_route_id = self._get_mto_route()
        res = []
        for value in values:
            from_loc, dest_loc, pick_type_id = value
            res += [{
                'name': self._format_rulename(from_loc, dest_loc) + _(' MTO'),
                'location_src_id': from_loc.id,
                'location_id': dest_loc.id,
                'route_id': mto_route_id,
                'action': 'move',
                'picking_type_id': pick_type_id,
                'procure_method': 'make_to_order',
                'active': True,
                'warehouse_id': self.id,
            }]
        return res

    @api.model
    def _get_crossdock_route(self, warehouse, route_name):
        return {
            'name': self._format_routename(warehouse, route_name),
            'warehouse_selectable': False,
            'product_selectable': True,
            'product_categ_selectable': True,
            'active': self.delivery_steps != 'ship_only' and self.reception_steps != 'one_step',
            'sequence': 20,
        }

    @api.multi
    def create_routes(self, warehouse):
        wh_route_ids = []
        route_obj = self.env['stock.location.route']
        pull_obj = self.env['procurement.rule']
        push_obj = self.env['stock.location.path']
        routes_dict = self.get_routes_dict(warehouse)
        #create reception route and rules
        route_name, values = routes_dict[warehouse.reception_steps]
        route_vals = self._get_reception_delivery_route(warehouse, route_name)
        reception_route_id = route_obj.create(route_vals)
        wh_route_ids.append((4, reception_route_id.id))
        push_rules_list, pull_rules_list = warehouse._get_push_pull_rules(True, values, reception_route_id)
        #create the push/procurement rules
        for push_rule in push_rules_list:
            push_obj.create(vals=push_rule)
        for pull_rule in pull_rules_list:
            #all procurement rules in reception route are mto, because we don't want to wait for the scheduler to trigger an orderpoint on input location
            pull_rule['procure_method'] = 'make_to_order'
            pull_obj.create(vals=pull_rule)

        #create MTS route and procurement rules for delivery and a specific route MTO to be set on the product
        route_name, values = routes_dict[warehouse.delivery_steps]
        route_vals = self._get_reception_delivery_route(warehouse, route_name)
        #create the route and its procurement rules
        delivery_route_id = route_obj.create(route_vals)
        wh_route_ids.append((4, delivery_route_id.id))
        dummy, pull_rules_list = warehouse._get_push_pull_rules(True, values, delivery_route_id)
        for pull_rule in pull_rules_list:
            pull_obj.create(vals=pull_rule)
        #create MTO procurement rule and link it to the generic MTO route
        mto_pull_vals = warehouse._get_mto_pull_rule(values)[0]
        mto_pull_id = pull_obj.create(mto_pull_vals)

        #create a route for cross dock operations, that can be set on products and product categories
        route_name, values = routes_dict['crossdock']
        crossdock_route_vals = self._get_crossdock_route(warehouse, route_name)
        crossdock_route_id = route_obj.create(vals=crossdock_route_vals)
        wh_route_ids.append((4, crossdock_route_id.id))
        dummy, pull_rules_list = warehouse._get_push_pull_rules(warehouse.delivery_steps != 'ship_only' and warehouse.reception_steps != 'one_step', values, crossdock_route_id)
        for pull_rule in pull_rules_list:
            # Fixed cross-dock is logically mto
            pull_rule['procure_method'] = 'make_to_order'
            pull_obj.create(vals=pull_rule)

        #create route selectable on the product to resupply the warehouse from another one
        warehouse._create_resupply_routes(warehouse.resupply_wh_ids, warehouse.default_resupply_wh_id)

        #return routes and mto procurement rule to store on the warehouse
        return {
            'route_ids': wh_route_ids,
            'mto_pull_id': mto_pull_id.id,
            'reception_route_id': reception_route_id.id,
            'delivery_route_id': delivery_route_id.id,
            'crossdock_route_id': crossdock_route_id.id,
        }

    @api.multi
    def create_sequences_and_picking_types(self):
        seq_obj = self.env['ir.sequence']
        picking_type_obj = self.env['stock.picking.type']
        #create new sequences
        in_seq_id = seq_obj.sudo().create({'name': self.name + _(' Sequence in'), 'prefix': self.code + '/IN/', 'padding': 5}).id
        out_seq_id = seq_obj.sudo().create({'name': self.name + _(' Sequence out'), 'prefix': self.code + '/OUT/', 'padding': 5}).id
        pack_seq_id = seq_obj.sudo().create({'name': self.name + _(' Sequence packing'), 'prefix': self.code + '/PACK/', 'padding': 5}).id
        pick_seq_id = seq_obj.sudo().create({'name': self.name + _(' Sequence picking'), 'prefix': self.code + '/PICK/', 'padding': 5}).id
        int_seq_id = seq_obj.sudo().create({'name': self.name + _(' Sequence internal'), 'prefix': self.code + '/INT/', 'padding': 5}).id

        wh_stock_loc = self.lot_stock_id
        wh_input_stock_loc = self.wh_input_stock_loc_id
        wh_output_stock_loc = self.wh_output_stock_loc_id
        wh_pack_stock_loc = self.wh_pack_stock_loc_id

        #fetch customer and supplier locations, for references
        customer_loc, supplier_loc = self._get_partner_locations()

        #create in, out, internal picking types for warehouse
        input_loc = wh_input_stock_loc
        if self.reception_steps == 'one_step':
            input_loc = wh_stock_loc
        output_loc = wh_output_stock_loc
        if self.delivery_steps == 'ship_only':
            output_loc = wh_stock_loc

        #choose the next available color for the picking types of this warehouse
        color = 0
        available_colors = [c % 9 for c in range(3, 12)]  # put flashy colors first
        all_used_colors = self.env['stock.picking.type'].search_read([('warehouse_id', '!=', False), ('color', '!=', False)], ['color'], order='color')
        #don't use sets to preserve the list order
        for x in all_used_colors:
            if x['color'] in available_colors:
                available_colors.remove(x['color'])
        if available_colors:
            color = available_colors[0]

        #order the picking types with a sequence allowing to have the following suit for each warehouse: reception, internal, pick, pack, ship.
        max_sequence = self.env['stock.picking.type'].search_read([], ['sequence'], order='sequence desc')
        max_sequence = max_sequence and max_sequence[0]['sequence'] or 0

        in_type_id = picking_type_obj.create(vals={
            'name': _('Receipts'),
            'warehouse_id': self.id,
            'code': 'incoming',
            'use_create_lots': True,
            'use_existing_lots': False,
            'sequence_id': in_seq_id,
            'default_location_src_id': supplier_loc.id,
            'default_location_dest_id': input_loc.id,
            'sequence': max_sequence + 1,
            'color': color})
        out_type_id = picking_type_obj.create(vals={
            'name': _('Delivery Orders'),
            'warehouse_id': self.id,
            'code': 'outgoing',
            'use_create_lots': False,
            'use_existing_lots': True,
            'sequence_id': out_seq_id,
            'return_picking_type_id': in_type_id.id,
            'default_location_src_id': output_loc.id,
            'default_location_dest_id': customer_loc.id,
            'sequence': max_sequence + 4,
            'color': color})
        in_type_id.write({'return_picking_type_id': out_type_id.id})
        int_type_id = picking_type_obj.create(vals={
            'name': _('Internal Transfers'),
            'warehouse_id': self.id,
            'code': 'internal',
            'use_create_lots': False,
            'use_existing_lots': True,
            'sequence_id': int_seq_id,
            'default_location_src_id': wh_stock_loc.id,
            'default_location_dest_id': wh_stock_loc.id,
            'active': True,
            'sequence': max_sequence + 2,
            'color': color})

        pack_type_id = picking_type_obj.create(vals={
            'name': _('Pack'),
            'warehouse_id': self.id,
            'code': 'internal',
            'use_create_lots': False,
            'use_existing_lots': True,
            'sequence_id': pack_seq_id,
            'default_location_src_id': wh_pack_stock_loc.id,
            'default_location_dest_id': output_loc.id,
            'active': self.delivery_steps == 'pick_pack_ship',
            'sequence': max_sequence + 3,
            'color': color})
        pick_type_id = picking_type_obj.create(vals={
            'name': _('Pick'),
            'warehouse_id': self.id,
            'code': 'internal',
            'use_create_lots': False,
            'use_existing_lots': True,
            'sequence_id': pick_seq_id,
            'default_location_src_id': wh_stock_loc.id,
            'default_location_dest_id': output_loc.id if self.delivery_steps == 'pick_ship' else wh_pack_stock_loc.id,
            'active': self.delivery_steps != 'ship_only',
            'sequence': max_sequence + 2,
            'color': color})

        #write picking types on WH
        vals = {
            'in_type_id': in_type_id.id,
            'out_type_id': out_type_id.id,
            'pack_type_id': pack_type_id.id,
            'pick_type_id': pick_type_id.id,
            'int_type_id': int_type_id.id,
        }
        super(StockWarehouse, self).write(vals=vals)

    @api.model
    def create(self, vals):
        if vals is None:
            vals = {}
        location_obj = self.env['stock.location']

        #create view location for warehouse
        loc_vals = {
                'name': _(vals.get('code')),
                'usage': 'view',
                'location_id': self.env.ref('stock.stock_location_locations').id,
        }
        if vals.get('company_id'):
            loc_vals['company_id'] = vals.get('company_id')
        wh_loc_id = location_obj.create(loc_vals)
        vals['view_location_id'] = wh_loc_id.id
        #create all location
        def_values = self.default_get({'reception_steps', 'delivery_steps'})
        reception_steps = vals.get('reception_steps',  def_values['reception_steps'])
        delivery_steps = vals.get('delivery_steps', def_values['delivery_steps'])
        # context_with_inactive = context.copy()
        # context_with_inactive['active_test'] = False
        # self.with_context(active_test=False)
        sub_locations = [
            {'name': _('Stock'), 'active': True, 'field': 'lot_stock_id'},
            {'name': _('Input'), 'active': reception_steps != 'one_step', 'field': 'wh_input_stock_loc_id'},
            {'name': _('Quality Control'), 'active': reception_steps == 'three_steps', 'field': 'wh_qc_stock_loc_id'},
            {'name': _('Output'), 'active': delivery_steps != 'ship_only', 'field': 'wh_output_stock_loc_id'},
            {'name': _('Packing Zone'), 'active': delivery_steps == 'pick_pack_ship', 'field': 'wh_pack_stock_loc_id'},
        ]
        for values in sub_locations:
            loc_vals = {
                'name': values['name'],
                'usage': 'internal',
                'location_id': wh_loc_id.id,
                'active': values['active'],
            }
            if vals.get('company_id'):
                loc_vals['company_id'] = vals.get('company_id')
            location_id = location_obj.with_context(active_test=False).create(loc_vals)
            vals[values['field']] = location_id.id

        #create WH
        new_id = super(StockWarehouse, self).create(vals)
        warehouse = new_id
        warehouse.create_sequences_and_picking_types()

        #create routes and push/procurement rules
        new_objects_dict = new_id.create_routes(warehouse)
        warehouse.write(new_objects_dict)

        if vals.get('partner_id'):
            comp_obj = self.env['res.company']
            if vals.get('company_id'):
                transit_loc = comp_obj.browse(vals.get('company_id')).internal_transit_location_id.id
            else:
                # transit_loc = comp_obj._company_default_get('stock.warehouse').internal_transit_location_id
                transit_loc = comp_obj.browse(comp_obj._model._company_default_get(self._cr, self._uid, 'stock.picking', context=self._context)).internal_transit_location_id.id
            partner = self.env['res.partner'].browse(vals['partner_id'])
            partner.write({'property_stock_customer': transit_loc,
                'property_stock_supplier': transit_loc})
        return new_id

    @api.multi
    def _format_rulename(self, from_loc, dest_loc):
        return self.code + ': ' + from_loc.name + ' -> ' + dest_loc.name

    @api.model
    def _format_routename(self, obj, name):
        return obj.name + ': ' + name

    @api.multi
    def get_routes_dict(self, warehouse):
        #fetch customer and supplier locations, for references
        customer_loc, supplier_loc = self._get_partner_locations()

        return {
            'one_step': (_('Receipt in 1 step'), []),
            'two_steps': (_('Receipt in 2 steps'), [(warehouse.wh_input_stock_loc_id, warehouse.lot_stock_id, warehouse.int_type_id.id)]),
            'three_steps': (_('Receipt in 3 steps'), [(warehouse.wh_input_stock_loc_id, warehouse.wh_qc_stock_loc_id, warehouse.int_type_id.id), (warehouse.wh_qc_stock_loc_id, warehouse.lot_stock_id, warehouse.int_type_id.id)]),
            'crossdock': (_('Cross-Dock'), [(warehouse.wh_input_stock_loc_id, warehouse.wh_output_stock_loc_id, warehouse.int_type_id.id), (warehouse.wh_output_stock_loc_id, customer_loc, warehouse.out_type_id.id)]),
            'ship_only': (_('Ship Only'), [(warehouse.lot_stock_id, customer_loc, warehouse.out_type_id.id)]),
            'pick_ship': (_('Pick + Ship'), [(warehouse.lot_stock_id, warehouse.wh_output_stock_loc_id, warehouse.pick_type_id.id), (warehouse.wh_output_stock_loc_id, customer_loc, warehouse.out_type_id.id)]),
            'pick_pack_ship': (_('Pick + Pack + Ship'), [(warehouse.lot_stock_id, warehouse.wh_pack_stock_loc_id, warehouse.pick_type_id.id), (warehouse.wh_pack_stock_loc_id, warehouse.wh_output_stock_loc_id, warehouse.pack_type_id.id), (warehouse.wh_output_stock_loc_id, customer_loc, warehouse.out_type_id.id)]),
        }

    @api.model
    def _handle_renaming(self, warehouse, name, code):
        #rename location
        location_id = self.lot_stock_id.location_id
        location_id.write({'name': code})
        #rename route and push-procurement rules
        for route in self.route_ids:
            route.write({'name': route.name.replace(self.name, name, 1)})
            for pull in route.pull_ids:
                pull.write({'name': pull.name.replace(self.name, name, 1)})
            for push in route.push_ids:
                push.write({'name': pull.name.replace(self.name, name, 1)})
        #change the mto procurement rule name
        if self.mto_pull_id.id:
            self.mto_pull_id.write({'name': self.mto_pull_id.name.replace(self.name, name, 1)})

    @api.multi
    def _check_delivery_resupply(self, new_location, change_to_multiple):
        """ Will check if the resupply routes from this warehouse follow the changes of number of delivery steps """
        #Check routes that are being delivered by this warehouse and change the rule going to transit location
        route_obj = self.env["stock.location.route"]
        pull_obj = self.env["procurement.rule"]
        routes = route_obj.search([('supplier_wh_id', '=', self.id)])
        pulls = pull_obj.search(['&', ('route_id', 'in', routes), ('location_id.usage', '=', 'transit')])
        if pulls:
            pulls.write({'location_src_id': new_location, 'procure_method': change_to_multiple and "make_to_order" or "make_to_stock"})
        # Create or clean MTO rules
        mto_route_id = self._get_mto_route()
        if not change_to_multiple:
            # If single delivery we should create the necessary MTO rules for the resupply
            # pulls = pull_obj.search(cr, uid, ['&', ('route_id', '=', mto_route_id), ('location_id.usage', '=', 'transit'), ('location_src_id', '=', warehouse.lot_stock_id.id)], context=context)
            pull_recs = pulls
            transfer_locs = list(set([x.location_id for x in pull_recs]))
            vals = [(self.lot_stock_id, x, self.out_type_id.id) for x in transfer_locs]
            mto_pull_vals = self._get_mto_pull_rule(vals)
            for mto_pull_val in mto_pull_vals:
                pull_obj.create(mto_pull_val)
        else:
            # We need to delete all the MTO procurement rules, otherwise they risk to be used in the system
            pulls = pull_obj.search(['&', ('route_id', '=', mto_route_id), ('location_id.usage', '=', 'transit'), ('location_src_id', '=', self.lot_stock_id.id)])
            if pulls:
                pulls.unlink()

    @api.multi
    def _check_reception_resupply(self, new_location):
        """
            Will check if the resupply routes to this warehouse follow the changes of number of receipt steps
        """
        #Check routes that are being delivered by this warehouse and change the rule coming from transit location
        route_obj = self.env["stock.location.route"]
        pull_obj = self.env["procurement.rule"]
        routes = route_obj.search([('supplied_wh_id', '=', self.id)])
        pulls = pull_obj.search(['&', ('route_id', 'in', routes.ids), ('location_src_id.usage', '=', 'transit')])
        if pulls:
            pulls.write({'location_id': new_location})

    @api.multi
    def _check_resupply(self, reception_new, delivery_new):
        if reception_new:
            old_val = self.reception_steps
            new_val = reception_new
            change_to_one = (old_val != 'one_step' and new_val == 'one_step')
            change_to_multiple = (old_val == 'one_step' and new_val != 'one_step')
            if change_to_one or change_to_multiple:
                new_location = change_to_one and self.lot_stock_id.id or self.wh_input_stock_loc_id.id
                self._check_reception_resupply(new_location)
        if delivery_new:
            old_val = self.delivery_steps
            new_val = delivery_new
            change_to_one = (old_val != 'ship_only' and new_val == 'ship_only')
            change_to_multiple = (old_val == 'ship_only' and new_val != 'ship_only')
            if change_to_one or change_to_multiple:
                new_location = change_to_one and self.lot_stock_id.id or self.wh_output_stock_loc_id.id
                self._check_delivery_resupply(new_location, change_to_multiple)

    @api.multi
    def write(self, vals):
        route_obj = self.env['stock.location.route']
        # context_with_inactive = context.copy()
        # context_with_inactive['active_test'] = False
        for warehouse in self:
            #first of all, check if we need to delete and recreate route
            if vals.get('reception_steps') or vals.get('delivery_steps'):
                #activate and deactivate location according to reception and delivery option
                warehouse.switch_location(warehouse, vals.get('reception_steps', False), vals.get('delivery_steps', False))
                # switch between route
                warehouse.with_context(active_test=False).change_route(warehouse, vals.get('reception_steps', False), vals.get('delivery_steps', False))
                # Check if we need to change something to resupply warehouses and associated MTO rules
                warehouse._check_resupply(vals.get('reception_steps'), vals.get('delivery_steps'))
            if vals.get('code') or vals.get('name'):
                name = warehouse.name
                #rename sequence
                if vals.get('name'):
                    name = vals.get('name', warehouse.name)
                warehouse.with_context(active_test=False)._handle_renaming(name, vals.get('code'), warehouse.code)
                if warehouse.in_type_id:
                    warehouse.in_type_id.sequence_id.write({'name': name + _(' Sequence in'), 'prefix': vals.get('code', warehouse.code) + '\IN\\'})
                if warehouse.out_type_id:
                    warehouse.in_type_id.sequence_id.write({'name': name + _(' Sequence out'), 'prefix': vals.get('code', warehouse.code) + '\OUT\\'})
                if warehouse.pack_type_id:
                    warehouse.in_type_id.sequence_id.write({'name': name + _(' Sequence packing'), 'prefix': vals.get('code', warehouse.code) + '\PACK\\'})
                if warehouse.pick_type_id:
                    warehouse.in_type_id.sequence_id.write({'name': name + _(' Sequence picking'), 'prefix': vals.get('code', warehouse.code) + '\PICK\\'})
                if warehouse.int_type_id:
                    warehouse.in_type_id.sequence_id.write({'name': name + _(' Sequence internal'), 'prefix': vals.get('code', warehouse.code) + '\INT\\'})
        if vals.get('resupply_wh_ids') and not vals.get('resupply_route_ids'):
            for cmd in vals.get('resupply_wh_ids'):
                if cmd[0] == 6:
                    new_ids = set(cmd[2])
                    old_ids = set([wh.id for wh in warehouse.resupply_wh_ids])
                    to_add_wh_ids = new_ids - old_ids
                    if to_add_wh_ids:
                        supplier_warehouses = self.browse(list(to_add_wh_ids))
                        warehouse._create_resupply_routes(supplier_warehouses, warehouse.default_resupply_wh_id)
                    to_remove_wh_ids = old_ids - new_ids
                    if to_remove_wh_ids:
                        to_remove_route_ids = route_obj.search([('supplied_wh_id', '=', warehouse.id), ('supplier_wh_id', 'in', list(to_remove_wh_ids))])
                        if to_remove_route_ids:
                            to_remove_route = route_obj.browse(to_remove_route_ids)
                            to_remove_route.unlink()
                else:
                    #not implemented
                    pass
        if 'default_resupply_wh_id' in vals:
            if vals.get('default_resupply_wh_id') == warehouse.id:
                raise UserError(_('The default resupply warehouse should be different than the warehouse itself!'))
            if warehouse.default_resupply_wh_id:
                #remove the existing resupplying route on the warehouse
                to_remove_route_ids = route_obj.search([('supplied_wh_id', '=', warehouse.id), ('supplier_wh_id', '=', warehouse.default_resupply_wh_id.id)])
                for inter_wh_route_id in to_remove_route_ids:
                    warehouse.write({'route_ids': [(3, inter_wh_route_id.id)]})
            if vals.get('default_resupply_wh_id'):
                #assign the new resupplying route on all products
                to_assign_route_ids = route_obj.search([('supplied_wh_id', '=', warehouse.id), ('supplier_wh_id', '=', vals.get('default_resupply_wh_id'))])
                for inter_wh_route_id in to_assign_route_ids:
                    warehouse.write({'route_ids': [(4, inter_wh_route_id.id)]})

        # If another partner assigned
        if vals.get('partner_id'):
            if not vals.get('company_id'):
                company = self.company_id
            else:
                company = self.env['res.company'].browse(vals['company_id'])
            transit_loc = company.internal_transit_location_id.id
            self.env['res.partner'].browse([vals['partner_id']]).write({'property_stock_customer': transit_loc,
                                                                            'property_stock_supplier': transit_loc})
        return super(StockWarehouse, self).write(vals=vals)

    @api.multi
    def get_all_routes_for_wh(self):
        route_obj = self.env["stock.location.route"]
        all_routes = [route.id for route in self.route_ids]
        all_routes += route_obj.search([('supplied_wh_id', '=', self.id)])
        all_routes += [self.mto_pull_id.route_id.id]
        return all_routes

    @api.multi
    def view_all_routes_for_wh(self):
        all_routes = []
        for wh in self:
            all_routes += wh.get_all_routes_for_wh()

        domain = [('id', 'in', all_routes)]
        return {
            'name': _('Warehouse\'s Routes'),
            'domain': domain,
            'res_model': 'stock.location.route',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'limit': 20
        }

class StockLocationPath(models.Model):
    _name = "stock.location.path"
    _description = "Pushed Flows"
    _order = "name"

    @api.multi
    @api.depends('route_id.sequence')
    def _get_rules(self):
        res = []
        for route in self:
            res += [x.id for x in route.push_ids]
        return res

    name = fields.Char('Operation Name', required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    route_id = fields.Many2one('stock.location.route', 'Route')
    location_from_id = fields.Many2one('stock.location', 'Source Location', ondelete='cascade', select=1, required=True,
        help="This rule can be applied when a move is confirmed that has this location as destination location")
    location_dest_id = fields.Many2one('stock.location', 'Destination Location', ondelete='cascade', select=1, required=True,
        help="The new location where the goods need to go")
    delay = fields.Integer('Delay (days)', help="Number of days needed to transfer the goods", default=0)
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type', required=True,
        help="This is the picking type that will be put on the stock moves")
    auto = fields.Selection([('auto', 'Automatic Move'), ('manual', 'Manual Operation'), ('transparent', 'Automatic No Step Added')], 'Automatic Move', required=True, select=1, default='auto',
        help="The 'Automatic Move' / 'Manual Operation' value will create a stock move after the current one.  " \
             "With 'Automatic No Step Added', the location is replaced in the original move.")
    propagate = fields.Boolean('Propagate cancel and split', help='If checked, when the previous move is cancelled or split, the move generated by this move will too', default=True)
    active = fields.Boolean(default=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    route_sequence = fields.Integer(string='Route Sequence')
    sequence = fields.Integer()

    @api.model
    def _prepare_push_apply(self, rule, move,):
        newdate = (datetime.strptime(move.date_expected, DEFAULT_SERVER_DATETIME_FORMAT) + relativedelta.relativedelta(days=rule.delay or 0)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return {
                'origin': move.origin or move.picking_id.name or "/",
                'location_id': move.location_dest_id.id,
                'location_dest_id': rule.location_dest_id.id,
                'date': newdate,
                'company_id': rule.company_id and rule.company_id.id or False,
                'date_expected': newdate,
                'picking_id': False,
                'picking_type_id': rule.picking_type_id and rule.picking_type_id.id or False,
                'propagate': rule.propagate,
                'push_rule_id': rule.id,
                'warehouse_id': rule.warehouse_id and rule.warehouse_id.id or False,
            }

    @api.model
    def _apply(self, rule, move):
        newdate = (datetime.strptime(move.date_expected, DEFAULT_SERVER_DATETIME_FORMAT) + relativedelta.relativedelta(days=rule.delay or 0)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        if rule.auto == 'transparent':
            old_dest_location = move.location_dest_id.id
            move.write({
                'date': newdate,
                'date_expected': newdate,
                'location_dest_id': rule.location_dest_id.id
            })
            #avoid looping if a push rule is not well configured
            if rule.location_dest_id.id != old_dest_location:
                #call again push_apply to see if a next step is defined
                move._push_apply()
        else:
            vals = self._prepare_push_apply(rule, move)
            move_id = move.copy(vals)
            move.write({
                'move_dest_id': move_id,
            })
            move_id.action_confirm()


# -------------------------
# Packaging related stuff
# -------------------------
class StockPackage(models.Model):
    """
    These are the packages, containing quants and/or other packages
    """
    _name = "stock.quant.package"
    _description = "Physical Packages"
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left'

    @api.multi
    def name_get(self):
        res = self._complete_name('complete_name', None)
        return res.items()

    @api.multi
    def _complete_name(self, name, args):
        """ Forms complete name of location from parent location to child location.
        @return: Dictionary of values
        """
        res = {}
        for m in self:
            res[m.id] = m.name
            parent = m.parent_id
            while parent:
                res[m.id] = parent.name + ' / ' + res[m.id]
                parent = parent.parent_id
        return res

    @api.multi
    @api.depends('location_id', 'company_id', 'owner_id')
    def _get_packages(self):
        """Returns packages from quants for store"""
        res = set()
        for quant in self:
            pack = quant.package_id
            while pack:
                res.add(pack.id)
                pack = pack.parent_id
        return list(res)

    @api.multi
    def _get_package_info(self):
        quant_obj = self.env["stock.quant"]
        default_company_id = self.env.user.company_id.id
        res = dict((res_id, {'location_id': False, 'company_id': default_company_id, 'owner_id': False}) for res_id in self.ids)
        for pack in self:
            quants = quant_obj.search([('package_id', 'child_of', pack.id)], limit=1)
            if quants:
                pack.location_id = quants.location_id.id
                pack.owner_id = quants.owner_id.id
                pack.company_id = quants.company_id.id
            else:
                pack.location_id = False
                pack.owner_id = False
                pack.company_id = False
        return res

    @api.multi
    @api.depends('quant_ids', 'children_ids', 'parent_id')
    def _get_packages_to_relocate(self):
        res = set()
        for pack in self:
            res.add(pack.id)
            if pack.parent_id:
                res.add(pack.parent_id.id)
        return list(res)

    name = fields.Char('Package Reference', select=True, copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('stock.quant.package') or _('Unknown Pack'))
    complete_name = fields.Char(compute="_complete_name", string="Package Name")
    parent_left = fields.Integer('Left Parent', select=1)
    parent_right = fields.Integer('Right Parent', select=1)
    packaging_id = fields.Many2one('product.packaging', 'Packaging', help="This field should be completed only if everything inside the package share the same product, otherwise it doesn't really makes sense.", select=True)
    location_id = fields.Many2one(compute="_get_package_info", comodel_name='stock.location', string='Location', readonly=True, select=True)
    quant_ids = fields.One2many('stock.quant', 'package_id', 'Bulk Content', readonly=True)
    parent_id = fields.Many2one('stock.quant.package', 'Parent Package', help="The package containing this item", ondelete='restrict', readonly=True)
    children_ids = fields.One2many('stock.quant.package', 'parent_id', 'Contained Packages', readonly=True)
    company_id = fields.Many2one(compute="_get_package_info", comodel_name='res.company', string='Company', multi="package", readonly=True, select=True)
    owner_id = fields.Many2one(compute="_get_package_info", comodel_name='res.partner', string='Owner', multi="package", readonly=True, select=True)

    @api.model
    def _check_location_constraint(self, packs):
        '''checks that all quants in a package are stored in the same location. This function cannot be used
           as a constraint because it needs to be checked on pack operations (they may not call write on the
           package)
        '''
        for pack in packs:
            parent = pack
            while parent.parent_id:
                parent = parent.parent_id
            quant_ids = parent.get_content()
            quants = [x for x in self.env['stock.quant'].browse(quant_ids) if x.qty > 0]
            location_id = quants and quants[0].location_id.id or False
            if not [quant.location_id.id == location_id for quant in quants]:
                raise UserError(_('Everything inside a package should be in the same location'))
        return True

    @api.multi
    def action_print(self):
        self.with_context(active_ids=self.ids)
        return self.env["report"].get_action(self.ids, 'stock.report_package_barcode_small')

    @api.multi
    def unpack(self):
        for package in self:
            package.quant_ids.write({'package_id': package.parent_id.id or False})
            package.children_ids.write({'parent_id': package.parent_id.id or False})
        #delete current package since it contains nothing anymore
        self.unlink()
        return self.env['ir.actions.act_window'].for_xml_id('stock', 'action_package_view')

    @api.multi
    def get_content(self):
        child_package_ids = self.search([('id', 'child_of', self.ids)])
        return self.env['stock.quant'].search([('package_id', 'in', child_package_ids.ids)]).ids

    @api.multi
    def get_content_package(self):
        quants_ids = self.get_content()
        res = self.env['ir.actions.act_window'].for_xml_id('stock', 'quantsact')
        res['domain'] = [('id', 'in', quants_ids)]
        return res

    @api.model
    def _get_product_total_qty(self, package_record, product_id):
        ''' find the total of given product 'product_id' inside the given package 'package_id'''
        quant_obj = self.env['stock.quant']
        all_quant_ids = package_record.get_content()
        total = 0
        for quant in quant_obj.browse(all_quant_ids):
            if quant.product_id.id == product_id:
                total += quant.qty
        return total

    @api.multi
    def _get_all_products_quantities(self, cr, uid, package_id, context=None):
        '''This function computes the different product quantities for the given package
        '''
        res = {}
        for quant in self.get_content():
            if quant.product_id.id not in res:
                res[quant.product_id.id] = 0
            res[quant.product_id.id] += quant.qty
        return res

    #Remove me?
    @api.multi
    def copy_pack(self, default_pack_values=None, default=None):
        stock_pack_operation_obj = self.env['stock.pack.operation']
        if default is None:
            default = {}
        new_package_id = self.copy(default_pack_values)
        default['result_package_id'] = new_package_id
        op_ids = stock_pack_operation_obj.search([('result_package_id', '=', self.ids)])
        for op_id in op_ids:
            op_id.copy(default)


class StockPackOperation(models.Model):
    _name = "stock.pack.operation"
    _description = "Packing Operation"

    _order = "result_package_id desc, id"

    @api.model
    def _get_remaining_prod_quantities(self, operation):
        '''Get the remaining quantities per product on an operation with a package. This function returns a dictionary'''
        #if the operation doesn't concern a package, it's not relevant to call this function
        if not operation.package_id or operation.product_id:
            return {operation.product_id.id: operation.remaining_qty}
        #get the total of products the package contains
        res = operation.package_id._get_all_products_quantities()
        #reduce by the quantities linked to a move
        for record in operation.linked_move_operation_ids:
            if record.move_id.product_id.id not in res:
                res[record.move_id.product_id.id] = 0
            res[record.move_id.product_id.id] -= record.qty
        return res

    @api.multi
    def _get_remaining_qty(self):
        uom_obj = self.env['product.uom']
        for ops in self:
            ops.remaining_qty = 0
            if ops.package_id and not ops.product_id:
                #dont try to compute the remaining quantity for packages because it's not relevant (a package could include different products).
                #should use _get_remaining_prod_quantities instead
                continue
            else:
                qty = ops.product_qty
                if ops.product_uom_id:
                    qty = uom_obj._compute_qty_obj(ops.product_uom_id, ops.product_qty, ops.product_id.uom_id)
                for record in ops.linked_move_operation_ids:
                    qty -= record.qty
                ops.remaining_qty = float_round(qty, precision_rounding=ops.product_id.uom_id.rounding)

    @api.multi
    @api.onchange("product_id", "product_uom_id", "product_qty")
    def product_id_change(self):
        res = self.on_change_tests()
        if self.product_id and not self.product_uom_id or self.product_uom_id.category_id.id != self.product_id.uom_id.category_id.id:
            res['value']['product_uom_id'] = self.product_id.uom_id.id
        if self.product_id:
            res['value']['lots_visible'] = (self.product_id.tracking != 'none')
            res['domain'] = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        return res

    @api.multi
    def on_change_tests(self):
        res = {'value': {}}
        uom_obj = self.env['product.uom']
        if self.product_id:
            product_uom_id = self.product_uom_id.id or self.product_id.uom_id.id
            selected_uom = uom_obj.browse(product_uom_id)
            if selected_uom.category_id.id != self.product_id.uom_id.category_id.id:
                res['warning'] = {
                    'title': _('Warning: wrong UoM!'),
                    'message': _('The selected UoM for product %s is not compatible with the UoM set on the product form. \nPlease choose an UoM within the same UoM category.') % (self.product_id.name)
                }
            if self.product_qty and 'warning' not in res:
                rounded_qty = uom_obj._compute_qty(product_uom_id, self.product_qty, product_uom_id, round=True)
                if rounded_qty != self.product_qty:
                    res['warning'] = {
                        'title': _('Warning: wrong quantity!'),
                        'message': _('The chosen quantity for product %s is not compatible with the UoM rounding. It will be automatically converted at confirmation') % (self.product_id.name)
                    }
        return res

    @api.multi
    def _compute_location_description(self):
        for op in self:
            from_name = op.location_id.name
            to_name = op.location_dest_id.name
            if op.package_id and op.product_id:
                from_name += " : " + op.package_id.name
            if op.result_package_id:
                to_name += " : " + op.result_package_id.name
            op.from_loc = from_name,
            op.to_loc = to_name

    @api.multi
    def _get_bool(self):
        for pack in self:
            pack.processed_boolean = (pack.qty_done > 0.0)

    @api.multi
    def _set_processed_qty(self, field_value):
        op = self
        if not op.product_id:
            if field_value and op.qty_done == 0:
                self.write({'qty_done': 1.0})
            if not field_value and op.qty_done != 0:
                self.write({'qty_done': 0.0})
        return True

    @api.multi
    def _compute_lots_visible(self):
        for pack in self:
            pick = pack.picking_id
            product_requires = (pack.product_id.tracking != 'none')
            if pick.picking_type_id:
                pack.lots_visible = (pick.picking_type_id.use_existing_lots or pick.picking_type_id.use_create_lots) and product_requires
            else:
                pack.lots_visible = product_requires

    @api.model
    def _get_default_from_loc(self):
        default_loc = self._context.get('default_location_id')
        if default_loc:
            return self.env['stock.location'].browse(default_loc).name

    @api.model
    def _get_default_to_loc(self):
        default_loc = self._context.get('default_location_dest_id')
        if default_loc:
            return self.env['stock.location'].browse(default_loc).name

    picking_id = fields.Many2one('stock.picking', 'Stock Picking', help='The stock operation where the packing has been made', required=True)
    product_id = fields.Many2one('product.product', 'Product', ondelete="CASCADE")  # 1
    product_uom_id = fields.Many2one('product.uom', 'Unit of Measure')
    product_qty = fields.Float('To Do', digits_compute=dp.get_precision('Product Unit of Measure'), required=True, default=0.0)
    qty_done = fields.Float('Processed', digits_compute=dp.get_precision('Product Unit of Measure'), default=0.0)
    processed_boolean = fields.Boolean(compute="_get_bool", fnct_inv=_set_processed_qty, string='Processed', default=lambda *a: False)
    package_id = fields.Many2one('stock.quant.package', 'Source Package')  # 2
    pack_lot_ids = fields.One2many('stock.pack.operation.lot', 'operation_id', 'Lots Used')
    result_package_id = fields.Many2one('stock.quant.package', 'Destination Package', help="If set, the operations are packed into this package", required=False, ondelete='cascade')
    date = fields.Datetime(required=True, default=fields.Date.context_today)
    owner_id = fields.Many2one('res.partner', 'Owner', help="Owner of the quants")
    #'update_cost': fields.boolean('Need cost update'),
    cost = fields.Float(help="Unit Cost for this product line")
    currency = fields.Many2one('res.currency', string="Currency", help="Currency in which Unit cost is expressed", ondelete='CASCADE')
    linked_move_operation_ids = fields.One2many('stock.move.operation.link', 'operation_id', string='Linked Moves', readonly=True, help='Moves impacted by this operation for the computation of the remaining quantities')
    remaining_qty = fields.Float(compute="_get_remaining_qty", digits=0, string="Remaining Qty", help="Remaining quantity in default UoM according to moves matched with this operation. ")
    location_id = fields.Many2one('stock.location', 'Source Location', required=True)
    location_dest_id = fields.Many2one('stock.location', 'Destination Location', required=True)
    picking_source_location_id = fields.Many2one(related='picking_id.location_id', relation='stock.location')
    picking_destination_location_id = fields.Many2one(related='picking_id.location_dest_id', relation='stock.location')
    from_loc = fields.Char(compute="_compute_location_description", string='From', multi='loc', default=_get_default_from_loc)
    to_loc = fields.Char(compute="_compute_location_description", string='To', multi='loc', default=_get_default_to_loc)
    fresh_record = fields.Boolean('Newly created pack operation', default=True)
    lots_visible = fields.Boolean(compute="_compute_lots_visible")
    state = fields.Selection(related='picking_id.state', selection=[
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('waiting', 'Waiting Another Operation'),
            ('confirmed', 'Waiting Availability'),
            ('partially_available', 'Partially Available'),
            ('assigned', 'Available'),
            ('done', 'Done'),
            ])

    @api.multi
    def split_quantities(self):
        for pack in self:
            if pack.product_qty - pack.qty_done > 0.0 and pack.qty_done < pack.product_qty:
                pack2 = pack.copy(default={'qty_done': 0.0, 'product_qty': pack.product_qty - pack.qty_done})
                pack.write({'product_qty': pack.qty_done})
            else:
                raise UserError(_('The quantity to split should be smaller than the quantity To Do.  '))
        return True

    @api.multi
    def write(self, vals):
        vals['fresh_record'] = False
        res = super(StockPackOperation, self).write(vals)
        return res

    @api.multi
    def unlink(self):
        if any([x.state in ('done', 'cancel') for x in self]):
            raise UserError(_('You can not delete pack operations of a done picking'))
        return super(StockPackOperation, self).unlink()

    @api.multi
    def check_tracking(self):
        """ Checks if serial number is assigned to stock move or not and raise an error if it had to.
        """
        for ops in self:
            if ops.picking_id and (ops.picking_id.picking_type_id.use_existing_lots or ops.picking_id.picking_type_id.use_create_lots) and \
            ops.product_id and ops.product_id.tracking != 'none' and ops.qty_done > 0.0:
                if not ops.pack_lot_ids:
                    raise UserError(_('You need to provide a Lot/Serial Number for product %s') % ops.product_id.name)
                if ops.product_id.tracking == 'serial':
                    for opslot in ops.pack_lot_ids:
                        if opslot.qty not in (1.0, 0.0):
                            raise UserError(_('You should provide a different serial number for each piece'))

    @api.multi
    def save(self):
        for pack in self:
            if pack.product_id.tracking != 'none':
                qty_done = sum([x.qty for x in pack.pack_lot_ids])
                pack.write({'qty_done': qty_done})
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def split_lot(self):
        assert len(self.ids) > 0
        pack = self[0]
        picking_type = pack.picking_id.picking_type_id
        serial = (pack.product_id.tracking == 'serial')
        view = self.env.ref('stock.view_pack_operation_lot_form').id
        only_create = picking_type.use_create_lots and not picking_type.use_existing_lots
        show_reserved = any([x for x in pack.pack_lot_ids if x.qty_todo > 0.0])

        self.with_context({'serial': serial,
                    'only_create': only_create,
                    'show_reserved': show_reserved})
        return {
                'name': _('Lot Details'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.pack.operation',
                'views': [(view, 'form')],
                'view_id': view,
                'target': 'new',
                'res_id': pack.id,
                'context': self._context,
        }

    @api.multi
    def show_details(self):
        view = self.env.ref('stock.view_pack_operation_details_form_save').id
        pack = self[0]
        return {
                'name': _('Operation Details'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.pack.operation',
                'views': [(view, 'form')],
                'view_id': view,
                'target': 'new',
                'res_id': pack.id,
                'context': self._context,
        }

class StockPackOperationLot(models.Model):
    _name = "stock.pack.operation.lot"
    _description = "Specifies lot/serial number for pack operations that need it"

    @api.multi
    @api.depends('qty')
    def _get_processed(self):
        for packlot in self:
            packlot.processed = (packlot.qty > 0.0)

    operation_id = fields.Many2one('stock.pack.operation')
    qty = fields.Float('Quantity', default=1.0)
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number')
    lot_name = fields.Char()
    qty_todo = fields.Float('Quantity')
    processed = fields.Boolean("_get_processed")

    @api.multi
    @api.depends('lot_id', 'lot_name')
    def _check_lot(self):
        for packlot in self:
            if not packlot.lot_name and not packlot.lot_id:
                return False
        return True

    _sql_constraints = [
        ('qty', 'CHECK(qty >= 0.0)','Quantity must be greater than or equal to 0.0!'),
        ('uniq_lot_id', 'unique(operation_id, lot_id)', 'You have already mentioned this lot in another line'),
        ('uniq_lot_name', 'unique(operation_id, lot_name)', 'You have already mentioned this lot name in another line')]

    @api.multi
    def do_plus(self):
        #return {'type': 'ir.actions.act_window_close'}
        for packlot in self:
            packlot.write({'qty': packlot.qty + 1})
        pack = self[0].operation_id
        return pack.split_lot()

    @api.multi
    def do_minus(self):
        for packlot in self:
            packlot.write({'qty': packlot.qty - 1})
        pack = self[0].operation_id
        return pack.split_lot()

class StockMoveOperationLink(models.Model):
    """
    Table making the link between stock.moves and stock.pack.operations to compute the remaining quantities on each of these objects
    """
    _name = "stock.move.operation.link"
    _description = "Link between stock moves and pack operations"

    qty = fields.Float('Quantity', help="Quantity of products to consider when talking about the contribution of this pack operation towards the remaining quantity of the move (and inverse). Given in the product main uom.")
    operation_id = fields.Many2one('stock.pack.operation', 'Operation', required=True, ondelete="cascade")
    move_id = fields.Many2one('stock.move', 'Move', required=True, ondelete="cascade")
    reserved_quant_id = fields.Many2one('stock.quant', 'Reserved Quant', help="Technical field containing the quant that created this link between an operation and a stock move. Used at the stock_move_obj.action_done() time to avoid seeking a matching quant again")

class StockWarehouseOrderpoint(models.Model):
    """
    Defines Minimum stock rules.
    """
    _name = "stock.warehouse.orderpoint"
    _description = "Minimum Inventory Rule"

    @api.multi
    def subtract_procurements_from_orderpoints(self):
        '''This function returns quantity of product that needs to be deducted from the orderpoint computed quantity because there's already a procurement created with aim to fulfill it.
        '''

        self._cr.execute("""select op.id, p.id, p.product_uom, p.product_qty, pt.uom_id, sm.product_qty from procurement_order as p left join stock_move as sm ON sm.procurement_id = p.id,
                                    stock_warehouse_orderpoint op, product_product pp, product_template pt
                                WHERE p.orderpoint_id = op.id AND p.state not in ('done', 'cancel') AND (sm.state IS NULL OR sm.state not in ('draft'))
                                AND pp.id = p.product_id AND pp.product_tmpl_id = pt.id
                                AND op.id IN %s
                                ORDER BY op.id, p.id
                    """, (tuple(self.ids),))
        results = self._cr.fetchall()
        current_proc = False
        current_op = False
        uom_obj = self.env["product.uom"]
        op_qty = 0
        res = dict.fromkeys(self.ids, 0.0)
        for move_result in results:
            op = move_result[0]
            if current_op != op:
                if current_op:
                    res[current_op] = op_qty
                current_op = op
                op_qty = 0
            proc = move_result[1]
            if proc != current_proc:
                op_qty += uom_obj._compute_qty(move_result[2], move_result[3], move_result[4], round=False)
                current_proc = proc
            if move_result[5]:  # If a move is associated (is move qty)
                op_qty -= move_result[5]
        if current_op:
            res[current_op] = op_qty
        return res

    @api.multi
    @api.depends('product_id', 'product_uom')
    def _check_product_uom(self, cr, uid, ids, context=None):
        '''
        Check if the UoM has the same category as the product standard UoM
        '''
        if not context:
            context = {}

        for rule in self.browse(cr, uid, ids, context=context):
            if rule.product_id.uom_id.category_id.id != rule.product_uom.category_id.id:
                return False
        return True

    name = fields.Char(required=True, copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('stock.orderpoint') or '')
    active = fields.Boolean(help="If the active field is set to False, it will allow you to hide the orderpoint without removing it.", default=lambda *a: 1)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True, ondelete="cascade")
    location_id = fields.Many2one('stock.location', 'Location', required=True, ondelete="cascade")
    product_id = fields.Many2one('product.product', 'Product', required=True, ondelete='cascade', domain=[('type', '=', 'product')])
    product_uom = fields.Many2one(related='product_id.uom_id', relation='product.uom', string='Product Unit of Measure', readonly=True, required=True, default=lambda self: self._context.get('product_uom'))
    product_min_qty = fields.Float('Minimum Quantity', required=True,
        digits_compute=dp.get_precision('Product Unit of Measure'),
        help="When the virtual stock goes below the Min Quantity specified for this field, Odoo generates "\
        "a procurement to bring the forecasted quantity to the Max Quantity.")
    product_max_qty = fields.Float('Maximum Quantity', required=True,
        digits_compute=dp.get_precision('Product Unit of Measure'),
        help="When the virtual stock goes below the Min Quantity, Odoo generates "\
        "a procurement to bring the forecasted quantity to the Quantity specified as Max Quantity.")
    qty_multiple = fields.Float('Qty Multiple', required=True,
        digits_compute=dp.get_precision('Product Unit of Measure'),
        help="The procurement quantity will be rounded up to this multiple.  If it is 0, the exact quantity will be used.  ", default=lambda *a: 1)
    procurement_ids = fields.One2many('procurement.order', 'orderpoint_id', 'Created Procurements')
    group_id = fields.Many2one('procurement.group', 'Procurement Group', help="Moves created through this orderpoint will be put in this procurement group. If none is given, the moves generated by procurement rules will be grouped into one big picking.", copy=False)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.user.company_id)
    lead_days = fields.Integer('Lead Time', help="Number of days after the orderpoint is triggered to receive the products or to order to the vendor", default=lambda *a: 1)
    lead_type = fields.Selection([('net', 'Day(s) to get the products'), ('supplier', 'Day(s) to purchase')], 'Lead Type', required=True, default=lambda *a: 'supplier')

    _sql_constraints = [
        ('qty_multiple_check', 'CHECK( qty_multiple >= 0 )', 'Qty Multiple must be greater than or equal to zero.'),
    ]
    # _constraints = [
    #     (_check_product_uom, 'You have to select a product unit of measure in the same category than the default unit of measure of the product', ['product_id', 'product_uom']),
    # ]

    @api.model
    def default_get(self, fields):
        warehouse_obj = self.env['stock.warehouse']
        res = super(StockWarehouseOrderpoint, self).default_get(fields)
        # default 'warehouse_id' and 'location_id'
        if 'warehouse_id' not in res:
            warehouse_ids = res.get('company_id') and warehouse_obj.search([('company_id', '=', res['company_id'])], limit=1).ids or []
            res['warehouse_id'] = warehouse_ids and warehouse_ids[0] or False
        if 'location_id' not in res:
            res['location_id'] = res.get('warehouse_id') and warehouse_obj.browse(res['warehouse_id']).lot_stock_id.id or False
        return res

    @api.multi
    @api.onchange('warehouse_id')
    def onchange_warehouse_id(self):
        """ Finds location id for changed warehouse.
        """
        if self.warehouse_id:
            self.location_id = self.warehouse_id.lot_stock_id.id

    @api.multi
    @api.onchange('product_id')
    def onchange_product_id(self):
        """ Finds UoM for changed product.
        """
        if self.product_id:
            d = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
            self.product_uom = self.product_id.uom_id.id
            return {'domain': d}
        return {'domain': {'product_uom': []}}

class StockPickingType(models.Model):
    _name = "stock.picking.type"
    _description = "The picking type determines the picking view"
    _order = 'sequence'

    @api.multi
    def open_barcode_interface(self):
        final_url = "/stock/barcode/#action=stock.ui&picking_type_id=" + str(self.ids[0]) if len(self.ids) else '0'
        return {'type': 'ir.actions.act_url', 'url': final_url, 'target': 'self'}

    @api.multi
    def _get_tristate_values(self):
        for picking_type_id in self:
            #get last 10 pickings of this type
            picking_ids = self.env['stock.picking'].search([('picking_type_id', '=', picking_type_id.id), ('state', '=', 'done')], order='date_done desc', limit=10)
            tristates = []
            for picking in picking_ids:
                if picking.date_done > picking.date:
                    tristates.insert(0, {'tooltip': picking.name or '' + ": " + _('Late'), 'value': -1})
                elif picking.backorder_id:
                    tristates.insert(0, {'tooltip': picking.name or '' + ": " + _('Backorder exists'), 'value': 0})
                else:
                    tristates.insert(0, {'tooltip': picking.name or '' + ": " + _('OK'), 'value': 1})
            picking_type_id.last_done_picking = json.dumps(tristates)

    @api.multi
    def _get_picking_count(self):
        obj = self.env['stock.picking']
        domains = {
            'count_picking_draft': [('state', '=', 'draft')],
            'count_picking_waiting': [('state', 'in', ('confirmed', 'waiting'))],
            'count_picking_ready': [('state', 'in', ('assigned', 'partially_available'))],
            'count_picking': [('state', 'in', ('assigned', 'waiting', 'confirmed', 'partially_available'))],
            'count_picking_late': [('min_date', '<', time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)), ('state', 'in', ('assigned', 'waiting', 'confirmed', 'partially_available'))],
            'count_picking_backorders': [('backorder_id', '!=', False), ('state', 'in', ('confirmed', 'assigned', 'waiting', 'partially_available'))],
        }
        result = {}
        for field in domains:
            data = obj.read_group(domains[field] +
                [('state', 'not in', ('done', 'cancel')), ('picking_type_id', 'in', self.ids)],
                ['picking_type_id'], ['picking_type_id'])
            count = dict(map(lambda x: (x['picking_type_id'] and x['picking_type_id'][0], x['picking_type_id_count']), data))
            for tid in self.ids:
                result.setdefault(tid, {})[field] = count.get(tid, 0)
        for tid in self:
            if result[tid.id]['count_picking']:
                tid.rate_picking_late = result[tid.id]['count_picking_late'] * 100 / result[tid.id]['count_picking']
                tid.rate_picking_backorders = result[tid.id]['count_picking_backorders'] * 100 / result[tid.id]['count_picking']
            else:
                tid.rate_picking_late = 0
                tid.rate_picking_backorders = 0
            tid.count_picking_draft = result[tid.id]['count_picking_draft']
            tid.count_picking_waiting = result[tid.id]['count_picking_waiting']
            tid.count_picking_ready = result[tid.id]['count_picking_ready']
            tid.count_picking = result[tid.id]['count_picking']
            tid. count_picking_late = result[tid.id]['count_picking_late']
            tid.count_picking_backorders = result[tid.id]['count_picking_backorders']

    @api.multi
    def _get_action(self, action):
        result = self.env.ref(action, raise_if_not_found=True)
        result = result.read()[0]
        if self:
            result.display_name = self.display_name
        return result

    @api.multi
    def get_action_picking_tree_late(self):
        return self._get_action('stock.action_picking_tree_late')

    @api.multi
    def get_action_picking_tree_backorder(self):
        return self._get_action('stock.action_picking_tree_backorder')

    @api.multi
    def get_action_picking_tree_waiting(self):
        return self._get_action('stock.action_picking_tree_waiting')

    @api.multi
    def get_action_picking_tree_ready(self):
        return self._get_action('stock.action_picking_tree_ready')

    @api.multi
    @api.onchange('code')
    def onchange_picking_code(self):
        if not self.code:
            return False
        stock_loc = self.env.ref('stock.stock_location_stock').id
        self.default_location_src_id = stock_loc
        self.default_location_dest_id = stock_loc
        if self.code == 'incoming':
            self.default_location_src_id = self.env.ref('stock.stock_location_suppliers')
        elif self.code == 'outgoing':
            self.default_location_dest_id = self.env.ref('stock.stock_location_customers')

    @api.multi
    def _get_name(self):
        return dict(self.name_get())

    @api.multi
    def name_get(self):
        """Overides orm name_get method to display 'Warehouse_name: PickingType_name' """
        res = []
        if not self.ids:
            return res
        for record in self:
            name = record.name
            if record.warehouse_id:
                name = record.warehouse_id.name + ': ' + name
            if self._context.get('special_shortened_wh_name'):
                if record.warehouse_id:
                    name = record.warehouse_id.name
                else:
                    name = _('Customer') + ' (' + record.name + ')'
            res.append((record.id, name))
        return res

    @api.model
    def _default_warehouse(self):
        res = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1)
        return res and res.ids[0] or False

    name = fields.Char('Picking Type Name', translate=True, required=True)
    complete_name = fields.Char(compute="_get_name", string='Name')
    color = fields.Integer()
    sequence = fields.Integer(help="Used to order the 'All Operations' kanban view")
    sequence_id = fields.Many2one('ir.sequence', 'Reference Sequence', required=True)
    default_location_src_id = fields.Many2one('stock.location', 'Default Source Location', help="This is the default source location when you create a picking manually with this picking type. It is possible however to change it or that the routes put another location. If it is empty, it will check for the supplier location on the partner. ")
    default_location_dest_id = fields.Many2one('stock.location', 'Default Destination Location', help="This is the default destination location when you create a picking manually with this picking type. It is possible however to change it or that the routes put another location. If it is empty, it will check for the customer location on the partner. ")
    code = fields.Selection([('incoming', 'Suppliers'), ('outgoing', 'Customers'), ('internal', 'Internal')], 'Type of Operation', required=True)
    return_picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type for Returns')
    show_entire_packs = fields.Boolean('Allow moving packs', help="If checked, this shows the packs to be moved as a whole in the Operations tab all the time, even if there was no entire pack reserved.")
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', ondelete='cascade', default=_default_warehouse)
    active = fields.Boolean(default=True)
    use_create_lots = fields.Boolean('Create New Lots', help="If this is checked only, it will suppose you want to create new Serial Numbers / Lots, so you can provide them in a text field. ")
    use_existing_lots = fields.Boolean('Use Existing Lots', help="If this is checked, you will be able to choose the Serial Number / Lots. You can also decide to not put lots in this picking type.  This means it will create stock with no lot or not put a restriction on the lot taken. ")
    # Statistics for the kanban view
    last_done_picking = fields.Char(compute="_get_tristate_values", string='Last 10 Done Pickings')
    count_picking_draft = fields.Integer(compute="_get_picking_count", multi='_get_picking_count')
    count_picking_ready = fields.Integer(compute="_get_picking_count", multi='_get_picking_count')
    count_picking = fields.Integer(compute="_get_picking_count", multi='_get_picking_count')
    count_picking_waiting = fields.Integer(compute="_get_picking_count", multi='_get_picking_count')
    count_picking_late = fields.Integer(compute="_get_picking_count", multi='_get_picking_count')
    count_picking_backorders = fields.Integer(compute="_get_picking_count", multi='_get_picking_count')
    rate_picking_late = fields.Integer(compute="_get_picking_count", multi='_get_picking_count')
    rate_picking_backorders = fields.Integer(compute="_get_picking_count", multi='_get_picking_count')
    # Barcode nomenclature
    barcode_nomenclature_id = fields.Many2one('barcode.nomenclature', 'Barcode Nomenclature', help='A barcode nomenclature')

class BarcodeRule(models.Model):
    _inherit = 'barcode.rule'

    def _get_type_selection(self):
        types = sets.Set(super(BarcodeRule, self)._get_type_selection())
        types.update([
            ('weight', 'Weighted Product'),
            ('location', 'Location'),
            ('lot', 'Lot'),
            ('package', 'Package')
        ])
        return list(types)

# class StockPackOperation(models.Model):
#     _inherit = 'stock.pack.operation'

#     @api.onchange('pack_lot_ids')
#     def _onchange_packlots(self):
#         self.qty_done = sum([x.qty for x in self.pack_lot_ids])
