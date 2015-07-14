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

import math
import re

from _common import ceiling

from openerp import tools, SUPERUSER_ID
from openerp.osv import osv, fields, expression
from openerp.tools.translate import _

import openerp.addons.decimal_precision as dp
from openerp.tools.float_utils import float_round

def ean_checksum(eancode):
    """returns the checksum of an ean string of length 13, returns -1 if the string has the wrong length"""
    if len(eancode) <> 13:
        return -1
    oddsum=0
    evensum=0
    total=0
    eanvalue=eancode
    reversevalue = eanvalue[::-1]
    finalean=reversevalue[1:]

    for i in range(len(finalean)):
        if i % 2 == 0:
            oddsum += int(finalean[i])
        else:
            evensum += int(finalean[i])
    total=(oddsum * 3) + evensum

    check = int(10 - math.ceil(total % 10.0)) %10
    return check

def check_ean(eancode):
    """returns True if eancode is a valid ean13 string, or null"""
    if not eancode:
        return True
    if len(eancode) <> 13:
        return False
    try:
        int(eancode)
    except:
        return False
    return ean_checksum(eancode) == int(eancode[-1])

def sanitize_ean13(ean13):
    """Creates and returns a valid ean13 from an invalid one"""
    if not ean13:
        return "0000000000000"
    ean13 = re.sub("[A-Za-z]","0",ean13);
    ean13 = re.sub("[^0-9]","",ean13);
    ean13 = ean13[:13]
    if len(ean13) < 13:
        ean13 = ean13 + '0' * (13-len(ean13))
    return ean13[:-1] + str(ean_checksum(ean13))

#----------------------------------------------------------
# UOM
#----------------------------------------------------------

class product_uom_categ(osv.osv):
    _name = 'product.uom.categ'
    _description = 'Product uom categ'
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
    }
product_uom_categ()

class product_uom(osv.osv):
    _name = 'product.uom'
    _description = 'Product Unit of Measure'

    def _compute_factor_inv(self, factor):
        return factor and (1.0 / factor) or 0.0

    def _factor_inv(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for uom in self.browse(cursor, user, ids, context=context):
            res[uom.id] = self._compute_factor_inv(uom.factor)
        return res

    def _factor_inv_write(self, cursor, user, id, name, value, arg, context=None):
        return self.write(cursor, user, id, {'factor': self._compute_factor_inv(value)}, context=context)

    def name_create(self, cr, uid, name, context=None):
        """ The UoM category and factor are required, so we'll have to add temporary values
            for imported UoMs """
        uom_categ = self.pool.get('product.uom.categ')
        # look for the category based on the english name, i.e. no context on purpose!
        # TODO: should find a way to have it translated but not created until actually used
        categ_misc = 'Unsorted/Imported Units'
        categ_id = uom_categ.search(cr, uid, [('name', '=', categ_misc)])
        if categ_id:
            categ_id = categ_id[0]
        else:
            categ_id, _ = uom_categ.name_create(cr, uid, categ_misc)
        uom_id = self.create(cr, uid, {self._rec_name: name,
                                       'category_id': categ_id,
                                       'factor': 1})
        return self.name_get(cr, uid, [uom_id], context=context)[0]

    def create(self, cr, uid, data, context=None):
        if 'factor_inv' in data:
            if data['factor_inv'] <> 1:
                data['factor'] = self._compute_factor_inv(data['factor_inv'])
            del(data['factor_inv'])
        return super(product_uom, self).create(cr, uid, data, context)

    _order = "name"
    _columns = {
        'name': fields.char('Unit of Measure', size=64, required=True, translate=True),
        'category_id': fields.many2one('product.uom.categ', 'Category', required=True, ondelete='cascade',
            help="Conversion between Units of Measure can only occur if they belong to the same category. The conversion will be made based on the ratios."),
        'factor': fields.float('Ratio', required=True, digits=0, # force NUMERIC with unlimited precision
            help='How much bigger or smaller this unit is compared to the reference Unit of Measure for this category:\n'\
                    '1 * (reference unit) = ratio * (this unit)'),
        'factor_inv': fields.function(_factor_inv, digits=0, # force NUMERIC with unlimited precision
            fnct_inv=_factor_inv_write,
            string='Ratio',
            help='How many times this Unit of Measure is bigger than the reference Unit of Measure in this category:\n'\
                    '1 * (this unit) = ratio * (reference unit)', required=True),
        'rounding': fields.float('Rounding Precision', digits_compute=dp.get_precision('Product Unit of Measure'), required=True,
            help="The computed quantity will be a multiple of this value. "\
                 "Use 1.0 for a Unit of Measure that cannot be further split, such as a piece."),
        'active': fields.boolean('Active', help="By unchecking the active field you can disable a unit of measure without deleting it."),
        'uom_type': fields.selection([('bigger','Bigger than the reference Unit of Measure'),
                                      ('reference','Reference Unit of Measure for this category'),
                                      ('smaller','Smaller than the reference Unit of Measure')],'Type', required=1),
    }

    _defaults = {
        'active': 1,
        'rounding': 0.01,
        'factor': 1,
        'uom_type': 'reference',
    }

    _sql_constraints = [
        ('factor_gt_zero', 'CHECK (factor!=0)', 'The conversion ratio for a unit of measure cannot be 0!')
    ]

    def _compute_qty(self, cr, uid, from_uom_id, qty, to_uom_id=False):
        if not from_uom_id or not qty or not to_uom_id:
            return qty
        uoms = self.browse(cr, uid, [from_uom_id, to_uom_id])
        if uoms[0].id == from_uom_id:
            from_unit, to_unit = uoms[0], uoms[-1]
        else:
            from_unit, to_unit = uoms[-1], uoms[0]
        return self._compute_qty_obj(cr, uid, from_unit, qty, to_unit)

    def _compute_qty_obj(self, cr, uid, from_unit, qty, to_unit, context=None):
        if context is None:
            context = {}
        if from_unit.category_id.id <> to_unit.category_id.id:
            if context.get('raise-exception', True):
                raise osv.except_osv(_('Error!'), _('Conversion from Product UoM %s to Default UoM %s is not possible as they both belong to different Category!.') % (from_unit.name,to_unit.name,))
            else:
                return qty
        amount = qty/from_unit.factor
        if to_unit:
            amount = ceiling(amount * to_unit.factor, to_unit.rounding)
        return amount

    def _compute_price(self, cr, uid, from_uom_id, price, to_uom_id=False):
        if not from_uom_id or not price or not to_uom_id:
            return price
        uoms = self.browse(cr, uid, [from_uom_id, to_uom_id])
        if uoms[0].id == from_uom_id:
            from_unit, to_unit = uoms[0], uoms[-1]
        else:
            from_unit, to_unit = uoms[-1], uoms[0]
        if from_unit.category_id.id <> to_unit.category_id.id:
            return price
        amount = price * from_unit.factor
        if to_uom_id:
            amount = amount / to_unit.factor
        return amount

    def onchange_type(self, cursor, user, ids, value):
        if value == 'reference':
            return {'value': {'factor': 1, 'factor_inv': 1}}
        return {}

    def write(self, cr, uid, ids, vals, context=None):
        if 'category_id' in vals:
            for uom in self.browse(cr, uid, ids, context=context):
                if uom.category_id.id != vals['category_id']:
                    raise osv.except_osv(_('Warning!'),_("Cannot change the category of existing Unit of Measure '%s'.") % (uom.name,))
        return super(product_uom, self).write(cr, uid, ids, vals, context=context)

product_uom()


class product_ul(osv.osv):
    _name = "product.ul"
    _description = "Shipping Unit"
    _columns = {
        'name' : fields.char('Name', size=64,select=True, required=True, translate=True),
        'type' : fields.selection([('unit','Unit'),('pack','Pack'),('box', 'Box'), ('pallet', 'Pallet')], 'Type', required=True),
    }
product_ul()


#----------------------------------------------------------
# Categories
#----------------------------------------------------------
class product_category(osv.osv):

    def name_get(self, cr, uid, ids, context=None):
        if isinstance(ids, (list, tuple)) and not len(ids):
            return []
        if isinstance(ids, (long, int)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name','parent_id'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1]+' / '+name
            res.append((record['id'], name))
        return res

    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    _name = "product.category"
    _description = "Product Category"
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True, select=True),
        'complete_name': fields.function(_name_get_fnc, type="char", string='Name'),
        'parent_id': fields.many2one('product.category','Parent Category', select=True, ondelete='cascade'),
        'child_id': fields.one2many('product.category', 'parent_id', string='Child Categories'),
        'sequence': fields.integer('Sequence', select=True, help="Gives the sequence order when displaying a list of product categories."),
        'type': fields.selection([('view','View'), ('normal','Normal')], 'Category Type', help="A category of the view type is a virtual category that can be used as the parent of another category to create a hierarchical structure."),
        'parent_left': fields.integer('Left Parent', select=1),
        'parent_right': fields.integer('Right Parent', select=1),
    }


    _defaults = {
        'type' : lambda *a : 'normal',
    }

    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'sequence, name'
    _order = 'parent_left'

    def _check_recursion(self, cr, uid, ids, context=None):
        level = 100
        while len(ids):
            cr.execute('select distinct parent_id from product_category where id IN %s',(tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive categories.', ['parent_id'])
    ]
    def child_get(self, cr, uid, ids):
        return [ids]

product_category()


#----------------------------------------------------------
# Products
#----------------------------------------------------------
class product_template(osv.osv):
    _name = "product.template"
    _description = "Product Template"

    _columns = {
        'name': fields.char('Name', size=128, required=True, translate=True, select=True),
        'product_manager': fields.many2one('res.users','Product Manager'),
        'description': fields.text('Description',translate=True),
        'description_purchase': fields.text('Purchase Description',translate=True),
        'description_sale': fields.text('Sale Description',translate=True),
        'type': fields.selection([('consu', 'Consumable'),('service','Service')], 'Product Type', required=True, help="Consumable are product where you don't manage stock, a service is a non-material product provided by a company or an individual."),
        'produce_delay': fields.float('Manufacturing Lead Time', help="Average delay in days to produce this product. In the case of multi-level BOM, the manufacturing lead times of the components will be added."),
        'rental': fields.boolean('Can be Rent'),
        'categ_id': fields.many2one('product.category','Category', required=True, change_default=True, domain="[('type','=','normal')]" ,help="Select category for the current product"),
        'list_price': fields.float('Sale Price', digits_compute=dp.get_precision('Product Price'), help="Base price to compute the customer price. Sometimes called the catalog price."),
        'standard_price': fields.float('Cost', digits_compute=dp.get_precision('Product Price'), help="Cost price of the product used for standard stock valuation in accounting and used as a base price on purchase orders.", groups="base.group_user"),
        'volume': fields.float('Volume', help="The volume in m3."),
        'weight': fields.float('Gross Weight', digits_compute=dp.get_precision('Stock Weight'), help="The gross weight in Kg."),
        'weight_net': fields.float('Net Weight', digits_compute=dp.get_precision('Stock Weight'), help="The net weight in Kg."),
        'cost_method': fields.selection([('standard','Standard Price'), ('average','Average Price')], 'Costing Method', required=True,
            help="Standard Price: The cost price is manually updated at the end of a specific period (usually every year). \nAverage Price: The cost price is recomputed at each incoming shipment."),
        'warranty': fields.float('Warranty'),
        'sale_ok': fields.boolean('Can be Sold', help="Specify if the product can be selected in a sales order line."),
        'state': fields.selection([('',''),
            ('draft', 'In Development'),
            ('sellable','Normal'),
            ('end','End of Lifecycle'),
            ('obsolete','Obsolete')], 'Status'),
        'uom_id': fields.many2one('product.uom', 'Unit of Measure', required=True, help="Default Unit of Measure used for all stock operation."),
        'uom_po_id': fields.many2one('product.uom', 'Purchase Unit of Measure', required=True, help="Default Unit of Measure used for purchase orders. It must be in the same category than the default unit of measure."),
        'uos_id' : fields.many2one('product.uom', 'Unit of Sale',
            help='Sepcify a unit of measure here if invoicing is made in another unit of measure than inventory. Keep empty to use the default unit of measure.'),
        'uos_coeff': fields.float('Unit of Measure -> UOS Coeff', digits_compute= dp.get_precision('Product UoS'),
            help='Coefficient to convert default Unit of Measure to Unit of Sale\n'
            ' uos = uom * coeff'),
        'mes_type': fields.selection((('fixed', 'Fixed'), ('variable', 'Variable')), 'Measure Type'),
        'seller_ids': fields.one2many('product.supplierinfo', 'product_id', 'Supplier'),
        'company_id': fields.many2one('res.company', 'Company', select=1),
    }

    def _get_uom_id(self, cr, uid, *args):
        cr.execute('select id from product_uom order by id limit 1')
        res = cr.fetchone()
        return res and res[0] or False

    def _default_category(self, cr, uid, context=None):
        if context is None:
            context = {}
        if 'categ_id' in context and context['categ_id']:
            return context['categ_id']
        md = self.pool.get('ir.model.data')
        res = False
        try:
            res = md.get_object_reference(cr, uid, 'product', 'product_category_all')[1]
        except ValueError:
            res = False
        return res

    def onchange_uom(self, cursor, user, ids, uom_id, uom_po_id):
        if uom_id:
            return {'value': {'uom_po_id': uom_id}}
        return {}

    def write(self, cr, uid, ids, vals, context=None):
        if 'uom_po_id' in vals:
            new_uom = self.pool.get('product.uom').browse(cr, uid, vals['uom_po_id'], context=context)
            for product in self.browse(cr, uid, ids, context=context):
                old_uom = product.uom_po_id
                if old_uom.category_id.id != new_uom.category_id.id:
                    raise osv.except_osv(_('Unit of Measure categories Mismatch!'), _("New Unit of Measure '%s' must belong to same Unit of Measure category '%s' as of old Unit of Measure '%s'. If you need to change the unit of measure, you may deactivate this product from the 'Procurements' tab and create a new one.") % (new_uom.name, old_uom.category_id.name, old_uom.name,))
        return super(product_template, self).write(cr, uid, ids, vals, context=context)

    _defaults = {
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'product.template', context=c),
        'list_price': 1,
        'cost_method': 'standard',
        'standard_price': 0.0,
        'sale_ok': 1,
        'produce_delay': 1,
        'uom_id': _get_uom_id,
        'uom_po_id': _get_uom_id,
        'uos_coeff' : 1.0,
        'mes_type' : 'fixed',
        'categ_id' : _default_category,
        'type' : 'consu',
    }

    def _check_uom(self, cursor, user, ids, context=None):
        for product in self.browse(cursor, user, ids, context=context):
            if product.uom_id.category_id.id <> product.uom_po_id.category_id.id:
                return False
        return True

    def _check_uos(self, cursor, user, ids, context=None):
        for product in self.browse(cursor, user, ids, context=context):
            if product.uos_id \
                    and product.uos_id.category_id.id \
                    == product.uom_id.category_id.id:
                return False
        return True

    _constraints = [
        (_check_uom, 'Error: The default Unit of Measure and the purchase Unit of Measure must be in the same category.', ['uom_id']),
    ]

    def name_get(self, cr, user, ids, context=None):
        if context is None:
            context = {}
        if 'partner_id' in context:
            pass
        return super(product_template, self).name_get(cr, user, ids, context)

product_template()

class product_product(osv.osv):
    def view_header_get(self, cr, uid, view_id, view_type, context=None):
        if context is None:
            context = {}
        res = super(product_product, self).view_header_get(cr, uid, view_id, view_type, context)
        if (context.get('categ_id', False)):
            return _('Products: ')+self.pool.get('product.category').browse(cr, uid, context['categ_id'], context=context).name
        return res

    def _product_price(self, cr, uid, ids, name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        quantity = context.get('quantity') or 1.0
        pricelist = context.get('pricelist', False)
        partner = context.get('partner', False)
        if pricelist:
            # Support context pricelists specified as display_name or ID for compatibility
            if isinstance(pricelist, basestring):
                pricelist_ids = self.pool.get('product.pricelist').name_search(
                    cr, uid, pricelist, operator='=', context=context, limit=1)
                pricelist = pricelist_ids[0][0] if pricelist_ids else pricelist
            for id in ids:
                try:
                    price = self.pool.get('product.pricelist').price_get(cr,uid,[pricelist], id, quantity, partner=partner, context=context)[pricelist]
                except:
                    price = 0.0
                res[id] = price
        for id in ids:
            res.setdefault(id, 0.0)
        return res

    def _get_product_available_func(states, what):
        def _product_available(self, cr, uid, ids, name, arg, context=None):
            return {}.fromkeys(ids, 0.0)
        return _product_available

    _product_qty_available = _get_product_available_func(('done',), ('in', 'out'))
    _product_virtual_available = _get_product_available_func(('confirmed','waiting','assigned','done'), ('in', 'out'))
    _product_outgoing_qty = _get_product_available_func(('confirmed','waiting','assigned'), ('out',))
    _product_incoming_qty = _get_product_available_func(('confirmed','waiting','assigned'), ('in',))

    def _product_lst_price(self, cr, uid, ids, name, arg, context=None):
        res = {}
        product_uom_obj = self.pool.get('product.uom')
        for id in ids:
            res.setdefault(id, 0.0)
        for product in self.browse(cr, uid, ids, context=context):
            if 'uom' in context:
                uom = product.uos_id or product.uom_id
                res[product.id] = product_uom_obj._compute_price(cr, uid,
                        uom.id, product.list_price, context['uom'])
            else:
                res[product.id] = product.list_price
            res[product.id] =  (res[product.id] or 0.0) * (product.price_margin or 1.0) + product.price_extra
        return res

    def _get_partner_code_name(self, cr, uid, ids, product, partner_id, context=None):
        for supinfo in product.seller_ids:
            if supinfo.name.id == partner_id:
                return {'code': supinfo.product_code or product.default_code, 'name': supinfo.product_name or product.name, 'variants': ''}
        res = {'code': product.default_code, 'name': product.name, 'variants': product.variants}
        return res

    def _product_code(self, cr, uid, ids, name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        for p in self.browse(cr, uid, ids, context=context):
            res[p.id] = self._get_partner_code_name(cr, uid, [], p, context.get('partner_id', None), context=context)['code']
        return res

    def _product_partner_ref(self, cr, uid, ids, name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        for p in self.browse(cr, uid, ids, context=context):
            data = self._get_partner_code_name(cr, uid, [], p, context.get('partner_id', None), context=context)
            if not data['variants']:
                data['variants'] = p.variants
            if not data['code']:
                data['code'] = p.code
            if not data['name']:
                data['name'] = p.name
            res[p.id] = (data['code'] and ('['+data['code']+'] ') or '') + \
                    (data['name'] or '') + (data['variants'] and (' - '+data['variants']) or '')
        return res


    def _get_main_product_supplier(self, cr, uid, product, context=None):
        """Determines the main (best) product supplier for ``product``,
        returning the corresponding ``supplierinfo`` record, or False
        if none were found. The default strategy is to select the
        supplier with the highest priority (i.e. smallest sequence).

        :param browse_record product: product to supply
        :rtype: product.supplierinfo browse_record or False
        """
        sellers = [(seller_info.sequence, seller_info)
                       for seller_info in product.seller_ids or []
                       if seller_info and isinstance(seller_info.sequence, (int, long))]
        return sellers and sellers[0][1] or False

    def _calc_seller(self, cr, uid, ids, fields, arg, context=None):
        result = {}
        for product in self.browse(cr, uid, ids, context=context):
            main_supplier = self._get_main_product_supplier(cr, uid, product, context=context)
            result[product.id] = {
                'seller_info_id': main_supplier and main_supplier.id or False,
                'seller_delay': main_supplier.delay if main_supplier else 1,
                'seller_qty': main_supplier and main_supplier.qty or 0.0,
                'seller_id': main_supplier and main_supplier.name.id or False
            }
        return result


    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image, avoid_resize_medium=True)
        return result

    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)

    def _get_name_template_ids(self, cr, uid, ids, context=None):
        template_ids = self.pool.get('product.product').search(cr, uid, [('product_tmpl_id', 'in', ids)])
        return list(set(template_ids))

    _defaults = {
        'active': lambda *a: 1,
        'price_extra': lambda *a: 0.0,
        'price_margin': lambda *a: 1.0,
        'color': 0,
    }

    _name = "product.product"
    _description = "Product"
    _table = "product_product"
    _inherits = {'product.template': 'product_tmpl_id'}
    _inherit = ['mail.thread']
    _order = 'default_code,name_template'
    _columns = {
        'qty_available': fields.function(_product_qty_available, type='float', string='Quantity On Hand'),
        'virtual_available': fields.function(_product_virtual_available, type='float', string='Quantity Available'),
        'incoming_qty': fields.function(_product_incoming_qty, type='float', string='Incoming'),
        'outgoing_qty': fields.function(_product_outgoing_qty, type='float', string='Outgoing'),
        'price': fields.function(_product_price, type='float', string='Price', digits_compute=dp.get_precision('Product Price')),
        'lst_price' : fields.function(_product_lst_price, type='float', string='Public Price', digits_compute=dp.get_precision('Product Price')),
        'code': fields.function(_product_code, type='char', string='Internal Reference'),
        'partner_ref' : fields.function(_product_partner_ref, type='char', string='Customer ref'),
        'default_code' : fields.char('Internal Reference', size=64, select=True),
        'active': fields.boolean('Active', help="If unchecked, it will allow you to hide the product without removing it."),
        'variants': fields.char('Variants', size=64),
        'product_tmpl_id': fields.many2one('product.template', 'Product Template', required=True, ondelete="cascade", select=True),
        'ean13': fields.char('EAN13 Barcode', size=13, help="International Article Number used for product identification."),
        'packaging' : fields.one2many('product.packaging', 'product_id', 'Logistical Units', help="Gives the different ways to package the same product. This has no impact on the picking order and is mainly used if you use the EDI module."),
        'price_extra': fields.float('Variant Price Extra', digits_compute=dp.get_precision('Product Price')),
        'price_margin': fields.float('Variant Price Margin', digits_compute=dp.get_precision('Product Price')),
        'pricelist_id': fields.dummy(string='Pricelist', relation='product.pricelist', type='many2one'),
        'name_template': fields.related('product_tmpl_id', 'name', string="Template Name", type='char', size=128, store={
            'product.template': (_get_name_template_ids, ['name'], 10),
            'product.product': (lambda self, cr, uid, ids, c=None: ids, ['product_tmpl_id'], 10),

            }, select=True),
        'color': fields.integer('Color Index'),
        # image: all image fields are base64 encoded and PIL-supported
        'image': fields.binary("Image",
            help="This field holds the image used as image for the product, limited to 1024x1024px."),
        'image_medium': fields.function(_get_image, fnct_inv=_set_image,
            string="Medium-sized image", type="binary", multi="_get_image",
            store={
                'product.product': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized image of the product. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved, "\
                 "only when the image exceeds one of those sizes. Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image, fnct_inv=_set_image,
            string="Small-sized image", type="binary", multi="_get_image",
            store={
                'product.product': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized image of the product. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
        'seller_info_id': fields.function(_calc_seller, type='many2one', relation="product.supplierinfo", string="Supplier Info", multi="seller_info"),
        'seller_delay': fields.function(_calc_seller, type='integer', string='Supplier Lead Time', multi="seller_info", help="This is the average delay in days between the purchase order confirmation and the reception of goods for this product and for the default supplier. It is used by the scheduler to order requests based on reordering delays."),
        'seller_qty': fields.function(_calc_seller, type='float', string='Supplier Quantity', multi="seller_info", help="This is minimum quantity to purchase from Main Supplier."),
        'seller_id': fields.function(_calc_seller, type='many2one', relation="res.partner", string='Main Supplier', help="Main Supplier who has highest priority in Supplier List.", multi="seller_info"),
    }
    def unlink(self, cr, uid, ids, context=None):
        unlink_ids = []
        unlink_product_tmpl_ids = []
        for product in self.browse(cr, uid, ids, context=context):
            # Check if product still exists, in case it has been unlinked by unlinking its template
            if not product.exists():
                continue
            tmpl_id = product.product_tmpl_id.id
            # Check if the product is last product of this template
            other_product_ids = self.search(cr, uid, [('product_tmpl_id', '=', tmpl_id), ('id', '!=', product.id)], context=context)
            if not other_product_ids:
                unlink_product_tmpl_ids.append(tmpl_id)
            unlink_ids.append(product.id)
        res = super(product_product, self).unlink(cr, uid, unlink_ids, context=context)
        # delete templates after calling super, as deleting template could lead to deleting
        # products due to ondelete='cascade'
        self.pool.get('product.template').unlink(cr, uid, unlink_product_tmpl_ids, context=context)
        return res

    def onchange_uom(self, cursor, user, ids, uom_id, uom_po_id):
        if uom_id and uom_po_id:
            uom_obj=self.pool.get('product.uom')
            uom=uom_obj.browse(cursor,user,[uom_id])[0]
            uom_po=uom_obj.browse(cursor,user,[uom_po_id])[0]
            if uom.category_id.id != uom_po.category_id.id:
                return {'value': {'uom_po_id': uom_id}}
        return False

    def _check_ean_key(self, cr, uid, ids, context=None):
        for product in self.read(cr, uid, ids, ['ean13'], context=context):
            res = check_ean(product['ean13'])
        return res


    _constraints = [(_check_ean_key, 'You provided an invalid "EAN13 Barcode" reference. You may use the "Internal Reference" field instead.', ['ean13'])]

    def on_order(self, cr, uid, ids, orderline, quantity):
        pass

    def name_get(self, cr, user, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not len(ids):
            return []
        def _name_get(d):
            name = d.get('name','')
            code = d.get('default_code',False)
            if code:
                name = '[%s] %s' % (code,name)
            if d.get('variants'):
                name = name + ' - %s' % (d['variants'],)
            return (d['id'], name)

        partner_id = context.get('partner_id', False)
        if partner_id:
            partner_ids = [partner_id, self.pool['res.partner'].browse(cr, user, partner_id, context=context).commercial_partner_id.id]
        else:
            partner_ids = []

        result = []
        for product in self.browse(cr, user, ids, context=context):
            sellers = partner_ids and filter(lambda x: x.name.id in partner_ids, product.seller_ids) or []
            if sellers:
                for s in sellers:
                    mydict = {
                              'id': product.id,
                              'name': s.product_name or product.name,
                              'default_code': s.product_code or product.default_code,
                              'variants': product.variants
                              }
                    result.append(_name_get(mydict))
            else:
                mydict = {
                          'id': product.id,
                          'name': product.name,
                          'default_code': product.default_code,
                          'variants': product.variants
                          }
                result.append(_name_get(mydict))
        return result

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            ids = []
            if operator in positive_operators:
                ids = self.search(cr, user, [('default_code','=',name)]+ args, limit=limit, context=context)
                if not ids:
                    ids = self.search(cr, user, [('ean13','=',name)]+ args, limit=limit, context=context)
            if not ids and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching products, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                ids = set()
                ids.update(self.search(cr, user, args + [('default_code',operator,name)], limit=limit, context=context))
                if not limit or len(ids) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    ids.update(self.search(cr, user, args + [('name',operator,name), ('id', 'not in', list(ids))], limit=(limit and (limit-len(ids)) or False) , context=context))
                ids = list(ids)
            elif not ids and operator in expression.NEGATIVE_TERM_OPERATORS:
                ids = self.search(cr, user, args + ['&', ('default_code', operator, name), ('name', operator, name)], limit=limit, context=context)
            if not ids and operator in positive_operators:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    ids = self.search(cr, user, [('default_code','=', res.group(2))] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context=context)
        return result

    #
    # Could be overrided for variants matrices prices
    #
    def price_get(self, cr, uid, ids, ptype='list_price', context=None):
        if context is None:
            context = {}

        if 'currency_id' in context:
            pricetype_obj = self.pool.get('product.price.type')
            price_type_id = pricetype_obj.search(cr, uid, [('field','=',ptype)])[0]
            price_type_currency_id = pricetype_obj.browse(cr,uid,price_type_id).currency_id.id

        res = {}
        product_uom_obj = self.pool.get('product.uom')
        company_id = self.pool['res.users'].read(cr, uid, uid, ['company_id'], context=context)['company_id'][0]
        for product in self.browse(cr, SUPERUSER_ID, ids, context=dict(context, force_company=company_id)):
            res[product.id] = product[ptype] or 0.0
            if ptype == 'list_price':
                res[product.id] = (res[product.id] * (product.price_margin or 1.0)) + \
                        product.price_extra
            if 'uom' in context:
                uom = product.uom_id or product.uos_id
                res[product.id] = product_uom_obj._compute_price(cr, uid,
                        uom.id, res[product.id], context['uom'])
            # Convert from price_type currency to asked one
            if 'currency_id' in context:
                # Take the price_type currency from the product field
                # This is right cause a field cannot be in more than one currency
                res[product.id] = self.pool.get('res.currency').compute(cr, uid, price_type_currency_id,
                    context['currency_id'], res[product.id],context=context)

        return res

    def copy(self, cr, uid, id, default=None, context=None):
        if context is None:
            context={}

        if not default:
            default = {}

        product = self.read(cr, uid, id, ['name'], context=context)
        default = default.copy()
        default.update(name=_("%s (copy)") % (product['name']))

        if context.get('variant',False):
            fields = ['product_tmpl_id', 'active', 'variants', 'default_code',
                    'price_margin', 'price_extra']
            data = self.read(cr, uid, id, fields=fields, context=context)
            for f in fields:
                if f in default:
                    data[f] = default[f]
            data['product_tmpl_id'] = data.get('product_tmpl_id', False) \
                    and data['product_tmpl_id'][0]
            del data['id']
            return self.create(cr, uid, data)
        else:
            return super(product_product, self).copy(cr, uid, id, default=default,
                    context=context)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        if context and context.get('search_default_categ_id', False):
            args.append((('categ_id', 'child_of', context['search_default_categ_id'])))
        return super(product_product, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)

    def _compute_uos_qty(self, cr, uid, ids, uom, qty, uos, context=None):
        '''
        Computes product's invoicing quantity in UoS from quantity in UoM.
        Takes into account the
        :param uom: Source unit
        :param qty: Source quantity
        :param uos: Target UoS unit.
        '''
        if not uom or not qty or not uos:
            return qty
        uom_obj = self.pool['product.uom']
        product_id = ids[0] if isinstance(ids, (list, tuple)) else ids
        product = self.browse(cr, uid, product_id, context=context)
        if isinstance(uos, (int, long)):
            uos = uom_obj.browse(cr, uid, uos, context=context)
        if isinstance(uom, (int, long)):
            uom = uom_obj.browse(cr, uid, uom, context=context)
        if product.uos_id:  # Product has UoS defined
            # We cannot convert directly between units even if the units are of the same category
            # as we need to apply the conversion coefficient which is valid only between quantities
            # in product's default UoM/UoS
            qty_default_uom = uom_obj._compute_qty_obj(cr, uid, uom, qty, product.uom_id)  # qty in product's default UoM
            qty_default_uos = qty_default_uom * product.uos_coeff
            return uom_obj._compute_qty_obj(cr, uid, product.uos_id, qty_default_uos, uos)
        else:
            return uom_obj._compute_qty_obj(cr, uid, uom, qty, uos)


product_product()

class product_packaging(osv.osv):
    _name = "product.packaging"
    _description = "Packaging"
    _rec_name = 'ean'
    _order = 'sequence'
    _columns = {
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of packaging."),
        'name' : fields.text('Description', size=64),
        'qty' : fields.float('Quantity by Package',
            help="The total number of products you can put by pallet or box."),
        'ul' : fields.many2one('product.ul', 'Type of Package', required=True),
        'ul_qty' : fields.integer('Package by layer', help='The number of packages by layer'),
        'rows' : fields.integer('Number of Layers', required=True,
            help='The number of layers on a pallet or box'),
        'product_id' : fields.many2one('product.product', 'Product', select=1, ondelete='cascade', required=True),
        'ean' : fields.char('EAN', size=14,
            help="The EAN code of the package unit."),
        'code' : fields.char('Code', size=14,
            help="The code of the transport unit."),
        'weight': fields.float('Total Package Weight',
            help='The weight of a full package, pallet or box.'),
        'weight_ul': fields.float('Empty Package Weight'),
        'height': fields.float('Height', help='The height of the package'),
        'width': fields.float('Width', help='The width of the package'),
        'length': fields.float('Length', help='The length of the package'),
    }


    def _check_ean_key(self, cr, uid, ids, context=None):
        for pack in self.browse(cr, uid, ids, context=context):
            res = check_ean(pack.ean)
        return res

    _constraints = [(_check_ean_key, 'Error: Invalid ean code', ['ean'])]

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        res = []
        for pckg in self.browse(cr, uid, ids, context=context):
            p_name = pckg.ean and '[' + pckg.ean + '] ' or ''
            p_name += pckg.ul.name
            res.append((pckg.id,p_name))
        return res

    def _get_1st_ul(self, cr, uid, context=None):
        cr.execute('select id from product_ul order by id asc limit 1')
        res = cr.fetchone()
        return (res and res[0]) or False

    _defaults = {
        'rows' : lambda *a : 3,
        'sequence' : lambda *a : 1,
        'ul' : _get_1st_ul,
    }

    def checksum(ean):
        salt = '31' * 6 + '3'
        sum = 0
        for ean_part, salt_part in zip(ean, salt):
            sum += int(ean_part) * int(salt_part)
        return (10 - (sum % 10)) % 10
    checksum = staticmethod(checksum)

product_packaging()


class product_supplierinfo(osv.osv):
    _name = "product.supplierinfo"
    _description = "Information about a product supplier"
    def _calc_qty(self, cr, uid, ids, fields, arg, context=None):
        result = {}
        product_uom_pool = self.pool.get('product.uom')
        for supplier_info in self.browse(cr, uid, ids, context=context):
            for field in fields:
                result[supplier_info.id] = {field:False}
            qty = supplier_info.min_qty
            result[supplier_info.id]['qty'] = qty
        return result

    _columns = {
        'name' : fields.many2one('res.partner', 'Supplier', required=True,domain = [('supplier','=',True)], ondelete='cascade', help="Supplier of this product"),
        'product_name': fields.char('Supplier Product Name', size=128, help="This supplier's product name will be used when printing a request for quotation. Keep empty to use the internal one."),
        'product_code': fields.char('Supplier Product Code', size=64, help="This supplier's product code will be used when printing a request for quotation. Keep empty to use the internal one."),
        'sequence' : fields.integer('Sequence', help="Assigns the priority to the list of product supplier."),
        'product_uom': fields.related('product_id', 'uom_po_id', type='many2one', relation='product.uom', string="Supplier Unit of Measure", readonly="1", help="This comes from the product form."),
        'min_qty': fields.float('Minimal Quantity', required=True, help="The minimal quantity to purchase to this supplier, expressed in the supplier Product Unit of Measure if not empty, in the default unit of measure of the product otherwise."),
        'qty': fields.function(_calc_qty, store=True, type='float', string='Quantity', multi="qty", help="This is a quantity which is converted into Default Unit of Measure."),
        'product_id' : fields.many2one('product.template', 'Product', required=True, ondelete='cascade', select=True),
        'delay' : fields.integer('Delivery Lead Time', required=True, help="Lead time in days between the confirmation of the purchase order and the reception of the products in your warehouse. Used by the scheduler for automatic computation of the purchase order planning."),
        'pricelist_ids': fields.one2many('pricelist.partnerinfo', 'suppinfo_id', 'Supplier Pricelist'),
        'company_id':fields.many2one('res.company','Company',select=1),
    }
    _defaults = {
        'qty': lambda *a: 0.0,
        'sequence': lambda *a: 1,
        'delay': lambda *a: 1,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'product.supplierinfo', context=c),
    }
    def price_get(self, cr, uid, supplier_ids, product_id, product_qty=1, context=None):
        """
        Calculate price from supplier pricelist.
        @param supplier_ids: Ids of res.partner object.
        @param product_id: Id of product.
        @param product_qty: specify quantity to purchase.
        """
        if type(supplier_ids) in (int,long,):
            supplier_ids = [supplier_ids]
        res = {}
        product_pool = self.pool.get('product.product')
        partner_pool = self.pool.get('res.partner')
        pricelist_pool = self.pool.get('product.pricelist')
        currency_pool = self.pool.get('res.currency')
        currency_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id
        for supplier in partner_pool.browse(cr, uid, supplier_ids, context=context):
            # Compute price from standard price of product
            price = product_pool.price_get(cr, uid, [product_id], 'standard_price', context=context)[product_id]

            # Compute price from Purchase pricelist of supplier
            pricelist_id = supplier.property_product_pricelist_purchase.id
            if pricelist_id:
                price = pricelist_pool.price_get(cr, uid, [pricelist_id], product_id, product_qty, context=context).setdefault(pricelist_id, 0)
                price = currency_pool.compute(cr, uid, pricelist_pool.browse(cr, uid, pricelist_id).currency_id.id, currency_id, price)

            # Compute price from supplier pricelist which are in Supplier Information
            supplier_info_ids = self.search(cr, uid, [('name','=',supplier.id),('product_id','=',product_id)])
            if supplier_info_ids:
                cr.execute('SELECT * ' \
                    'FROM pricelist_partnerinfo ' \
                    'WHERE suppinfo_id IN %s' \
                    'AND min_quantity <= %s ' \
                    'ORDER BY min_quantity DESC LIMIT 1', (tuple(supplier_info_ids),product_qty,))
                res2 = cr.dictfetchone()
                if res2:
                    price = res2['price']
            res[supplier.id] = price
        return res
    _order = 'sequence'
product_supplierinfo()


class pricelist_partnerinfo(osv.osv):
    _name = 'pricelist.partnerinfo'
    _columns = {
        'name': fields.char('Description', size=64),
        'suppinfo_id': fields.many2one('product.supplierinfo', 'Partner Information', required=True, ondelete='cascade'),
        'min_quantity': fields.float('Quantity', required=True, help="The minimal quantity to trigger this rule, expressed in the supplier Unit of Measure if any or in the default Unit of Measure of the product otherrwise."),
        'price': fields.float('Unit Price', required=True, digits_compute=dp.get_precision('Product Price'), help="This price will be considered as a price for the supplier Unit of Measure if any or the default Unit of Measure of the product otherwise"),
    }
    _order = 'min_quantity asc'
pricelist_partnerinfo()

class res_currency(osv.osv):
    _inherit = 'res.currency'

    def _check_main_currency_rounding(self, cr, uid, ids, context=None):
        cr.execute('SELECT digits FROM decimal_precision WHERE name like %s',('Account',))
        digits = cr.fetchone()
        if digits and len(digits):
            digits = digits[0]
            main_currency = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id
            for currency_id in ids:
                if currency_id == main_currency.id:
                    if main_currency.rounding < 10 ** -digits:
                        return False
        return True

    _constraints = [
        (_check_main_currency_rounding, 'Error! You cannot define a rounding factor for the company\'s main currency that is smaller than the decimal precision of \'Account\'.', ['rounding']),
    ]

class decimal_precision(osv.osv):
    _inherit = 'decimal.precision'

    def _check_main_currency_rounding(self, cr, uid, ids, context=None):
        cr.execute('SELECT id, digits FROM decimal_precision WHERE name like %s',('Account',))
        res = cr.fetchone()
        if res and len(res):
            account_precision_id, digits = res
            main_currency = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id
            for decimal_precision in ids:
                if decimal_precision == account_precision_id:
                    if main_currency.rounding < 10 ** -digits:
                        return False
        return True

    _constraints = [
        (_check_main_currency_rounding, 'Error! You cannot define the decimal precision of \'Account\' as greater than the rounding factor of the company\'s main currency', ['digits']),
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
