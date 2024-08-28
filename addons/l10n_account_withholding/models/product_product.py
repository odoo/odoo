# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class ProductTemplate(models.Model):
    """
    We want to keep the product view clean and simple to use. This means that adding new fields for withholding taxes
    is not acceptable.
    We also cannot easily reuse the taxes_id/supplier_taxes_id fields as adding taxes in them would cause these taxes to
    affect a lot of other flows (POS, eCommerce, etc.)
    Instead, we will replace the field in the view by a "new" field using the same table as the existing ones but which
    accepts both regular and withholding taxes.
    The existing fields now become a subset of that new field which only accepts regular taxes.
    And finally, we add another subset-field which only accepts withholding taxes.

    This way, we do not add any new fields in the view, nor table/column in the database and keep a easy-to-use
    interface while having the flexibility of choosing which field is used in which context.
    """
    _inherit = 'product.template'

    # ------------------
    # Fields declaration
    # ------------------

    # Sale taxes.
    all_tax_ids = fields.Many2many(
        'account.tax', 'product_taxes_rel', 'prod_id', 'tax_id',
        string="All Sales Taxes",
        help="Default taxes used when selling the product",
        domain=[('type_tax_use', '=', 'sale')],
        compute="_compute_all_tax_ids",
        inverse="_inverse_all_tax_ids",
    )
    withholding_tax_ids = fields.Many2many(
        'account.tax', 'product_taxes_rel', 'prod_id', 'tax_id',
        string="Withholding Sales Taxes",
        domain=[('type_tax_use', '=', 'sale'), ('is_withholding_tax_on_payment', '=', True)],
    )
    taxes_id = fields.Many2many(
        domain=[('type_tax_use', '=', 'sale'), ('is_withholding_tax_on_payment', '=', False)]
    )
    # Purchase taxes
    all_supplier_tax_ids = fields.Many2many(
        'account.tax', 'product_supplier_taxes_rel', 'prod_id', 'tax_id',
        string="All Purchase Taxes",
        help="Default taxes used when buying the product",
        domain=[('type_tax_use', '=', 'purchase')],
        compute="_compute_all_supplier_tax_ids",
        inverse="_inverse_all_supplier_tax_ids",
    )
    supplier_withholding_tax_ids = fields.Many2many(
        'account.tax', 'product_supplier_taxes_rel', 'prod_id', 'tax_id',
        string="Withholding Purchase Taxes",
        domain=[('type_tax_use', '=', 'purchase'), ('is_withholding_tax_on_payment', '=', True)],
    )
    supplier_taxes_id = fields.Many2many(
        domain=[('type_tax_use', '=', 'purchase'), ('is_withholding_tax_on_payment', '=', False)],
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('withholding_tax_ids', 'taxes_id')
    def _compute_all_tax_ids(self):
        for product in self:
            product.all_tax_ids = product.withholding_tax_ids + product.taxes_id

    def _inverse_all_tax_ids(self):
        for product in self:
            withholding_taxes = product.all_tax_ids.filtered('is_withholding_tax_on_payment')
            product.write({
                'withholding_tax_ids': withholding_taxes,
                'taxes_id': product.all_tax_ids - withholding_taxes,
            })

    @api.depends('supplier_withholding_tax_ids', 'supplier_taxes_id')
    def _compute_all_supplier_tax_ids(self):
        for product in self:
            product.all_supplier_tax_ids = product.supplier_withholding_tax_ids + product.supplier_taxes_id

    def _inverse_all_supplier_tax_ids(self):
        for product in self:
            withholding_taxes = product.all_supplier_tax_ids.filtered('is_withholding_tax_on_payment')
            product.write({
                'supplier_withholding_tax_ids': withholding_taxes,
                'supplier_taxes_id': product.all_supplier_tax_ids - withholding_taxes,
            })
