# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, orm
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import float_compare
from openerp.tools.translate import _
from openerp import tools, SUPERUSER_ID
from openerp.addons.product import _common


class mrp_property_group(osv.osv):
    """
    Group of mrp properties.
    """
    _name = 'mrp.property.group'
    _description = 'Property Group'
    _columns = {
        'name': fields.char('Property Group', size=64, required=True),
        'description': fields.text('Description'),
    }

class mrp_property(osv.osv):
    """
    Properties of mrp.
    """
    _name = 'mrp.property'
    _description = 'Property'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'composition': fields.selection([('min','min'),('max','max'),('plus','plus')], 'Properties composition', required=True, help="Not used in computations, for information purpose only."),
        'group_id': fields.many2one('mrp.property.group', 'Property Group', required=True),
        'description': fields.text('Description'),
    }
    _defaults = {
        'composition': lambda *a: 'min',
    }
#----------------------------------------------------------
# Work Centers
#----------------------------------------------------------
# capacity_hour : capacity per hour. default: 1.0.
#          Eg: If 5 concurrent operations at one time: capacity = 5 (because 5 employees)
# unit_per_cycle : how many units are produced for one cycle

class mrp_workcenter(osv.osv):
    _name = 'mrp.workcenter'
    _description = 'Work Center'
    _inherits = {'resource.resource':"resource_id"}
    _columns = {
        'note': fields.text('Description', help="Description of the Work Center. Explain here what's a cycle according to this Work Center."),
        'capacity_per_cycle': fields.float('Capacity per Cycle', help="Number of operations this Work Center can do in parallel. If this Work Center represents a team of 5 workers, the capacity per cycle is 5."),
        'time_cycle': fields.float('Time for 1 cycle (hour)', help="Time in hours for doing one cycle."),
        'time_start': fields.float('Time before prod.', help="Time in hours for the setup."),
        'time_stop': fields.float('Time after prod.', help="Time in hours for the cleaning."),
        'costs_hour': fields.float('Cost per hour', help="Specify Cost of Work Center per hour."),
        'costs_hour_account_id': fields.many2one('account.analytic.account', 'Hour Account', domain=[('type','!=','view')],
            help="Fill this only if you want automatic analytic accounting entries on production orders."),
        'costs_cycle': fields.float('Cost per cycle', help="Specify Cost of Work Center per cycle."),
        'costs_cycle_account_id': fields.many2one('account.analytic.account', 'Cycle Account', domain=[('type','!=','view')],
            help="Fill this only if you want automatic analytic accounting entries on production orders."),
        'costs_journal_id': fields.many2one('account.analytic.journal', 'Analytic Journal'),
        'costs_general_account_id': fields.many2one('account.account', 'General Account', domain=[('type','!=','view')]),
        'resource_id': fields.many2one('resource.resource','Resource', ondelete='cascade', required=True),
        'product_id': fields.many2one('product.product','Work Center Product', help="Fill this product to easily track your production costs in the analytic accounting."),
    }
    _defaults = {
        'capacity_per_cycle': 1.0,
        'resource_type': 'material',
     }

    def on_change_product_cost(self, cr, uid, ids, product_id, context=None):
        value = {}

        if product_id:
            cost = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            value = {'costs_hour': cost.standard_price}
        return {'value': value}

class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'disassemble': fields.boolean('Disassemble'),
    }

class mrp_routing(osv.osv):
    """
    For specifying the routings of Work Centers.
    """
    _name = 'mrp.routing'
    _description = 'Routing'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the routing without removing it."),
        'code': fields.char('Code', size=8),

        'note': fields.text('Description'),
        'workcenter_lines': fields.one2many('mrp.routing.workcenter', 'routing_id', 'Work Centers'),

        'location_id': fields.many2one('stock.location', 'Production Location',
            help="Keep empty if you produce at the location where the finished products are needed." \
                "Set a location if you produce at a fixed location. This can be a partner location " \
                "if you subcontract the manufacturing operations."
        ),
        'company_id': fields.many2one('res.company', 'Company'),
    }
    _defaults = {
        'active': lambda *a: 1,
        'company_id': lambda self, cr, uid, context: self.pool.get('res.company')._company_default_get(cr, uid, 'mrp.routing', context=context)
    }

class mrp_routing_workcenter(osv.osv):
    """
    Defines working cycles and hours of a Work Center using routings.
    """
    _name = 'mrp.routing.workcenter'
    _description = 'Work Center Usage'
    _order = 'sequence'
    _columns = {
        'workcenter_id': fields.many2one('mrp.workcenter', 'Work Center', required=True),
        'name': fields.char('Name', size=64, required=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of routing Work Centers."),
        'cycle_nbr': fields.float('Number of Cycles', required=True,
            help="Number of iterations this work center has to do in the specified operation of the routing."),
        'hour_nbr': fields.float('Number of Hours', required=True, help="Time in hours for this Work Center to achieve the operation of the specified routing."),
        'routing_id': fields.many2one('mrp.routing', 'Parent Routing', select=True, ondelete='cascade',
             help="Routing indicates all the Work Centers used, for how long and/or cycles." \
                "If Routing is indicated then,the third tab of a production order (Work Centers) will be automatically pre-completed."),
        'note': fields.text('Description'),
        'company_id': fields.related('routing_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
    }
    _defaults = {
        'cycle_nbr': lambda *a: 1.0,
        'hour_nbr': lambda *a: 0.0,
    }

class mrp_bom(osv.osv):
    """
    Defines bills of material for a product.
    """
    _name = 'mrp.bom'
    _description = 'Bill of Material'
    _inherit = ['mail.thread']

    def _child_compute(self, cr, uid, ids, name, arg, context=None):
        """ Gets child bom.
        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param uid: The current user ID for security checks
        @param ids: List of selected IDs
        @param name: Name of the field
        @param arg: User defined argument
        @param context: A standard dictionary for contextual values
        @return:  Dictionary of values
        """
        result = {}
        if context is None:
            context = {}
        bom_obj = self.pool.get('mrp.bom')
        bom_id = context and context.get('active_id', False) or False
        cr.execute('select id from mrp_bom')
        if all(bom_id != r[0] for r in cr.fetchall()):
            ids.sort()
            bom_id = ids[0]
        bom_parent = bom_obj.browse(cr, uid, bom_id, context=context)
        for bom in self.browse(cr, uid, ids, context=context):
            if (bom_parent) or (bom.id == bom_id):
                result[bom.id] = map(lambda x: x.id, bom.bom_lines)
            else:
                result[bom.id] = []
            if bom.bom_lines:
                continue
            ok = ((name=='child_complete_ids'))
            if (bom.type=='phantom' or ok):
                sids = bom_obj.search(cr, uid, [('bom_id','=',False),('product_id','=',bom.product_id.id)])
                if sids:
                    bom2 = bom_obj.browse(cr, uid, sids[0], context=context)
                    result[bom.id] += map(lambda x: x.id, bom2.bom_lines)

        return result

    _columns = {
        'name': fields.char('Name', size=64),
        'code': fields.char('Reference', size=16),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the bills of material without removing it."),
        'type': fields.selection([('normal', 'Normal BoM'), ('phantom', 'Sets / Phantom')], 'BoM Type', required=True,
                                 help= "If a by-product is used in several products, it can be useful to create its own BoM. "\
                                 "Though if you don't want separated production orders for this by-product, select Set/Phantom as BoM type. "\
                                 "If a Phantom BoM is used for a root product, it will be sold and shipped as a set of components, instead of being produced."),
        'date_start': fields.date('Valid From', help="Validity of this BoM or component. Keep empty if it's always valid."),
        'date_stop': fields.date('Valid Until', help="Validity of this BoM or component. Keep empty if it's always valid."),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of bills of material."),
        'position': fields.char('Internal Reference', size=64, help="Reference to a position in an external plan."),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_uos_qty': fields.float('Product UOS Qty'),
        'product_uos': fields.many2one('product.uom', 'Product UOS', help="Product UOS (Unit of Sale) is the unit of measurement for the invoicing and promotion of stock."),
        'product_qty': fields.float('Product Quantity', required=True, digits_compute=dp.get_precision('Product Unit of Measure')),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True, help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control"),
        'product_rounding': fields.float('Product Rounding', help="Rounding applied on the product quantity."),
        'product_efficiency': fields.float('Manufacturing Efficiency', required=True, help="A factor of 0.9 means a loss of 10% within the production process."),
        'bom_lines': fields.one2many('mrp.bom', 'bom_id', 'BoM Lines'),
        'bom_id': fields.many2one('mrp.bom', 'Parent BoM', ondelete='cascade', select=True),
        'routing_id': fields.many2one('mrp.routing', 'Routing', help="The list of operations (list of work centers) to produce the finished product. The routing is mainly used to compute work center costs during operations and to plan future loads on work centers based on production planning."),
        'property_ids': fields.many2many('mrp.property', 'mrp_bom_property_rel', 'bom_id', 'property_id', 'Properties'),
        'child_complete_ids': fields.function(_child_compute, relation='mrp.bom', string="BoM Hierarchy", type='many2many'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
    }
    _defaults = {
        'active': lambda *a: 1,
        'product_efficiency': lambda *a: 1.0,
        'product_qty': lambda *a: 1.0,
        'product_rounding': lambda *a: 0.0,
        'type': lambda *a: 'normal',
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'mrp.bom', context=c),
    }
    _order = "sequence"
    _parent_name = "bom_id"
    _sql_constraints = [
        ('bom_qty_zero', 'CHECK (product_qty>0)', 'All product quantities must be greater than 0.\n' \
            'You should install the mrp_byproduct module if you want to manage extra products on BoMs !'),
    ]

    def _check_recursion(self, cr, uid, ids, context=None):
        level = 100
        while len(ids):
            cr.execute('select distinct bom_id from mrp_bom where id IN %s', (tuple(ids),))
            ids = filter(None, map(lambda x: x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    def _check_product(self, cr, uid, ids, context=None):
        all_prod = []
        boms = self.browse(cr, uid, ids, context=context)
        def check_bom(boms):
            res = True
            for bom in boms:
                if bom.product_id.id in all_prod:
                    res = res and False
                all_prod.append(bom.product_id.id)
                lines = bom.bom_lines
                if lines:
                    res = res and check_bom([bom_id for bom_id in lines if bom_id not in boms])
            return res
        return check_bom(boms)

    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive BoM.', ['parent_id']),
        (_check_product, 'BoM line product should not be same as BoM product.', ['product_id']),
    ]

    def onchange_product_id(self, cr, uid, ids, product_id, name, product_qty=0, context=None):
        """ Changes UoM and name if product_id changes.
        @param name: Name of the field
        @param product_id: Changed product_id
        @return:  Dictionary of changed values
        """
        res = {}
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            res['value'] = {'name': prod.name, 'product_uom': prod.uom_id.id, 'product_uos_qty': 0, 'product_uos': False}
            if prod.uos_id.id:
                res['value']['product_uos_qty'] = product_qty * prod.uos_coeff
                res['value']['product_uos'] = prod.uos_id.id
        return res

    def onchange_uom(self, cr, uid, ids, product_id, product_uom, context=None):
        res = {'value': {}}
        if not product_uom or not product_id:
            return res
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        uom = self.pool.get('product.uom').browse(cr, uid, product_uom, context=context)
        if uom.category_id.id != product.uom_id.category_id.id:
            res['warning'] = {'title': _('Warning'), 'message': _('The Product Unit of Measure you chose has a different category than in the product form.')}
            res['value'].update({'product_uom': product.uom_id.id})
        return res

    def _bom_find(self, cr, uid, product_id, product_uom, properties=None):
        """ Finds BoM for particular product and product uom.
        @param product_id: Selected product.
        @param product_uom: Unit of measure of a product.
        @param properties: List of related properties.
        @return: False or BoM id.
        """
        if properties is None:
            properties = []
        domain = [('product_id', '=', product_id), ('bom_id', '=', False),
            '|', ('date_start', '=', False), ('date_start', '<=', time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
            '|', ('date_stop', '=', False), ('date_stop', '>=', time.strftime(DEFAULT_SERVER_DATETIME_FORMAT))]
        ids = self.search(cr, uid, domain)
        max_prop = 0
        result = False
        for bom in self.pool.get('mrp.bom').browse(cr, uid, ids):
            prop = 0
            for prop_id in bom.property_ids:
                if prop_id.id in properties:
                    prop += 1
            if (prop > max_prop) or ((max_prop == 0) and not result):
                result = bom.id
                max_prop = prop
        return result

    def _bom_explode(self, cr, uid, bom, factor, properties=None, addthis=False, level=0, routing_id=False):
        """ Finds Products and Work Centers for related BoM for manufacturing order.
        @param bom: BoM of particular product.
        @param factor: Factor of product UoM.
        @param properties: A List of properties Ids.
        @param addthis: If BoM found then True else False.
        @param level: Depth level to find BoM lines starts from 10.
        @return: result: List of dictionaries containing product details.
                 result2: List of dictionaries containing Work Center details.
        """
        routing_obj = self.pool.get('mrp.routing')
        factor = factor / (bom.product_efficiency or 1.0)
        factor = _common.ceiling(factor, bom.product_rounding)
        if factor < bom.product_rounding:
            factor = bom.product_rounding
        result = []
        result2 = []
        phantom = False
        if bom.type == 'phantom' and not bom.bom_lines:
            newbom = self._bom_find(cr, uid, bom.product_id.id, bom.product_uom.id, properties)

            if newbom:
                res = self._bom_explode(cr, uid, self.browse(cr, uid, [newbom])[0], factor * bom.product_qty, properties, addthis=True, level=level + 10)
                result = result + res[0]
                result2 = result2 + res[1]
                phantom = True
            else:
                phantom = False
        if not phantom:
            if addthis and not bom.bom_lines:
                result.append({
                    'name': bom.product_id.name,
                    'product_id': bom.product_id.id,
                    'product_qty': bom.product_qty * factor,
                    'product_uom': bom.product_uom.id,
                    'product_uos_qty': bom.product_uos and bom.product_uos_qty * factor or False,
                    'product_uos': bom.product_uos and bom.product_uos.id or False,
                })
            routing = (routing_id and routing_obj.browse(cr, uid, routing_id)) or bom.routing_id or False
            if routing:
                for wc_use in routing.workcenter_lines:
                    wc = wc_use.workcenter_id
                    d, m = divmod(factor, wc_use.workcenter_id.capacity_per_cycle)
                    mult = (d + (m and 1.0 or 0.0))
                    cycle = mult * wc_use.cycle_nbr
                    result2.append({
                        'name': tools.ustr(wc_use.name) + ' - ' + tools.ustr(bom.product_id.name),
                        'workcenter_id': wc.id,
                        'sequence': level + (wc_use.sequence or 0),
                        'cycle': cycle,
                        'hour': float(wc_use.hour_nbr * mult + ((wc.time_start or 0.0) + (wc.time_stop or 0.0) + cycle * (wc.time_cycle or 0.0)) * (wc.time_efficiency or 1.0)),
                    })
            for bom2 in bom.bom_lines:
                res = self._bom_explode(cr, uid, bom2, factor, properties, addthis=True, level=level + 10)
                result = result + res[0]
                result2 = result2 + res[1]
        return result, result2

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        bom_data = self.read(cr, uid, id, [], context=context)
        default.update(name=_("%s (copy)") % (bom_data['name']), bom_id=False)
        return super(mrp_bom, self).copy_data(cr, uid, id, default, context=context)


class mrp_production(osv.osv):
    """
    Production Orders / Manufacturing Orders
    """
    _name = 'mrp.production'
    _description = 'Manufacturing Order'
    _date_name = 'date_planned'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    def _production_calc(self, cr, uid, ids, prop, unknow_none, context=None):
        """ Calculates total hours and total no. of cycles for a production order.
        @param prop: Name of field.
        @param unknow_none:
        @return: Dictionary of values.
        """
        result = {}
        for prod in self.browse(cr, uid, ids, context=context):
            result[prod.id] = {
                'hour_total': 0.0,
                'cycle_total': 0.0,
            }
            for wc in prod.workcenter_lines:
                result[prod.id]['hour_total'] += wc.hour
                result[prod.id]['cycle_total'] += wc.cycle
        return result

    def _src_id_default(self, cr, uid, ids, context=None):
        try:
            location_model, location_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'stock_location_stock')
            self.pool.get('stock.location').check_access_rule(cr, uid, [location_id], 'read', context=context)
        except (orm.except_orm, ValueError):
            location_id = False
        return location_id

    def _dest_id_default(self, cr, uid, ids, context=None):
        try:
            location_model, location_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'stock_location_stock')
            self.pool.get('stock.location').check_access_rule(cr, uid, [location_id], 'read', context=context)
        except (orm.except_orm, ValueError):
            location_id = False
        return location_id

    def _get_progress(self, cr, uid, ids, name, arg, context=None):
        """ Return product quantity percentage """
        result = dict.fromkeys(ids, 100)
        for mrp_production in self.browse(cr, uid, ids, context=context):
            if abs(mrp_production.product_qty):
                done = 0.0
                for move in mrp_production.move_created_ids2:
                    if not move.scrapped and move.product_id == mrp_production.product_id:
                        done += move.product_qty
                result[mrp_production.id] = done / abs(mrp_production.product_qty) * 100
        return result

    def create(self, cr, uid, values, context=None):
        if values['product_qty'] < 0:
            self._description = _('Disassemble Order')
        return super(mrp_production, self).create(cr, uid, values, context=context)

    def _moves_assigned(self, cr, uid, ids, name, arg, context=None):
        """ Test whether all the consume lines are assigned """
        res = {}
        for production in self.browse(cr, uid, ids, context=context):
            res[production.id] = True
            states = [x.state != 'assigned' for x in production.move_lines if x]
            if any(states) or len(states) == 0:
                res[production.id] = False
        return res

    def _mrp_from_move(self, cr, uid, ids, context=None):
        """ Return mrp"""
        res = []
        for move in self.browse(cr, uid, ids, context=context):
            res += self.pool.get("mrp.production").search(cr, uid, [('move_lines', 'in', move.id)], context=context)
        return res

    _columns = {
        'name': fields.char('Reference', size=64, required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'origin': fields.char('Source Document', size=64, readonly=True, states={'draft': [('readonly', False)]},
            help="Reference of the document that generated this production order request."),
        'priority': fields.selection([('0', 'Not urgent'), ('1', 'Normal'), ('2', 'Urgent'), ('3', 'Very Urgent')], 'Priority',
            select=True, readonly=True, states=dict.fromkeys(['draft', 'confirmed'], [('readonly', False)])),

        'product_id': fields.many2one('product.product', 'Product', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'product_qty': fields.float('Product Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'product_uos_qty': fields.float('Product UoS Quantity', readonly=True, states={'draft': [('readonly', False)]}),
        'product_uos': fields.many2one('product.uom', 'Product UoS', readonly=True, states={'draft': [('readonly', False)]}),
        'progress': fields.function(_get_progress, type='float',
            string='Production progress'),

        'location_src_id': fields.many2one('stock.location', 'Raw Materials Location', required=True,
            readonly=True, states={'draft': [('readonly', False)]},
            help="Location where the system will look for components."),
        'location_dest_id': fields.many2one('stock.location', 'Finished Products Location', required=True,
            readonly=True, states={'draft': [('readonly', False)]},
            help="Location where the system will stock the finished products."),
        'date_planned': fields.datetime('Scheduled Date', required=True, select=1, readonly=True, states={'draft': [('readonly', False)]}),
        'date_start': fields.datetime('Start Date', select=True, readonly=True),
        'date_finished': fields.datetime('End Date', select=True, readonly=True),
        'bom_id': fields.many2one('mrp.bom', 'Bill of Material', domain=[('bom_id', '=', False)], readonly=True, states={'draft': [('readonly', False)]},
            help="Bill of Materials allow you to define the list of required raw materials to make a finished product."),
        'routing_id': fields.many2one('mrp.routing', string='Routing', on_delete='set null', readonly=True, states={'draft': [('readonly', False)]},
            help="The list of operations (list of work centers) to produce the finished product. The routing is mainly used to compute work center costs during operations and to plan future loads on work centers based on production plannification."),
        'move_prod_id': fields.many2one('stock.move', 'Product Move', readonly=True),
        'move_lines': fields.one2many('stock.move', 'raw_material_production_id', 'Products to Consume',
            domain=[('state', 'not in', ('done', 'cancel'))], readonly=True, states={'draft': [('readonly', False)]}),
        'move_lines2': fields.one2many('stock.move', 'raw_material_production_id', 'Consumed Products',
            domain=[('state', 'in', ('done', 'cancel'))], readonly=True),
        'move_created_ids': fields.one2many('stock.move', 'production_id', 'Products to Produce',
            domain=[('state', 'not in', ('done', 'cancel'))], readonly=True),
        'move_created_ids2': fields.one2many('stock.move', 'production_id', 'Produced Products',
            domain=[('state', 'in', ('done', 'cancel'))], readonly=True),
        'product_lines': fields.one2many('mrp.production.product.line', 'production_id', 'Scheduled goods',
            readonly=True),
        'workcenter_lines': fields.one2many('mrp.production.workcenter.line', 'production_id', 'Work Centers Utilisation',
            readonly=True, states={'draft': [('readonly', False)]}),
        'state': fields.selection(
            [('draft', 'New'), ('cancel', 'Cancelled'), ('confirmed', 'Awaiting Raw Materials'),
                ('ready', 'Ready to Produce'), ('in_production', 'Production Started'), ('done', 'Done')],
            string='Status', readonly=True,
            track_visibility='onchange',
            help="When the production order is created the status is set to 'Draft'.\n\
                If the order is confirmed the status is set to 'Waiting Goods'.\n\
                If any exceptions are there, the status is set to 'Picking Exception'.\n\
                If the stock is available then the status is set to 'Ready to Produce'.\n\
                When the production gets started then the status is set to 'In Production'.\n\
                When the production is over, the status is set to 'Done'."),
        'hour_total': fields.function(_production_calc, type='float', string='Total Hours', multi='workorder', store=True),
        'cycle_total': fields.function(_production_calc, type='float', string='Total Cycles', multi='workorder', store=True),
        'disassemble': fields.boolean('Disassemble'),
        'disassemble_doc': fields.char('Disassemble Document(s)', size=64, readonly=True, help="Reference of disassembled document(s) for this Manufacturing Order."),
        'qty_to_disassemble': fields.float('Remaining Quantity to Disassemble', help="Available product quantity to disassemble", digits_compute=dp.get_precision('Product Unit of Measure')),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'ready_production': fields.function(_moves_assigned, type='boolean', store={'stock.move': (_mrp_from_move, ['state'], 10)}),
    }

    _defaults = {
        'priority': lambda *a: '1',
        'state': lambda *a: 'draft',
        'date_planned': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'product_qty': lambda *a: 1.0,
        'user_id': lambda self, cr, uid, c: uid,
        'name': lambda x, y, z, c: x.pool.get('ir.sequence').get(y, z, 'mrp.production') or '/',
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'mrp.production', context=c),
        'location_src_id': _src_id_default,
        'location_dest_id': _dest_id_default,
        'disassemble': False,
        'disassemble_doc': False
    }

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per Company!'),
    ]

    _order = 'priority desc, date_planned asc'

    def _check_qty(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            if order.product_qty == 0:
                return False
        return True

    _constraints = [
        (_check_qty, 'Order quantity cannot be zero!', ['product_qty']),
    ]

    def unlink(self, cr, uid, ids, context=None):
        for production in self.browse(cr, uid, ids, context=context):
            if production.state not in ('draft', 'cancel'):
                raise osv.except_osv(_('Invalid Action!'), _('Cannot delete a manufacturing order in state \'%s\'.') % production.state)
        return super(mrp_production, self).unlink(cr, uid, ids, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        mo = self.browse(cr, uid, id, context=context)
        origin = False
        if default.get('disassemble'):
            origin = mo.origin + '-' + mo.name if not mo.disassemble and mo.origin else mo.name
        if not mo.disassemble:
            origin = mo.origin
        default.update({
            'name': self.pool.get('ir.sequence').get(cr, uid, 'mrp.production'),
            'move_lines': [],
            'move_lines2': [],
            'move_created_ids': [],
            'move_created_ids2': [],
            'product_lines': [],
            'move_prod_id': False,
            'origin': origin,
        })
        return super(mrp_production, self).copy(cr, uid, id, default, context)

    def location_id_change(self, cr, uid, ids, src, dest, context=None):
        """ Changes destination location if source location is changed.
        @param src: Source location id.
        @param dest: Destination location id.
        @return: Dictionary of values.
        """
        if dest:
            return {}
        if src:
            return {'value': {'location_dest_id': src}}
        return {}

    def onchange_product_qty(self, cr, uid, ids, quantity, context=None):
        if quantity < 0:
            return {'value': {'disassemble': True, 'qty_to_disassemble': 0.0}}
        return {'value': {'disassemble': False, 'qty_to_disassemble': quantity}}

    def product_id_change(self, cr, uid, ids, product_id, product_qty=0, context=None):
        """ Finds UoM of changed product.
        @param product_id: Id of changed product.
        @return: Dictionary of values.
        """
        result = {}
        if not product_id:
            return {'value': {
                'product_uom': False,
                'bom_id': False,
                'routing_id': False,
                'product_uos_qty': 0,
                'product_uos': False
            }}
        bom_obj = self.pool.get('mrp.bom')
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        bom_id = bom_obj._bom_find(cr, uid, product.id, product.uom_id and product.uom_id.id, [])
        routing_id = False
        if bom_id:
            bom_point = bom_obj.browse(cr, uid, bom_id, context=context)
            routing_id = bom_point.routing_id.id or False
        product_uom_id = product.uom_id and product.uom_id.id or False
        result['value'] = {'product_uos_qty': 0, 'product_uos': False, 'product_uom': product_uom_id, 'bom_id': bom_id, 'routing_id': routing_id}
        if product.uos_id.id:
            result['value']['product_uos_qty'] = product_qty * product.uos_coeff
            result['value']['product_uos'] = product.uos_id.id
        return result

    def bom_id_change(self, cr, uid, ids, bom_id, context=None):
        """ Finds routing for changed BoM.
        @param product: Id of product.
        @return: Dictionary of values.
        """
        if not bom_id:
            return {'value': {
                'routing_id': False
            }}
        bom_point = self.pool.get('mrp.bom').browse(cr, uid, bom_id, context=context)
        routing_id = bom_point.routing_id.id or False
        result = {
            'routing_id': routing_id
        }
        return {'value': result}


    def _action_compute_lines(self, cr, uid, ids, properties=None, context=None):
        """ Compute product_lines and workcenter_lines from BoM structure
        @return: product_lines
        """
        if properties is None:
            properties = []
        results = []
        bom_obj = self.pool.get('mrp.bom')
        uom_obj = self.pool.get('product.uom')
        prod_line_obj = self.pool.get('mrp.production.product.line')
        workcenter_line_obj = self.pool.get('mrp.production.workcenter.line')
        for production in self.browse(cr, uid, ids, context=context):
            #unlink product_lines
            prod_line_obj.unlink(cr, SUPERUSER_ID, [line.id for line in production.product_lines], context=context)
            #unlink workcenter_lines
            workcenter_line_obj.unlink(cr, SUPERUSER_ID, [line.id for line in production.workcenter_lines], context=context)
            # search BoM structure and route
            bom_point = production.bom_id
            bom_id = production.bom_id.id
            if not bom_point:
                bom_id = bom_obj._bom_find(cr, uid, production.product_id.id, production.product_uom.id, properties)
                if bom_id:
                    bom_point = bom_obj.browse(cr, uid, bom_id)
                    routing_id = bom_point.routing_id.id or False
                    self.write(cr, uid, [production.id], {'bom_id': bom_id, 'routing_id': routing_id})
    
            if not bom_id:
                raise osv.except_osv(_('Error!'), _("Cannot find a bill of material for this product."))

            # get components and workcenter_lines from BoM structure
            factor = uom_obj._compute_qty(cr, uid, production.product_uom.id, abs(production.product_qty), bom_point.product_uom.id)
            res = bom_obj._bom_explode(cr, uid, bom_point, factor / bom_point.product_qty, properties, routing_id=production.routing_id.id)
            results = res[0]  # product_lines
            results2 = res[1]  # workcenter_lines
            # reset product_lines in production order
            for line in results:
                line['production_id'] = production.id
                prod_line_obj.create(cr, uid, line)

            #reset workcenter_lines in production order
            for line in results2:
                line['production_id'] = production.id
                workcenter_line_obj.create(cr, uid, line)
        return results

    def action_compute(self, cr, uid, ids, properties=None, context=None):
        """ Computes bills of material of a product.
        @param properties: List containing dictionaries of properties.
        @return: No. of products.
        """
        return len(self._action_compute_lines(cr, uid, ids, properties=properties, context=context))

    def action_disassemble(self, cr, uid, id, qty, context=None):
        """ Disassemble the production order.
        """
        mo = self.browse(cr, uid, id, context=context)
        values = {
            'disassemble': True,
            'origin': mo.name,
            'routing_id': False,
            'product_qty': qty,
            'qty_to_disassemble': 0,
        }
        mo_id = self.copy(cr, uid, mo.id, values, context=context)
        if mo_id:
            source_doc = self.read(cr, uid, mo_id, ['name'], context=context)
            mo.write({'disassemble_doc': mo.disassemble_doc and mo.disassemble_doc + ", " + source_doc['name'] or source_doc['name']}, context=context)
        view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'mrp', 'mrp_production_form_view')
        view_id = view_ref and view_ref[1] or False,
        return {
            'type': 'ir.actions.act_window',
            'name': _('Disassemble Manufacturing Order'),
            'res_model': 'mrp.production',
            'res_id': mo_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'target': 'current',
        }

    def action_cancel(self, cr, uid, ids, context=None):
        """ Cancels the production order and related stock moves.
        @return: True
        """
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')
        for production in self.browse(cr, uid, ids, context=context):
            if production.move_created_ids:
                move_obj.action_cancel(cr, uid, [x.id for x in production.move_created_ids])
            move_obj.action_cancel(cr, uid, [x.id for x in production.move_lines])
        self.write(cr, uid, ids, {'state': 'cancel'})
        # Put related procurements in exception
        proc_obj = self.pool.get("procurement.order")
        procs = proc_obj.search(cr, uid, [('production_id', 'in', ids)], context=context)
        if procs:
            proc_obj.write(cr, uid, procs, {'state': 'exception'}, context=context)
        return True

    def action_ready(self, cr, uid, ids, context=None):
        """ Changes the production state to Ready and location id of stock move.
        @return: True
        """
        move_obj = self.pool.get('stock.move')
        self.write(cr, uid, ids, {'state': 'ready'})

        for production in self.browse(cr, uid, ids, context=context):
            if not production.move_created_ids:
                self._make_production_produce_line(cr, uid, production, context=context)

            if production.move_prod_id and production.move_prod_id.location_id.id != production.location_dest_id.id:
                move_obj.write(cr, uid, [production.move_prod_id.id],
                        {'location_id': production.location_dest_id.id})
        return True

    def action_production_end(self, cr, uid, ids, context=None):
        """ Changes production state to Finish and writes finished date.
        @return: True
        """
        for production in self.browse(cr, uid, ids):
            self._costs_generate(cr, uid, production)
        write_res = self.write(cr, uid, ids, {'state': 'done', 'date_finished': time.strftime('%Y-%m-%d %H:%M:%S')})
        # Check related procurements
        proc_obj = self.pool.get("procurement.order")
        procs = proc_obj.search(cr, uid, [('production_id', 'in', ids)], context=context)
        proc_obj.check(cr, uid, procs, context=context)
        return write_res

    def test_production_done(self, cr, uid, ids):
        """ Tests whether production is done or not.
        @return: True or False
        """
        res = True
        for production in self.browse(cr, uid, ids):
            if production.move_lines:
                res = False

            if production.move_created_ids:
                res = False
        return res

    def _get_subproduct_factor(self, cr, uid, production_id, move_id=None, context=None):
        """ Compute the factor to compute the qty of procucts to produce for the given production_id. By default,
            it's always equal to the quantity encoded in the production order or the production wizard, but if the
            module mrp_subproduct is installed, then we must use the move_id to identify the product to produce
            and its quantity.
        :param production_id: ID of the mrp.order
        :param move_id: ID of the stock move that needs to be produced. Will be used in mrp_subproduct.
        :return: The factor to apply to the quantity that we should produce for the given production order.
        """
        return 1

    def _get_produced_qty(self, cr, uid, production, context=None):
        ''' returns the produced quantity of product 'production.product_id' for the given production, in the product UoM
        '''
        produced_qty = 0
        for produced_product in production.move_created_ids2:
            if (produced_product.scrapped) or (produced_product.product_id.id != production.product_id.id):
                continue
            produced_qty += produced_product.product_qty
        return produced_qty

    def _get_consumed_data(self, cr, uid, production, context=None):
        ''' returns a dictionary containing for each raw material of the given production, its quantity already consumed (in the raw material UoM)
        '''
        consumed_data = {}
        # Calculate already consumed qtys
        for consumed in production.move_lines2:
            if consumed.scrapped:
                continue
            if not consumed_data.get(consumed.product_id.id, False):
                consumed_data[consumed.product_id.id] = 0
            consumed_data[consumed.product_id.id] += consumed.product_qty
        return consumed_data

    def _calculate_qty(self, cr, uid, production, product_qty=0.0, context=None):
        """
            Calculates the quantity still needed to produce an extra number of products
        """
        quant_obj = self.pool.get("stock.quant")
        produced_qty = self._get_produced_qty(cr, uid, production, context=context)
        consumed_data = self._get_consumed_data(cr, uid, production, context=context)

        #In case no product_qty is given, take the remaining qty to produce for the given production
        if not product_qty:
            product_qty = production.product_qty - produced_qty

        dicts = {}
        # Find product qty to be consumed and consume it
        for scheduled in production.product_lines:
            consumed_qty = consumed_data.get(scheduled.product_id.id, 0.0)
            # qty available for consume and produce
            qty_avail = scheduled.product_qty - consumed_qty
            if qty_avail <= 0.0:
                # there will be nothing to consume for this raw material
                continue

            if not dicts.get(scheduled.product_id.id):
                dicts[scheduled.product_id.id] = {}

            # total qty of consumed product we need after this consumption
            total_consume = ((product_qty + produced_qty) * scheduled.product_qty / abs(production.product_qty))
            qty = total_consume - consumed_qty

            # Search for quants related to this related move
            for move in production.move_lines:
                if qty <= 0.0:
                    break
                if move.product_id.id != scheduled.product_id.id:
                    continue
                product_id = scheduled.product_id.id

                q = min(move.product_qty, qty)
                quants = quant_obj.quants_get_prefered_domain(cr, uid, move.location_id, scheduled.product_id, q, domain=[('qty', '>', 0.0)],
                                                     prefered_domain_list=[[('reservation_id', '=', move.id)], [('reservation_id', '=', False)]], context=context)
                for quant, quant_qty in quants:
                    if quant:
                        lot_id = quant.lot_id.id
                        if not product_id in dicts.keys():
                            dicts[product_id] = {lot_id: quant_qty}
                        elif lot_id in dicts[product_id].keys():
                            dicts[product_id][lot_id] += quant_qty
                        else:
                            dicts[product_id][lot_id] = quant_qty
                        qty -= quant_qty
            if qty > 0:
                if dicts[product_id].get(False):
                    dicts[product_id][False] += qty
                else:
                    dicts[product_id][False] = qty

        consume_lines = []
        for prod in dicts.keys():
            for lot, qty in dicts[prod].items():
                consume_lines.append({'product_id': prod, 'product_qty': qty, 'lot_id': lot})
        return consume_lines

    def action_produce(self, cr, uid, production_id, production_qty, production_mode, wiz=False, context=None):
        """ To produce final product based on production mode (consume/consume&produce).
        If Production mode is consume, all stock move lines of raw materials will be done/consumed.
        If Production mode is consume & produce, all stock move lines of raw materials will be done/consumed
        and stock move lines of final product will be also done/produced.
        @param production_id: the ID of mrp.production object
        @param production_qty: specify qty to produce
        @param production_mode: specify production mode (consume/consume&produce).
        @param wiz: the mrp produce product wizard, which will tell the amount of consumed products needed
        @return: True
        """
        stock_mov_obj = self.pool.get('stock.move')
        production = self.browse(cr, uid, production_id, context=context)
        if not production.move_lines and production.state == 'ready':
            # trigger workflow if not products to consume (eg: services)
            self.signal_button_produce(cr, uid, [production_id])

        produced_qty = self._get_produced_qty(cr, uid, production, context=context)

        main_production_move = False
        if production_mode == 'consume_produce':
            # To produce remaining qty of final product
            #vals = {'state':'confirmed'}
            #final_product_todo = [x.id for x in production.move_created_ids]
            #stock_mov_obj.write(cr, uid, final_product_todo, vals)
            #stock_mov_obj.action_confirm(cr, uid, final_product_todo, context)
            produced_products = {}
            for produced_product in production.move_created_ids2:
                if produced_product.scrapped:
                    continue
                if not produced_products.get(produced_product.product_id.id, False):
                    produced_products[produced_product.product_id.id] = 0
                produced_products[produced_product.product_id.id] += produced_product.product_qty

            for produce_product in production.move_created_ids:
                produced_qty = produced_products.get(produce_product.product_id.id, 0)
                subproduct_factor = self._get_subproduct_factor(cr, uid, production.id, produce_product.id, context=context)
                rest_qty = (subproduct_factor * abs(production.product_qty)) - produced_qty
                if float_compare(rest_qty, (subproduct_factor * production_qty), precision_rounding=produce_product.product_id.uom_id.rounding) < 0:
                    prod_name = produce_product.product_id.name_get()[0][1]
                    raise osv.except_osv(_('Warning!'), _('You are going to produce total %s quantities of "%s".\nBut you can only produce up to total %s quantities.') % ((subproduct_factor * production_qty), prod_name, rest_qty))
                if float_compare(rest_qty, 0, precision_rounding=produce_product.product_id.uom_id.rounding) > 0:
                    lot_id = False
                    if wiz:
                        lot_id = wiz.lot_id.id
                    new_moves = stock_mov_obj.action_consume(cr, uid, [produce_product.id], (subproduct_factor * production_qty), location_id=produce_product.location_id.id, restrict_lot_id=lot_id, context=context)
                    stock_mov_obj.write(cr, uid, new_moves, {'production_id': production_id}, context=context)
                    if produce_product.product_id.id == production.product_id.id and new_moves:
                        main_production_move = new_moves[0]

        if production_mode in ['consume', 'consume_produce']:
            if wiz:
                consume_lines = []
                for cons in wiz.consume_lines:
                    consume_lines.append({'product_id': cons.product_id.id, 'lot_id': cons.lot_id.id, 'product_qty': cons.product_qty})
            else:
                consume_lines = self._calculate_qty(cr, uid, production, production_qty, context=context)
            for consume in consume_lines:
                remaining_qty = consume['product_qty']
                for raw_material_line in production.move_lines:
                    if remaining_qty <= 0:
                        break
                    if consume['product_id'] != raw_material_line.product_id.id:
                        continue
                    consumed_qty = min(remaining_qty, raw_material_line.product_qty)
                    stock_mov_obj.action_consume(cr, uid, [raw_material_line.id], consumed_qty, raw_material_line.location_id.id, restrict_lot_id=consume['lot_id'], consumed_for=main_production_move, context=context)
                    remaining_qty -= consumed_qty
                if remaining_qty:
                    #consumed more in wizard than previously planned
                    product = self.pool.get('product.product').browse(cr, uid, consume['product_id'], context=context)
                    extra_move_id = self._make_consume_line_from_data(cr, uid, production, product, product.uom_id.id, remaining_qty, False, 0, context=context)
                    stock_mov_obj.action_done(cr, uid, [extra_move_id], context=context)

        self.message_post(cr, uid, production_id, body=_("%s produced") % self._description, context=context)
        self.signal_button_produce_done(cr, uid, [production_id])
        return True

    def _costs_generate(self, cr, uid, production):
        """ Calculates total costs at the end of the production.
        @param production: Id of production order.
        @return: Calculated amount.
        """
        amount = 0.0
        analytic_line_obj = self.pool.get('account.analytic.line')
        for wc_line in production.workcenter_lines:
            wc = wc_line.workcenter_id
            if wc.costs_journal_id and wc.costs_general_account_id:
                # Cost per hour
                value = wc_line.hour * wc.costs_hour
                account = wc.costs_hour_account_id.id
                if value and account:
                    amount += value
                    # we user SUPERUSER_ID as we do not garantee an mrp user
                    # has access to account analytic lines but still should be
                    # able to produce orders
                    analytic_line_obj.create(cr, SUPERUSER_ID, {
                        'name': wc_line.name + ' (H)',
                        'amount': value,
                        'account_id': account,
                        'general_account_id': wc.costs_general_account_id.id,
                        'journal_id': wc.costs_journal_id.id,
                        'ref': wc.code,
                        'product_id': wc.product_id.id,
                        'unit_amount': wc_line.hour,
                        'product_uom_id': wc.product_id and wc.product_id.uom_id.id or False
                    })
                # Cost per cycle
                value = wc_line.cycle * wc.costs_cycle
                account = wc.costs_cycle_account_id.id
                if value and account:
                    amount += value
                    analytic_line_obj.create(cr, SUPERUSER_ID, {
                        'name': wc_line.name + ' (C)',
                        'amount': value,
                        'account_id': account,
                        'general_account_id': wc.costs_general_account_id.id,
                        'journal_id': wc.costs_journal_id.id,
                        'ref': wc.code,
                        'product_id': wc.product_id.id,
                        'unit_amount': wc_line.cycle,
                        'product_uom_id': wc.product_id and wc.product_id.uom_id.id or False
                    })
        return amount

    def action_in_production(self, cr, uid, ids, context=None):
        """ Changes state to In Production and writes starting date.
        @return: True
        """
        return self.write(cr, uid, ids, {'state': 'in_production', 'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})

    def consume_lines_get(self, cr, uid, ids, *args):
        res = []
        for order in self.browse(cr, uid, ids, context={}):
            res += [x.id for x in order.move_lines]
        return res

    def test_ready(self, cr, uid, ids):
        res = False
        for production in self.browse(cr, uid, ids):
            if production.ready_production:
                res = True
        return res
    
    
    def _make_production_produce_line(self, cr, uid, production, context=None):
        stock_move = self.pool.get('stock.move')
        source_location_id = production.product_id.property_stock_production.id
        destination_location_id = production.location_dest_id.id
        data = {
            'name': production.name,
            'date': production.date_planned,
            'product_id': production.product_id.id,
            'product_uom': production.product_uom.id,
            'product_uom_qty': abs(production.product_qty),
            'product_uos_qty': production.product_uos and production.product_uos_qty or False,
            'product_uos': production.product_uos and production.product_uos.id or False,
            'location_id': production.disassemble and destination_location_id or source_location_id,
            'location_dest_id': production.disassemble and source_location_id or destination_location_id,
            'move_dest_id': production.move_prod_id.id,
            'company_id': production.company_id.id,
            'production_id': production.id,
            'origin': production.name,
            'state': production.disassemble and 'assigned' or 'waiting', # for products to produce
        }
        move_id = stock_move.create(cr, uid, data, context=context)
        #a phantom bom cannot be used in mrp order so it's ok to assume the list returned by action_confirm
        #is 1 element long, so we can take the first.
        return stock_move.action_confirm(cr, uid, [move_id], context=context)[0]

    def _get_raw_material_procure_method(self, cr, uid, product, context=None):
        '''This method returns the procure_method to use when creating the stock move for the production raw materials'''
        try:
            mto_route = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'route_warehouse0_mto')[1]
        except:
            return "make_to_stock"
        routes = product.route_ids + product.categ_id.total_route_ids
        if mto_route in [x.id for x in routes]:
            return "make_to_order"
        return "make_to_stock"

    def _make_consume_line_from_data(self, cr, uid, production, product, uom_id, qty, uos_id, uos_qty, context=None):
        stock_move = self.pool.get('stock.move')
        # Internal shipment is created for Stockable and Consumer Products
        if product.type not in ('product', 'consu'):
            return False
        # Take routing location as a Source Location.
        source_location_id = production.location_src_id.id
        if production.bom_id.routing_id and production.bom_id.routing_id.location_id:
            source_location_id = production.bom_id.routing_id.location_id.id

        destination_location_id = production.product_id.property_stock_production.id
        if not source_location_id:
            source_location_id = production.location_src_id.id
        move_id = stock_move.create(cr, uid, {
            'name': production.name,
            'date': production.date_planned,
            'product_id': product.id,
            'product_uom_qty': abs(qty),
            'product_uom': uom_id,
            'product_uos_qty': uos_id and uos_qty or False,
            'product_uos': uos_id or False,
            'location_id': source_location_id,
            'location_dest_id': destination_location_id,
            'company_id': production.company_id.id,
            'procure_method': self._get_raw_material_procure_method(cr, uid, product, context=context),
            'raw_material_production_id': production.id,
            #this saves us a browse in create()
            'price_unit': product.standard_price,
            'origin': production.name,
            'disassemble': production.disassemble,
        })
        return move_id

    def _make_production_consume_line(self, cr, uid, line, context=None):
        return self._make_consume_line_from_data(cr, uid, line.production_id, line.product_id, line.product_uom.id, line.product_qty, line.product_uos.id, line.product_uos_qty, context=context)

    def action_confirm(self, cr, uid, ids, context=None):
        """ Confirms production order.
        @return: Newly generated Shipment Id.
        """
        uncompute_ids = filter(lambda x: x, [not x.product_lines and x.id or False for x in self.browse(cr, uid, ids, context=context)])
        self.action_compute(cr, uid, uncompute_ids, context=context)
        for production in self.browse(cr, uid, ids, context=context):
            self._make_production_produce_line(cr, uid, production, context=context)

            stock_moves = []
            for line in production.product_lines:
                stock_move_id = self._make_production_consume_line(cr, uid, line, context=context)
                if stock_move_id:
                    stock_moves.append(stock_move_id)
            if stock_moves:
                self.pool.get('stock.move').action_confirm(cr, uid, stock_moves, context=context)
            production.write({'state': 'confirmed'}, context=context)
        return 0

    def action_assign(self, cr, uid, ids, context=None):
        """
        Checks the availability on the consume lines of the production order
        """
        move_obj = self.pool.get("stock.move")
        for production in self.browse(cr, uid, ids, context=context):
            move_obj.action_assign(cr, uid, [x.id for x in production.move_lines], context=context)


    def force_production(self, cr, uid, ids, *args):
        """ Assigns products.
        @param *args: Arguments
        @return: True
        """
        move_obj = self.pool.get('stock.move')
        for order in self.browse(cr, uid, ids):
            move_obj.force_assign(cr, uid, [x.id for x in order.move_lines])
        return True


class mrp_production_workcenter_line(osv.osv):
    _name = 'mrp.production.workcenter.line'
    _description = 'Work Order'
    _order = 'sequence'
    _inherit = ['mail.thread']

    _columns = {
        'name': fields.char('Work Order', size=64, required=True),
        'workcenter_id': fields.many2one('mrp.workcenter', 'Work Center', required=True),
        'cycle': fields.float('Number of Cycles', digits=(16, 2)),
        'hour': fields.float('Number of Hours', digits=(16, 2)),
        'sequence': fields.integer('Sequence', required=True, help="Gives the sequence order when displaying a list of work orders."),
        'production_id': fields.many2one('mrp.production', 'Manufacturing Order',
            track_visibility='onchange', select=True, ondelete='cascade', required=True),
    }
    _defaults = {
        'sequence': lambda *a: 1,
        'hour': lambda *a: 0,
        'cycle': lambda *a: 0,
    }

class mrp_production_product_line(osv.osv):
    _name = 'mrp.production.product.line'
    _description = 'Production Scheduled Product'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_qty': fields.float('Product Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'product_uos_qty': fields.float('Product UOS Quantity'),
        'product_uos': fields.many2one('product.uom', 'Product UOS'),
        'production_id': fields.many2one('mrp.production', 'Production Order', select=True),
    }

class product_product(osv.osv):
    _inherit = "product.product"
    def _bom_orders_count(self, cr, uid, ids, field_name, arg, context=None):
        Bom = self.pool('mrp.bom')
        Production = self.pool('mrp.production')
        return {
            product_id: {
                'bom_count': Bom.search_count(cr, uid, [('product_id', '=', product_id), ('bom_id', '=', False)], context=context),
                'mo_count': Production.search_count(cr,uid, [('product_id', '=', product_id)], context=context),
                'bom_strct': Bom.search_count(cr, uid, [('product_id', '=', product_id), ('bom_id', '=', False)], context=context),
            }
            for product_id in ids
        }
    _columns = {
        'bom_ids': fields.one2many('mrp.bom', 'product_id', 'Bill of Materials'),
        'bom_count': fields.function(_bom_orders_count, string='# Bill of Material', type='integer', multi="_bom_order_count"),
        'bom_strct': fields.function(_bom_orders_count, string='# Bill of Material Structure', type='integer', multi="_bom_order_count"),
        'mo_count': fields.function(_bom_orders_count, string='# Manufacturing Orders', type='integer', multi="_bom_order_count"),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
