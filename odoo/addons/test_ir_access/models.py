from odoo import api, fields, models
from odoo.fields import Domain


class TestIrAccessCategory(models.Model):
    _name = "test_ir_access.category"
    _description = "Category read through ir.access"

    name = fields.Char()
    featured_item_id = fields.Many2one(comodel_name="test_ir_access.item")


class TestIrAccessItem(models.Model):
    _name = "test_ir_access.item"
    _description = "Item read through ir.access"

    name = fields.Char()
    val = fields.Integer()
    category_id = fields.Many2one(comodel_name="test_ir_access.category")


class TestIrAccessNode(models.Model):
    _name = "test_ir_access.node"
    _description = "Tree node read through ir.access"

    name = fields.Char()
    parent_id = fields.Many2one(comodel_name="test_ir_access.node")


class TestIrAccessDelegated(models.Model):
    _name = "test_ir_access.delegated"
    _description = "Delegates to an item through a column"
    _inherits = {"test_ir_access.item": "item_id"}

    item_id = fields.Many2one(
        comodel_name="test_ir_access.item",
        required=True,
        ondelete="cascade",
    )


class TestIrAccessDelegatedComputed(models.Model):
    _name = "test_ir_access.delegated_computed"
    _description = "Delegates to an item through a computed, searchable link"
    _inherits = {"test_ir_access.item": "item_id"}

    held_id = fields.Many2one(
        comodel_name="test_ir_access.item",
        ondelete="restrict",
    )
    item_id = fields.Many2one(
        comodel_name="test_ir_access.item",
        compute="_compute_item_id",
        search="_search_item_id",
        compute_sudo=True,
        store=False,
        required=True,
        ondelete="cascade",
    )

    @api.depends("held_id")
    def _compute_item_id(self):
        for record in self:
            record.item_id = record.held_id

    def _search_item_id(self, operator, value):
        return Domain("held_id", operator, value)

    def _create_parent_records(self, data_list):
        for data in data_list:
            data["stored"]["item_id"] = data["stored"].get("held_id")
        super()._create_parent_records(data_list)
        for data in data_list:
            data["stored"]["held_id"] = data["stored"].pop("item_id")


class TestIrAccessGuarded(models.Model):
    _name = "test_ir_access.guarded"
    _description = "Readable where its category is, by the model's own guard"

    name = fields.Char()
    category_id = fields.Many2one(comodel_name="test_ir_access.category")

    @api.model
    def _access_guard(self, operation):
        guard = super()._access_guard(operation)
        if operation == "read":
            return guard & Domain("category_id", "access", "read")
        return guard


class TestIrAccessOwned(models.Model):
    _name = "test_ir_access.owned"
    _description = "Follows the access of the item that owns it"
    _inherit = ["mixin.owner.access"]
    _access_owner_field = "item_id"

    name = fields.Char()
    item_id = fields.Many2one(comodel_name="test_ir_access.item")
