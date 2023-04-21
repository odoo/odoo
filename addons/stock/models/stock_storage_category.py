# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class StorageCategory(models.Model):
    _name = 'stock.storage.category'
    _description = "Storage Category"
    _order = "name"

    name = fields.Char('Storage Category', required=True)
    max_weight = fields.Float('Max Weight', digits='Stock Weight')
    capacity_ids = fields.One2many('stock.storage.category.capacity', 'storage_category_id', copy=True)
    product_capacity_ids = fields.One2many('stock.storage.category.capacity', compute="_compute_storage_capacity_ids", inverse="_set_storage_capacity_ids")
    package_capacity_ids = fields.One2many('stock.storage.category.capacity', compute="_compute_storage_capacity_ids", inverse="_set_storage_capacity_ids")
    allow_new_product = fields.Selection([
        ('empty', 'If the location is empty'),
        ('same', 'If all products are same'),
        ('mixed', 'Allow mixed products')], default='mixed', required=True)
    location_ids = fields.One2many('stock.location', 'storage_category_id')
    company_id = fields.Many2one('res.company', 'Company')
    weight_uom_name = fields.Char(string='Weight unit', compute='_compute_weight_uom_name')

    _sql_constraints = [
        ('positive_max_weight', 'CHECK(max_weight >= 0)', 'Max weight should be a positive number.'),
    ]

    @api.depends('capacity_ids')
    def _compute_storage_capacity_ids(self):
        for storage_category in self:
            storage_category.product_capacity_ids = storage_category.capacity_ids.filtered(lambda c: c.product_id)
            storage_category.package_capacity_ids = storage_category.capacity_ids.filtered(lambda c: c.package_type_id)

    def _compute_weight_uom_name(self):
        self.weight_uom_name = self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    def _set_storage_capacity_ids(self):
        for storage_category in self:
            storage_category.capacity_ids = storage_category.product_capacity_ids | storage_category.package_capacity_ids

    def copy(self, default=None):
        default = dict(default or {})
        default.update(name=_("%s (copy)") % self.name)
        return super().copy(default)


class StorageCategoryProductCapacity(models.Model):
    _name = 'stock.storage.category.capacity'
    _description = "Storage Category Capacity"
    _check_company_auto = True
    _order = "storage_category_id"

    @api.model
    def _domain_product_id(self):
        domain = "('type', '=', 'product')"
        if self.env.context.get('active_model') == 'product.template':
            product_template_id = self.env.context.get('active_id', False)
            domain = f"('product_tmpl_id', '=', {product_template_id})"
        elif self.env.context.get('default_product_id', False):
            product_id = self.env.context.get('default_product_id', False)
            domain = f"('id', '=', {product_id})"
        return f"[{domain}, '|', ('company_id', '=', False), ('company_id', '=', company_id)]"

    storage_category_id = fields.Many2one('stock.storage.category', ondelete='cascade', required=True, index=True)
    product_id = fields.Many2one('product.product', 'Product', domain=lambda self: self._domain_product_id(), ondelete='cascade', check_company=True)
    package_type_id = fields.Many2one('stock.package.type', 'Package Type', ondelete='cascade', check_company=True)
    quantity = fields.Float('Quantity', required=True)
    product_uom_id = fields.Many2one(related='product_id.uom_id')
    company_id = fields.Many2one('res.company', 'Company', related="storage_category_id.company_id")

    _sql_constraints = [
        ('positive_quantity', 'CHECK(quantity > 0)', 'Quantity should be a positive number.'),
        ('unique_product', 'UNIQUE(product_id, storage_category_id)', 'Multiple capacity rules for one product.'),
        ('unique_package_type', 'UNIQUE(package_type_id, storage_category_id)', 'Multiple capacity rules for one package type.'),
    ]
