# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _


class PackageType(models.Model):
    _name = 'stock.package.type'
    _description = "Stock package type"

    name = fields.Char('Package Type', required=True)
    sequence = fields.Integer('Sequence', default=1, help="The first in the sequence is the default one.")
    height = fields.Float('Height', help="Packaging Height")
    width = fields.Float('Width', help="Packaging Width")
    packaging_length = fields.Float('Length', help="Packaging Length")
    base_weight = fields.Float(string='Weight', help='Weight of the package type')
    max_weight = fields.Float('Max Weight', help='Maximum weight shippable in this packaging')
    barcode = fields.Char('Barcode', copy=False)
    weight_uom_id = fields.Many2one('uom.uom', default=lambda self: self.env.company.default_weight_uom_id, string='Weight unit of measure')
    dimension_uom_id = fields.Many2one('uom.uom', default=lambda self: self.env.company.default_dimension_uom_id, string='Dimensions unit of measure')
    company_id = fields.Many2one('res.company', 'Company', index=True)
    storage_category_capacity_ids = fields.One2many('stock.storage.category.capacity', 'package_type_id', 'Storage Category Capacity', copy=True)

    _sql_constraints = [
        ('barcode_uniq', 'unique(barcode)', "A barcode can only be assigned to one package type !"),
        ('positive_height', 'CHECK(height>=0.0)', 'Height must be positive'),
        ('positive_width', 'CHECK(width>=0.0)', 'Width must be positive'),
        ('positive_length', 'CHECK(packaging_length>=0.0)', 'Length must be positive'),
        ('positive_max_weight', 'CHECK(max_weight>=0.0)', 'Max Weight must be positive'),
        ('weight_uom_check', 'CHECK(weight_uom_id IS NOT NULL OR (base_weight = 0 AND max_weight = 0))', 'Weight Unit of measure must be provided with package weight.'),
        ('dimension_uom_check', 'CHECK(dimension_uom_id IS NOT NULL OR (height = 0 AND width = 0 AND packaging_length = 0))', 'Length Unit of measure must be provided with package dimensions.')
    ]

    def copy(self, default=None):
        default = dict(default or {})
        default.update(name=_("%s (copy)") % self.name)
        return super().copy(default)
