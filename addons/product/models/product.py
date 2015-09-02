# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from openerp import api, fields, models, tools, _
from openerp.osv import expression
import psycopg2

import openerp.addons.decimal_precision as dp
from openerp.exceptions import ValidationError
from openerp.exceptions import except_orm

#----------------------------------------------------------
# Categories
#----------------------------------------------------------
class ProductCategory(models.Model):
    _name = "product.category"
    _description = "Product Category"

    name = fields.Char(required=True, translate=True, index=True)
    complete_name = fields.Char(compute='_compute_name_get_fnc', string='Name')
    parent_id = fields.Many2one('product.category', string='Parent Category', index=True, ondelete='cascade')
    child_id = fields.One2many('product.category', 'parent_id', string='Child Categories')
    sequence = fields.Integer('Sequence', index=True, help="Gives the sequence order when displaying a list of product categories.")
    category_type = fields.Selection([('view', 'View'), ('normal', 'Normal')], string='Category Type', default='normal', oldname='type',
        help="A category of the view type is a virtual category that can be used as the parent of another category to create a hierarchical structure.")
    parent_left = fields.Integer(string='Left Parent', index=1)
    parent_right = fields.Integer(string='Right Parent', index=1)

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
                    category_ids = self.search([('id', 'not in', category_ids)])
                    domain = expression.OR([[('parent_id', 'in', category_ids)], domain])
                else:
                    domain = expression.AND([[('parent_id', 'in', category_ids)], domain])
                for i in range(1, len(categories)):
                    domain = [[('name', operator, ' / '.join(categories[-1 - i:]))], domain]
                    if operator in expression.NEGATIVE_TERM_OPERATORS:
                        domain = expression.AND(domain)
                    else:
                        domain = expression.OR(domain)
            product_category_ids = self.search(expression.AND([domain, args]), limit=limit)
        else:
            product_category_ids = self.search(args, limit=limit)
        return product_category_ids.name_get()

    @api.multi
    def _compute_name_get_fnc(self):
        name_get = dict(self.name_get())
        for pc in self:
            pc.complete_name = name_get[pc.id]

    _name = "product.category"
    _description = "Product Category"

    name = fields.Char(required=True, translate=True, select=True)
    complete_name = fields.Char(compute='_name_get_fnc', string='Name')
    parent_id = fields.Many2one('product.category', string='Parent Category', select=True, ondelete='cascade')
    child_id = fields.One2many('product.category', 'parent_id', string='Child Categories')
    sequence = fields.Integer('Sequence', select=True, help="Gives the sequence order when displaying a list of product categories.")
    type = fields.Selection([('view','View'), ('normal','Normal')], string='Category Type',
        help="A category of the view type is a virtual category that can be used as the parent of another category to create a hierarchical structure.", default='normal')
    parent_left = fields.Integer(string='Left Parent', select=1)
    parent_right = fields.Integer(string='Right Parent', select=1)

    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'sequence, name'
    _order = 'parent_left'

    @api.constrains('parent_id')
    def _check_recursion(self):
        if self.id == self.parent_id.id:
            raise ValidationError(_("Error ! You cannot create recursive categories."))


class ProducePriceHistory(models.Model):
    """
    Keep track of the ``product.template`` standard prices as they are changed.
    """

    _name = 'product.price.history'
    _rec_name = 'datetime'
    _order = 'datetime desc'

    def _get_default_company(self):
        if 'force_company' in self._context:
            return self._context['force_company']
        else:
            company = self.env.user.company_id
        return company.id if company else False

    company_id = fields.Many2one('res.company', required=True, default=_get_default_company)
    product_template_id = fields.Many2one('product.template', string='Product Template', required=True, ondelete='cascade')
    datetime = fields.Datetime(string='Date', default=fields.datetime.now())
    cost = fields.Float(string='Cost')

#----------------------------------------------------------
# Products
#----------------------------------------------------------
class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ['mail.thread']
    _description = "Product Template"
    _order = "name"

    def _get_uom_id(self):
        return self.env["product.uom"].search([], limit=1, order='id').id

    def _default_category(self):
        context = self._context or {}
        if 'categ_id' in context and context['categ_id']:
            return context['categ_id']
        res = False
        try:
            res = self.env['ir.model.data'].get_object_reference('product', 'product_category_all')[1]
        except ValueError:
            res = False
        return res

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
    type = fields.Selection('_get_product_template_type', string='Product Type', required=True, help="Consumable are product where you don't manage stock, a service is a non-material product provided by a company or an individual.", default='consu')
    rental = fields.Boolean(string='Can be Rent')
    categ_id = fields.Many2one('product.category', string='Internal Category', required=True, change_default=True, domain="[('type', '=', 'normal')]",
        help="Select category for the current product", default=_default_get_category)

    price = fields.Float(compute='_product_template_price', inverse='_set_product_template_price', string='Price', digits_compute=dp.get_precision('Product Price'))
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency')
    list_price = fields.Float(string='Sale Price', digits_compute=dp.get_precision('Product Price'),
        help="Base price to compute the customer price. Sometimes called the catalog price.", default=1)
    lst_price = fields.Float(related='list_price', string='Public Price', digits_compute=dp.get_precision('Product Price'))
    standard_price = fields.Float(compute='_compute_product_template_field', inverse='_set_standard_price_product_template_field', string='Cost',
        digits_compute=dp.get_precision('Product Price'), groups="base.group_user", store=True, default=0.0,
        help="Cost of the product, in the default unit of measure of the product.")
    volume = fields.Float(compute='_compute_product_template_field', inverse='_set_volume_product_template_field', string='Volume',
        help="The volume in m3.", store=True)
    weight = fields.Float(compute='_compute_product_template_field', inverse='_set_weight_product_template_field', string='Gross Weight', digits_compute=dp.get_precision('Stock Weight'),
        help="The weight of the contents in Kg, not including any packaging, etc.", store=True)

    warranty = fields.Float(string='Warranty')
    sale_ok = fields.Boolean(string='Can be Sold', help="Specify if the product can be selected in a sales order line.", default=1)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    state = fields.Selection([('draft', 'In Development'), ('sellable', 'Normal'), ('end', 'End of Lifecycle'), ('obsolete', 'Obsolete')],
        string='Status')
    uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True,
        help="Default Unit of Measure used for all stock operation.", default=_default_get_uom_id)
    uom_po_id = fields.Many2one('product.uom', string='Purchase Unit of Measure', required=True, default=_default_get_uom_id,
        help="Default Unit of Measure used for purchase orders. It must be in the same category than the default unit of measure.")
    company_id = fields.Many2one('res.company', string='Company', index=1, default=lambda self: self.env['res.company']._company_default_get('product.template'))

    # image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary("Image",
        help="This field holds the image used as image for the product, limited to 1024x1024px.")
    image_medium = fields.Binary(compute='_compute_image', inverse='_inverse_image_medium', string="Medium-sized image", store=True,
        help="Medium-sized image of the product. It is automatically "\
             "resized as a 128x128px image, with aspect ratio preserved, "\
             "only when the image exceeds one of those sizes. Use this field in form views or some kanban views.")
    image_small = fields.Binary(compute='_compute_image', inverse='_inverse_image_small', string="Small-sized image", store=True,
        help="Small-sized image of the product. It is automatically "\
             "resized as a 64x64px image, with aspect ratio preserved. "\
             "Use this field anywhere a small image is required.")

    packaging_ids = fields.One2many('product.packaging', 'product_tmpl_id', string='Logistical Units',
        help="Gives the different ways to package the same product. This has no impact on "
            "the picking order and is mainly used if you use the EDI module.")
    seller_ids = fields.One2many('product.supplierinfo', 'product_tmpl_id', string='Vendor')
    selected_seller_id = fields.Many2one('product.supplierinfo', compute='_select_seller', string='Selected Seller',
        help='Technical field that selects a seller based on priority (sequence) and an optional partner and/or a minimal quantity in the context')
    seller_delay = fields.Integer(related='selected_seller_id.delay', string='Vendor Lead Time',
        help="This is the average delay in days between the purchase order confirmation and the receipts for this product and for the default vendor. It is used by the scheduler to order requests based on reordering delays.")
    seller_qty = fields.Float(related='selected_seller_id.qty', string='Vendor Quantity',
        help="This is minimum quantity to purchase from Main Vendor.")
    seller_id = fields.Many2one('res.partner', related='selected_seller_id.name', string='Main Vendor',
        help="Main vendor who has highest priority in vendor list.")
    seller_price = fields.Float(related='selected_seller_id.price', string='Vendor Price', help="Purchase price from from Main Vendor.")

    active = fields.Boolean(help="If unchecked, it will allow you to hide the product without removing it.", default=True)
    color = fields.Integer(string='Color Index', default=0)
    is_product_variant = fields.Boolean(compute='_is_product_variant', string='Is a product variant')

    attribute_line_ids = fields.One2many('product.attribute.line', 'product_tmpl_id', string='Product Attributes')
    product_variant_ids = fields.One2many('product.product', 'product_tmpl_id', string='Products', required=True)
    product_variant_count = fields.Integer(compute='_compute_product_variant_count', string='# of Product Variants')

    # related to display product product information if is_product_variant
    barcode = fields.Char(related='product_variant_ids.barcode', string='Barcode', oldname='ean13')
    default_code = fields.Char(related='product_variant_ids.default_code', string='Internal Reference')
    item_ids = fields.One2many('product.pricelist.item', 'product_tmpl_id', string='Pricelist Items')

    @api.depends('image')
    def _compute_image(self):
        for product in self:
            image = tools.image_get_resized_images(product.image)
            product.image_medium = image['image_medium']
            product.image_small = image['image_small']

    def _inverse_image_medium(self):
        self.image = tools.image_resize_image_big(self.image_medium)

    def _inverse_image_small(self):
        self.image = tools.image_resize_image_big(self.image_small)

    @api.multi
    def _is_product_variant(self):
        return self._is_product_variant_impl()

    @api.multi
    def _is_product_variant_impl(self):
        return dict.fromkeys(self.ids, False)

    def _product_template_price(self):
        context = self._context or {}
        plobj = self.env['product.pricelist']
        quantity = context.get('quantity') or 1.0
        pricelist = context.get('pricelist', False)
        partner = context.get('partner', False)
        if pricelist:
            # Support context pricelists specified as display_name or ID for compatibility
            if isinstance(pricelist, basestring):
                pricelist_ids = plobj.name_search(pricelist, operator='=', limit=1)
                pricelist = pricelist_ids[0][0] if pricelist_ids else pricelist
            if isinstance(pricelist, (int, long)):
                qtys = map(lambda x: (x, quantity, partner), self)
                price = plobj.browse(pricelist)._price_get_multi(qtys)
                for product in self:
                    product.price = price.get(product.id, 0.0)

    def _set_product_template_price(self):
        product_uom_obj = self.env['product.uom']
        if 'uom' in self._context:
            value = product_uom_obj.browse(self._context['uom'])._compute_price(self.price, self.uom_id.id)
        self.list_price = value or 0.0

    @api.v7
    def get_history_price(self, cr, uid, product_tmpl_id, company_id, date=None, context=None):
        product_template = self.browse(cr, uid, product_tmpl_id, context)
        return product_template.get_history_price(company_id, date=date)

    @api.v8
    def get_history_price(self, company_id, date=None):
        if date is None:
            date = fields.Date.today()
        history_id = self.env['product.price.history'].search([('company_id', '=', company_id), ('product_template_id', '=', self.id), ('datetime', '<=', date)], limit=1)
        if history_id:
            return history_id.read(['cost'])['cost']
        return 0.0

    def _set_standard_price(self, value):
        ''' Store the standard price change in order to be able to retrieve the cost of a product template for a given date'''
        price_history_obj = self.env['product.price.history']
        user_company = self.env.user.company_id.id
        company_id = self._context.get('force_company', user_company)
        price_history_obj.create({
            'product_template_id': self.id,
            'cost': value,
            'company_id': company_id,
        })

    @api.multi
    def _compute_product_variant_count(self):
        for product in self:
            product.product_variant_count = len(product.product_variant_ids)

    @api.depends('product_variant_ids.standard_price')
    def _compute_product_template_field(self):
        ''' Compute the field from the product_variant if there is only one variant, otherwise returns 0.0 '''
        for product in self:
            if product.product_variant_count == 1:
                product.standard_price = product.product_variant_ids.standard_price
                product.volume = product.product_variant_ids.volume
                product.weight = product.product_variant_ids.weight

    def _set_standard_price_product_template_field(self):
        ''' Set the standard price modification on the variant if there is only one variant '''
        if self.product_variant_count == 1:
            self.product_variant_ids.write({'standard_price': self.standard_price})

    def _set_volume_product_template_field(self):
        ''' Set the volume modification on the variant if there is only one variant '''
        if self.product_variant_count == 1:
            self.product_variant_ids.write({'volume': self.volume})

    def _set_weight_product_template_field(self):
        ''' Set the weight modification on the variant if there is only one variant '''
        if self.product_variant_count == 1:
            self.product_variant_ids.write({'weigh': self.weigh})

    @api.multi
    def _select_seller(self):
        context = self._context or {}
        partner = context.get('partner_id')
        minimal_quantity = context.get('quantity', 0.0)
        date = context.get('date', fields.Date.today())
        for product in self:
            product.selected_seller_id = False
            for seller in product.seller_ids:
                if seller.date_start and seller.date_start > date:
                    continue
                if seller.date_end and seller.date_end < date:
                    continue
                if partner and seller.name.id != partner:
                    continue
                if minimal_quantity and minimal_quantity < seller.qty:
                    continue
                product.selected_seller_id = seller
                break

    @api.v7
    def _price_get(self, cr, uid, products, ptype='list_price', context=None):
        return self._price_get(products, ptype='list_price')

    @api.v8
    def _price_get(self, products, ptype='list_price'):
        context = self._context or {}

        if 'currency_id' in context:
            currency_id = self.env.user.company_id.currency_id.id
        res = {}
        for product in products:
            # standard_price field can only be seen by users in base.group_user
            # Thus, in order to compute the sale price from the cost for users not in this group
            # We fetch the standard price as the superuser
            if ptype != 'standard_price':
                res[product.id] = product[ptype] or 0.0
            else:
                company_id = product.env.user.company_id.id
                product = product.with_context(force_company=company_id)
                res[product.id] = res[product.id] = product.sudo()[ptype]
            if ptype == 'list_price':
                res[product.id] += product._name == "product.product" and float(product.price_extra) or 0.0
            if 'uom' in context:
                res[product.id] = product.uom_id._compute_price(res[product.id], context['uom'])
            # Convert from current user company currency to asked one
            if 'currency_id' in context:
                # Take current user company currency.
                # This is right cause a field cannot be in more than one currency
                to_cureency = self.env['res.currency'].browse(context['currency_id'])
                res[product.id] = currency_id.compute(res[product.id], to_cureency)
        return res

    @api.onchange('type')
    def onchange_type(self):
        return {}

    @api.onchange('uom_id', 'uom_po_id')
    def onchange_uom(self):
        if self.uom_id:
            self.uom_po_id = self.uom_id

    @api.multi
    def create_variant_ids(self):
        product_obj = self.env["product.product"]
        ctx = self._context and self._context.copy() or {}
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
                product_obj.browse(product_ids).with_context(ctx).write({'attribute_value_ids': [(4, variant_id.id)]})

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
                product_obj.browse(variant_ids_to_active).with_context(ctx).write({'active': True})

            # create new product
            for variant_ids in all_variants:
                values = {
                    'product_tmpl_id': tmpl_id.id,
                    'attribute_value_ids': [(6, 0, variant_ids)]
                }
                product = product_obj.with_context(ctx).create(values)
                variants_active_ids.append(product.id)

            # unlink or inactive product
            for variant_id in variants_inactive:
                try:
                    with self.env.cr.savepoint(), tools.mute_logger('openerp.sql_db'):
                        variant_id.with_context(ctx).unlink()
                #We catch all kind of exception to be sure that the operation doesn't fail.
                except (psycopg2.Error, except_orm):
                    variant_id.with_context(ctx).write({'active': False})
                    pass
        return True

    @api.model
    def create(self, vals):
        ''' Store the initial standard price in order to be able to retrieve the cost of a product template for a given date'''
        product_template_id = super(ProductTemplate, self).create(vals)
        if not self._context or "create_product_product" not in self._context:
            product_template_id.create_variant_ids()
        product_template_id._set_standard_price(vals.get('standard_price', 0.0))

        # TODO: this is needed to set given values to first variant after creation
        # these fields should be moved to product as lead to confusion
        related_vals = {}
        if vals.get('barcode'):
            related_vals['barcode'] = vals['barcode']
        if vals.get('default_code'):
            related_vals['default_code'] = vals['default_code']
        if vals.get('standard_price'):
            related_vals['standard_price'] = vals['standard_price']
        if vals.get('volume'):
            related_vals['volume'] = vals['volume']
        if vals.get('weight'):
            related_vals['weight'] = vals['weight']
        if related_vals:
            product_template_id.write(related_vals)

        return product_template_id

    @api.multi
    def write(self, vals):
        ''' Store the standard price change in order to be able to retrieve the cost of a product template for a given date'''
        if 'standard_price' in vals:
            for prod_template_id in self:
                prod_template_id._set_standard_price(vals['standard_price'])
        res = super(ProductTemplate, self).write(vals)
        if 'attribute_line_ids' in vals or vals.get('active'):
            self.create_variant_ids()
        if 'active' in vals and not vals.get('active'):
            ctx = self._context and self._context.copy() or {}
            ctx.update(active_test=False)
            product_ids = []
            for product in self.with_context(ctx):
                product_ids = map(int, product.product_variant_ids)
            self.env["product.product"].browse(product_ids).with_context(ctx).write({'active': vals.get('active')})
        return res

    def copy(self, default=None):
        default = default or {}
        template = self
        default['name'] = _("%s (copy)") % (template['name'])
        return super(ProductTemplate, self).copy(default=default)

    @api.constrains('uom_id', 'uom_po_id')
    def _check_uom(self):
        if self.uom_id.category_id.id != self.uom_po_id.category_id.id:
            return ValidationError(_('Error: The default Unit of Measure and the purchase Unit of Measure must be in the same category.'))
        return True

    @api.multi
    def name_get(self):
        if 'partner_id' in self._context:
            pass
        return super(ProductTemplate, self).name_get()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        # Only use the product.product heuristics if there is a search term and the domain
        # does not specify a match on `product.template` IDs.
        if not name or any(term[0] == 'id' for term in (args or [])):
            return super(ProductTemplate, self).name_search(
                name=name, args=args, operator=operator, limit=limit)
        template_ids = set()
        product_product = self.env['product.product']
        results = product_product.name_search(name, args, operator=operator, limit=limit)
        product_ids = [p[0] for p in results]
        for p in product_product.browse(product_ids):
            template_ids.add(p.product_tmpl_id.id)
        while (results and len(template_ids) < limit):
            domain = [('product_tmpl_id', 'not in', list(template_ids))]
            results = product_product.name_search(
                name, args+domain, operator=operator, limit=limit)
            product_ids = [p[0] for p in results]
            for p in product_product.browse(product_ids):
                template_ids.add(p.product_tmpl_id.id)

        # re-apply product.template order + name_get
        return super(ProductTemplate, self).name_search('', args=[('id', 'in', list(template_ids))], operator='ilike', limit=limit)


class ProductProduct(models.Model):
    _name = "product.product"
    _description = "Product"
    _inherits = {'product.template': 'product_tmpl_id'}
    _inherit = ['mail.thread']
    _order = 'default_code, name_template'

    price = fields.Float(compute='_product_price', inverse='_set_product_price', string='Price', digits_compute=dp.get_precision('Product Price'), default=0.0)
    price_extra = fields.Char(compute='_get_price_extra', string='Variant Extra Price',
        help="This is the sum of the extra price of all attributes", digits_compute=dp.get_precision('Product Price'))
    lst_price = fields.Float(compute='_product_lst_price', inverse='_set_product_lst_price', string='Sale Price', digits_compute=dp.get_precision('Product Price'))
    code = fields.Char(compute='_product_code', string='Internal Reference')
    partner_ref = fields.Char(compute='_product_partner_ref', string='Customer ref')
    default_code = fields.Char(string='Internal Reference', index=True)
    active = fields.Boolean(help="If unchecked, it will allow you to hide the product without removing it.", default=1)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', required=True, ondelete="cascade", index=True, auto_join=True)
    barcode = fields.Char('Barcode', help="International Article Number used for product identification.", oldname='ean13', copy=False)
    name_template = fields.Char(related='product_tmpl_id.name', string="Template Name", store=True, index=True)
    attribute_value_ids = fields.Many2many('product.attribute.value', column1='prod_id', column2='att_id', string='Attributes', ondelete='restrict')
    is_product_variant = fields.Boolean(compute='_is_product_variant_impl', string='Is a product variant')

    # image: all image fields are base64 encoded and PIL-supported
    image_variant = fields.Binary(string="Variant Image",
        help="This field holds the image used as image for the product variant, limited to 1024x1024px.")
    image = fields.Binary(compute='_get_image_variant', inverse='_set_image_variant', string="Big-sized image",
        help="Image of the product variant (Big-sized image of product template if false). It is automatically "\
            "resized as a 1024x1024px image, with aspect ratio preserved.")
    image_small = fields.Binary(compute='_get_image_variant', inverse='_set_image_small_variant', string="Small-sized image",
        help="Image of the product variant (Small-sized image of product tmplate if false).")
    image_medium = fields.Binary(compute='_get_image_variant', inverse='_set_image_medium_variant', string="Medium-sized image",
        help="Image of the product variant (Medium-sized image of product template if false).")

    standard_price = fields.Float(digits_compute=dp.get_precision('Product Price'), company_dependent=True,
        help="Cost of the product template used for standard stock valuation in accounting and used as a base price on purchase orders. "
            "Expressed in the default unit of measure of the product.", groups="base.group_user", string="Cost")
    volume = fields.Float(help="The volume in m3.")
    weight = fields.Float(string='Gross Weight', digits_compute=dp.get_precision('Stock Weight'), help="The weight of the contents in Kg, not including any packaging, etc.")

    _sql_constraints = [
        ('barcode_uniq', 'unique(barcode)', _("A barcode can only be assigned to one product !")),
    ]

    def _product_price(self):
        plobj = self.env['product.pricelist']
        context = self._context or {}
        quantity = context.get('quantity') or 1.0
        pricelist = context.get('pricelist', False)
        partner = context.get('partner', False)
        if pricelist:
            # Support context pricelists specified as display_name or ID for compatibility
            if isinstance(pricelist, basestring):
                pricelist_ids = plobj.name_search(pricelist, operator='=', limit=1)
                pricelist = pricelist_ids[0][0] if pricelist_ids else pricelist

            if isinstance(pricelist, (int, long)):
                products = self
                qtys = map(lambda x: (x, quantity, partner), products)
                price = plobj.browse(pricelist)._price_get_multi(qtys)
                for product in products:
                    product.price = price.get(product.id, 0.0)

    def _set_product_price(self):
        if 'uom' in self._context:
            uom = self.uom_id
            self.price = self.env['product.uom'].browse(self._context['uom'])._compute_price(self.price, uom.id)
        self.write({'list_price': self.price})

    @api.multi
    def open_product_template(self):
        """ Utility method used to add an "Open Template" button in product views """
        self.ensure_one()
        return {'type': 'ir.actions.act_window',
                'res_model': 'product.template',
                'view_mode': 'form',
                'res_id': self.product_tmpl_id.id,
                'target': 'current',
                'flags': {'form': {'action_buttons': True}}}

    @api.model
    def view_header_get(self, view_id, view_type):
        res = super(ProductProduct, self).view_header_get(view_id, view_type)
        if (self._context.get('categ_id', False)):
            return _('Products: ') + self.env['product.category'].browse(self._context['categ_id']).name
        return res

    def _product_lst_price(self):
        context = self._context or {}
        for product in self:
            if 'uom' in context:
                uom = product.uom_id
                amount = uom._compute_price(product.list_price, context['uom'])
            else:
                amount = product.list_price
            product.lst_price = amount + float(product.price_extra)

    def _set_product_lst_price(self):
        if 'uom' in self._context:
            uom = self.uom_id
            self.lst_price = self.env['product.uom'].browse(self._context['uom'])._compute_price(self.lst_price, uom.id)
        list_price = self.lst_price - float(self.price_extra)
        self.write({'list_price': list_price})

    def _get_partner_code_name(self, product, partner_id):
        for supinfo in product.seller_ids:
            if supinfo.name.id == partner_id:
                return {'code': supinfo.product_code or product.default_code, 'name': supinfo.product_name or product.name}
        return {'code': product.default_code, 'name': product.name}

    @api.multi
    def _product_code(self):
        context = self._context or {}
        for product in self:
            product.code = self._get_partner_code_name(product, context.get('partner_id', None))['code']

    @api.multi
    def _product_partner_ref(self):
        context = self._context or {}
        for product in self:
            data = self._get_partner_code_name(product, context.get('partner_id', None))
            if not data['code']:
                data['code'] = product.code
            if not data['name']:
                data['name'] = product.name
            product.partner_ref = (data['code'] and ('['+data['code']+'] ') or '') + (data['name'] or '')

    @api.multi
    def _is_product_variant_impl(self):
        return dict.fromkeys(self.ids, True)

    @api.depends('image_variant')
    def _get_image_variant(self):
        for product in self:
            image = tools.image_resize_image_big(product.image_variant)
            product.image = image or product.product_tmpl_id.image
            product.image_small = image or product.product_tmpl_id.image_small
            product.image_medium = image or product.product_tmpl_id.image_medium

    def _set_image_variant(self):
        image = tools.image_resize_image_big(self.image)
        if self.product_tmpl_id.image:
            self.image_variant = image
        else:
            self.product_tmpl_id.image = image

    def _set_image_small_variant(self):
        image = tools.image_resize_image_big(self.image_small)
        if self.product_tmpl_id.image:
            self.image_variant = image
        else:
            self.product_tmpl_id.image = image

    def _set_image_medium_variant(self):
        image = tools.image_resize_image_big(self.image_medium)
        if self.product_tmpl_id.image:
            self.image_variant = image
        else:
            self.product_tmpl_id.image = image

    @api.multi
    def _get_price_extra(self):
        for product in self:
            price_extra = 0.0
            for variant_id in product.attribute_value_ids:
                for price_id in variant_id.price_ids:
                    if price_id.product_tmpl_id.id == product.product_tmpl_id.id:
                        price_extra += price_id.price_extra
            product.price_extra = price_extra

    @api.multi
    def unlink(self):
        unlink_ids = []
        unlink_product_tmpl_ids = []
        for product in self:
            # Check if product still exists, in case it has been unlinked by unlinking its template
            if not product.exists():
                continue
            tmpl_id = product.product_tmpl_id.id
            # Check if the product is last product of this template
            other_product_ids = self.search([('product_tmpl_id', '=', tmpl_id), ('id', '!=', product.id)])
            if not other_product_ids:
                unlink_product_tmpl_ids.append(tmpl_id)
            unlink_ids.append(product.id)
        unlink = self.browse(unlink_ids)
        res = super(ProductProduct, unlink).unlink()
        # delete templates after calling super, as deleting template could lead to deleting
        # products due to ondelete='cascade'
        unlink_product_tmpl = self.env['product.template'].browse(unlink_product_tmpl_ids)
        unlink_product_tmpl.unlink()
        return res

    @api.onchange('type')
    def onchange_type(self):
        return {}

    @api.onchange('uom_id')
    def onchange_uom(self):
        if self.uom_id and self.uom_po_id:
            if self.uom_id.category_id.id != self.uom_po_id.category_id.id:
                self.uom_po_id = self.uom_id

    @api.multi
    def on_order(self, orderline, quantity):
        pass

    @api.multi
    def name_get(self):
        context = self._context or {}
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
                sellers = filter(lambda x: x.name.id in partner_ids, product.seller_ids)
            if sellers:
                for s in sellers:
                    seller_variant = s.product_name and (
                        variant and "%s (%s)" % (s.product_name, variant) or s.product_name
                        ) or False
                    mydict = {'id': product.id,
                              'name': seller_variant or name,
                              'default_code': s.product_code or product.default_code}
                    result.append(_name_get(mydict))
            else:
                mydict = {'id': product.id,
                          'name': name,
                          'default_code': product.default_code}
                result.append(_name_get(mydict))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        context = self._context or {}
        args = args or []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            ids = []
            if operator in positive_operators:
                ids = self.search([('default_code', '=', name)] + args, limit=limit).ids
                if not ids:
                    ids = self.search([('barcode', '=', name)] + args, limit=limit).ids
            if not ids and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching products, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                ids = self.search(args + [('default_code', operator, name)], limit=limit).ids
                if not limit or len(ids) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    limit2 = (limit - len(ids)) if limit else False
                    ids += self.search(args + [('name', operator, name), ('id', 'not in', ids)], limit=limit2).ids
            elif not ids and operator in expression.NEGATIVE_TERM_OPERATORS:
                ids = self.search(args + ['&', ('default_code', operator, name), ('name', operator, name)], limit=limit).ids
            if not ids and operator in positive_operators:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    ids = self.search([('default_code', '=', res.group(2))] + args, limit=limit).ids
            # still no results, partner in context: search on supplier info as last hope to find something
            if not ids and context.get('partner_id'):
                supplier_ids = self.env['product.supplierinfo'].search(
                    [('name', '=', context.get('partner_id')), '|',
                        ('product_code', operator, name),
                        ('product_name', operator, name)])
                if supplier_ids:
                    ids = self.search([('product_tmpl_id.seller_ids', 'in', supplier_ids)], limit=limit).ids
        else:
            ids = self.search(args, limit=limit).ids
        return self.browse(ids).name_get()

    #
    # Could be overrided for variants matrices prices
    #
    @api.v7
    def price_get(self, cr, uid, ids, ptype='list_price', context=None):
        products = self.browse(cr, uid, ids, context=context)
        return products.price_get(ptype='list_price')

    @api.v8
    def price_get(self, ptype='list_price'):
        products = self
        return self.env["product.template"]._price_get(products, ptype=ptype)

    def copy(self, default=None):
        context = self._context or {}
        default = default or {}

        if context.get('variant'):
            # if we copy a variant or create one, we keep the same template
            default['product_tmpl_id'] = self.product_tmpl_id.id
        elif 'name' not in default:
            default['name'] = _("%s (copy)") % (self.name,)

        return super(ProductProduct, self).copy(default=default)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self._context or {}
        if context.get('search_default_categ_id'):
            args.append((('categ_id', 'child_of', context['search_default_categ_id'])))
        return super(ProductProduct, self).search(args, offset=offset, limit=limit, order=order, count=count)

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
    def create(self, vals):
        ctx = dict(self._context or {}, create_product_product=True)
        return super(ProductProduct, self.with_context(ctx)).create(vals)


class ProductPackaging(models.Model):
    _name = "product.packaging"
    _description = "Packaging"
    _order = 'sequence'

    name = fields.Char(string='Packaging Type', required=True)
    sequence = fields.Integer(string='Sequence', help="The first in the sequence is the default one.", default=1)
    product_tmpl_id = fields.Many2one('product.template', string='Product')
    qty = fields.Float(string='Quantity by Package', help="The total number of products you can put by pallet or box.")


class ProductSupplierinfo(models.Model):
    _name = "product.supplierinfo"
    _description = "Information about a product vendor"
    _order = 'sequence, min_qty desc, price'

    name = fields.Many2one('res.partner', string='Vendor', required=True, domain=[('supplier', '=', True)], ondelete='cascade', help="Vendor of this product")
    product_name = fields.Char(string='Vendor Product Name', help="This vendor's product name will be used when printing a request for quotation. Keep empty to use the internal one.")
    product_code = fields.Char(string='Vendor Product Code', help="This vendor's product code will be used when printing a request for quotation. Keep empty to use the internal one.")
    sequence = fields.Integer(string='Sequence', help="Assigns the priority to the list of product vendor.", default=1)
    product_uom = fields.Many2one('product.uom', related='product_tmpl_id.uom_po_id', string="Vendor Unit of Measure", readonly="1", help="This comes from the product form.")
    min_qty = fields.Float(string='Minimal Quantity', required=True, help="The minimal quantity to purchase from this vendor, expressed in the vendor Product Unit of Measure if not any, in the default unit of measure of the product otherwise.", default=0.0)
    qty = fields.Float(compute='_compute_calc_qty', store=True, string='Quantity', multi="qty", help="This is a quantity which is converted into Default Unit of Measure.")
    price = fields.Float(string='Price', required=True, digits_compute=dp.get_precision('Product Price'), help="The price to purchase a product", default=0.0)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id.id)
    date_start = fields.Date(string='Start Date', help="Start date for this vendor price")
    date_end = fields.Date(string='End Date', help="End date for this vendor price")
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', ondelete='cascade', index=True, oldname='product_id')
    delay = fields.Integer(string='Delivery Lead Time', required=True,
        help="Lead time in days between the confirmation of the purchase order and the receipt of the products in your warehouse. Used by the scheduler for automatic computation of the purchase order planning.", default=1)
    company_id = fields.Many2one('res.company', string='Company', index=1, default=lambda self: self.env.user.company_id.id)

    @api.depends('min_qty')
    def _compute_calc_qty(self):
        for supplier_info in self:
            supplier_info.qty = supplier_info.min_qty
