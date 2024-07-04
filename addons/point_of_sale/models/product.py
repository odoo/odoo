# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from collections import defaultdict
from itertools import groupby
from operator import itemgetter
from datetime import date
from odoo.osv.expression import AND


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    available_in_pos = fields.Boolean(string='Available in POS', help='Check if you want this product to appear in the Point of Sale.', default=False)
    to_weight = fields.Boolean(string='To Weigh With Scale', help="Check if the product should be weighted using the hardware scale integration.")
    pos_categ_ids = fields.Many2many(
        'pos.category', string='Point of Sale Category',
        help="Category used in the Point of Sale.")
    combo_ids = fields.Many2many('pos.combo', string='Combo Choices')
    type = fields.Selection(selection_add=[
        ('combo', 'Combo')
    ], ondelete={'combo': 'set consu'})

    @api.ondelete(at_uninstall=False)
    def _unlink_except_open_session(self):
        product_ctx = dict(self.env.context or {}, active_test=False)
        if self.with_context(product_ctx).search_count([('id', 'in', self.ids), ('available_in_pos', '=', True)]):
            if self.env['pos.session'].sudo().search_count([('state', '!=', 'closed')]):
                raise UserError(_("To delete a product, make sure all point of sale sessions are closed.\n\n"
                    "Deleting a product available in a session would be like attempting to snatch a"
                    "hamburger from a customer’s hand mid-bite; chaos will ensue as ketchup and mayo go flying everywhere!"))

    def _prepare_tooltip(self):
        tooltip = super()._prepare_tooltip()
        if self.type == 'combo':
            tooltip = _(
                "Combos allows to choose one product amongst a selection of choices per category."
            )
        return tooltip

    @api.onchange('sale_ok')
    def _onchange_sale_ok(self):
        if not self.sale_ok:
            self.available_in_pos = False

    @api.onchange('available_in_pos')
    def _onchange_available_in_pos(self):
        if self.available_in_pos and not self.sale_ok:
            self.sale_ok = True

    @api.onchange('type')
    def _onchange_type(self):
        res = super()._onchange_type()
        if self.type == 'combo':
            self.taxes_id = False
            self.supplier_taxes_id = False
        return res

    @api.constrains('available_in_pos')
    def _check_combo_inclusions(self):
        for product in self:
            if not product.available_in_pos:
                combo_name = self.env['pos.combo.line'].sudo().search([('product_id', 'in', product.product_variant_ids.ids)], limit=1).combo_id.name
                if combo_name:
                    raise UserError(_('You must first remove this product from the %s combo', combo_name))

    def _create_variant_ids(self):
        res = super()._create_variant_ids()
        for template in self:
            archived_product = self.env['product.product'].search([('product_tmpl_id', '=', template.id), ('active', '=', False)], limit=1)
            if archived_product:
                combo_choices_to_delete = self.env['pos.combo.line'].search([
                    ('product_id', '=', archived_product.id)
                ])
                if combo_choices_to_delete:
                    # Delete old combo line
                    combo_ids = combo_choices_to_delete.mapped('combo_id')
                    combo_choices_to_delete.unlink()
                    # Create new combo line (one for each new variant) in each combo
                    new_variants = template.product_variant_ids.filtered(lambda v: v.active)
                    self.env['pos.combo.line'].create([
                        {
                            'product_id': variant.id,
                            'combo_id': combo_id.id,
                        }
                        for variant in new_variants for combo_id in combo_ids
                    ])
        return res

    @api.onchange('type')
    def _onchange_type(self):
        if self.type == "combo" and self.attribute_line_ids:
            raise UserError(_("Combo products cannot contains variants or attributes"))
        return super()._onchange_type()


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        config_id = self.env['pos.config'].browse(data['pos.config']['data'][0]['id'])
        return config_id._get_available_product_domain()

    @api.model
    def _load_pos_data_fields(self, config_id):
        return [
            'id', 'display_name', 'lst_price', 'standard_price', 'categ_id', 'pos_categ_ids', 'taxes_id', 'barcode', 'name',
            'default_code', 'to_weight', 'uom_id', 'description_sale', 'description', 'product_tmpl_id', 'tracking', 'type',
            'write_date', 'available_in_pos', 'attribute_line_ids', 'active', 'image_128', 'combo_ids', 'product_template_variant_value_ids',
        ]

    def _load_pos_data(self, data):
        config_id = self.env['pos.config'].browse(data['pos.config']['data'][0]['id'])
        limit_count = config_id.get_limited_product_count()
        fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
        if limit_count:
            products = config_id.with_context({**self.env.context, 'display_default_code': False}).get_limited_products_loading(fields)
        else:
            domain = self._load_pos_data_domain(data)
            products = self.with_context({**self.env.context, 'display_default_code': False}).search_read(
                domain,
                fields,
                order='sequence,default_code,name',
                load=False)

        self._process_pos_ui_product_product(products, config_id)
        return {
            'data': products,
            'fields': fields,
        }

    def _process_pos_ui_product_product(self, products, config_id):

        def filter_taxes_on_company(product_taxes, taxes_by_company):
            """
            Filter the list of tax ids on a single company starting from the current one.
            If there is no tax in the result, it's filtered on the parent company and so
            on until a non empty result is found.
            """
            taxes, comp = None, self.env.company
            while not taxes and comp:
                taxes = list(set(product_taxes) & set(taxes_by_company[comp.id]))
                comp = comp.parent_id
            return taxes

        taxes = self.env['account.tax'].search(self.env['account.tax']._check_company_domain(self.env.company))
        # group all taxes by company in a dict where:
        # - key: ID of the company
        # - values: list of tax ids
        taxes_by_company = defaultdict(set)
        if self.env.company.parent_id:
            for tax in taxes:
                taxes_by_company[tax.company_id.id].add(tax.id)

        different_currency = config_id.currency_id != self.env.company.currency_id
        for product in products:
            if different_currency:
                product['lst_price'] = self.env.company.currency_id._convert(product['lst_price'], config_id.currency_id, self.env.company, fields.Date.today())
            product['image_128'] = bool(product['image_128'])

            if len(taxes_by_company) > 1 and len(product['taxes_id']) > 1:
                product['taxes_id'] = filter_taxes_on_company(product['taxes_id'], taxes_by_company)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_active_pos_session(self):
        product_ctx = dict(self.env.context or {}, active_test=False)
        if self.env['pos.session'].sudo().search_count([('state', '!=', 'closed')]):
            if self.with_context(product_ctx).search_count([('id', 'in', self.ids), ('product_tmpl_id.available_in_pos', '=', True)]):
                raise UserError(_("To delete a product, make sure all point of sale sessions are closed.\n\n"
                    "Deleting a product available in a session would be like attempting to snatch a"
                    "hamburger from a customer’s hand mid-bite; chaos will ensue as ketchup and mayo go flying everywhere!"))

    def get_product_info_pos(self, price, quantity, pos_config_id):
        self.ensure_one()
        config = self.env['pos.config'].browse(pos_config_id)

        # Tax related
        taxes = self.taxes_id.compute_all(price, config.currency_id, quantity, self)
        grouped_taxes = {}
        for tax in taxes['taxes']:
            if tax['id'] in grouped_taxes:
                grouped_taxes[tax['id']]['amount'] += tax['amount']/quantity if quantity else 0
            else:
                grouped_taxes[tax['id']] = {
                    'name': tax['name'],
                    'amount': tax['amount']/quantity if quantity else 0
                }

        all_prices = {
            'price_without_tax': taxes['total_excluded']/quantity if quantity else 0,
            'price_with_tax': taxes['total_included']/quantity if quantity else 0,
            'tax_details': list(grouped_taxes.values()),
        }

        # Pricelists
        if config.use_pricelist:
            pricelists = config.available_pricelist_ids
        else:
            pricelists = config.pricelist_id
        price_per_pricelist_id = pricelists._price_get(self, quantity) if pricelists else False
        pricelist_list = [{'name': pl.name, 'price': price_per_pricelist_id[pl.id]} for pl in pricelists]

        # Warehouses
        warehouse_list = [
            {'name': w.name,
            'available_quantity': self.with_context({'warehouse_id': w.id}).qty_available,
            'forecasted_quantity': self.with_context({'warehouse_id': w.id}).virtual_available,
            'uom': self.uom_name}
            for w in self.env['stock.warehouse'].search([])]

        # Suppliers
        key = itemgetter('partner_id')
        supplier_list = []
        for key, group in groupby(sorted(self.seller_ids, key=key), key=key):
            for s in list(group):
                if not((s.date_start and s.date_start > date.today()) or (s.date_end and s.date_end < date.today()) or (s.min_qty > quantity)):
                    supplier_list.append({
                        'name': s.partner_id.name,
                        'delay': s.delay,
                        'price': s.price
                    })
                    break

        # Variants
        variant_list = [{'name': attribute_line.attribute_id.name,
                         'values': list(map(lambda attr_name: {'name': attr_name, 'search': '%s %s' % (self.name, attr_name)}, attribute_line.value_ids.mapped('name')))}
                        for attribute_line in self.attribute_line_ids]

        return {
            'all_prices': all_prices,
            'pricelists': pricelist_list,
            'warehouses': warehouse_list,
            'suppliers': supplier_list,
            'variants': variant_list
        }


class ProductAttribute(models.Model):
    _name = 'product.attribute'
    _inherit = ['product.attribute', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['name', 'display_type', 'template_value_ids', 'attribute_line_ids', 'create_variant']


class ProductAttributeCustomValue(models.Model):
    _name = 'product.attribute.custom.value'
    _inherit = ["product.attribute.custom.value", "pos.load.mixin"]

    pos_order_line_id = fields.Many2one('pos.order.line', string="PoS Order Line", ondelete='cascade')

    @api.model
    def _load_pos_data_domain(self, data):
        return [('pos_order_line_id', 'in', [line['id'] for line in data['pos.order.line']['data']])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['custom_value', 'custom_product_template_attribute_value_id', 'pos_order_line_id']


class ProductTemplateAttributeLine(models.Model):
    _name = 'product.template.attribute.line'
    _inherit = ['product.template.attribute.line', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['display_name', 'attribute_id', 'product_template_value_ids']


class ProductTemplateAttributeValue(models.Model):
    _name = 'product.template.attribute.value'
    _inherit = ['product.template.attribute.value', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        return AND([[('ptav_active', '=', True)], [('attribute_id', 'in', [attr['id'] for attr in data['product.attribute']['data']])]])

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['attribute_id', 'attribute_line_id', 'product_attribute_value_id', 'price_extra', 'name', 'is_custom', 'html_color', 'image']


class ProductPackaging(models.Model):
    _name = 'product.packaging'
    _inherit = ['product.packaging', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        return AND([[('barcode', 'not in', ['', False])], [('product_id', 'in', [x['id'] for x in data['product.product']['data']])] if data else []])

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'barcode', 'product_id', 'qty']


class UomCateg(models.Model):
    _name = 'uom.category'
    _inherit = ['uom.category', 'pos.load.mixin']

    is_pos_groupable = fields.Boolean(string='Group Products in POS',
        help="Check if you want to group products of this category in point of sale orders")

    @api.model
    def _load_pos_data_domain(self, data):
        return [('uom_ids', 'in', [uom['category_id'] for uom in data['uom.uom']['data']])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'uom_ids']


class Uom(models.Model):
    _name = 'uom.uom'
    _inherit = ['uom.uom', 'pos.load.mixin']

    is_pos_groupable = fields.Boolean(related='category_id.is_pos_groupable', readonly=False)

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'category_id', 'factor_inv', 'factor', 'is_pos_groupable', 'uom_type', 'rounding']

    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
        return {
            'data': self.with_context({**self.env.context}).search_read(domain, fields, load=False),
            'fields': fields,
        }


class ProductPricelist(models.Model):
    _name = 'product.pricelist'
    _inherit = ['product.pricelist', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        config_id = self.env['pos.config'].browse(data['pos.config']['data'][0]['id'])
        return [('id', 'in', config_id.available_pricelist_ids.ids)] if config_id.use_pricelist else [('id', '=', config_id.pricelist_id.id)]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'display_name', 'discount_policy', 'item_ids']


class ProductPricelistItem(models.Model):
    _name = 'product.pricelist.item'
    _inherit = ['product.pricelist.item', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        product_tmpl_ids = [p['product_tmpl_id'] for p in data['product.product']['data']]
        product_ids = [p['id'] for p in data['product.product']['data']]
        pricelist_ids = [p['id'] for p in data['product.pricelist']['data']]
        return [
            ('pricelist_id', 'in', pricelist_ids),
            '|', ('product_tmpl_id', '=', False), ('product_tmpl_id', 'in', product_tmpl_ids),
            '|', ('product_id', '=', False), ('product_id', 'in', product_ids),
        ]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['product_tmpl_id', 'product_id', 'pricelist_id', 'price_surcharge', 'price_discount', 'price_round',
                'price_min_margin', 'price_max_margin', 'company_id', 'currency_id', 'date_start', 'date_end', 'compute_price',
                'fixed_price', 'percent_price', 'base_pricelist_id', 'base', 'categ_id', 'min_quantity']


class ProductCategory(models.Model):
    _name = 'product.category'
    _inherit = ['product.category', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'parent_id']
