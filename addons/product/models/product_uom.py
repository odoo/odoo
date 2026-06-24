# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductUom(models.Model):
    _name = 'product.uom'
    _description = 'Link between products and their UoMs'
    _rec_name = 'barcode'

    uom_id = fields.Many2one('uom.uom', 'Unit', required=True, index=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True, index=True, ondelete='cascade')
    barcode = fields.Char(index='btree_not_null', required=True, copy=False)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    allowed_uom_ids = fields.Many2many('uom.uom', compute='_compute_allowed_uom_ids')

    _barcode_uniq = models.Constraint('unique(barcode)', 'A barcode can only be assigned to one packaging.')

    @api.constrains('barcode')
    def _check_barcode_uniqueness(self):
        """ With GS1 nomenclature, products and packagings use the same pattern. Therefore, we need
        to ensure the uniqueness between products' barcodes and packagings' ones"""
        domain = [('barcode', 'in', [b for b in self.mapped('barcode') if b])]
        if self.env['product.product'].search_count(domain, limit=1):
            raise ValidationError(_("A product already uses the barcode"))

    @api.depends('product_id')
    @api.depends_context('active_model')
    def _compute_allowed_uom_ids(self):
        if self.env.context.get('active_model') == 'uom.uom':
            self.allowed_uom_ids = self.uom_id
            return
        for product_uom in self:
            product = product_uom.product_id
            seller_uom = product.seller_ids.filtered(
                lambda s: not s.product_id or s.product_id == product
            ).uom_id
            product_uom.allowed_uom_ids = product._get_available_uoms() | seller_uom
