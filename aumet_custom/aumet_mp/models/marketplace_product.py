# -*- coding: utf-8 -*-
import base64
import requests
from odoo import models, fields, api


class MarketplaceProduct(models.Model):
    _name = 'marketplace.product'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'Aumet Market Place Product'

    product_id = fields.Integer('Product ID', required=True, readonly=True)  # id
    name = fields.Char('Product Name', required=True, readonly=True)  # productName
    name_ar = fields.Char('Product Name (AR)', required=True, readonly=True)  # productName_ar
    subtitle_en = fields.Char('Product Subtitle', readonly=True)  # subtitle_en
    subtitle_ar = fields.Char('Product Subtitle (AR)', readonly=True)  # subtitle_ar
    scientific_name = fields.Char('Scientific Name', readonly=True)  # scientificName
    product_barcode = fields.Char('Product Barcode', readonly=True)  # productBarcode
    category_id = fields.Integer('Category ID', readonly=True)  # categoryId
    category_name = fields.Integer('Category Name', readonly=True)  # category_name_en
    category_name_ar = fields.Integer('Category Name (AR)', readonly=True)  # category_name_ar
    unit_price = fields.Float('Unit Price', required=True, readonly=True)  # unitPrice
    retail_selling_price = fields.Float('Retail Selling Price', readonly=True)  # retailSellingPrice
    discount = fields.Float('Discount', readonly=True)  # discount
    vat = fields.Float('VAT', readonly=True)  # vat
    currency = fields.Char('Currency', readonly=True)  # currency
    stock_status_name_en = fields.Char('Stock Status Name', readonly=True)  # stockStatusName_en
    stock_status_name_ar = fields.Char('Stock Status Name (AR)', readonly=True)  # stockStatusName_ar
    stock = fields.Integer('Stock', readonly=True)  # stock
    made_in_country_name_en = fields.Char('Made in country name', readonly=True)  # madeInCountryName_en
    made_in_country_name_ar = fields.Char('Made in country name (AR)', readonly=True)  # madeInCountryName_ar

    partner_id = fields.Many2one('res.partner', string='Distributor')  # entityId
    entity_product_id = fields.Integer(string='Entity Product ID')  # entityProductId

    is_archived = fields.Boolean('Is Archived', readonly=True)  # isArchived
    is_product_locked = fields.Boolean('Is Product Locked', readonly=True)  # is_product_locked
    image_1920 = fields.Image(string='Product Imageّ', readonly=True)  # image
    image_128 = fields.Image('Image', max_width=128, max_height=128, readonly=True)
    description = fields.Text('Description', readonly=True)  # description

    active = fields.Boolean(compute='_compute_active_product', store=True)

    aumet_payment_method_ids = fields.Many2many('aumet.payment.method', string='Payment Methods')

    @api.depends('is_archived')
    def _compute_active_product(self):
        for product in self:
            if product.is_archived != 0:
                product.active = False
            else:
                product.active = True

    def _get_payment_method_dict(self, payment_method):
        return {
            'payment_method_id': payment_method['paymentMethodId'],
            'name': payment_method['paymentMethodName'],
            'discount': payment_method['paymentMethodDiscount'],
            'discount_expire_date': payment_method['discountExpireDate'],
            'unit_price': payment_method['unitPrice'],
        }

    def _get_payment_methods(self, payment_methods):
        payment_method_ids = []
        for payment_method in payment_methods:
            payment_method_dict = self._get_payment_method_dict(payment_method)
            payment_method_id = self.env['aumet.payment.method'].search(
                [('payment_method_id', '=', payment_method['paymentMethodId'])])
            if not payment_method_id.exists():
                payment_method_id = self.env['aumet.payment.method'].create(payment_method_dict)
            else:
                payment_method_id.write(payment_method_dict)
            payment_method_ids.append(payment_method_id.id)
        return payment_method_ids

    def get_product_dict(self, product):
        def get_as_base64(url):
            try:
                return base64.b64encode(requests.get(url).content)
            except:
                return False

        partner_id = self.env['res.partner'].search([('mp_entity_id', '=', product['entityId'])])
        if not partner_id.exists():
            partner_dict = {
                'mp_distributor': True,
                'mp_entity_id': product['entityId'],
                'name': product['entityName'],
                'supplier_rank': 1,
            }
            if product['entityImage']:
                partner_dict['image_1920'] = get_as_base64(product['entityImage'])
            partner_id = self.env['res.partner'].create(partner_dict)

        if product.get('payment_methods', []):
            payment_method_ids = self._get_payment_methods(product['payment_methods'])
        else:
            payment_method_ids = []
        product_dict = {
            'product_id': product['id'],
            'name': product['productName'],
            'name_ar': product['productName_ar'],
            'subtitle_en': product['subtitle_en'],
            'subtitle_ar': product['subtitle_ar'],
            'scientific_name': product['scientificName'],
            'product_barcode': product['productBarcode'],
            'category_id': product['categoryId'],
            'category_name': product['category_name_en'],
            'category_name_ar': product['category_name_ar'],
            'unit_price': product['unitPrice'],
            'retail_selling_price': product['retailSellingPrice'],
            'discount': product['discount'],
            'vat': product['vat'],
            'currency': product['currency'],
            'stock_status_name_en': product['stockStatusName_en'],
            'stock_status_name_ar': product['stockStatusName_ar'],
            'stock': product['stock'],
            'made_in_country_name_en': product['madeInCountryName_en'],
            'made_in_country_name_ar': product['madeInCountryName_ar'],
            'partner_id': partner_id.id,
            'entity_product_id': product['entityProductId'],
            'is_archived': product['isArchived'],
            'is_product_locked': product['is_product_locked'],
            'description': product['description'],
        }
        if product['image']:
            product_dict['image_1920'] = get_as_base64(product['image'])
        if payment_method_ids:
            product_dict['aumet_payment_method_ids'] = [(6, 0, payment_method_ids)]
        return product_dict

    def create_product(self, product):
        product_dict = self.get_product_dict(product)
        self.env['marketplace.product'].create(product_dict)

    def update_product(self, product_id, product):
        product_dict = self.get_product_dict(product)
        product_id.write(product_dict)

    def create_from_marketplace(self, products):
        for product in products:
            product_id = self.search([('product_id', '=', product['id'])])
            if product_id.exists():
                self.update_product(product_id, product)
            else:
                self.create_product(product)
