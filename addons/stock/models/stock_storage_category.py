from odoo import api, fields, models

from ..tools import debug_log as dbg


class StockStorageCategory(models.Model):
    _name = "stock.storage.category"
    _description = "Storage Category"
    _order = "name"

    name = fields.Char(
        string="Storage Category",
        required=True,
    )
    max_weight = fields.Float(
        digits="Stock Weight",
        help="Maximum weight the locations of this storage category can hold. "
        "Leave 0 for no weight limit.",
    )
    capacity_ids = fields.One2many(
        comodel_name="stock.storage.category.capacity",
        inverse_name="storage_category_id",
        copy=True,
    )
    product_capacity_ids = fields.One2many(
        comodel_name="stock.storage.category.capacity",
        compute="_compute_storage_capacity_ids",
        inverse="_inverse_storage_capacity_ids",
    )
    package_capacity_ids = fields.One2many(
        comodel_name="stock.storage.category.capacity",
        compute="_compute_storage_capacity_ids",
        inverse="_inverse_storage_capacity_ids",
    )
    allow_new_product = fields.Selection(
        selection=[
            ("empty", "If the location is empty"),
            ("same", "If all products are same"),
            ("mixed", "Allow mixed products"),
        ],
        default="mixed",
        required=True,
    )
    location_ids = fields.One2many(
        comodel_name="stock.location",
        inverse_name="storage_category_id",
    )
    company_id = fields.Many2one(comodel_name="res.company")
    weight_uom_name = fields.Char(
        string="Weight unit",
        compute="_compute_weight_uom_name",
    )

    _positive_max_weight = models.Constraint(
        "CHECK(max_weight >= 0)",
        "Max weight should be a positive number.",
    )

    @api.depends("capacity_ids")
    def _compute_storage_capacity_ids(self):
        for storage_category in self:
            storage_category.product_capacity_ids = (
                storage_category.capacity_ids.filtered(lambda c: c.product_id)
            )
            storage_category.package_capacity_ids = (
                storage_category.capacity_ids.filtered(lambda c: c.package_type_id)
            )

    def _compute_weight_uom_name(self):
        self.weight_uom_name = self.env[
            "product.template"
        ]._get_weight_uom_name_from_ir_config_parameter()

    def _inverse_storage_capacity_ids(self):
        for storage_category in self:
            dbg.lifecycle.debug(
                "[storage_category:%s] capacities: %d product, %d package",
                storage_category.id,
                len(storage_category.product_capacity_ids),
                len(storage_category.package_capacity_ids),
            )
            storage_category.capacity_ids = (
                storage_category.product_capacity_ids
                | storage_category.package_capacity_ids
            )

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [
            dict(vals, name=self.env._("%s (copy)", category.name))
            for category, vals in zip(self, vals_list, strict=True)
        ]


class StockStorageCategoryCapacity(models.Model):
    _name = "stock.storage.category.capacity"
    _description = "Storage Category Capacity"
    _check_company_auto = True
    _order = "storage_category_id"

    storage_category_id = fields.Many2one(
        comodel_name="stock.storage.category",
        index=True,
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        index="btree_not_null",
        domain="[('product_tmpl_id', '=', context.get('active_id', False))] if context.get('active_model') == 'product.template' else"
        " [('id', '=', context.get('default_product_id', False))] if context.get('default_product_id') else"
        " [('is_storable', '=', True)]",
        ondelete="cascade",
        check_company=True,
    )
    package_type_id = fields.Many2one(
        comodel_name="stock.package.type",
        index="btree_not_null",
        ondelete="cascade",
        check_company=True,
    )
    quantity = fields.Float(required=True)
    product_uom_id = fields.Many2one(related="product_id.uom_id")
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="storage_category_id.company_id",
        string="Company",
    )

    _positive_quantity = models.Constraint(
        "CHECK(quantity > 0)",
        "Quantity should be a positive number.",
    )
    _product_or_package_type = models.Constraint(
        "CHECK((product_id IS NULL) != (package_type_id IS NULL))",
        "A storage capacity rule must concern either a product or a package type, but not both.",
    )
    _unique_product = models.UniqueIndex(
        "(product_id, storage_category_id) WHERE product_id IS NOT NULL",
        "Multiple capacity rules for one product.",
    )
    _unique_package_type = models.UniqueIndex(
        "(package_type_id, storage_category_id) WHERE package_type_id IS NOT NULL",
        "Multiple capacity rules for one package type.",
    )
