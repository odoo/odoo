# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools import format_list, groupby


class ProductUom(models.Model):
    _name = 'product.uom'
    _description = 'Link between products and their UoMs'
    _rec_name = 'barcode'

    uom_id = fields.Many2one('uom.uom', 'Unit', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True, ondelete='cascade')
    barcode = fields.Char(index='btree_not_null', required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    def _get_barcodes_by_company(self):
        return [
            (company_id, [p.barcode for p in product_uom if p.barcode])
            for company_id, product_uom in groupby(self, lambda p: p.company_id.id)
        ]

    def _check_duplicated_barcodes(self, barcodes_within_company, company_id):
        domain = [('barcode', 'in', barcodes_within_company)]
        if company_id:
            domain.append(('company_id', 'in', (False, company_id)))
        products_by_barcode = self.env['product.product'].sudo()._read_group(
            domain, ['barcode'], ['id:recordset'], having=[('__count', '>', 1)],
        )
        packagings_by_barcode = self.sudo()._read_group(
            domain, ['barcode'], ['id:recordset'], having=[('__count', '>', 1)],
        )

        duplicates_as_str = "\n".join(
            _(
                "- Barcode \"%(barcode)s\" already assigned to product(s): %(product_list)s",
                barcode=barcode, product_list=format_list(self.env, duplicate_products._filtered_access('read').mapped('display_name')),
            )
            for barcode, duplicate_products in products_by_barcode
        )
        duplicates_as_str += "\n".join(
            _(
                "- Barcode \"%(barcode)s\" already assigned to packaging(s): %(packaging_list)s",
                barcode=barcode, packaging_list=format_list(self.env, duplicate_packagings._filtered_access('read').mapped('display_name')),
            )
            for barcode, duplicate_packagings in packagings_by_barcode
        )
        if duplicates_as_str:
            duplicates_as_str += _(
                "\n\nNote: products that you don't have access to will not be shown above."
            )
            raise ValidationError(_("Barcode(s) already assigned:\n\n%s", duplicates_as_str))

    @api.constrains('barcode')
    def _check_barcode_uniqueness(self):
        """ With GS1 nomenclature, products and packagings use the same pattern. Therefore, we need
        to ensure the uniqueness between products' barcodes and packagings' ones"""
        # Barcodes should only be unique within a company
        for company_id, barcodes_within_company in self._get_barcodes_by_company():
            self._check_duplicated_barcodes(barcodes_within_company, company_id)

    @api.constrains('uom_id', 'product_id')
    def _check_valid_uom(self):
        for product_uom in self:
            if product_uom.uom_id not in product_uom.product_id.uom_ids:
                raise ValidationError(_("The unit of measure is not valid for this product"))

    def _compute_display_name(self):
        if not self.env.context.get('show_variant_name'):
            return super()._compute_display_name()
        for record in self:
            record.display_name = f"{record.barcode} for: {record.product_id.display_name}"
