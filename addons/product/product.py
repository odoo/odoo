# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import psycopg2

from odoo import api, fields, models, tools, _
import odoo.addons.decimal_precision as dp
from odoo.osv import expression
from odoo.tools.float_utils import float_round, float_compare
from odoo.exceptions import UserError, except_orm

#----------------------------------------------------------
# UOM
#----------------------------------------------------------

class ProductUomCateg(models.Model):
    _name = 'product.uom.categ'
    _description = 'Product uom categ'

    name = fields.Char(required=True, translate=True)


class ProductUom(models.Model):
    _name = 'product.uom'
    _description = 'Product Unit of Measure'
    _order = "name"

    def _get_factor_inv(self, factor):
        return factor and (1.0 / factor) or 0.0

    @api.depends('factor')
    def _compute_factor_inv(self):
        for uom in self:
            uom.factor_inv = self._get_factor_inv(uom.factor)

    def _compute_factor_inv_write(self):
        for uom in self:
            uom.factor = self._get_factor_inv(uom.factor)

    @api.model
    def name_create(self, name):
        """ The UoM category and factor are required, so we'll have to add temporary values
            for imported UoMs """
        ProductUomCateg = self.env['product.uom.categ']
        values = {self._rec_name: name, 'factor': 1}
        # look for the category based on the english name, i.e. no context on purpose!
        # TODO: should find a way to have it translated but not created until actually used
        if not self.env.context.get('default_category_id'):
            categ_misc = 'Unsorted/Imported Units'
            category = ProductUomCateg.search([('name', '=', categ_misc)], limit=1)
            if category:
                values['category_id'] = category.id
            else:
                values['category_id'] = ProductUomCateg.name_create(
                    categ_misc)
        product_uom = self.create(values)
        return product_uom.name_get()[0]

    @api.model
    def create(self, vals):
        if 'factor_inv' in vals:
            if vals['factor_inv'] != 1:
                vals['factor'] = self._get_factor_inv(vals['factor_inv'])
            del(vals['factor_inv'])
        return super(ProductUom, self).create(vals)

    name = fields.Char(string='Unit of Measure', required=True, translate=True)
    category_id = fields.Many2one('product.uom.categ', string='Unit of Measure Category', required=True, ondelete='cascade',
        help="Conversion between Units of Measure can only occur if they belong to the same category. The conversion will be made based on the ratios.")
    factor = fields.Float(string='Ratio', required=True, digits=0,  # force NUMERIC with unlimited precision
        help='How much bigger or smaller this unit is compared to the reference Unit of Measure for this category:\n'\
                '1 * (reference unit) = ratio * (this unit)', default=1)
    factor_inv = fields.Float(compute='_compute_factor_inv', digits=0,  # force NUMERIC with unlimited precision
        inverse='_compute_factor_inv_write', string='Bigger Ratio',
        help='How many times this Unit of Measure is bigger than the reference Unit of Measure in this category:\n'\
                '1 * (this unit) = ratio * (reference unit)', required=True)
    rounding = fields.Float(string='Rounding Precision', digits=0, required=True,
        help="The computed quantity will be a multiple of this value. "\
             "Use 1.0 for a Unit of Measure that cannot be further split, such as a piece.", default=0.01)
    active = fields.Boolean(help="By unchecking the active field you can disable a unit of measure without deleting it.", default=True)
    uom_type = fields.Selection([('bigger', 'Bigger than the reference Unit of Measure'),
                                  ('reference', 'Reference Unit of Measure for this category'),
                                  ('smaller', 'Smaller than the reference Unit of Measure')], string='Type', required=True, default='reference')

    _sql_constraints = [
        ('factor_gt_zero', 'CHECK (factor!=0)', 'The conversion ratio for a unit of measure cannot be 0!')
    ]

    @api.v7
    def _compute_qty(self, cr, uid, from_uom_id, qty, to_uom_id=False, round=True, rounding_method='UP'):
        from_uom = self.browse(cr, uid, from_uom_id)
        return from_uom._compute_qty(qty, to_uom_id=to_uom_id, round=round, rounding_method=rounding_method)

    @api.v8
    def _compute_qty(self, qty, to_uom_id=False, round=True, rounding_method='UP'):
        self.ensure_one()
        if not self or not qty or not to_uom_id:
            return qty
        to_uom = self.browse(to_uom_id)
        if to_uom == self:
            from_unit, to_unit = to_uom, self
        else:
            from_unit, to_unit = self, to_uom
        return from_unit._compute_qty_obj(qty, to_unit, round=round, rounding_method=rounding_method)

    @api.v7
    def _compute_qty_obj(self, cr, uid, from_unit, qty, to_unit, round=True, rounding_method='UP', context=None):
        return from_unit._compute_qty_obj(qty, to_unit, round=round, rounding_method=rounding_method)

    @api.v8
    def _compute_qty_obj(self, qty, to_unit, round=True, rounding_method='UP'):
        self.ensure_one()
        if self.category_id != to_unit.category_id:
            if self.env.context.get('raise-exception', True):
                raise UserError(_('Conversion from Product UoM %s to Default UoM %s is not possible as they both belong to different Category!.') % (self.name, to_unit.name))
            else:
                return qty
        amount = qty/self.factor
        if to_unit:
            amount = amount * to_unit.factor
            if round:
                amount = float_round(amount, precision_rounding=to_unit.rounding, rounding_method=rounding_method)
        return amount

    @api.v7
    def _compute_price(self, cr, uid, from_uom_id, price, to_uom_id=False):
        from_unit = self.browse(cr, uid, from_uom_id)
        return from_unit._compute_price(price, to_uom_id=to_uom_id)

    @api.v8
    def _compute_price(self, price, to_uom_id=False):
        self.ensure_one()
        if (not price or not to_uom_id
                or (to_uom_id == self.id)):
            return price
        to_unit = self.browse(to_uom_id)
        if self.category_id != to_unit.category_id:
            return price
        amount = (price * self.factor) / to_unit.factor
        return amount

    @api.onchange('uom_type')
    def onchange_type(self):
        if self.uom_type == 'reference':
            self.factor = 1
            self.factor_inv = 1


#----------------------------------------------------------
# Categories
#----------------------------------------------------------
class ProductCategory(models.Model):
    _name = "product.category"
    _description = "Product Category"
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'sequence, name'
    _order = 'parent_left'

    @api.multi
    def name_get(self):
        def get_names(cat):
            """ Return the list [cat.name, cat.parent_id.name, ...] """
            res = []
            while cat:
                res.append(cat.name)
                cat = cat.parent_id
            return res
        return [(cat.id, " / ".join(reversed(get_names(cat)))) for cat in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            # Be sure name_search is symetric to name_get
            categories = name.split(' / ')
            parents = list(categories)
            child = parents.pop()
            domain = [('name', operator, child)]
            if parents:
                names_ids = self.name_search(' / '.join(parents), args=args, operator='ilike', limit=limit)
                category_ids = [name_id[0] for name_id in names_ids]
                if operator in expression.NEGATIVE_TERM_OPERATORS:
                    category_ids = self.search([('id', 'not in', category_ids)]).ids
                    domain = expression.OR([[('parent_id', 'in', category_ids)], domain])
                else:
                    domain = expression.AND([[('parent_id', 'in', category_ids)], domain])
                for i in range(1, len(categories)):
                    domain = [[('name', operator, ' / '.join(categories[-1 - i:]))], domain]
                    if operator in expression.NEGATIVE_TERM_OPERATORS:
                        domain = expression.AND(domain)
                    else:
                        domain = expression.OR(domain)
            product_categories = self.search(expression.AND([domain, args]), limit=limit)
        else:
            product_categories = self.search(args, limit=limit)
        return product_categories.name_get()

    def _compute_name(self):
        name_get = dict(self.name_get())
        for pc in self:
            pc.complete_name = name_get[pc.id]

    name = fields.Char(required=True, translate=True, index=True)
    complete_name = fields.Char(compute='_compute_name', string='Name')
    parent_id = fields.Many2one('product.category', string='Parent Category', index=True, ondelete='cascade')
    child_id = fields.One2many('product.category', 'parent_id', string='Child Categories')
    sequence = fields.Integer(index=True, help="Gives the sequence order when displaying a list of product categories.")
    type = fields.Selection([('view', 'View'), ('normal', 'Normal')], string='Category Type',
        help="A category of the view type is a virtual category that can be used as the parent of another category to create a hierarchical structure.", default='normal')
    parent_left = fields.Integer(string='Left Parent', index=True)
    parent_right = fields.Integer(string='Right Parent', index=True)

    _constraints = [
        (models.Model._check_recursion, 'Error ! You cannot create recursive categories.', ['parent_id'])
    ]


class ProducePriceHistory(models.Model):
    """
    Keep track of the ``product.template`` standard prices as they are changed.
    """

    _name = 'product.price.history'
    _rec_name = 'datetime'
    _order = 'datetime desc'

    def _default_get_company(self):
        return self.env.context.get('force_company') or self.env.user.company_id.id

    company_id = fields.Many2one('res.company', string='Company', required=True, default=_default_get_company)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    datetime = fields.Datetime(string='Date', default=fields.datetime.now())
    cost = fields.Float()


#----------------------------------------------------------
# Product Attributes
#----------------------------------------------------------
class ProductAttribute(models.Model):
    _name = "product.attribute"
    _description = "Product Attribute"
    _order = 'sequence, id'

    name = fields.Char(translate=True, required=True)
    value_ids = fields.One2many('product.attribute.value', 'attribute_id', string='Values', copy=True)
    sequence = fields.Integer(help="Determine the display order")
    attribute_line_ids = fields.One2many('product.attribute.line', 'attribute_id', string='Lines')


class ProductAttributeValue(models.Model):
    _name = "product.attribute.value"
    _order = 'sequence'

    @api.multi
    def _compute_price_extra(self):
        product_tmpl_id = self.env.context.get('active_id')
        if product_tmpl_id and self.env.context.get('active_model') == 'product.template':
            for attr_price in self:
                for price_id in attr_price.price_ids.filtered(lambda x: x.product_tmpl_id.id == product_tmpl_id):
                    attr_price.price_extra = price_id.price_extra

    def _inverse_price_extra(self):
        ProductAttributePrice = self.env['product.attribute.price']
        product_tmpl_id = self.env.context.get('active_id')
        if product_tmpl_id and self.env.context.get('active_model') == 'product.template':
            product_attr_price = ProductAttributePrice.search([('value_id', '=', self.id), ('product_tmpl_id', '=', product_tmpl_id)])
            if product_attr_price:
                product_attr_price.write({'price_extra': self.price_extra})
            else:
                ProductAttributePrice.create({
                        'product_tmpl_id': product_tmpl_id,
                        'value_id': self.id,
                        'price_extra': self.price_extra})

    @api.multi
    def name_get(self):
        if not self.env.context.get('show_attribute', True):
            return super(ProductAttributeValue, self).name_get()
        res = []
        for value in self:
            res.append([value.id, "%s: %s" % (value.attribute_id.name, value.name)])
        return res

    sequence = fields.Integer(help="Determine the display order")
    name = fields.Char(string='Value', translate=True, required=True)
    attribute_id = fields.Many2one('product.attribute', string='Attribute', required=True, ondelete='cascade')
    product_ids = fields.Many2many('product.product', column1='att_id', column2='prod_id', string='Variants', readonly=True)
    price_extra = fields.Float(compute='_compute_price_extra', string='Attribute Price Extra', inverse='_inverse_price_extra',
        digits=dp.get_precision('Product Price'),
        help="Price Extra: Extra price for the variant with this attribute value on sale price. eg. 200 price extra, 1000 + 200 = 1200.")
    price_ids = fields.One2many('product.attribute.price', 'value_id', string='Attribute Prices', readonly=True)

    _sql_constraints = [
        ('value_company_uniq', 'unique (name, attribute_id)', 'This attribute value already exists !')
    ]

    @api.multi
    def unlink(self):
        products = self.env['product.product'].with_context(active_test=False).search([('attribute_value_ids', 'in', self.ids)])
        if products:
            raise UserError(_('The operation cannot be completed:\nYou are trying to delete an attribute value with a reference on a product variant.'))
        return super(ProductAttributeValue, self).unlink()


class ProductAttributePrice(models.Model):
    _name = "product.attribute.price"

    product_tmpl_id = fields.Many2one('product.template', string='Product Template', required=True, ondelete='cascade')
    value_id = fields.Many2one('product.attribute.value', string='Product Attribute Value', required=True, ondelete='cascade')
    price_extra = fields.Float(string='Price Extra', digits=dp.get_precision('Product Price'))


class ProductAttributeLine(models.Model):
    _name = "product.attribute.line"
    _rec_name = 'attribute_id'

    product_tmpl_id = fields.Many2one('product.template', string='Product Template', required=True, ondelete='cascade')
    attribute_id = fields.Many2one('product.attribute', string='Attribute', required=True, ondelete='restrict')
    value_ids = fields.Many2many('product.attribute.value', column1='line_id', column2='val_id', string='Attribute Values')

    @api.constrains('attribute_id')
    def _check_valid_attribute(self):
        for attr in self:
            if attr.value_ids > attr.attribute_id.value_ids:
                raise ValidationError(_("Error ! You cannot use this attribute with the following value."))

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        # TDE FIXME: currently overriding the domain; however as it includes a
        # search on a m2o and one on a m2m, probably this will quickly become
        # difficult to compute - check if performance optimization is required
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            new_args = ['|', ('attribute_id', operator, name), ('value_ids', operator, name)]
        else:
            new_args = args
        return super(ProductAttributeLine, self).name_search(name=name, args=new_args, operator=operator, limit=limit)


#----------------------------------------------------------
# Products
#----------------------------------------------------------
class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ['mail.thread']
    _description = "Product Template"
    _order = "name"

    def _default_get_uom_id(self):
        return self.env["product.uom"].search([], limit=1, order='id').id

    def _default_get_category(self):
        return self.env.context.get('categ_id') or self.env.ref('product.product_category_all').id

    def _compute_is_product_variant(self):
        return self._compute_is_product_variant_impl()

    def _compute_is_product_variant_impl(self):
        for product in self:
            product.is_product_variant = False

    def _compute_product_template_price(self):
        context = dict(self.env.context)
        ProductPricelist = self.env['product.pricelist']
        quantity = context.get('quantity') or 1.0
        pricelist = context.get('pricelist', False)
        partner = context.get('partner', False)
        if pricelist:
            # Support context pricelists specified as display_name or ID for compatibility
            if isinstance(pricelist, basestring):
                pricelist_ids = ProductPricelist.name_search(pricelist, operator='=', limit=1)
                pricelist = pricelist_ids[0][0] if pricelist_ids else pricelist
            if isinstance(pricelist, (int, long)):
                qtys = map(lambda x: (x, quantity, partner), self)
                price = ProductPricelist.browse(pricelist)._price_get_multi(qtys)
                for product in self:
                    product.price = price.get(product.id, 0.0)

    def _inverse_product_template_price(self):
        for product in self:
            value = product.price
            if self.env.context.get('uom'):
                value = self.env['product.uom'].browse(self.env.context['uom'])._compute_price(product.price, product.uom_id.id)
            product.list_price = value

    @api.depends('company_id')
    def _compute_product_currency(self):
        try:
            main_company = self.env.ref('base.main_company')
        except ValueError:
            main_company = self.env['res.company'].search([], limit=1, order="id")
        for product in self:
            product.currency_id = product.company_id.currency_id.id or main_company.currency_id.id

    def _compute_product_variant_count(self):
        for product in self:
            product.product_variant_count = len(product.product_variant_ids)

    @api.depends('product_variant_ids.standard_price', 'product_variant_ids.volume', 'product_variant_ids.weight', 'product_variant_ids.default_code')
    def _compute_product_template_field(self):
        ''' Compute the field from the product_variant if there is only one variant, otherwise returns 0.0 '''
        for product in self.filtered(lambda x: x.product_variant_count == 1):
            product.standard_price = product.product_variant_ids.standard_price
            product.volume = product.product_variant_ids.volume
            product.weight = product.product_variant_ids.weight
            product.default_code = product.product_variant_ids.default_code

    def _inverse_standard_price_product_template_field(self):
        ''' Set the standard price modification on the variant if there is only one variant '''
        for product in self.filtered(lambda x: x.product_variant_count == 1):
            product.product_variant_ids.write({'standard_price': product.standard_price})

    def _inverse_volume_product_template_field(self):
        ''' Set the volume modification on the variant if there is only one variant '''
        for product in self.filtered(lambda x: x.product_variant_count == 1):
            product.product_variant_ids.write({'volume': product.volume})

    def _inverse_weight_product_template_field(self):
        ''' Set the weight modification on the variant if there is only one variant '''
        for product in self.filtered(lambda x: x.product_variant_count == 1):
            product.product_variant_ids.write({'weight': product.weight})

    def _inverse_default_code_product_template_field(self):
        ''' Set the default_code modification on the variant if there is only one variant '''
        for product in self.filtered(lambda x: x.product_variant_count == 1):
            product.product_variant_ids.write({'default_code': product.default_code})

    def _search_by_standard_price(self, operator, value):
        r = self.env['product.product'].search_read([('standard_price', '=', value)], ['product_tmpl_id'], limit=None)
        return [('id', 'in', [x['product_tmpl_id'][0] for x in r])]

    @api.model
    def _get_product_template_type(self):
        return [('consu', 'Consumable'), ('service', 'Service')]

    name = fields.Char(required=True, translate=True, index=True)
    sequence = fields.Integer(help='Gives the sequence order when displaying a product list', default=1)
    product_manager = fields.Many2one('res.users', string='Product Manager')
    description = fields.Text(translate=True, help="A precise description of the Product, used only for internal information purposes.")
    description_purchase = fields.Text(string='Purchase Description', translate=True,
        help="A description of the Product that you want to communicate to your vendors. "
             "This description will be copied to every Purchase Order, Receipt and Vendor Bill/Refund.")
    description_sale = fields.Text(string='Sale Description', translate=True,
        help="A description of the Product that you want to communicate to your customers. "
             "This description will be copied to every Sale Order, Delivery Order and Customer Invoice/Refund")
    type = fields.Selection('_get_product_template_type', string='Product Type', required=True, 
                        help="Consumable are product where you don't manage stock, a service is a non-material product provided by a company or an individual.", default='consu')
    rental = fields.Boolean(string='Can be Rent')
    categ_id = fields.Many2one('product.category', string='Internal Category', required=True, change_default=True, domain="[('type', '=', 'normal')]",
        help="Select category for the current product", default=_default_get_category)
    price = fields.Float(compute='_compute_product_template_price', inverse='_inverse_product_template_price', digits=dp.get_precision('Product Price'))

    currency_id = fields.Many2one('res.currency', compute='_compute_product_currency', string='Currency')
    list_price = fields.Float(string='Sale Price', digits=dp.get_precision('Product Price'),
        help="Base price to compute the customer price. Sometimes called the catalog price.", default=1)
    lst_price = fields.Float(related='list_price', string='Public Price', digits=dp.get_precision('Product Price'))
    standard_price = fields.Float(compute='_compute_product_template_field', inverse='_inverse_standard_price_product_template_field', search='_search_by_standard_price',
        string='Cost', digits=dp.get_precision('Product Price'), groups="base.group_user", default=0.0,
        help="Cost of the product, in the default unit of measure of the product.")
    volume = fields.Float(compute='_compute_product_template_field', inverse='_inverse_volume_product_template_field',
        help="The volume in m3.", store=True)
    weight = fields.Float(compute='_compute_product_template_field', inverse='_inverse_weight_product_template_field', string='Gross Weight', digits=dp.get_precision('Stock Weight'),
        help="The weight of the contents in Kg, not including any packaging, etc.", store=True)

    warranty = fields.Float()
    sale_ok = fields.Boolean(string='Can be Sold', help="Specify if the product can be selected in a sales order line.", default=1)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True,
        help="Default Unit of Measure used for all stock operation.", default=_default_get_uom_id)
    uom_po_id = fields.Many2one('product.uom', string='Purchase Unit of Measure', required=True, default=_default_get_uom_id,
        help="Default Unit of Measure used for purchase orders. It must be in the same category than the default unit of measure.")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env['res.company']._company_default_get('product.template'))
    packaging_ids = fields.One2many('product.packaging', 'product_tmpl_id', string='Logistical Units',
        help="Gives the different ways to package the same product. This has no impact on "
            "the picking order and is mainly used if you use the EDI module.")
    seller_ids = fields.One2many('product.supplierinfo', 'product_tmpl_id', string='Vendor')

    active = fields.Boolean(help="If unchecked, it will allow you to hide the product without removing it.", default=True)
    color = fields.Integer(string='Color Index', default=0)
    is_product_variant = fields.Boolean(compute='_compute_is_product_variant', string='Is a product variant')

    attribute_line_ids = fields.One2many('product.attribute.line', 'product_tmpl_id', string='Product Attributes')
    product_variant_ids = fields.One2many('product.product', 'product_tmpl_id', string='Products', required=True)
    product_variant_count = fields.Integer(compute='_compute_product_variant_count', string='# of Product Variants')

    # related to display product product information if is_product_variant
    barcode = fields.Char(related='product_variant_ids.barcode', oldname='ean13')
    default_code = fields.Char(compute='_compute_product_template_field', inverse='_inverse_default_code_product_template_field', string='Internal Reference', store=True)
    item_ids = fields.One2many('product.pricelist.item', 'product_tmpl_id', string='Pricelist Items')

    # image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary(attachment=True,
        help="This field holds the image used as image for the product, limited to 1024x1024px.")
    image_medium = fields.Binary(compute='_compute_image', inverse='_inverse_image_medium', string="Medium-sized image", store=True, attachment=True,
        help="Medium-sized image of the product. It is automatically "\
             "resized as a 128x128px image, with aspect ratio preserved, "\
             "only when the image exceeds one of those sizes. Use this field in form views or some kanban views.")
    image_small = fields.Binary(compute='_compute_image', inverse='_inverse_image_small', string="Small-sized image", store=True, attachment=True,
        help="Small-sized image of the product. It is automatically "\
             "resized as a 64x64px image, with aspect ratio preserved. "\
             "Use this field anywhere a small image is required.")

    @api.depends('image')
    def _compute_images(self):
        for rec in self:
            rec.image_medium = tools.image_resize_image_medium(rec.image, avoid_if_small=True)
            rec.image_small = tools.image_resize_image_small(rec.image)

    def _inverse_image_medium(self):
        for rec in self:
            rec.image = tools.image_resize_image_big(rec.image_medium)

    def _inverse_image_small(self):
        for rec in self:
            rec.image = tools.image_resize_image_big(rec.image_small)

    @api.model
    def _price_get(self, products, ptype='list_price'):
        context = dict(self.env.context)
        if context.get('currency_id'):
            currency = self.env.user.company_id.currency_id
            to_cureency = self.env['res.currency'].browse(context['currency_id'])

        res = {}
        for product in products:
            # standard_price field can only be seen by users in base.group_user
            # Thus, in order to compute the sale price from the cost for users not in this group
            # We fetch the standard price as the superuser
            if ptype != 'standard_price':
                res[product.id] = product[ptype] or 0.0
            else:
                product = product.with_context(force_company=context.get('force_company') or product.env.user.company_id.id)
                res[product.id] = res[product.id] = product.sudo()[ptype]
            if ptype == 'list_price':
                res[product.id] += product._name == "product.product" and float(product.price_extra) or 0.0
            if 'uom' in context:
                res[product.id] = product.uom_id._compute_price(res[product.id], context['uom'])
            # Convert from current user company currency to asked one
            if 'currency_id' in context:
                # Take current user company currency.
                # This is right cause a field cannot be in more than one currency
                res[product.id] = currency.compute(res[product.id], to_cureency)
        return res

    @api.onchange('uom_id', 'uom_po_id')
    def onchange_uom(self):
        self.uom_po_id = self.uom_id

    @api.multi
    def create_variant_ids(self):
        ctx = dict(self.env.context)
        Product = self.env["product.product"]
        if ctx.get("create_product_variant"):
            return None

        ctx.update(active_test=False, create_product_variant=True)

        for tmpl_id in self.with_context(ctx):

            # list of values combination
            variant_alone = []
            all_variants = [[]]
            for variant_id in tmpl_id.attribute_line_ids:
                if len(variant_id.value_ids) == 1:
                    variant_alone.append(variant_id.value_ids[0])
                temp_variants = []
                for variant in all_variants:
                    for value_id in variant_id.value_ids:
                        temp_variants.append(sorted(variant + [int(value_id)]))
                if temp_variants:
                    all_variants = temp_variants

            # adding an attribute with only one value should not recreate product
            # write this attribute on every product to make sure we don't lose them
            for variant_id in variant_alone:
                product_ids = []
                for product_id in tmpl_id.product_variant_ids:
                    if variant_id.id not in map(int, product_id.attribute_value_ids):
                        product_ids.append(product_id.id)
                Product.browse(product_ids).with_context(ctx).write({'attribute_value_ids': [(4, variant_id.id)]})

            # check product
            variant_ids_to_active = []
            variants_active_ids = []
            variants_inactive = []
            for product_id in tmpl_id.product_variant_ids:
                variants = sorted(map(int, product_id.attribute_value_ids))
                if variants in all_variants:
                    variants_active_ids.append(product_id.id)
                    all_variants.pop(all_variants.index(variants))
                    if not product_id.active:
                        variant_ids_to_active.append(product_id.id)
                else:
                    variants_inactive.append(product_id)
            if variant_ids_to_active:
                Product.browse(variant_ids_to_active).with_context(ctx).write({'active': True})

            # create new product
            for variant_ids in all_variants:
                values = {
                    'product_tmpl_id': tmpl_id.id,
                    'attribute_value_ids': [(6, 0, variant_ids)]
                }
                product = Product.with_context(ctx).create(values)
                variants_active_ids.append(product.id)

            # unlink or inactive product
            for variant_id in variants_inactive:
                try:
                    with self.env.cr.savepoint(), tools.mute_logger('odoo.sql_db'):
                        variant_id.with_context(ctx).unlink()
                #We catch all kind of exception to be sure that the operation doesn't fail.
                except (psycopg2.Error, except_orm):
                    variant_id.with_context(ctx).write({'active': False})
                    pass
        return True

    @api.model
    def create(self, vals):
        ''' Store the initial standard price in order to be able to retrieve the cost of a product template for a given date'''
        product_template = super(ProductTemplate, self).create(vals)
        if not self.env.context.get("create_product_product"):
            product_template.create_variant_ids()
 
        # TODO: this is needed to set given values to first variant after creation
        # these fields should be moved to product as lead to confusion
        related = ['barcode', 'default_code', 'standard_price', 'volume', 'weight']
        related_vals = {}
        for r in related:
            if vals.get(r):
                related_vals[r] = vals[r]
        product_template.write(related_vals)
        return product_template

    @api.multi
    def write(self, vals):
        ctx = dict(self.env.context)
        res = super(ProductTemplate, self).write(vals)
        if 'attribute_line_ids' in vals or vals.get('active'):
            self.create_variant_ids()
        if 'active' in vals and not vals.get('active'):
            ctx.update(active_test=False)
            products = self.with_context(ctx).mapped('product_variant_ids')
            products.with_context(ctx).write({'active': vals.get('active')})
        return res

    @api.multi
    def copy(self, default=None):
        if default is None:
            default = {}
        default['name'] = _("%s (copy)") % (self.name)
        return super(ProductTemplate, self).copy(default=default)

    @api.constrains('uom_id', 'uom_po_id')
    def _check_uom(self):
        for uom in self:
            if uom.uom_id.category_id != uom.uom_po_id.category_id:
                return ValidationError(_('Error: The default Unit of Measure and the purchase Unit of Measure must be in the same category.'))

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        # Only use the product.product heuristics if there is a search term and the domain
        # does not specify a match on `product.template` IDs.
        Product = self.env['product.product']
        if not name or any(term[0] == 'id' for term in (args or [])):
            return super(ProductTemplate, self).name_search(
                name=name, args=args, operator=operator, limit=limit)
        results = Product.name_search(name, args, operator=operator, limit=limit)
        product_ids = [p[0] for p in results]
        template_ids = Product.browse(product_ids).mapped('product_tmpl_id').ids
        while (results and len(template_ids) < limit):
            domain = [('product_tmpl_id', 'not in', list(template_ids))]
            args = args if args is not None else []
            results = Product.name_search(
                name, args+domain, operator=operator, limit=limit)
            product_ids = [p[0] for p in results]
            template_ids = Product.browse(product_ids).mapped('product_tmpl_id').ids

        # re-apply product.template order + name_get
        return super(ProductTemplate, self).name_search('', args=[('id', 'in', template_ids)], operator='ilike', limit=limit)


class ProductProduct(models.Model):
    _name = "product.product"
    _description = "Product"
    _inherits = {'product.template': 'product_tmpl_id'}
    _inherit = ['mail.thread']
    _order = 'default_code, name_template'

    def _compute_product_price(self):
        context = dict(self.env.context)
        ProductPricelist = self.env['product.pricelist']
        quantity = context.get('quantity') or 1.0
        pricelist = context.get('pricelist', False)
        partner = context.get('partner', False)
        if pricelist:
            # Support context pricelists specified as display_name or ID for compatibility
            if isinstance(pricelist, basestring):
                pricelist_ids = ProductPricelist.name_search(pricelist, operator='=', limit=1)
                pricelist = pricelist_ids[0][0] if pricelist_ids else pricelist

            if isinstance(pricelist, (int, long)):
                qtys = map(lambda x: (x, quantity, partner), self)
                price = ProductPricelist.browse(pricelist)._price_get_multi(qtys)
                for product in self:
                    product.price = price.get(product.id, 0.0)
        for product in self:
            product.price = product.price if product.price else 0.0

    @api.multi
    def open_product_template(self):
        """ Utility method used to add an "Open Template" button in product views """
        self.ensure_one()
        return {'type': 'ir.actions.act_window',
                'res_model': 'product.template',
                'view_mode': 'form',
                'res_id': self.product_tmpl_id.id,
                'target': 'new'}

    @api.model
    def view_header_get(self, view_id, view_type):
        res = super(ProductProduct, self).view_header_get(view_id, view_type)
        if (self.env.context.get('categ_id', False)):
            return _('Products: ') + self.env['product.category'].browse(self.env.context['categ_id']).name
        return res

    def _compute_product_lst_price(self):
        for product in self:
            amount = product.list_price
            if self.env.context.get('uom'):
                amount = product.uom_id._compute_price(amount, self.env.context['uom'])
            product.lst_price = amount + float(product.price_extra)

    def _inverse_product_lst_price(self):
        for product in self:
            value = product.lst_price
            if self.env.context.get('uom'):
                value = self.env['product.uom'].browse(self.env.context['uom'])._compute_price(value, product.uom_id.id)
            product.list_price = value - float(product.price_extra)

    def _get_partner_code_name(self, partner_id):
        self.ensure_one()
        for supinfo in self.seller_ids.filtered(lambda s: s.name.id == partner_id):
            return {'code': supinfo.product_code or self.default_code, 'name': supinfo.product_name or self.name}
        return {'code': self.default_code, 'name': self.name}

    def _compute_product_code(self):
        for product in self:
            product.code = product._get_partner_code_name(self.env.context.get('partner_id', None))['code']

    def _compute_product_partner_ref(self):
        for product in self:
            data = product._get_partner_code_name(self.env.context.get('partner_id', None))
            data['code'] = data['code'] or product.code
            data['name'] = data['name'] or product.name
            product.partner_ref = (data['code'] and ('['+data['code']+'] ') or '') + (data['name'] or '')

    def _compute_is_product_variant_impl(self):
        for product in self:
            product.is_product_variant = True

    def _compute_image_variant(self):
        for product in self:
            if not product.image_variant:
                product.image = product.product_tmpl_id.image
                product.image_small = product.product_tmpl_id.image_small
                product.image_medium = product.product_tmpl_id.image_medium
                continue
            if self.env.context.get('bin_size'):
                product.image = product.image_variant
                product.image_small = product.image_variant
                product.image_medium = product.image_variant
            else:
                product.image = tools.image_resize_image_big(product.image_variant)
                product.image_small = tools.image_resize_image_small(product.image_variant)
                product.image_medium = tools.image_resize_image_medium(product.image_variant)

    def _inverse_image_variant(self):
        for product in self:
            image = tools.image_resize_image_big(product.image)
            if product.product_tmpl_id.image:
                product.image_variant = image
            else:
                product.product_tmpl_id.image = image

    def _inverse_image_small_variant(self):
        for product in self:
            image = tools.image_resize_image_big(product.image_small)
            if product.product_tmpl_id.image:
                product.image_variant = image
            else:
                product.product_tmpl_id.image = image

    def _inverse_image_medium_variant(self):
        for product in self:
            image = tools.image_resize_image_big(product.image_medium)
            if product.product_tmpl_id.image:
                product.image_variant = image
            else:
                product.product_tmpl_id.image = image

    def _compute_price_extra(self):
        for product in self:
            price_extra = 0.0
            for variant_id in product.attribute_value_ids:
                for price_id in variant_id.price_ids.filtered(lambda p: p.product_tmpl_id == product.product_tmpl_id):
                    price_extra += price_id.price_extra
            product.price_extra = price_extra

    @api.v7
    def _select_seller(self, cr, uid, product_id, partner_id=False, quantity=0.0, date=fields.Date.today(), uom_id=False, context=None):
        return product_id._select_seller(partner_id=partner_id, quantity=quantity, date=date, uom_id=uom_id)

    @api.v8
    def _select_seller(self, partner_id=False, quantity=0.0, date=fields.Date.today(), uom_id=False):
        self.ensure_one()
        ProductSupplierinfo = self.env['product.supplierinfo']
        for seller in self.seller_ids:
            # Set quantity in UoM of seller
            quantity_uom_seller = quantity
            if quantity_uom_seller and uom_id and uom_id != seller.product_uom:
                quantity_uom_seller = uom_id._compute_qty_obj(quantity_uom_seller, seller.product_uom)

            if seller.date_start and seller.date_start > date:
                continue
            if seller.date_end and seller.date_end < date:
                continue
            if partner_id and seller.name not in [partner_id, partner_id.parent_id]:
                continue
            if quantity_uom_seller < seller.qty:
                continue
            if seller.product_id and seller.product_id != self.id:
                continue

            ProductSupplierinfo |= seller
            break
        return ProductSupplierinfo


    price = fields.Float(compute='_compute_product_price', inverse='_inverse_product_price', digits=dp.get_precision('Product Price'))
    price_extra = fields.Float(compute='_compute_price_extra', string='Variant Extra Price',
        help="This is the sum of the extra price of all attributes", digits=dp.get_precision('Product Price'))
    lst_price = fields.Float(compute='_compute_product_lst_price', inverse='_inverse_product_lst_price', string='Sale Price', digits=dp.get_precision('Product Price'))
    code = fields.Char(compute='_compute_product_code', string='Internal Reference')
    partner_ref = fields.Char(compute='_compute_product_partner_ref', string='Customer ref')
    default_code = fields.Char(string='Internal Reference', index=True)
    active = fields.Boolean(help="If unchecked, it will allow you to hide the product without removing it.", default=1)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', required=True, ondelete="cascade", index=True, auto_join=True)
    barcode = fields.Char(help="International Article Number used for product identification.", oldname='ean13', copy=False)
    name_template = fields.Char(related='product_tmpl_id.name', string="Template Name", store=True, index=True)
    attribute_value_ids = fields.Many2many('product.attribute.value', column1='prod_id', column2='att_id', string='Attributes', ondelete='restrict')
    is_product_variant = fields.Boolean(compute='_compute_is_product_variant_impl', string='Is a product variant')
    # image: all image fields are base64 encoded and PIL-supported
    image_variant = fields.Binary(string="Variant Image", attachment=True,
        help="This field holds the image used as image for the product variant, limited to 1024x1024px.")

    image = fields.Binary(compute='_compute_image_variant', inverse='_inverse_image_variant', string="Big-sized image",
        help="Image of the product variant (Big-sized image of product template if false). It is automatically "\
            "resized as a 1024x1024px image, with aspect ratio preserved.")
    image_small = fields.Binary(compute='_compute_image_variant', inverse='_inverse_image_small_variant', string="Small-sized image",
        help="Image of the product variant (Small-sized image of product tmplate if false).")
    image_medium = fields.Binary(compute='_compute_image_variant', inverse='_inverse_image_medium_variant', string="Medium-sized image",
        help="Image of the product variant (Medium-sized image of product template if false).")
    standard_price = fields.Float(digits=dp.get_precision('Product Price'), company_dependent=True,
        help="Cost of the product template used for standard stock valuation in accounting and used as a base price on purchase orders. "
            "Expressed in the default unit of measure of the product.", groups="base.group_user", string="Cost")
    volume = fields.Float(help="The volume in m3.")
    weight = fields.Float(digits=dp.get_precision('Stock Weight'), help="The weight of the contents in Kg, not including any packaging, etc.")

    @api.constrains('attribute_value_ids')
    def _check_attribute_value_ids(self):
        for product in self:
            attributes = set()
            for value in product.attribute_value_ids:
                if value.attribute_id in attributes:
                    raise ValidationError(_("Error! It is not allowed to choose more than one value for a given attribute."))
                else:
                    attributes.add(value.attribute_id)

    _sql_constraints = [
        ('barcode_uniq', 'unique(barcode)', _("A barcode can only be assigned to one product !")),
    ]

    @api.multi
    def unlink(self):
        Products = self.env['product.product']
        ProductTemplate = self.env['product.template']
        for product in self:
            # Check if product still exists, in case it has been unlinked by unlinking its template
            if not product.exists():
                continue
            # Check if the product is last product of this template
            other_product_ids = self.search([('product_tmpl_id', '=', product.product_tmpl_id.id), ('id', '!=', product.id)])
            if not other_product_ids:
                ProductTemplate += product.product_tmpl_id
            Products |= product
        res = super(ProductProduct, Products).unlink()
        # delete templates after calling super, as deleting template could lead to deleting
        # products due to ondelete='cascade'
        ProductTemplate.unlink()
        return res

    @api.onchange('uom_id')
    def onchange_uom(self):
        if self.uom_id.category_id != self.uom_po_id.category_id:
            self.uom_po_id = self.uom_id

    @api.multi
    def name_get(self):
        context = dict(self.env.context)
        def _name_get(d):
            name = d.get('name', '')
            code = context.get('display_default_code', True) and d.get('default_code', False) or False
            if code:
                name = '[%s] %s' % (code, name)
            return (d['id'], name)

        partner_id = context.get('partner_id', False)
        if partner_id:
            partner_ids = [partner_id, self.env['res.partner'].browse(partner_id).commercial_partner_id.id]
        else:
            partner_ids = []

        # all user don't have access to seller and partner
        # check access and use superuser
        self.check_access_rights("read")
        self.check_access_rule("read")

        result = []
        for product in self.sudo():
            variant = ", ".join([v.name for v in product.attribute_value_ids])
            name = variant and "%s (%s)" % (product.name, variant) or product.name
            sellers = []
            if partner_ids:
                if variant:
                    sellers = product.seller_ids.filtered(lambda x: x.name.id in partner_ids and x.product_id == product)
                if not sellers:
                    sellers = product.seller_ids.filtered(lambda x: x.name.id in partner_ids and not x.product_id)
            if sellers:
                for s in sellers:
                    seller_variant = s.product_name and (
                        variant and "%s (%s)" % (s.product_name, variant) or s.product_name
                        ) or False
                    mydict = {
                              'id': product.id,
                              'name': seller_variant or name,
                              'default_code': s.product_code or product.default_code,
                              }
                    temp = _name_get(mydict)
                    if temp not in result:
                        result.append(temp)
            else:
                mydict = {
                          'id': product.id,
                          'name': name,
                          'default_code': product.default_code,
                          }
                result.append(_name_get(mydict))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        context = dict(self.env.context)
        args = args or []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            if operator in positive_operators:
                products = self.search([('default_code', '=', name)] + args, limit=limit)
                if not products:
                    products = self.search([('barcode', '=', name)] + args, limit=limit)
            if not products and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching products, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                products = self.search(args + [('default_code', operator, name)], limit=limit)
                if not limit or len(products) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    limit2 = (limit - len(products)) if limit else False
                    products = self.search(args + [('name', operator, name), ('id', 'not in', products.ids)], limit=limit2)
            elif not products and operator in expression.NEGATIVE_TERM_OPERATORS:
                products = self.search(args + ['&', ('default_code', operator, name), ('name', operator, name)], limit=limit)
            if not products and operator in positive_operators:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    products = self.search([('default_code', '=', res.group(2))] + args, limit=limit)
            # still no results, partner in context: search on supplier info as last hope to find something
            if not products and context.get('partner_id'):
                suppliers = self.env['product.supplierinfo'].search(
                    [('name', '=', context.get('partner_id')), '|',
                        ('product_code', operator, name),
                        ('product_name', operator, name)])
                if suppliers:
                    products = self.search([('product_tmpl_id.seller_ids', 'in', suppliers)], limit=limit)
        else:
            products = self.search(args, limit=limit)
        return products.name_get()

    #
    # Could be overrided for variants matrices prices
    #
    @api.v7
    def price_get(self, cr, uid, ids, ptype='list_price', context=None):
        products = self.browse(cr, uid, ids, context=context)
        return products.price_get(ptype='list_price')

    @api.v8
    def price_get(self, ptype='list_price'):
        return self.env["product.template"]._price_get(self, ptype=ptype)

    @api.multi
    def copy(self, default=None):
        if default is None:
            default = {}

        if self.env.context.get('variant'):
            # if we copy a variant or create one, we keep the same template
            default['product_tmpl_id'] = self.product_tmpl_id.id
        elif 'name' not in default:
            default['name'] = _("%s (copy)") % (self.name,)

        return super(ProductProduct, self).copy(default=default)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self.env.context.get('search_default_categ_id'):
            args.append((('categ_id', 'child_of', self.env.context['search_default_categ_id'])))
        return super(ProductProduct, self).search(args, offset=offset, limit=limit, order=order, count=count)

    @api.model
    def create(self, vals):
        product_product = super(ProductProduct, self.with_context(create_product_product=True)).create(vals)
        product_product._set_standard_price(vals.get('standard_price', 0.0))
        return product_product

    @api.multi
    def write(self, vals):
        ''' Store the standard price change in order to be able to retrieve the cost of a product for a given date'''
        res = super(ProductProduct, self).write(vals)
        if 'standard_price' in vals:
            for product in self:
                product._set_standard_price(vals['standard_price'])
        return res

    def _set_standard_price(self, value):
        ''' Store the standard price change in order to be able to retrieve the cost of a product for a given date'''
        self.ensure_one()
        self.env['product.price.history'].create({
            'product_id': self.id,
            'cost': value,
            'company_id': self.env.context.get('force_company') or self.env.user.company_id.id
            })

    @api.v7
    def get_history_price(self, cr, uid, product_id, company_id, date=None, context=None):
        product_product = self.browse(cr, uid, product_id, context)
        return product_product.get_history_price(company_id, date=date)

    @api.v8
    def get_history_price(self, company_id, date=None):
        self.ensure_one()
        if date is None:
            date = fields.Date.today()
        product_price_history = self.env['product.price.history'].search([('company_id', '=', company_id), ('product_id', '=', self.id), ('datetime', '<=', date)], limit=1)
        if product_price_history:
            return product_price_history.cost
        return 0.0

    @api.multi
    def _need_procurement(self):
        # When sale/product is installed alone, there is no need to create procurements. Only
        # sale_stock and sale_service need procurements
        return False


class ProductPackaging(models.Model):
    _name = "product.packaging"
    _description = "Packaging"
    _order = 'sequence'

    name = fields.Char(string='Packaging Type', required=True)
    sequence = fields.Integer(help="The first in the sequence is the default one.", default=1)
    product_tmpl_id = fields.Many2one('product.template', string='Product')
    qty = fields.Float(string='Quantity by Package', help="The total number of products you can put by pallet or box.")


class ProductSupplierinfo(models.Model):
    _name = "product.supplierinfo"
    _description = "Information about a product vendor"
    _order = 'sequence, min_qty desc, price'

    @api.depends('min_qty')
    def _compute_calc_qty(self):
        for supplier_info in self:
            supplier_info.qty = supplier_info.min_qty

    name = fields.Many2one('res.partner', string='Vendor', required=True, domain=[('supplier', '=', True)], ondelete='cascade', help="Vendor of this product")
    product_name = fields.Char(string='Vendor Product Name', help="This vendor's product name will be used when printing a request for quotation. Keep empty to use the internal one.")
    product_code = fields.Char(string='Vendor Product Code', help="This vendor's product code will be used when printing a request for quotation. Keep empty to use the internal one.")
    sequence = fields.Integer(help="Assigns the priority to the list of product vendor.", default=1)
    product_uom = fields.Many2one('product.uom', related='product_tmpl_id.uom_po_id', string="Vendor Unit of Measure", readonly=True, help="This comes from the product form.")
    min_qty = fields.Float(string='Minimal Quantity', required=True, help="The minimal quantity to purchase from this vendor, expressed in the vendor Product Unit of Measure if not any, in the default unit of measure of the product otherwise.", default=0.0)
    qty = fields.Float(compute='_compute_calc_qty', store=True, string='Quantity', help="This is a quantity which is converted into Default Unit of Measure.")
    price = fields.Float(required=True, digits=dp.get_precision('Product Price'), help="The price to purchase a product", default=0.0)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id.id)
    date_start = fields.Date(string='Start Date', help="Start date for this vendor price")
    date_end = fields.Date(string='End Date', help="End date for this vendor price")
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', ondelete='cascade', index=True, oldname='product_id')
    delay = fields.Integer(string='Delivery Lead Time', required=True,
        help="Lead time in days between the confirmation of the purchase order and the receipt of the products in your warehouse. Used by the scheduler for automatic computation of the purchase order planning.", default=1)
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id.id)
    product_id = fields.Many2one('product.product', string='Product Variant', help="When this field is filled in, the vendor data will only apply to the variant.")


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.constrains('rounding')
    def _check_main_currency_rounding(self):
        decimal_precision = self.env['decimal.precision'].search([('name', 'like', 'Account')], limit=1)
        main_currency = self.env.user.company_id.currency_id
        for currency in self:
            if decimal_precision and currency == main_currency and \
                    float_compare(main_currency.rounding, 10 ** -decimal_precision.digits, precision_digits=6) == -1:
                raise ValidationError(_("Error! You cannot define a rounding factor for the company\'s main currency that is smaller than the decimal precision of \'Account\'."))


class DecimalPrecision(models.Model):
    _inherit = 'decimal.precision'

    @api.constrains('digits')
    def _check_main_currency_rounding(self):
        decimal_precision = self.search([('name', 'like', 'Account')], limit=1)
        main_currency = self.env.user.company_id.currency_id
        for decimal in self:
            if decimal_precision and decimal == decimal_precision and \
                    float_compare(main_currency.rounding, 10 ** -decimal_precision.digits, precision_digits=6) == -1:
                raise ValidationError(_("Error! You cannot define the decimal precision of \'Account\' as greater than the rounding factor of the company\'s main currency"))
