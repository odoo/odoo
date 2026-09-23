from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged("post_install", "-at_install", "web_unit", "web_model")
class IrModelAccessTest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        company_model = cls.env["ir.model"]._get_id("res.company")
        cls.env["ir.access"].create(
            [
                {
                    "name": "read",
                    "model_id": company_model,
                    "group_id": cls.env.ref(group).id,
                    "kind": "permission",
                    "operation": "r",
                }
                for group in ("base.group_portal", "base.group_user")
            ]
        )

        cls.portal_user = new_test_user(
            cls.env, login="portalDude", groups="base.group_portal"
        )
        cls.public_user = new_test_user(
            cls.env, login="publicDude", groups="base.group_public"
        )
        cls.spreadsheet_user = new_test_user(
            cls.env, login="spreadsheetDude", groups="base.group_user"
        )

    def test_display_name_for(self):
        result = (
            self.env["ir.model"]
            .with_user(self.spreadsheet_user)
            .display_name_for(["res.company"])
        )
        self.assertEqual(
            result, [{"display_name": "Companies", "model": "res.company"}]
        )
        result = (
            self.env["ir.model"]
            .with_user(self.portal_user)
            .display_name_for(["res.company"])
        )
        self.assertEqual(
            result, [{"display_name": "res.company", "model": "res.company"}]
        )
        result = (
            self.env["ir.model"]
            .with_user(self.public_user)
            .display_name_for(["res.company"])
        )
        self.assertEqual(
            result, [{"display_name": "res.company", "model": "res.company"}]
        )
        result = self.env["ir.model"].display_name_for(["res.company"])
        self.assertEqual(
            result, [{"display_name": "Companies", "model": "res.company"}]
        )
        result = self.env["ir.model"].display_name_for(["unexistent"])
        self.assertEqual(
            result, [{"display_name": "unexistent", "model": "unexistent"}]
        )
        result = self.env["ir.model"].display_name_for(["res.company", "unexistent"])
        self.assertEqual(
            result,
            [
                {"display_name": "Companies", "model": "res.company"},
                {"display_name": "unexistent", "model": "unexistent"},
            ],
        )
        result = self.env["ir.model"].display_name_for(
            ["res.company", "base.language.export"]
        )
        self.assertEqual(
            result,
            [
                {"display_name": "Companies", "model": "res.company"},
                {
                    "display_name": "base.language.export",
                    "model": "base.language.export",
                },
            ],
        )

        result = self.env["ir.model"].get_available_models()
        result = {values["model"] for values in result}
        self.assertIn("res.company", result)
        self.assertNotIn("base.language.export", result)

    def test_get_definitions_access_gated(self):
        IrModel = self.env["ir.model"]

        result = IrModel.with_user(self.spreadsheet_user)._get_definitions(
            ["res.company"]
        )
        self.assertIn("res.company", result)
        self.assertIn("fields", result["res.company"])

        result = IrModel.with_user(self.portal_user)._get_definitions(["res.company"])
        self.assertEqual(result, {})

        result = IrModel.with_user(self.public_user)._get_definitions(["res.company"])
        self.assertEqual(result, {})

        result = IrModel._get_definitions(["res.company", "base.language.export"])
        self.assertIn("res.company", result)
        self.assertIn("base.language.export", result)

        self.assertEqual(set(result), {"res.company", "base.language.export"})


@tagged("web_unit", "web_model")
class TestIrModel(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.registry_enter_test_mode_cls()

        cls.env["ir.model"].create(
            {
                "name": "Banana Ripeness",
                "model": "x_banana_ripeness",
                "field_id": [
                    Command.create(
                        {
                            "name": "x_name",
                            "ttype": "char",
                            "field_description": "Name",
                        }
                    ),
                ],
            }
        )
        cls.ripeness_green = cls.env["x_banana_ripeness"].name_create("Green")
        cls.ripeness_okay = cls.env["x_banana_ripeness"].name_create("Okay, I guess?")
        cls.ripeness_gone = cls.env["x_banana_ripeness"].name_create(
            "Walked away on its own"
        )

        cls.bananas_model = cls.env["ir.model"].create(
            {
                "name": "Bananas",
                "model": "x_bananas",
                "field_id": [
                    Command.create(
                        {
                            "name": "x_name",
                            "ttype": "char",
                            "field_description": "Name",
                        }
                    ),
                    Command.create(
                        {
                            "name": "x_length",
                            "ttype": "float",
                            "field_description": "Length",
                        }
                    ),
                    Command.create(
                        {
                            "name": "x_color",
                            "ttype": "integer",
                            "field_description": "Color",
                        }
                    ),
                    Command.create(
                        {
                            "name": "x_ripeness_id",
                            "ttype": "many2one",
                            "field_description": "Ripeness",
                            "relation": "x_banana_ripeness",
                            "group_expand": True,
                        }
                    ),
                ],
            }
        )
        cls.env["ir.model.fields"].create(
            {
                "name": "x_is_yellow",
                "field_description": "Is the banana yellow?",
                "ttype": "boolean",
                "model_id": cls.bananas_model.id,
                "store": False,
                "depends": "x_color",
                "compute": "for banana in self:\n    banana['x_is_yellow'] = banana.x_color == 9",
            }
        )
        cls.env["ir.default"].set("x_bananas", "x_ripeness_id", cls.ripeness_green[0])
        cls.env["x_bananas"].create(
            [
                {
                    "x_name": "Banana #1",
                    "x_length": 3.14159,
                    "x_color": 9,
                },
                {
                    "x_name": "Banana #2",
                    "x_length": 0,
                    "x_color": 6,
                },
                {
                    "x_name": "Banana #3",
                    "x_length": 10,
                    "x_color": 6,
                },
            ]
        )

    def setUp(self):
        self.addCleanup(self.registry.reset_changes)
        super().setUp()

    def test_model_order_constraint(self):
        VALID_ORDERS = [
            "id",
            "id desc",
            "id asc, x_length",
            "x_color, x_length, create_uid",
        ]
        for order in VALID_ORDERS:
            self.bananas_model.order = order

        INVALID_ORDERS = [
            "",
            "x_wat",
            "id esc",
            "create_uid,",
            "id, x_is_yellow",
        ]
        for order in INVALID_ORDERS:
            with self.assertRaises(ValidationError):
                self.bananas_model.order = order

        fields_value = [
            Command.create(
                {"name": "x_name", "ttype": "char", "field_description": "Name"}
            ),
            Command.create(
                {
                    "name": "x_length",
                    "ttype": "float",
                    "field_description": "Length",
                }
            ),
            Command.create(
                {
                    "name": "x_color",
                    "ttype": "integer",
                    "field_description": "Color",
                }
            ),
        ]
        self.env["ir.model"].create(
            {
                "name": "MegaBananas",
                "model": "x_mega_bananas",
                "order": "x_name asc, id desc",
                "field_id": fields_value,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["ir.model"].create(
                {
                    "name": "GigaBananas",
                    "model": "x_giga_bananas",
                    "order": "x_name asc, x_wat",
                    "field_id": fields_value,
                }
            )

        user_model = self.env["ir.model"].search([("model", "=", "res.users")])
        user_model._check_order()

    def test_model_order_search(self):
        ORDERS = {
            "id asc": ["Banana #1", "Banana #2", "Banana #3"],
            "id desc": ["Banana #3", "Banana #2", "Banana #1"],
            "x_color asc, id asc": ["Banana #2", "Banana #3", "Banana #1"],
            "x_color asc, id desc": ["Banana #3", "Banana #2", "Banana #1"],
            "x_length asc, id": ["Banana #2", "Banana #1", "Banana #3"],
        }
        for order, names in ORDERS.items():
            self.bananas_model.order = order
            self.assertEqual(self.env["x_bananas"]._order, order)

            bananas = self.env["x_bananas"].search([])
            self.assertEqual(
                bananas.mapped("x_name"), names, "failed to order by %s" % order
            )

    def test_model_fold_search(self):
        self.assertEqual(self.bananas_model.fold_name, False)
        self.assertEqual(self.env["x_bananas"]._fold_name, None)

        self.bananas_model.fold_name = "x_name"
        self.assertEqual(self.env["x_bananas"]._fold_name, "x_name")

    def test_group_expansion(self):
        model = self.env["x_bananas"].with_context(read_group_expand=True)
        groups = model.formatted_read_group([], ["x_ripeness_id"], ["__count"])
        expected = [
            {
                "x_ripeness_id": self.ripeness_green,
                "__count": 3,
                "__extra_domain": [("x_ripeness_id", "=", self.ripeness_green[0])],
            },
            {
                "x_ripeness_id": self.ripeness_okay,
                "__count": 0,
                "__extra_domain": [("x_ripeness_id", "=", self.ripeness_okay[0])],
            },
            {
                "x_ripeness_id": self.ripeness_gone,
                "__count": 0,
                "__extra_domain": [("x_ripeness_id", "=", self.ripeness_gone[0])],
            },
        ]
        self.assertEqual(groups, expected, "should include 2 empty ripeness stages")

    def test_rec_name_deletion(self):
        record = self.env["x_bananas"].create({"x_name": "Ifan Ben-Mezd"})
        self.assertEqual(record._rec_name, "x_name")
        ClassRecord = self.registry[record._name]
        self.assertEqual(
            self.registry.field_depends[ClassRecord.display_name], ("x_name",)
        )
        self.assertEqual(record.display_name, "Ifan Ben-Mezd")

        self.env["ir.model.fields"]._get("x_bananas", "x_name").unlink()
        record = self.env["x_bananas"].browse(record.id)
        self.assertEqual(record._rec_name, None)
        self.assertEqual(self.registry.field_depends[ClassRecord.display_name], ())
        self.assertEqual(record.display_name, f"x_bananas,{record.id}")

    def test_monetary_currency_field(self):
        fields_value = [
            Command.create(
                {
                    "name": "x_monetary",
                    "ttype": "monetary",
                    "field_description": "Monetary",
                    "currency_field": "test",
                }
            ),
        ]
        with self.assertRaises(ValidationError):
            self.env["ir.model"].create(
                {
                    "name": "Paper Company Model",
                    "model": "x_paper_model",
                    "field_id": fields_value,
                }
            )

        fields_value = [
            Command.create(
                {
                    "name": "x_monetary",
                    "ttype": "monetary",
                    "field_description": "Monetary",
                    "currency_field": "x_falsy_currency",
                }
            ),
            Command.create(
                {
                    "name": "x_falsy_currency",
                    "ttype": "one2many",
                    "field_description": "Currency",
                    "relation": "res.currency",
                }
            ),
        ]
        with self.assertRaises(ValidationError):
            self.env["ir.model"].create(
                {
                    "name": "Paper Company Model",
                    "model": "x_paper_model",
                    "field_id": fields_value,
                }
            )

        fields_value = [
            Command.create(
                {
                    "name": "x_monetary",
                    "ttype": "monetary",
                    "field_description": "Monetary",
                    "currency_field": "x_falsy_currency",
                }
            ),
            Command.create(
                {
                    "name": "x_falsy_currency",
                    "ttype": "many2one",
                    "field_description": "Currency",
                    "relation": "res.partner",
                }
            ),
        ]
        with self.assertRaises(ValidationError):
            self.env["ir.model"].create(
                {
                    "name": "Paper Company Model",
                    "model": "x_paper_model",
                    "field_id": fields_value,
                }
            )

        fields_value = [
            Command.create(
                {
                    "name": "x_monetary",
                    "ttype": "monetary",
                    "field_description": "Monetary",
                    "currency_field": "x_good_currency",
                }
            ),
            Command.create(
                {
                    "name": "x_good_currency",
                    "ttype": "many2one",
                    "field_description": "Currency",
                    "relation": "res.currency",
                }
            ),
        ]
        model = self.env["ir.model"].create(
            {
                "name": "Paper Company Model",
                "model": "x_paper_model",
                "field_id": fields_value,
            }
        )
        monetary_field = model.field_id.search([["name", "ilike", "x_monetary"]])
        self.assertEqual(
            len(monetary_field),
            1,
            "Should have the monetary field in the created ir.model",
        )
        self.assertEqual(
            monetary_field.currency_field,
            "x_good_currency",
            "The currency field in monetary should have x_good_currency as name",
        )

    def test_invalid_field_domain(self):
        field_ripeness_id = self.env["ir.model.fields"]._get(
            "x_bananas", "x_ripeness_id"
        )

        valid_domain = "[('x_name', '=', 'Green')]"
        invalid_domain = "[('x_name', '=', Green)]"

        field_ripeness_id.domain = valid_domain

        with self.assertRaises(ValidationError) as error:
            field_ripeness_id.domain = invalid_domain

        self.assertIn(
            "An error occurred while evaluating the domain",
            str(error.exception),
        )
        self.assertEqual(field_ripeness_id.domain, valid_domain)
