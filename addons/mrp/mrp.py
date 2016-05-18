# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from collections import OrderedDict

import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools import float_compare, float_is_zero
from openerp.tools.translate import _
from openerp import tools, SUPERUSER_ID
from openerp.exceptions import UserError, AccessError


class mrp_property_group(osv.osv):
    """
    Group of mrp properties.
    """
    _name = 'mrp.property.group'
    _description = 'Property Group'
    _columns = {
        'name': fields.char('Property Group', required=True),
        'description': fields.text('Description'),
    }

class mrp_property(osv.osv):
    """
    Properties of mrp.
    """
    _name = 'mrp.property'
    _description = 'Property'
    _columns = {
        'name': fields.char('Name', required=True),
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
        'costs_hour_account_id': fields.many2one('account.analytic.account', 'Hour Account',
            help="Fill this only if you want automatic analytic accounting entries on production orders.", domain=[('account_type', '=', 'normal')]),
        'costs_cycle': fields.float('Cost per cycle', help="Specify Cost of Work Center per cycle."),
        'costs_cycle_account_id': fields.many2one('account.analytic.account', 'Cycle Account',
            help="Fill this only if you want automatic analytic accounting entries on production orders.", domain=[('account_type', '=', 'normal')]),
        'costs_general_account_id': fields.many2one('account.account', 'General Account', domain=[('deprecated', '=', False)]),
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

    def _check_capacity_per_cycle(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.capacity_per_cycle <= 0.0:
                return False
        return True

    _constraints = [
        (_check_capacity_per_cycle, 'The capacity per cycle must be strictly positive.', ['capacity_per_cycle']),
    ]

class mrp_routing(osv.osv):
    """
    For specifying the routings of Work Centers.
    """
    _name = 'mrp.routing'
    _description = 'Routings'
    _columns = {
        'name': fields.char('Name', required=True),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the routing without removing it."),
        'code': fields.char('Code', size=8),

        'note': fields.text('Description'),
        'workcenter_lines': fields.one2many('mrp.routing.workcenter', 'routing_id', 'Work Centers', copy=True),

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
    _order = 'sequence, id'
    _columns = {
        'workcenter_id': fields.many2one('mrp.workcenter', 'Work Center', required=True),
        'name': fields.char('Name', required=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of routing Work Centers."),
        'cycle_nbr': fields.float('Number of Cycles', required=True,
            help="Number of iterations this work center has to do in the specified operation of the routing."),
        'hour_nbr': fields.float('Number of Hours', required=True, help="Time in hours for this Work Center to achieve the operation of the specified routing."),
        'routing_id': fields.many2one('mrp.routing', 'Parent Routing', select=True, ondelete='cascade',
             help="Routings indicates all the Work Centers used, for how long and/or cycles." \
                "If Routings is set then,the third tab of a production order (Work Centers) will be automatically pre-completed."),
        'note': fields.text('Description'),
        'company_id': fields.related('routing_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
    }
    _defaults = {
        'cycle_nbr': lambda *a: 1.0,
        'hour_nbr': lambda *a: 0.0,
        'sequence': 100,
    }

class mrp_bom(osv.osv):
    """
    Defines bills of material for a product.
    """
    _name = 'mrp.bom'
    _description = 'Bill of Material'
    _inherit = ['mail.thread']

    _columns = {
        'code': fields.char('Reference', size=16),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the bills of material without removing it."),
        'type': fields.selection([('normal','Manufacture this product'),('phantom','Ship this product as a set of components (kit)')], 'BoM Type', required=True,
                help= "Set: When processing a sales order for this product, the delivery order will contain the raw materials, instead of the finished product."),
        'position': fields.char('Internal Reference', help="Reference to a position in an external plan."),
        'product_tmpl_id': fields.many2one('product.template', 'Product', domain="[('type', 'in', ['product', 'consu'])]", required=True),
        'product_id': fields.many2one('product.product', 'Product Variant',
            domain="['&', ('product_tmpl_id','=',product_tmpl_id), ('type', 'in', ['product', 'consu'])]",
            help="If a product variant is defined the BOM is available only for this product."),
        'bom_line_ids': fields.one2many('mrp.bom.line', 'bom_id', 'BoM Lines', copy=True),
        'product_qty': fields.float('Product Quantity', required=True, digits_compute=dp.get_precision('Product Unit of Measure')),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True, help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control"),
        'date_start': fields.date('Valid From', help="Validity of this BoM. Keep empty if it's always valid."),
        'date_stop': fields.date('Valid Until', help="Validity of this BoM. Keep empty if it's always valid."),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of bills of material."),
        'routing_id': fields.many2one('mrp.routing', 'Routing', help="The list of operations (list of work centers) to produce the finished product. "\
                "The routing is mainly used to compute work center costs during operations and to plan future loads on work centers based on production planning."),
        'product_rounding': fields.float('Product Rounding', help="Rounding applied on the product quantity."),
        'product_efficiency': fields.float('Manufacturing Efficiency', required=True, help="A factor of 0.9 means a loss of 10% during the production process."),
        'property_ids': fields.many2many('mrp.property', string='Properties'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
    }

    def _get_uom_id(self, cr, uid, *args):
        return self.pool["product.uom"].search(cr, uid, [], limit=1, order='id')[0]
    _defaults = {
        'active': lambda *a: 1,
        'product_qty': lambda *a: 1.0,
        'product_efficiency': lambda *a: 1.0,
        'product_rounding': lambda *a: 0.0,
        'type': lambda *a: 'normal',
        'product_uom': _get_uom_id,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'mrp.bom', context=c),
    }
    _order = "sequence"


    def _bom_find(self, cr, uid, product_tmpl_id=None, product_id=None, properties=None, context=None):
        """ Finds BoM for particular product and product uom.
        @param product_tmpl_id: Selected product.
        @param product_uom: Unit of measure of a product.
        @param properties: List of related properties.
        @return: False or BoM id.
        """
        if not context:
            context = {}
        if properties is None:
            properties = []
        if product_id:
            if not product_tmpl_id:
                product_tmpl_id = self.pool['product.product'].browse(cr, uid, product_id, context=context).product_tmpl_id.id
            domain = [
                '|',
                    ('product_id', '=', product_id),
                    '&',
                        ('product_id', '=', False),
                        ('product_tmpl_id', '=', product_tmpl_id)
            ]
        elif product_tmpl_id:
            domain = [('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl_id)]
        else:
            # neither product nor template, makes no sense to search
            return False
        if context.get('company_id'):
            domain = domain + [('company_id', '=', context['company_id'])]
        domain = domain + [ '|', ('date_start', '=', False), ('date_start', '<=', time.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                            '|', ('date_stop', '=', False), ('date_stop', '>=', time.strftime(DEFAULT_SERVER_DATE_FORMAT))]
        # order to prioritize bom with product_id over the one without
        ids = self.search(cr, uid, domain, order='sequence, product_id', context=context)
        # Search a BoM which has all properties specified, or if you can not find one, you could
        # pass a BoM without any properties with the smallest sequence
        bom_empty_prop = False
        for bom in self.pool.get('mrp.bom').browse(cr, uid, ids, context=context):
            if not set(map(int, bom.property_ids or [])) - set(properties or []):
                if not properties or bom.property_ids:
                    return bom.id
                elif not bom_empty_prop:
                    bom_empty_prop = bom.id
        return bom_empty_prop

    def _skip_bom_line(self, cr, uid, line, product, context=None):
        """ Control if a BoM line should be produce, can be inherited for add
        custom control.
        @param line: BoM line.
        @param product: Selected product produced.
        @return: True or False
        """
        if line.date_start and line.date_start > time.strftime(DEFAULT_SERVER_DATE_FORMAT) or \
            line.date_stop and line.date_stop < time.strftime(DEFAULT_SERVER_DATE_FORMAT):
                return True
        # all bom_line_id variant values must be in the product
        if line.attribute_value_ids:
            if not product or (set(map(int,line.attribute_value_ids or [])) - set(map(int,product.attribute_value_ids))):
                return True
        return False

    def _prepare_wc_line(self, cr, uid, bom, wc_use, level=0, factor=1, context=None):
        wc = wc_use.workcenter_id
        d, m = divmod(factor, wc_use.workcenter_id.capacity_per_cycle)
        mult = (d + (m and 1.0 or 0.0))
        cycle = mult * wc_use.cycle_nbr
        return {
            'name': tools.ustr(wc_use.name) + ' - ' + tools.ustr(bom.product_tmpl_id.name_get()[0][1]),
            'workcenter_id': wc.id,
            'sequence': level + (wc_use.sequence or 0),
            'cycle': cycle,
            'hour': float(wc_use.hour_nbr * mult + ((wc.time_start or 0.0) + (wc.time_stop or 0.0) + cycle * (wc.time_cycle or 0.0)) * (wc.time_efficiency or 1.0)),
        }

    def _prepare_consume_line(self, cr, uid, bom_line_id, quantity, context=None):
        return {
            'name': bom_line_id.product_id.name,
            'product_id': bom_line_id.product_id.id,
            'product_qty': quantity,
            'product_uom': bom_line_id.product_uom.id
        }

    def _bom_explode(self, cr, uid, bom, product, factor, properties=None, level=0, routing_id=False, previous_products=None, master_bom=None, context=None):
        """ Finds Products and Work Centers for related BoM for manufacturing order.
        @param bom: BoM of particular product template.
        @param product: Select a particular variant of the BoM. If False use BoM without variants.
        @param factor: Factor represents the quantity, but in UoM of the BoM, taking into account the numbers produced by the BoM
        @param properties: A List of properties Ids.
        @param level: Depth level to find BoM lines starts from 10.
        @param previous_products: List of product previously use by bom explore to avoid recursion
        @param master_bom: When recursion, used to display the name of the master bom
        @return: result: List of dictionaries containing product details.
                 result2: List of dictionaries containing Work Center details.
        """
        uom_obj = self.pool.get("product.uom")
        routing_obj = self.pool.get('mrp.routing')
        master_bom = master_bom or bom


        def _factor(factor, product_efficiency, product_rounding):
            factor = factor / (product_efficiency or 1.0)
            if product_rounding:
                factor = tools.float_round(factor,
                                           precision_rounding=product_rounding,
                                           rounding_method='UP')
            if factor < product_rounding:
                factor = product_rounding
            return factor

        factor = _factor(factor, bom.product_efficiency, bom.product_rounding)

        result = []
        result2 = []

        routing = (routing_id and routing_obj.browse(cr, uid, routing_id)) or bom.routing_id or False
        if routing:
            for wc_use in routing.workcenter_lines:
                result2.append(self._prepare_wc_line(
                    cr, uid, bom, wc_use, level=level, factor=factor,
                    context=context))

        for bom_line_id in bom.bom_line_ids:
            if self._skip_bom_line(cr, uid, bom_line_id, product, context=context):
                continue
            if set(map(int, bom_line_id.property_ids or [])) - set(properties or []):
                continue

            if previous_products and bom_line_id.product_id.product_tmpl_id.id in previous_products:
                raise UserError(_('BoM "%s" contains a BoM line with a product recursion: "%s".') % (master_bom.code or "", bom_line_id.product_id.name_get()[0][1]))

            quantity = _factor(bom_line_id.product_qty * factor, bom_line_id.product_efficiency, bom_line_id.product_rounding)
            bom_id = self._bom_find(cr, uid, product_id=bom_line_id.product_id.id, properties=properties, context=context)

            #If BoM should not behave like kit, just add the product, otherwise explode further
            if (not bom_id) or (self.browse(cr, uid, bom_id, context=context).type != "phantom"):
                result.append(self._prepare_consume_line(
                    cr, uid, bom_line_id, quantity, context=context))
            else:
                all_prod = [bom.product_tmpl_id.id] + (previous_products or [])
                bom2 = self.browse(cr, uid, bom_id, context=context)
                # We need to convert to units/UoM of chosen BoM
                factor2 = uom_obj._compute_qty(cr, uid, bom_line_id.product_uom.id, quantity, bom2.product_uom.id)
                quantity2 = factor2 / bom2.product_qty
                res = self._bom_explode(cr, uid, bom2, bom_line_id.product_id, quantity2,
                    properties=properties, level=level + 10, previous_products=all_prod, master_bom=master_bom, context=context)
                result = result + res[0]
                result2 = result2 + res[1]
        return result, result2

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        bom_data = self.read(cr, uid, id, [], context=context)
        default.update(name=_("%s (copy)") % (bom_data['display_name']))
        return super(mrp_bom, self).copy_data(cr, uid, id, default, context=context)

    def onchange_uom(self, cr, uid, ids, product_tmpl_id, product_uom, context=None):
        res = {'value': {}}
        if not product_uom or not product_tmpl_id:
            return res
        product = self.pool.get('product.template').browse(cr, uid, product_tmpl_id, context=context)
        uom = self.pool.get('product.uom').browse(cr, uid, product_uom, context=context)
        if uom.category_id.id != product.uom_id.category_id.id:
            res['warning'] = {'title': _('Warning'), 'message': _('The Product Unit of Measure you chose has a different category than in the product form.')}
            res['value'].update({'product_uom': product.uom_id.id})
        return res

    def unlink(self, cr, uid, ids, context=None):
        if self.pool['mrp.production'].search(cr, uid, [('bom_id', 'in', ids), ('state', 'not in', ['done', 'cancel'])], context=context):
            raise UserError(_('You can not delete a Bill of Material with running manufacturing orders.\nPlease close or cancel it first.'))
        return super(mrp_bom, self).unlink(cr, uid, ids, context=context)

    def onchange_product_tmpl_id(self, cr, uid, ids, product_tmpl_id, product_qty=0, context=None):
        """ Changes UoM and name if product_id changes.
        @param product_id: Changed product_id
        @return:  Dictionary of changed values
        """
        res = {}
        if product_tmpl_id:
            prod = self.pool.get('product.template').browse(cr, uid, product_tmpl_id, context=context)
            res['value'] = {
                'product_uom': prod.uom_id.id,
            }
        return res

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.product_tmpl_id.name
            if record.code:
                name = '[%s] %s' % (record.code, name)
            res.append((record.id, name))
        return res

class mrp_bom_line(osv.osv):
    _name = 'mrp.bom.line'
    _order = "sequence"
    _rec_name = "product_id"

    def _get_child_bom_lines(self, cr, uid, ids, field_name, arg, context=None):
        """If the BOM line refers to a BOM, return the ids of the child BOM lines"""
        bom_obj = self.pool['mrp.bom']
        res = {}
        for bom_line in self.browse(cr, uid, ids, context=context):
            bom_id = bom_obj._bom_find(cr, uid,
                product_tmpl_id=bom_line.product_id.product_tmpl_id.id,
                product_id=bom_line.product_id.id, context=context)
            if bom_id:
                child_bom = bom_obj.browse(cr, uid, bom_id, context=context)
                res[bom_line.id] = [x.id for x in child_bom.bom_line_ids]
            else:
                res[bom_line.id] = False
        return res

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_qty': fields.float('Product Quantity', required=True, digits_compute=dp.get_precision('Product Unit of Measure')),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True,
            help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control"),
        
        'date_start': fields.date('Valid From', help="Validity of component. Keep empty if it's always valid."),
        'date_stop': fields.date('Valid Until', help="Validity of component. Keep empty if it's always valid."),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying."),
        'routing_id': fields.many2one('mrp.routing', 'Routing', help="The list of operations (list of work centers) to produce the finished product. The routing is mainly used to compute work center costs during operations and to plan future loads on work centers based on production planning."),
        'product_rounding': fields.float('Product Rounding', help="Rounding applied on the product quantity."),
        'product_efficiency': fields.float('Manufacturing Efficiency', required=True, help="A factor of 0.9 means a loss of 10% within the production process."),
        'property_ids': fields.many2many('mrp.property', string='Properties'), #Not used

        'bom_id': fields.many2one('mrp.bom', 'Parent BoM', ondelete='cascade', select=True, required=True),
        'attribute_value_ids': fields.many2many('product.attribute.value', string='Variants', help="BOM Product Variants needed form apply this line."),
        'child_line_ids': fields.function(_get_child_bom_lines, relation="mrp.bom.line", string="BOM lines of the referred bom", type="one2many")
    }

    def _get_uom_id(self, cr, uid, *args):
        return self.pool["product.uom"].search(cr, uid, [], limit=1, order='id')[0]
    _defaults = {
        'product_qty': lambda *a: 1.0,
        'product_efficiency': lambda *a: 1.0,
        'product_rounding': lambda *a: 0.0,
        'product_uom': _get_uom_id,
        'sequence': 1,
    }
    _sql_constraints = [
        ('bom_qty_zero', 'CHECK (product_qty>0)', 'All product quantities must be greater than 0.\n' \
            'You should install the mrp_byproduct module if you want to manage extra products on BoMs !'),
    ]

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product')
        if 'product_id' in values and not 'product_uom' in values:
            values['product_uom'] = product_obj.browse(cr, uid, values.get('product_id'), context=context).uom_id.id
        return super(mrp_bom_line, self).create(cr, uid, values, context=context)

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

    def onchange_product_id(self, cr, uid, ids, product_id, product_qty=0, context=None):
        """ Changes UoM if product_id changes.
        @param product_id: Changed product_id
        @return:  Dictionary of changed values
        """
        res = {}
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            res['value'] = {
                'product_uom': prod.uom_id.id,
            }
        return res

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

    def _get_workcenter_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool['mrp.production.workcenter.line'].browse(cr, uid, ids, context=context):
            result[line.production_id.id] = True
        return result.keys()

    def _src_id_default(self, cr, uid, ids, context=None):
        try:
            location_model, location_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'stock_location_stock')
            self.pool.get('stock.location').check_access_rule(cr, uid, [location_id], 'read', context=context)
        except (AccessError, ValueError):
            location_id = False
        return location_id

    def _dest_id_default(self, cr, uid, ids, context=None):
        try:
            location_model, location_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'stock_location_stock')
            self.pool.get('stock.location').check_access_rule(cr, uid, [location_id], 'read', context=context)
        except (AccessError, ValueError):
            location_id = False
        return location_id

    def _get_progress(self, cr, uid, ids, name, arg, context=None):
        """ Return product quantity percentage """
        result = dict.fromkeys(ids, 100)
        for mrp_production in self.browse(cr, uid, ids, context=context):
            if mrp_production.product_qty:
                done = 0.0
                for move in mrp_production.move_created_ids2:
                    if not move.scrapped and move.product_id == mrp_production.product_id:
                        done += move.product_qty
                result[mrp_production.id] = done / mrp_production.product_qty * 100
        return result

    def _moves_assigned(self, cr, uid, ids, name, arg, context=None):
        """ Test whether all the consume lines are assigned """
        res = {}
        for production in self.browse(cr, uid, ids, context=context):
            res[production.id] = True
            states = [x.state != 'assigned' for x in production.move_lines if x]
            if any(states) or len(states) == 0: #When no moves, ready_production will be False, but test_ready will pass
                res[production.id] = False
        return res

    def _mrp_from_move(self, cr, uid, ids, context=None):
        """ Return mrp"""
        res = []
        for move in self.browse(cr, uid, ids, context=context):
            res += self.pool.get("mrp.production").search(cr, uid, [('move_lines', 'in', move.id)], context=context)
        return res

    _columns = {
        'name': fields.char('Reference', required=True, readonly=True, states={'draft': [('readonly', False)]}, copy=False),
        'origin': fields.char('Source Document', readonly=True, states={'draft': [('readonly', False)]},
            help="Reference of the document that generated this production order request.", copy=False),
        'priority': fields.selection([('0', 'Not urgent'), ('1', 'Normal'), ('2', 'Urgent'), ('3', 'Very Urgent')], 'Priority',
            select=True, readonly=True, states=dict.fromkeys(['draft', 'confirmed'], [('readonly', False)])),

        'product_id': fields.many2one('product.product', 'Product', required=True, readonly=True, states={'draft': [('readonly', False)]}, 
                                      domain=[('type', 'in', ['product', 'consu'])]),
        'product_qty': fields.float('Product Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'progress': fields.function(_get_progress, type='float',
            string='Production progress'),

        'location_src_id': fields.many2one('stock.location', 'Raw Materials Location', required=True,
            readonly=True, states={'draft': [('readonly', False)]},
            help="Location where the system will look for components."),
        'location_dest_id': fields.many2one('stock.location', 'Finished Products Location', required=True,
            readonly=True, states={'draft': [('readonly', False)]},
            help="Location where the system will stock the finished products."),
        'date_planned': fields.datetime('Scheduled Date', required=True, select=1, readonly=True, states={'draft': [('readonly', False)]}, copy=False),
        'date_start': fields.datetime('Start Date', select=True, readonly=True, copy=False),
        'date_finished': fields.datetime('End Date', select=True, readonly=True, copy=False),
        'bom_id': fields.many2one('mrp.bom', 'Bill of Material', readonly=True, states={'draft': [('readonly', False)]},
            help="Bill of Materials allow you to define the list of required raw materials to make a finished product."),
        'routing_id': fields.many2one('mrp.routing', string='Routing', on_delete='set null', readonly=True, states={'draft': [('readonly', False)]},
            help="The list of operations (list of work centers) to produce the finished product. The routing is mainly used to compute work center costs during operations and to plan future loads on work centers based on production plannification."),
        'move_prod_id': fields.many2one('stock.move', 'Product Move', readonly=True, copy=False),
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
            track_visibility='onchange', copy=False,
            help="When the production order is created the status is set to 'Draft'.\n"
                "If the order is confirmed the status is set to 'Waiting Goods.\n"
                "If any exceptions are there, the status is set to 'Picking Exception.\n"
                "If the stock is available then the status is set to 'Ready to Produce.\n"
                "When the production gets started then the status is set to 'In Production.\n"
                "When the production is over, the status is set to 'Done'."),
        'hour_total': fields.function(_production_calc, type='float', string='Total Hours', multi='workorder', store={
            _name: (lambda self, cr, uid, ids, c={}: ids, ['workcenter_lines'], 40),
            'mrp.production.workcenter.line': (_get_workcenter_line, ['hour', 'cycle'], 40),
        }),
        'cycle_total': fields.function(_production_calc, type='float', string='Total Cycles', multi='workorder', store={
            _name: (lambda self, cr, uid, ids, c={}: ids, ['workcenter_lines'], 40),
            'mrp.production.workcenter.line': (_get_workcenter_line, ['hour', 'cycle'], 40),
        }),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'ready_production': fields.function(_moves_assigned, type='boolean', string="Ready for production", store={'stock.move': (_mrp_from_move, ['state'], 10)}),
        'product_tmpl_id': fields.related('product_id', 'product_tmpl_id', type='many2one', relation='product.template', string='Product'),
    }

    _defaults = {
        'priority': lambda *a: '1',
        'state': lambda *a: 'draft',
        'date_planned': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'product_qty': lambda *a: 1.0,
        'user_id': lambda self, cr, uid, c: uid,
        'name': lambda self, cr, uid, context: self.pool['ir.sequence'].next_by_code(cr, uid, 'mrp.production', context=context) or '/',
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'mrp.production', context=c),
        'location_src_id': _src_id_default,
        'location_dest_id': _dest_id_default
    }

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per Company!'),
    ]

    _order = 'priority desc, date_planned asc'

    def _check_qty(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            if order.product_qty <= 0:
                return False
        return True

    _constraints = [
        (_check_qty, 'Order quantity cannot be negative or zero!', ['product_qty']),
    ]

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product')
        if 'product_id' in values and not 'product_uom' in values:
            values['product_uom'] = product_obj.browse(cr, uid, values.get('product_id'), context=context).uom_id.id
        return super(mrp_production, self).create(cr, uid, values, context=context)

    def unlink(self, cr, uid, ids, context=None):
        for production in self.browse(cr, uid, ids, context=context):
            if production.state not in ('draft', 'cancel'):
                state_label = dict(production.fields_get(['state'])['state']['selection']).get(production.state)
                raise UserError(_('Cannot delete a manufacturing order in state \'%s\'.') % state_label)
        return super(mrp_production, self).unlink(cr, uid, ids, context=context)

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
                'product_tmpl_id': False
            }}
        bom_obj = self.pool.get('mrp.bom')
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        bom_id = bom_obj._bom_find(cr, uid, product_id=product.id, properties=[], context=context)
        routing_id = False
        if bom_id:
            bom_point = bom_obj.browse(cr, uid, bom_id, context=context)
            routing_id = bom_point.routing_id.id or False
        product_uom_id = product.uom_id and product.uom_id.id or False
        result['value'] = {'product_uom': product_uom_id, 'bom_id': bom_id, 'routing_id': routing_id, 'product_tmpl_id': product.product_tmpl_id}
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


    def _prepare_lines(self, cr, uid, production, properties=None, context=None):
        # search BoM structure and route
        bom_obj = self.pool.get('mrp.bom')
        uom_obj = self.pool.get('product.uom')
        bom_point = production.bom_id
        bom_id = production.bom_id.id
        if not bom_point:
            bom_id = bom_obj._bom_find(cr, uid, product_id=production.product_id.id, properties=properties, context=context)
            if bom_id:
                bom_point = bom_obj.browse(cr, uid, bom_id)
                routing_id = bom_point.routing_id.id or False
                self.write(cr, uid, [production.id], {'bom_id': bom_id, 'routing_id': routing_id})

        if not bom_id:
            raise UserError(_("Cannot find a bill of material for this product."))

        # get components and workcenter_lines from BoM structure
        factor = uom_obj._compute_qty(cr, uid, production.product_uom.id, production.product_qty, bom_point.product_uom.id)
        # product_lines, workcenter_lines
        return bom_obj._bom_explode(cr, uid, bom_point, production.product_id, factor / bom_point.product_qty, properties, routing_id=production.routing_id.id, context=context)


    def _action_compute_lines(self, cr, uid, ids, properties=None, context=None):
        """ Compute product_lines and workcenter_lines from BoM structure
        @return: product_lines
        """
        if properties is None:
            properties = []
        results = []
        prod_line_obj = self.pool.get('mrp.production.product.line')
        workcenter_line_obj = self.pool.get('mrp.production.workcenter.line')
        for production in self.browse(cr, uid, ids, context=context):
            #unlink product_lines
            prod_line_obj.unlink(cr, SUPERUSER_ID, [line.id for line in production.product_lines], context=context)
            #unlink workcenter_lines
            workcenter_line_obj.unlink(cr, SUPERUSER_ID, [line.id for line in production.workcenter_lines], context=context)

            res = self._prepare_lines(cr, uid, production, properties=properties, context=context)
            results = res[0] # product_lines
            results2 = res[1] # workcenter_lines

            # reset product_lines in production order
            for line in results:
                line['production_id'] = production.id
                prod_line_obj.create(cr, uid, line)

            #reset workcenter_lines in production order
            for line in results2:
                line['production_id'] = production.id
                workcenter_line_obj.create(cr, uid, line, context)
        return results

    def action_compute(self, cr, uid, ids, properties=None, context=None):
        """ Computes bills of material of a product.
        @param properties: List containing dictionaries of properties.
        @return: No. of products.
        """
        return len(self._action_compute_lines(cr, uid, ids, properties=properties, context=context))

    def action_cancel(self, cr, uid, ids, context=None):
        """ Cancels the production order and related stock moves.
        @return: True
        """
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')
        proc_obj = self.pool.get('procurement.order')
        for production in self.browse(cr, uid, ids, context=context):
            if production.move_created_ids:
                move_obj.action_cancel(cr, uid, [x.id for x in production.move_created_ids])
            procs = proc_obj.search(cr, uid, [('move_dest_id', 'in', [x.id for x in production.move_lines])], context=context)
            if procs:
                proc_obj.cancel(cr, uid, procs, context=context)
            move_obj.action_cancel(cr, uid, [x.id for x in production.move_lines])
        self.write(cr, uid, ids, {'state': 'cancel'})
        # Put related procurements in exception
        proc_obj = self.pool.get("procurement.order")
        procs = proc_obj.search(cr, uid, [('production_id', 'in', ids)], context=context)
        if procs:
            proc_obj.message_post(cr, uid, procs, body=_('Manufacturing order cancelled.'), context=context)
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

    def _compute_costs_from_production(self, cr, uid, ids, context=None):
        """ Generate workcenter costs in analytic accounts"""
        for production in self.browse(cr, uid, ids):
            total_cost = self._costs_generate(cr, uid, production)

    def action_production_end(self, cr, uid, ids, context=None):
        """ Changes production state to Finish and writes finished date.
        @return: True
        """
        self._compute_costs_from_production(cr, uid, ids, context)
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
            product_qty is in the uom of the product
        """
        quant_obj = self.pool.get("stock.quant")
        uom_obj = self.pool.get("product.uom")
        produced_qty = self._get_produced_qty(cr, uid, production, context=context)
        consumed_data = self._get_consumed_data(cr, uid, production, context=context)

        #In case no product_qty is given, take the remaining qty to produce for the given production
        if not product_qty:
            product_qty = uom_obj._compute_qty(cr, uid, production.product_uom.id, production.product_qty, production.product_id.uom_id.id) - produced_qty
        production_qty = uom_obj._compute_qty(cr, uid, production.product_uom.id, production.product_qty, production.product_id.uom_id.id)

        scheduled_qty = OrderedDict()
        for scheduled in production.product_lines:
            if scheduled.product_id.type not in ['product', 'consu']:
                continue
            qty = uom_obj._compute_qty(cr, uid, scheduled.product_uom.id, scheduled.product_qty, scheduled.product_id.uom_id.id)
            if scheduled_qty.get(scheduled.product_id.id):
                scheduled_qty[scheduled.product_id.id] += qty
            else:
                scheduled_qty[scheduled.product_id.id] = qty
        dicts = OrderedDict()
        # Find product qty to be consumed and consume it
        for product_id in scheduled_qty.keys():

            consumed_qty = consumed_data.get(product_id, 0.0)
            
            # qty available for consume and produce
            sched_product_qty = scheduled_qty[product_id]
            qty_avail = sched_product_qty - consumed_qty
            if qty_avail <= 0.0:
                # there will be nothing to consume for this raw material
                continue

            if not dicts.get(product_id):
                dicts[product_id] = {}

            # total qty of consumed product we need after this consumption
            if product_qty + produced_qty <= production_qty:
                total_consume = ((product_qty + produced_qty) * sched_product_qty / production_qty)
            else:
                total_consume = sched_product_qty
            qty = total_consume - consumed_qty

            # Search for quants related to this related move
            for move in production.move_lines:
                if qty <= 0.0:
                    break
                if move.product_id.id != product_id:
                    continue

                q = min(move.product_qty, qty)
                quants = quant_obj.quants_get_preferred_domain(cr, uid, q, move, domain=[('qty', '>', 0.0)],
                                                     preferred_domain_list=[[('reservation_id', '=', move.id)]], context=context)
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
            if float_compare(qty, 0, self.pool['decimal.precision'].precision_get(cr, uid, 'Product Unit of Measure')) == 1:
                if dicts[product_id].get(False):
                    dicts[product_id][False] += qty
                else:
                    dicts[product_id][False] = qty

        consume_lines = []
        for prod in dicts.keys():
            for lot, qty in dicts[prod].items():
                consume_lines.append({'product_id': prod, 'product_qty': qty, 'lot_id': lot})
        return consume_lines

    def _calculate_total_cost(self, cr, uid, total_consume_moves, context=None):
        total_cost = 0
        for consumed_move in self.pool['stock.move'].browse(cr, uid, total_consume_moves, context=context):
            total_cost += sum([x.inventory_value for x in consumed_move.quant_ids if x.qty > 0])
        return total_cost

    def _calculate_workcenter_cost(self, cr, uid, production_id, context=None):
        """ Compute the planned production cost from the workcenters """
        production = self.browse(cr, uid, production_id, context=context)
        total_cost = 0.0
        for wc_line in production.workcenter_lines:
            wc = wc_line.workcenter_id
            total_cost += wc_line.hour*wc.costs_hour + wc_line.cycle*wc.costs_cycle

        return total_cost

    def action_produce(self, cr, uid, production_id, production_qty, production_mode, wiz=False, context=None):
        """ To produce final product based on production mode (consume/consume&produce).
        If Production mode is consume, all stock move lines of raw materials will be done/consumed.
        If Production mode is consume & produce, all stock move lines of raw materials will be done/consumed
        and stock move lines of final product will be also done/produced.
        @param production_id: the ID of mrp.production object
        @param production_qty: specify qty to produce in the uom of the production order
        @param production_mode: specify production mode (consume/consume&produce).
        @param wiz: the mrp produce product wizard, which will tell the amount of consumed products needed
        @return: True
        """
        stock_mov_obj = self.pool.get('stock.move')
        uom_obj = self.pool.get("product.uom")
        production = self.browse(cr, uid, production_id, context=context)
        production_qty_uom = uom_obj._compute_qty(cr, uid, production.product_uom.id, production_qty, production.product_id.uom_id.id)
        precision = self.pool['decimal.precision'].precision_get(cr, uid, 'Product Unit of Measure')

        main_production_move = False
        if production_mode == 'consume_produce':
            for produce_product in production.move_created_ids:
                if produce_product.product_id.id == production.product_id.id:
                    main_production_move = produce_product.id

        total_consume_moves = []
        if production_mode in ['consume', 'consume_produce']:
            if wiz:
                consume_lines = []
                for cons in wiz.consume_lines:
                    consume_lines.append({'product_id': cons.product_id.id, 'lot_id': cons.lot_id.id, 'product_qty': cons.product_qty})
            else:
                consume_lines = self._calculate_qty(cr, uid, production, production_qty_uom, context=context)
            for consume in consume_lines:
                remaining_qty = consume['product_qty']
                for raw_material_line in production.move_lines:
                    if raw_material_line.state in ('done', 'cancel'):
                        continue
                    if remaining_qty <= 0:
                        break
                    if consume['product_id'] != raw_material_line.product_id.id:
                        continue
                    consumed_qty = min(remaining_qty, raw_material_line.product_qty)
                    stock_mov_obj.action_consume(cr, uid, [raw_material_line.id], consumed_qty, raw_material_line.location_id.id,
                                                 restrict_lot_id=consume['lot_id'], consumed_for=main_production_move, context=context)
                    total_consume_moves.append(raw_material_line.id)
                    remaining_qty -= consumed_qty
                if not float_is_zero(remaining_qty, precision_digits=precision):
                    #consumed more in wizard than previously planned
                    product = self.pool.get('product.product').browse(cr, uid, consume['product_id'], context=context)
                    extra_move_id = self._make_consume_line_from_data(cr, uid, production, product, product.uom_id.id, remaining_qty, context=context)
                    stock_mov_obj.write(cr, uid, [extra_move_id], {'restrict_lot_id': consume['lot_id'],
                                                                    'consumed_for': main_production_move}, context=context)
                    stock_mov_obj.action_done(cr, uid, [extra_move_id], context=context)
                    total_consume_moves.append(extra_move_id)

        if production_mode == 'consume_produce':
            # add production lines that have already been consumed since the last 'consume & produce'
            last_production_date = production.move_created_ids2 and max(production.move_created_ids2.mapped('date')) or False
            already_consumed_lines = production.move_lines2.filtered(lambda l: l.date > last_production_date)
            total_consume_moves += already_consumed_lines.ids

            price_unit = 0
            for produce_product in production.move_created_ids:
                is_main_product = (produce_product.product_id.id == production.product_id.id) and production.product_id.cost_method=='real'
                if is_main_product:
                    total_cost = self._calculate_total_cost(cr, uid, total_consume_moves, context=context)
                    production_cost = self._calculate_workcenter_cost(cr, uid, production_id, context=context)
                    price_unit = (total_cost + production_cost) / production_qty_uom

                subproduct_factor = self._get_subproduct_factor(cr, uid, production.id, produce_product.id, context=context)
                lot_id = False
                if wiz:
                    lot_id = wiz.lot_id.id
                qty = min(subproduct_factor * production_qty_uom, produce_product.product_qty) #Needed when producing more than maximum quantity
                if is_main_product and price_unit:
                    stock_mov_obj.write(cr, uid, [produce_product.id], {'price_unit': price_unit}, context=context)
                new_moves = stock_mov_obj.action_consume(cr, uid, [produce_product.id], qty,
                                                         location_id=produce_product.location_id.id, restrict_lot_id=lot_id, context=context)
                stock_mov_obj.write(cr, uid, new_moves, {'production_id': production_id}, context=context)
                remaining_qty = subproduct_factor * production_qty_uom - qty
                if not float_is_zero(remaining_qty, precision_digits=precision):
                    # In case you need to make more than planned
                    #consumed more in wizard than previously planned
                    extra_move_id = stock_mov_obj.copy(cr, uid, produce_product.id, default={'product_uom_qty': remaining_qty,
                                                                                             'production_id': production_id}, context=context)
                    if is_main_product:
                        stock_mov_obj.write(cr, uid, [extra_move_id], {'price_unit': price_unit}, context=context)
                    stock_mov_obj.action_confirm(cr, uid, [extra_move_id], context=context)
                    stock_mov_obj.action_done(cr, uid, [extra_move_id], context=context)

        self.message_post(cr, uid, production_id, body=_("%s produced") % self._description, context=context)

        # Remove remaining products to consume if no more products to produce
        if not production.move_created_ids and production.move_lines:
            stock_mov_obj.action_cancel(cr, uid, [x.id for x in production.move_lines], context=context)

        self.signal_workflow(cr, uid, [production_id], 'button_produce_done')
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
            if wc.costs_general_account_id:
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
        res = True
        for production in self.browse(cr, uid, ids):
            if production.move_lines and not production.ready_production:
                res = False
        return res

    
    
    def _make_production_produce_line(self, cr, uid, production, context=None):
        stock_move = self.pool.get('stock.move')
        proc_obj = self.pool.get('procurement.order')
        source_location_id = production.product_id.property_stock_production.id
        destination_location_id = production.location_dest_id.id
        procs = proc_obj.search(cr, uid, [('production_id', '=', production.id)], context=context)
        procurement = procs and\
            proc_obj.browse(cr, uid, procs[0], context=context) or False
        data = {
            'name': production.name,
            'date': production.date_planned,
            'date_expected': production.date_planned,
            'product_id': production.product_id.id,
            'product_uom': production.product_uom.id,
            'product_uom_qty': production.product_qty,
            'location_id': source_location_id,
            'location_dest_id': destination_location_id,
            'move_dest_id': production.move_prod_id.id,
            'procurement_id': procurement and procurement.id,
            'company_id': production.company_id.id,
            'production_id': production.id,
            'origin': production.name,
            'group_id': procurement and procurement.group_id.id,
        }
        move_id = stock_move.create(cr, uid, data, context=context)
        return stock_move.action_confirm(cr, uid, [move_id], context=context)[0]

    def _get_raw_material_procure_method(self, cr, uid, product, location_id=False, location_dest_id=False, context=None):
        '''This method returns the procure_method to use when creating the stock move for the production raw materials
        Besides the standard configuration of looking if the product or product category has the MTO route,
        you can also define a rule e.g. from Stock to Production (which might be used in the future like the sale orders)
        '''
        warehouse_obj = self.pool['stock.warehouse']
        routes = product.route_ids + product.categ_id.total_route_ids

        if location_id and location_dest_id:
            pull_obj = self.pool['procurement.rule']
            pulls = pull_obj.search(cr, uid, [('route_id', 'in', [x.id for x in routes]),
                                            ('location_id', '=', location_dest_id),
                                            ('location_src_id', '=', location_id)], limit=1, context=context)
            if pulls:
                return pull_obj.browse(cr, uid, pulls[0], context=context).procure_method

        try:
            mto_route = warehouse_obj._get_mto_route(cr, uid, context=context)
        except:
            return "make_to_stock"

        if mto_route in [x.id for x in routes]:
            return "make_to_order"
        return "make_to_stock"

    def _create_previous_move(self, cr, uid, move_id, product, source_location_id, dest_location_id, context=None):
        '''
        When the routing gives a different location than the raw material location of the production order, 
        we should create an extra move from the raw material location to the location of the routing, which 
        precedes the consumption line (chained).  The picking type depends on the warehouse in which this happens
        and the type of locations. 
        '''
        loc_obj = self.pool.get("stock.location")
        stock_move = self.pool.get('stock.move')
        type_obj = self.pool.get('stock.picking.type')
        # Need to search for a picking type
        move = stock_move.browse(cr, uid, move_id, context=context)
        src_loc = loc_obj.browse(cr, uid, source_location_id, context=context)
        dest_loc = loc_obj.browse(cr, uid, dest_location_id, context=context)
        code = stock_move.get_code_from_locs(cr, uid, move, src_loc, dest_loc, context=context)
        if code == 'outgoing':
            check_loc = src_loc
        else:
            check_loc = dest_loc
        wh = loc_obj.get_warehouse(cr, uid, check_loc, context=context)
        domain = [('code', '=', code)]
        if wh: 
            domain += [('warehouse_id', '=', wh)]
        types = type_obj.search(cr, uid, domain, context=context)
        move = stock_move.copy(cr, uid, move_id, default = {
            'location_id': source_location_id,
            'location_dest_id': dest_location_id,
            'procure_method': self._get_raw_material_procure_method(cr, uid, product, location_id=source_location_id,
                                                                    location_dest_id=dest_location_id, context=context),
            'raw_material_production_id': False, 
            'move_dest_id': move_id,
            'picking_type_id': types and types[0] or False,
        }, context=context)
        return move

    def _make_consume_line_from_data(self, cr, uid, production, product, uom_id, qty, context=None):
        stock_move = self.pool.get('stock.move')
        loc_obj = self.pool.get('stock.location')
        # Internal shipment is created for Stockable and Consumer Products
        if product.type not in ('product', 'consu'):
            return False
        # Take routing location as a Source Location.
        source_location_id = production.location_src_id.id
        prod_location_id = source_location_id
        prev_move= False
        if production.bom_id.routing_id and production.bom_id.routing_id.location_id and production.bom_id.routing_id.location_id.id != source_location_id:
            source_location_id = production.bom_id.routing_id.location_id.id
            prev_move = True

        destination_location_id = production.product_id.property_stock_production.id
        move_id = stock_move.create(cr, uid, {
            'name': production.name,
            'date': production.date_planned,
            'date_expected': production.date_planned,
            'product_id': product.id,
            'product_uom_qty': qty,
            'product_uom': uom_id,
            'location_id': source_location_id,
            'location_dest_id': destination_location_id,
            'company_id': production.company_id.id,
            'procure_method': prev_move and 'make_to_stock' or self._get_raw_material_procure_method(cr, uid, product, location_id=source_location_id,
                                                                                                     location_dest_id=destination_location_id, context=context), #Make_to_stock avoids creating procurement
            'raw_material_production_id': production.id,
            #this saves us a browse in create()
            'price_unit': product.standard_price,
            'origin': production.name,
            'warehouse_id': loc_obj.get_warehouse(cr, uid, production.location_src_id, context=context),
            'group_id': production.move_prod_id.group_id.id,
        }, context=context)
        
        if prev_move:
            prev_move = self._create_previous_move(cr, uid, move_id, product, prod_location_id, source_location_id, context=context)
            stock_move.action_confirm(cr, uid, [prev_move], context=context)
        return move_id

    def _make_production_consume_line(self, cr, uid, line, context=None):
        return self._make_consume_line_from_data(cr, uid, line.production_id, line.product_id, line.product_uom.id, line.product_qty, context=context)

    def action_confirm(self, cr, uid, ids, context=None):
        """ Confirms production order.
        @return: Newly generated Shipment Id.
        """
        user_lang = self.pool.get('res.users').browse(cr, uid, [uid]).partner_id.lang
        context = dict(context, lang=user_lang)
        uncompute_ids = filter(lambda x: x, [not x.product_lines and x.id or False for x in self.browse(cr, uid, ids, context=context)])
        self.action_compute(cr, uid, uncompute_ids, context=context)
        for production in self.browse(cr, uid, ids, context=context):
            self._make_production_produce_line(cr, uid, production, context=context)
            stock_moves = []
            for line in production.product_lines:
                if line.product_id.type in ['product', 'consu']:
                    stock_move_id = self._make_production_consume_line(cr, uid, line, context=context)
                    stock_moves.append(stock_move_id)
            if stock_moves:
                self.pool.get('stock.move').action_confirm(cr, uid, stock_moves, context=context)
            production.write({'state': 'confirmed'})
        return 0

    def action_assign(self, cr, uid, ids, context=None):
        """
        Checks the availability on the consume lines of the production order
        """
        from openerp import workflow
        move_obj = self.pool.get("stock.move")
        for production in self.browse(cr, uid, ids, context=context):
            move_obj.action_assign(cr, uid, [x.id for x in production.move_lines], context=context)
            if self.pool.get('mrp.production').test_ready(cr, uid, [production.id]):
                workflow.trg_validate(uid, 'mrp.production', production.id, 'moves_ready', cr)


    def force_production(self, cr, uid, ids, *args):
        """ Assigns products.
        @param *args: Arguments
        @return: True
        """
        from openerp import workflow
        move_obj = self.pool.get('stock.move')
        for order in self.browse(cr, uid, ids):
            move_obj.force_assign(cr, uid, [x.id for x in order.move_lines])
            if self.pool.get('mrp.production').test_ready(cr, uid, [order.id]):
                workflow.trg_validate(uid, 'mrp.production', order.id, 'moves_ready', cr)
        return True


class mrp_production_workcenter_line(osv.osv):
    _name = 'mrp.production.workcenter.line'
    _description = 'Work Order'
    _order = 'sequence'
    _inherit = ['mail.thread']

    _columns = {
        'name': fields.char('Work Order', required=True),
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
        'name': fields.char('Name', required=True),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_qty': fields.float('Product Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'production_id': fields.many2one('mrp.production', 'Production Order', select=True),
    }
