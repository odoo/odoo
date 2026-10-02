# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import api, fields, models


class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = "Product Brand"
    _order = 'name'

    name = fields.Char('Brand Name', required=True)
    description = fields.Text(translate=True)
    logo = fields.Binary('Logo File', attachment=True)
    product_ids = fields.One2many(
        'product.template',
        'product_brand_id',
        string='Brand Products',
    )
    products_count = fields.Integer(
        string='Number of products',
        compute='_compute_products_count',
    )

    @api.depends('product_ids')
    def _compute_products_count(self):
        for brand in self:
            brand.products_count = len(brand.product_ids)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_brand_id = fields.Many2one(
        'product.brand',
        string='Brand',
        index=True,
        help='Select a brand for this product', tracking=True
    )
    company_id = fields.Many2one(
        'res.company', 'Company', index=True, required=False, tracking=True)

    # Overrides for tracking.
    name = fields.Char(tracking=True)
    type = fields.Selection(tracking=True)
    list_price = fields.Float(tracking=True)
    standard_price = fields.Float(tracking=True)
    default_code = fields.Char(tracking=True)
    barcode = fields.Char(tracking=True)
    categ_id = fields.Many2one(tracking=True)
    public_categ_ids = fields.Many2many(tracking=True)
    allow_out_of_stock_order = fields.Boolean(tracking=True)
    show_availability = fields.Boolean(tracking=True)

    @api.model
    def _search_get_detail(self, website, order, options):
        res = super(ProductTemplate, self)._search_get_detail(website, order, options)
        if options.get('brand', False):
            domains = res.get('base_domain', [])
            domains.append([('product_brand_id', 'in', options.get('brand', []))])
            res['base_domain'] = domains
        return res

class Product(models.Model):
    _inherit = "product.product"

    # Overrides for tracking.
    default_code = fields.Char(tracking=True)
    barcode = fields.Char(tracking=True)
    qty_available = fields.Float(tracking=True)
