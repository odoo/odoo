from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TestUnit(models.Model):
    _name = "test.unit"
    _description = "Test Unit"

    name = fields.Char(
        string="Name",
        translate=True,
        required=True,
    )
    state = fields.Selection(
        selection=[("a", "A"), ("b", "B")],
        string="State",
    )
    surname = fields.Char(compute="_compute_surname")
    line_ids = fields.One2many(
        comodel_name="test.unit.line",
        inverse_name="unit_id",
    )
    readonly_name = fields.Char(
        string="Readonly Name",
        readonly=True,
    )
    size = fields.Integer()

    @api.depends("name")
    def _compute_surname(self):
        for unit in self:
            unit.surname = unit.name or ""


class TestUnitLine(models.Model):
    _name = "test.unit.line"
    _description = "Test Unit Line"

    name = fields.Char(
        string="Name",
        required=True,
    )
    unit_id = fields.Many2one(
        comodel_name="test.unit",
        required=True,
    )


class TestBox(models.Model):
    _name = "test.box"
    _inherits = {"test.unit": "unit_id"}
    _description = "Test Box"

    unit_id = fields.Many2one(
        comodel_name="test.unit",
        string="Unit",
        required=True,
        ondelete="cascade",
    )
    field_in_box = fields.Char(string="Field1")
    size = fields.Integer()


class TestPallet(models.Model):
    _name = "test.pallet"
    _inherits = {"test.box": "box_id"}
    _description = "Test Pallet"

    box_id = fields.Many2one(
        comodel_name="test.box",
        string="Box",
        required=True,
        ondelete="cascade",
    )
    field_in_pallet = fields.Char(string="Field2")


class TestAnotherUnit(models.Model):
    _name = "test.another_unit"
    _description = "Another Test Unit"

    val1 = fields.Integer(
        string="Value 1",
        required=True,
    )


class TestAnotherBox(models.Model):
    _name = "test.another_box"
    _inherits = {"test.another_unit": "another_unit_id"}
    _description = "Another Test Box"

    another_unit_id = fields.Many2one(
        comodel_name="test.another_unit",
        string="Another Unit",
        required=True,
        ondelete="cascade",
    )
    val2 = fields.Integer(
        string="Value 2",
        required=True,
    )

    @api.constrains("val1", "val2")
    def _check_values(self):
        if any(box.val1 != box.val2 for box in self):
            raise ValidationError("The two values must be equals")


class TestUnstoredInheritsChild(models.Model):
    _name = "test.unstored.inherits.child"
    _description = "Test Unstored Inherits Child"

    contract_name = fields.Char()
    parent_id = fields.Many2one(comodel_name="test.unstored.inherits.parent")
    test_unstored_inherits_shared_line_ids = fields.One2many(
        comodel_name="test.unstored.inherits.shared.line",
        inverse_name="test_unstored_inherits_child_id",
        compute="_compute_test_unstored_inherits_shared_line_ids",
        store=True,
        readonly=False,
    )

    @api.depends("contract_name")
    def _compute_test_unstored_inherits_shared_line_ids(self):
        for record in self:
            record.test_unstored_inherits_shared_line_ids = [
                (5, 0, 0),
                (
                    0,
                    0,
                    {
                        "name": record.contract_name,
                        "test_unstored_inherits_child_id": record.id,
                    },
                ),
            ]


class TestUnstoredInheritsParent(models.Model):
    _name = "test.unstored.inherits.parent"
    _inherits = {"test.unstored.inherits.child": "child_id"}
    _description = "Test Unstored Inherits Parent"

    name = fields.Char()
    child_id = fields.Many2one(
        comodel_name="test.unstored.inherits.child",
        compute="_compute_child_id",
        search="_search_child_id",
        compute_sudo=True,
        store=False,
        required=True,
        ondelete="cascade",
    )

    @api.depends("name")
    def _compute_child_id(self):
        for record in self:
            record.child_id = self.env["test.unstored.inherits.child"].search(
                [("parent_id", "=", record.id)], limit=1
            )

    def _search_child_id(self, operator, value):
        return [("id", "=", False)]

    @api.model
    def _create(self, data_list):
        children = [vals["stored"].pop("child_id", None) for vals in data_list]
        result = super()._create(data_list)
        for parent, child_id, vals in zip(result, children, data_list, strict=True):
            child = self.env["test.unstored.inherits.child"].browse(child_id)
            child.write(
                {
                    **vals.get("inherited", {})["test.unstored.inherits.child"],
                    "parent_id": parent.id,
                }
            )
        return result


class TestUnstoredInheritsSharedLine(models.Model):
    _name = "test.unstored.inherits.shared.line"
    _description = "Test Unstored Inherits Shared Line"

    name = fields.Char()
    test_unstored_inherits_child_id = fields.Many2one(
        comodel_name="test.unstored.inherits.child"
    )
