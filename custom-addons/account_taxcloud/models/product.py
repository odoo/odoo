# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import UserError

class ProductTicCategory(models.Model):
    _name = 'product.tic.category'
    _description = "Product TIC Category"
    _rec_name = 'code'
    _rec_names_search = ['description', 'code']

    code = fields.Integer(string="TIC Category Code", required=True)
    description = fields.Char(string='TIC Description', required=True)

    @api.depends('code', 'description')
    def _compute_display_name(self):
        for category in self:
            category.display_name = _('[%s] %s', category.code, (category.description or '')[:50])

    @api.model
    def name_create(self, name):
        try:
            name = int(name)
        except ValueError:
            raise UserError(_('The Taxcloud Category must be integer.'))
        return super().name_create(name)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    tic_category_id = fields.Many2one('product.tic.category', string="TaxCloud Category",
        help="This refers to TIC (Taxability Information Codes), these are used by TaxCloud to compute specific tax "
             "rates for each product type. The value set here prevails over the one set on the product category.")

class ResCompany(models.Model):
    _inherit = 'res.company'

    taxcloud_api_id = fields.Char(string='TaxCloud API ID')
    taxcloud_api_key = fields.Char(string='TaxCloud API KEY')
    tic_category_id = fields.Many2one('product.tic.category', string='Default TIC Code',
                                      help="TIC (Taxability Information Codes) allow to get specific tax rates for each product type. "
                                           "This default value applies if no product is used in the order/invoice, or if no TIC is set on "
                                           "the product or its product category. By default, TaxCloud relies on the TIC *[0] Uncategorized* "
                                           "default referring to general goods and services.")
    is_taxcloud_configured = fields.Boolean(compute='_compute_is_taxcloud_configured',
                                            help='Used to determine whether or not to warn the user to configure TaxCloud.')

    @api.depends('taxcloud_api_id', 'taxcloud_api_key')
    def _compute_is_taxcloud_configured(self):
        for company in self:
            company.is_taxcloud_configured = company.taxcloud_api_id and company.taxcloud_api_key


class ProductCategory(models.Model):
    _inherit = "product.category"

    tic_category_id = fields.Many2one('product.tic.category', string='TIC Code',
        help="This refers to TIC (Taxability Information Codes), these are used by TaxCloud to compute specific tax rates for "
             "each product type. This value is used when no TIC is set on the product. If no value is set here, the default "
             "value set in Invoicing settings is used.")
