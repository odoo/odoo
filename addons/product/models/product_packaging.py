# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


from odoo.tools import float_compare, float_round


class ProductPackaging(models.Model):
    _name = "product.packaging"
    _description = "Product Packaging"
    _order = 'product_id, sequence, id'
    _check_company_auto = True

    name = fields.Char('Product Packaging', required=True)
    sequence = fields.Integer('Sequence', default=1, help="The first in the sequence is the default one.")
    product_id = fields.Many2one('product.product', string='Product', check_company=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', check_company=True)
    qty = fields.Float('Contained Quantity', default=1, digits='Product Unit of Measure', help="Quantity of products contained in the packaging.")
    barcode = fields.Char('Barcode', copy=False, help="Barcode used for packaging identification. Scan this packaging barcode from a transfer in the Barcode app to move all the contained units")
    product_uom_id = fields.Many2one('uom.uom', compute="_compute_product_uom_id", readonly=True)
    company_id = fields.Many2one('res.company', 'Company', index=True)

    _sql_constraints = [
        ('positive_qty', 'CHECK(qty > 0)', 'Contained Quantity should be positive.'),
        ('barcode_uniq', 'unique(barcode)', 'A barcode can only be assigned to one packaging.'),
    ]

    @api.depends('product_tmpl_id', 'product_id')
    def _compute_product_uom_id(self):
        for packaging in self:
            packaging.product_uom_id = packaging.product_id.uom_id or packaging.product_tmpl_id.uom_id

    @api.constrains('barcode')
    def _check_barcode_uniqueness(self):
        """ With GS1 nomenclature, products and packagings use the same pattern. Therefore, we need
        to ensure the uniqueness between products' barcodes and packagings' ones"""
        domain = [('barcode', 'in', [b for b in self.mapped('barcode') if b])]
        if self.env['product.product'].search(domain, order="id", limit=1):
            raise ValidationError(_("A product already uses the barcode"))

    def _check_qty(self, product_qty, uom_id, rounding_method="HALF-UP"):
        """Check if product_qty in given uom is a multiple of the packaging qty.
        If not, rounding the product_qty to closest multiple of the packaging qty
        according to the rounding_method "UP", "HALF-UP or "DOWN".
        """
        self.ensure_one()
        default_uom = self.product_id.uom_id or self.product_tmpl_id.uom_id
        packaging_qty = default_uom._compute_quantity(self.qty, uom_id)
        # We do not use the modulo operator to check if qty is a mltiple of q. Indeed the quantity
        # per package might be a float, leading to incorrect results. For example:
        # 8 % 1.6 = 1.5999999999999996
        # 5.4 % 1.8 = 2.220446049250313e-16
        if product_qty and packaging_qty:
            rounded_qty = float_round(product_qty / packaging_qty, precision_rounding=1.0,
                                  rounding_method=rounding_method) * packaging_qty
            return rounded_qty if float_compare(rounded_qty, product_qty, precision_rounding=default_uom.rounding) else product_qty
        return product_qty

    def _find_suitable_product_packaging(self, product_qty, uom_id):
        """ try find in `self` if a packaging's qty in given uom is a divisor of
        the given product_qty. If so, return the one with greatest divisor.
        """
        packagings = self.sorted(lambda p: p.qty, reverse=True)
        for packaging in packagings:
            new_qty = packaging._check_qty(product_qty, uom_id)
            if new_qty == product_qty:
                return packaging
        return self.env['product.packaging']

    @api.model
    def _compute_packaging(self, product_packaging_id, product_id, product_uom_qty, product_uom, optional_type=False):
        """Helper method to be used to compute packaging and packaging_qty for
        stock.move, purchase.order.line, and sale.order.line.
        If there is product_packaging_id, check with current product_uom_qty, the
        packaging_qty is an integer or not. If no, remove it.
        If there is no product_packaging_id or it's removed during the above process,
        try suggest a packaging with integer packaging_qty.
        """
        if not product_id or not product_uom_qty or not product_uom:
            return False
        else:
            # remove packaging if not match the product
            if product_packaging_id.product_id != product_id and product_packaging_id.product_tmpl_id != product_id.product_tmpl_id:
                product_packaging_id = False
            # remove packaging if product_uom_qty is not a multiple of packaging_uom_qty
            if product_packaging_id:
                packaging_uom = product_packaging_id.product_uom_id
                packaging_uom_qty = product_uom._compute_quantity(product_uom_qty, packaging_uom)
                product_packaging_qty = packaging_uom_qty / product_packaging_id.qty
                product_packaging_qty_integer = float_round(product_packaging_qty, precision_rounding=1.0)
                if not float_compare(product_packaging_qty,
                                        product_packaging_qty_integer,
                                        precision_rounding=product_uom.rounding) == 0:
                    product_packaging_id = False
            # if now no packaging, try find a suitable one
            if not product_packaging_id:
                condidate_packagings = product_id.packaging_ids + product_id.product_tmpl_id.tmpl_packaging_ids
                if optional_type:
                    condidate_packagings = condidate_packagings.filtered(optional_type)
                product_packaging_id = condidate_packagings._find_suitable_product_packaging(product_uom_qty, product_uom)
            return product_packaging_id

    @api.model
    def _compute_packaging_qty(self, product_packaging_id, product_uom_qty, product_uom):
        if not product_packaging_id:
            return 0
        packaging_uom = product_packaging_id.product_uom_id
        packaging_uom_qty = product_uom._compute_quantity(product_uom_qty, packaging_uom)
        return packaging_uom_qty / product_packaging_id.qty
