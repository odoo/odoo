# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil import relativedelta

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class Location(models.Model):
    _name = "stock.location"
    _description = "Inventory Locations"
    _parent_name = "location_id"
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left'
    _rec_name = 'complete_name'

    @api.model
    def default_get(self, fields):
        res = super(Location, self).default_get(fields)
        if 'barcode' in fields and 'barcode' not in res and res.get('complete_name'):
            res['barcode'] = res['complete_name']
        return res

    name = fields.Char('Location Name', required=True, translate=True)
    complete_name = fields.Char("Full Location Name", compute='_compute_complete_name', store=True)
    active = fields.Boolean('Active', default=True, help="By unchecking the active field, you may hide a location without deleting it.")
    usage = fields.Selection([
        ('supplier', 'Vendor Location'),
        ('view', 'View'),
        ('internal', 'Internal Location'),
        ('customer', 'Customer Location'),
        ('inventory', 'Inventory Loss'),
        ('procurement', 'Procurement'),
        ('production', 'Production'),
        ('transit', 'Transit Location')], string='Location Type',
        default='internal', index=True, required=True,
        help="* Vendor Location: Virtual location representing the source location for products coming from your vendors"
             "\n* View: Virtual location used to create a hierarchical structures for your warehouse, aggregating its child locations ; can't directly contain products"
             "\n* Internal Location: Physical locations inside your own warehouses,"
             "\n* Customer Location: Virtual location representing the destination location for products sent to your customers"
             "\n* Inventory Loss: Virtual location serving as counterpart for inventory operations used to correct stock levels (Physical inventories)"
             "\n* Procurement: Virtual location serving as temporary counterpart for procurement operations when the source (vendor or production) is not known yet. This location should be empty when the procurement scheduler has finished running."
             "\n* Production: Virtual counterpart location for production operations: this location consumes the raw material and produces finished products"
             "\n* Transit Location: Counterpart location that should be used in inter-companies or inter-warehouses operations")
    location_id = fields.Many2one(
        'stock.location', 'Parent Location', index=True, ondelete='cascade',
        help="The parent location that includes this location. Example : The 'Dispatch Zone' is the 'Gate 1' parent location.")
    child_ids = fields.One2many('stock.location', 'location_id', 'Contains')
    partner_id = fields.Many2one('res.partner', 'Owner', help="Owner of the location if not internal")
    comment = fields.Text('Additional Information')
    posx = fields.Integer('Corridor (X)', default=0, help="Optional localization details, for information purpose only")
    posy = fields.Integer('Shelves (Y)', default=0, help="Optional localization details, for information purpose only")
    posz = fields.Integer('Height (Z)', default=0, help="Optional localization details, for information purpose only")
    parent_left = fields.Integer('Left Parent', index=True)
    parent_right = fields.Integer('Right Parent', index=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('stock.location'), index=True,
        help='Let this field empty if this location is shared between companies')
    scrap_location = fields.Boolean('Is a Scrap Location?', default=False, help='Check this box to allow using this location to put scrapped/damaged goods.')
    return_location = fields.Boolean('Is a Return Location?', help='Check this box to allow using this location as a return location.')
    removal_strategy_id = fields.Many2one('product.removal', 'Removal Strategy', help="Defines the default method used for suggesting the exact location (shelf) where to take the products from, which lot etc. for this location. This method can be enforced at the product category level, and a fallback is made on the parent locations if none is set here.")
    putaway_strategy_id = fields.Many2one('product.putaway', 'Put Away Strategy', help="Defines the default method used for suggesting the exact location (shelf) where to store the products. This method can be enforced at the product category level, and a fallback is made on the parent locations if none is set here.")
    barcode = fields.Char('Barcode', copy=False, oldname='loc_barcode')

    _sql_constraints = [('barcode_company_uniq', 'unique (barcode,company_id)', 'The barcode for a location must be unique per company !')]

    @api.one
    @api.depends('name', 'location_id')
    def _compute_complete_name(self):
        """ Forms complete name of location from parent location to child location. """
        name = self.name
        current = self
        while current.location_id:
            current = current.location_id
            name = '%s/%s' % (current.name, name)
        self.complete_name = name

    @api.multi
    def name_get(self):
        ret_list = []
        for location in self:
            orig_location = location
            name = location.name
            while location.location_id and location.usage != 'view':
                location = location.location_id
                name = location.name + "/" + name
            ret_list.append((orig_location.id, name))
        return ret_list

    def get_putaway_strategy(self, product):
        ''' Returns the location where the product has to be put, if any compliant putaway strategy is found. Otherwise returns None.'''
        current_location = self
        putaway_location = self.env['stock.location']
        while current_location and not putaway_location:
            if current_location.putaway_strategy_id:
                putaway_location = current_location.putaway_strategy_id.putaway_apply(product)
            current_location = current_location.location_id
        return putaway_location

    @api.multi
    @api.returns('stock.warehouse', lambda value: value.id)
    def get_warehouse(self):
        """ Returns warehouse id of warehouse that contains location """
        return self.env['stock.warehouse'].search([
            ('view_location_id.parent_left', '<=', self.parent_left),
            ('view_location_id.parent_right', '>=', self.parent_left)], limit=1)


class Route(models.Model):
    _name = 'stock.location.route'
    _description = "Inventory Routes"
    _order = 'sequence'

    name = fields.Char('Route Name', required=True, translate=True)
    active = fields.Boolean('Active', default=True, help="If the active field is set to False, it will allow you to hide the route without removing it.")
    sequence = fields.Integer('Sequence', default=0)
    pull_ids = fields.One2many('procurement.rule', 'route_id', 'Procurement Rules', copy=True, 
        help="The demand represented by a procurement from e.g. a sale order, a reordering rule, another move, needs to be solved by applying a procurement rule. Depending on the action on the procurement rule,"\
        "this triggers a purchase order, manufacturing order or another move. This way we create chains in the reverse order from the endpoint with the original demand to the starting point. "\
        "That way, it is always known where we need to go and that is why they are preferred over push rules.")
    push_ids = fields.One2many('stock.location.path', 'route_id', 'Push Rules', copy=True, 
        help="When a move is foreseen to a location, the push rule will automatically create a move to a next location after. This is mainly only needed when creating manual operations e.g. 2/3 step manual purchase order or 2/3 step finished product manual manufacturing order. In other cases, it is important to use pull rules where you know where you are going based on a demand.")
    product_selectable = fields.Boolean('Applicable on Product', default=True, help="When checked, the route will be selectable in the Inventory tab of the Product form.  It will take priority over the Warehouse route. ")
    product_categ_selectable = fields.Boolean('Applicable on Product Category', help="When checked, the route will be selectable on the Product Category.  It will take priority over the Warehouse route. ")
    warehouse_selectable = fields.Boolean('Applicable on Warehouse', help="When a warehouse is selected for this route, this route should be seen as the default route when products pass through this warehouse.  This behaviour can be overridden by the routes on the Product/Product Categories or by the Preferred Routes on the Procurement")
    supplied_wh_id = fields.Many2one('stock.warehouse', 'Supplied Warehouse')
    supplier_wh_id = fields.Many2one('stock.warehouse', 'Supplying Warehouse')
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('stock.location.route'), index=True,
        help='Leave this field empty if this route is shared between all companies')
    product_ids = fields.Many2many('product.template', 'stock_route_product', 'route_id', 'product_id', 'Products')
    categ_ids = fields.Many2many('product.category', 'stock_location_route_categ', 'route_id', 'categ_id', 'Product Categories')
    warehouse_ids = fields.Many2many('stock.warehouse', 'stock_route_warehouse', 'route_id', 'warehouse_id', 'Warehouses')

    @api.multi
    def write(self, values):
        '''when a route is deactivated, deactivate also its pull and push rules'''
        res = super(Route, self).write(values)
        if 'active' in values:
            self.mapped('push_ids').filtered(lambda path: path.active != values['active']).write({'active': values['active']})
            self.mapped('pull_ids').filtered(lambda rule: rule.active != values['active']).write({'active': values['active']})
        return res

    @api.multi
    def view_product_ids(self):
        return {
            'name': _('Products'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'product.template',
            'type': 'ir.actions.act_window',
            'domain': [('route_ids', 'in', self.ids)],
        }

    @api.multi
    def view_categ_ids(self):
        return {
            'name': _('Product Categories'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'product.category',
            'type': 'ir.actions.act_window',
            'domain': [('route_ids', 'in', self.ids)],
        }


class PushedFlow(models.Model):
    _name = "stock.location.path"
    _description = "Pushed Flow"
    _order = "sequence, name"

    name = fields.Char('Operation Name', required=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('procurement.order'), index=True)
    route_id = fields.Many2one('stock.location.route', 'Route', required=True, ondelete='cascade')
    location_from_id = fields.Many2one(
        'stock.location', 'Source Location', index=True, ondelete='cascade', required=True,
        help="This rule can be applied when a move is confirmed that has this location as destination location")
    location_dest_id = fields.Many2one(
        'stock.location', 'Destination Location', index=True, ondelete='cascade', required=True,
        help="The new location where the goods need to go")
    delay = fields.Integer('Delay (days)', default=0, help="Number of days needed to transfer the goods")
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type', required=True,
        help="This is the operation type that will be put on the stock moves")
    auto = fields.Selection([
        ('manual', 'Manual Operation'),
        ('transparent', 'Automatic No Step Added')], string='Automatic Move',
        default='manual', index=True, required=True,
        help="The 'Manual Operation' value will create a stock move after the current one."
             "With 'Automatic No Step Added', the location is replaced in the original move.")
    propagate = fields.Boolean('Propagate cancel and split', default=True, help='If checked, when the previous move is cancelled or split, the move generated by this move will too')
    active = fields.Boolean('Active', default=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    route_sequence = fields.Integer('Route Sequence', related='route_id.sequence', store=True)
    sequence = fields.Integer('Sequence')

    def _apply(self, move):
        new_date = (datetime.strptime(move.date_expected, DEFAULT_SERVER_DATETIME_FORMAT) + relativedelta.relativedelta(days=self.delay)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        if self.auto == 'transparent':
            move.write({
                'date': new_date,
                'date_expected': new_date,
                'location_dest_id': self.location_dest_id.id})
            # avoid looping if a push rule is not well configured; otherwise call again push_apply to see if a next step is defined
            if self.location_dest_id != move.location_dest_id:
                # TDE FIXME: should probably be done in the move model IMO
                move._push_apply()
        else:
            new_move = move.copy({
                'origin': move.origin or move.picking_id.name or "/",
                'location_id': move.location_dest_id.id,
                'location_dest_id': self.location_dest_id.id,
                'date': new_date,
                'date_expected': new_date,
                'company_id': self.company_id.id,
                'picking_id': False,
                'picking_type_id': self.picking_type_id.id,
                'propagate': self.propagate,
                'push_rule_id': self.id,
                'warehouse_id': self.warehouse_id.id,
                'procurement_id': False,
            })
            move.write({'move_dest_id': new_move.id})
            new_move.action_confirm()
