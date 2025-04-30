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

    _barcode_uniq = models.Constraint('unique(barcode)', 'A barcode can only be assigned to one packaging.')

    @api.constrains('barcode')
    def _check_barcode_uniqueness(self):
        """ With GS1 nomenclature, products and packagings use the same pattern. Therefore, we need
        to ensure the uniqueness between products' barcodes and packagings' ones"""
        domain = [('barcode', 'in', [b for b in self.mapped('barcode') if b])]
        if self.env['product.product'].search_count(domain, limit=1):
            raise ValidationError(_("A product already uses the barcode"))

    def _compute_display_name(self):
        if not self.env.context.get('show_variant_name'):
            return super()._compute_display_name()
        for record in self:
            record.display_name = f"{record.barcode} for: {record.product_id.display_name}"
