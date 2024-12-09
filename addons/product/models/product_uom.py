# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductUom(models.Model):
    _description = 'Link between the products and the UoM'

    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True, ondelete='cascade')
    name = fields.Char('Barcode', index='btree_not_null', required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)

    _barcode_uniq = models.Constraint('unique(name)', 'A barcode can only be assigned to one packaging.')

    @api.constrains('name')
    def _check_barcode_uniqueness(self):
        """ With GS1 nomenclature, products and packagings use the same pattern. Therefore, we need
        to ensure the uniqueness between products' barcodes and packagings' ones"""
        domain = [('barcode', 'in', [b for b in self.mapped('name') if b])]
        if self.env['product.product'].search_count(domain, limit=1):
            raise ValidationError(_("A product already uses the barcode"))

    def _compute_display_name(self):
        for record in self:
            if self.env.context.get('show_variant_name'):
                record.display_name = f"{record.name} for: {record.product_id.display_name}"
            else:
                record.display_name = record.name
