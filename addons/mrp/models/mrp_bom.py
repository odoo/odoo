# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

import openerp.addons.decimal_precision as dp
from openerp import tools
from openerp.exceptions import UserError
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _


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
            'hour': float(wc_use.hour_nbr * mult + ((wc.time_start or 0.0) + (wc.time_stop or 0.0) + cycle * (wc.time_cycle or 0.0)) * (wc.time_efficiency or 100)),
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