from datetime import datetime
from unittest.mock import patch

from psycopg import IntegrityError
from psycopg.types.json import Json

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user
from odoo.tools import mute_logger


class TestIrDefault(TransactionCase):
    def test_unique_scope_prevents_duplicate(self):
        IrDefault = self.env["ir.default"]
        field = self.env["ir.model.fields"]._get("res.partner", "ref")
        IrDefault.search([("field_id", "=", field.id)]).unlink()

        IrDefault.set("res.partner", "ref", "A")
        IrDefault.set("res.partner", "ref", "B")
        rows = IrDefault.search(
            [
                ("field_id", "=", field.id),
                ("user_id", "=", False),
                ("company_id", "=", False),
                ("condition", "=", False),
            ]
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(IrDefault._get_model_defaults("res.partner").get("ref"), "B")

        with (
            mute_logger("odoo.db.cursor"),
            self.assertRaisesRegex(IntegrityError, "ir_default_unique_scope"),
            self.cr.savepoint(),
        ):
            IrDefault.create({"field_id": field.id, "json_value": '"C"'})
            IrDefault.flush_all()

    def test_defaults(self):
        companyA = self.env.company
        companyB = companyA.create({"name": "CompanyB"})
        user1 = self.env.user
        user2 = user1.create({"name": "u2", "login": "u2"})
        user3 = user1.create(
            {
                "name": "u3",
                "login": "u3",
                "company_id": companyB.id,
                "company_ids": companyB.ids,
            }
        )

        IrDefault1 = self.env["ir.default"]
        IrDefault2 = IrDefault1.with_user(user2)
        IrDefault3 = IrDefault1.with_user(user3)

        IrDefault1.search([("field_id.model", "=", "res.partner")]).unlink()
        IrDefault1.set("res.partner", "ref", "GLOBAL", user_id=False, company_id=False)
        self.assertEqual(
            IrDefault1._get_model_defaults("res.partner"),
            {"ref": "GLOBAL"},
            "Can't retrieve the created default value for all users.",
        )
        self.assertEqual(
            IrDefault2._get_model_defaults("res.partner"),
            {"ref": "GLOBAL"},
            "Can't retrieve the created default value for all users.",
        )
        self.assertEqual(
            IrDefault3._get_model_defaults("res.partner"),
            {"ref": "GLOBAL"},
            "Can't retrieve the created default value for all users.",
        )

        IrDefault1.set("res.partner", "ref", "COMPANY", user_id=False, company_id=True)
        self.assertEqual(
            IrDefault1._get_model_defaults("res.partner"),
            {"ref": "COMPANY"},
            "Can't retrieve the created default value for company.",
        )
        self.assertEqual(
            IrDefault2._get_model_defaults("res.partner"),
            {"ref": "COMPANY"},
            "Can't retrieve the created default value for company.",
        )
        self.assertEqual(
            IrDefault3._get_model_defaults("res.partner"),
            {"ref": "GLOBAL"},
            "Unexpected default value for company.",
        )

        IrDefault2.set("res.partner", "ref", "USER", user_id=True, company_id=True)
        self.assertEqual(
            IrDefault1._get_model_defaults("res.partner"),
            {"ref": "COMPANY"},
            "Can't retrieve the created default value for user.",
        )
        self.assertEqual(
            IrDefault2._get_model_defaults("res.partner"),
            {"ref": "USER"},
            "Unexpected default value for user.",
        )
        self.assertEqual(
            IrDefault3._get_model_defaults("res.partner"),
            {"ref": "GLOBAL"},
            "Unexpected default value for company.",
        )

        default1 = IrDefault1.env["res.partner"].default_get(["ref"]).get("ref")
        self.assertEqual(default1, "COMPANY", "Wrong default value.")
        default2 = IrDefault2.env["res.partner"].default_get(["ref"]).get("ref")
        self.assertEqual(default2, "USER", "Wrong default value.")
        default3 = IrDefault3.env["res.partner"].default_get(["ref"]).get("ref")
        self.assertEqual(default3, "GLOBAL", "Wrong default value.")

    def test_conditions(self):
        IrDefault = self.env["ir.default"]

        IrDefault.search([("field_id.model", "=", "res.partner")]).unlink()
        IrDefault.set("res.partner", "ref", "X")
        self.assertEqual(IrDefault._get_model_defaults("res.partner"), {"ref": "X"})
        self.assertEqual(
            IrDefault._get_model_defaults("res.partner", condition="name=Agrolait"),
            {},
        )

        IrDefault.search([("field_id.model", "=", "res.partner")]).unlink()
        IrDefault.set("res.partner", "street", "X")
        IrDefault.set("res.partner", "street", "Mr", condition="name=Mister")
        self.assertEqual(IrDefault._get_model_defaults("res.partner"), {"street": "X"})
        self.assertEqual(
            IrDefault._get_model_defaults("res.partner", condition="name=Miss"),
            {},
        )
        self.assertEqual(
            IrDefault._get_model_defaults("res.partner", condition="name=Mister"),
            {"street": "Mr"},
        )

    def test_invalid(self):
        IrDefault = self.env["ir.default"]
        with self.assertRaises(ValidationError):
            IrDefault.set("unknown_model", "unknown_field", 42)
        with self.assertRaises(ValidationError):
            IrDefault.set("res.partner", "unknown_field", 42)
        with self.assertRaises(ValidationError):
            IrDefault.set("res.partner", "type", "invalid_type")
        with self.assertRaises(ValidationError):
            IrDefault.set("res.partner", "partner_latitude", "foo")
        with self.assertRaises(ValidationError):
            IrDefault.set("res.partner", "color", 2147483648)

    def test_removal(self):
        IrDefault = self.env["ir.default"]
        IrDefault.search([("field_id.model", "=", "res.partner")]).unlink()

        country_id = self.env["res.country"].create({"name": "country", "code": "ZZ"})
        IrDefault.set("res.partner", "country_id", country_id.id)
        self.assertEqual(
            IrDefault._get_model_defaults("res.partner"),
            {"country_id": country_id.id},
        )

        country_id.unlink()
        self.assertEqual(IrDefault._get_model_defaults("res.partner"), {})

    def test_multi_company_defaults(self):
        company_a = self.env["res.company"].create({"name": "C_A"})
        company_b = self.env["res.company"].create({"name": "C_B"})
        company_a_b = company_a + company_b
        company_b_a = company_b + company_a
        multi_company_user = self.env["res.users"].create(
            {
                "name": "u2",
                "login": "u2",
                "company_id": company_a.id,
                "company_ids": company_a_b.ids,
            }
        )
        IrDefault = self.env["ir.default"].with_user(multi_company_user)
        IrDefault.with_context(allowed_company_ids=company_a.ids).set(
            "res.partner", "ref", "CADefault", user_id=True, company_id=True
        )
        IrDefault.with_context(allowed_company_ids=company_b.ids).set(
            "res.partner", "ref", "CBDefault", user_id=True, company_id=True
        )
        self.assertEqual(
            IrDefault._get_model_defaults("res.partner")["ref"],
            "CADefault",
        )
        self.assertEqual(
            IrDefault.with_context(
                allowed_company_ids=company_a.ids
            )._get_model_defaults("res.partner")["ref"],
            "CADefault",
        )
        self.assertEqual(
            IrDefault.with_context(
                allowed_company_ids=company_b.ids
            )._get_model_defaults("res.partner")["ref"],
            "CBDefault",
        )
        self.assertEqual(
            IrDefault.with_context(
                allowed_company_ids=company_a_b.ids
            )._get_model_defaults("res.partner")["ref"],
            "CADefault",
        )
        self.assertEqual(
            IrDefault.with_context(
                allowed_company_ids=company_b_a.ids
            )._get_model_defaults("res.partner")["ref"],
            "CBDefault",
        )

    def test_json_format_invalid(self):
        IrDefault = self.env["ir.default"]
        field_id = self.env["ir.model.fields"].search(
            [("model", "=", "res.partner"), ("name", "=", "ref")]
        )
        with self.assertRaises(ValidationError):
            IrDefault.create(
                {
                    "field_id": field_id.id,
                    "json_value": '{"name":"John", }',
                }
            )
        color_field = self.env["ir.model.fields"].search(
            [("model", "=", "res.partner"), ("name", "=", "color")]
        )
        with self.assertRaises(ValidationError):
            IrDefault.create(
                {
                    "field_id": color_field.id,
                    "json_value": "2147483648",
                }
            )

    def test_json_format_rejects_a_field_outside_the_registry(self):
        self.env.cr.execute(
            'INSERT INTO ir_model (model, name, state, "order")'
            " VALUES ('x_ghost', %s, 'manual', 'id') RETURNING id",
            (Json({"en_US": "Ghost"}),),
        )
        [model_id] = self.env.cr.fetchone()
        self.env.cr.execute(
            "INSERT INTO ir_model_fields"
            " (model_id, model, name, field_description, ttype, state)"
            " VALUES (%s, 'x_ghost', 'x_ghostf', %s, 'char', 'manual') RETURNING id",
            (model_id, Json({"en_US": "Ghost field"})),
        )
        [field_id] = self.env.cr.fetchone()
        with self.assertRaises(ValidationError):
            self.env["ir.default"].create({"field_id": field_id, "json_value": '"x"'})

    def test_rename_value(self):
        IrDefault = self.env["ir.default"]
        IrDefault.search([("field_id.model", "=", "res.partner")]).unlink()

        IrDefault.set("res.partner", "ref", "OLD")
        IrDefault.rename_value("res.partner", "ref", "OLD", "NEW")
        self.assertEqual(IrDefault._get("res.partner", "ref"), "NEW")

        IrDefault.rename_value("res.partner", "ref", "NOPE", "OTHER")
        self.assertEqual(IrDefault._get("res.partner", "ref"), "NEW")

    def test_get(self):
        IrDefault = self.env["ir.default"]
        IrDefault.search([("field_id.model", "=", "res.partner")]).unlink()

        self.assertIsNone(IrDefault._get("res.partner", "ref"))

        IrDefault.set("res.partner", "ref", "GLOBAL")
        self.assertEqual(IrDefault._get("res.partner", "ref"), "GLOBAL")

        IrDefault.set("res.partner", "ref", "MINE", user_id=True, company_id=True)
        self.assertEqual(
            IrDefault._get("res.partner", "ref", user_id=True, company_id=True),
            "MINE",
        )
        self.assertEqual(
            IrDefault._get(
                "res.partner",
                "ref",
                user_id=self.env.uid,
                company_id=self.env.company.id,
            ),
            "MINE",
        )
        self.assertEqual(IrDefault._get("res.partner", "ref"), "GLOBAL")
        self.assertIsNone(
            IrDefault._get("res.partner", "ref", user_id=self.env.uid + 1000)
        )

    def test_discard_records(self):
        IrDefault = self.env["ir.default"]
        IrDefault.search([("field_id.model", "=", "res.partner")]).unlink()
        country = self.env["res.country"].create({"name": "ZZ-country", "code": "Z9"})
        IrDefault.set("res.partner", "country_id", country.id)
        self.assertEqual(
            IrDefault._get_model_defaults("res.partner"),
            {"country_id": country.id},
        )
        IrDefault.discard_records(country)
        self.assertEqual(IrDefault._get_model_defaults("res.partner"), {})

    def test_discard_values(self):
        IrDefault = self.env["ir.default"]
        IrDefault.search([("field_id.model", "=", "res.partner")]).unlink()

        IrDefault.set("res.partner", "ref", "DROP")
        IrDefault.discard_values("res.partner", "ref", ["OTHER", "DROP"])
        self.assertIsNone(IrDefault._get("res.partner", "ref"))

        IrDefault.set("res.partner", "ref", "KEEP")
        IrDefault.discard_values("res.partner", "ref", ["NOPE"])
        self.assertEqual(IrDefault._get("res.partner", "ref"), "KEEP")

    def test_set_datetime_value_coercion(self):
        IrDefault = self.env["ir.default"]
        IrDefault.set("ir.cron", "nextcall", datetime(2021, 5, 6, 7, 8, 9))
        self.assertEqual(IrDefault._get("ir.cron", "nextcall"), "2021-05-06 07:08:09")

    def test_set_skips_write_when_value_unchanged(self):
        IrDefault = self.env["ir.default"]
        IrDefault.search([("field_id.model", "=", "res.partner")]).unlink()
        IrDefault.set("res.partner", "ref", "SAME")

        with patch.object(type(IrDefault), "write", autospec=True) as mocked_write:
            IrDefault.set("res.partner", "ref", "SAME")
        self.assertEqual(
            mocked_write.call_count, 0, "an identical set() must not write"
        )

        IrDefault.set("res.partner", "ref", "CHANGED")
        self.assertEqual(IrDefault._get("res.partner", "ref"), "CHANGED")

    def test_set_checks_field_write_access(self):
        model_name, field_name = "ir.actions.server", "code"

        plain_user = new_test_user(
            self.env, login="ird_plain_user", groups="base.group_user"
        )
        with self.assertRaises(AccessError):
            self.env["ir.default"].with_user(plain_user).set(
                model_name, field_name, "record", user_id=True
            )

        system_user = new_test_user(
            self.env,
            login="ird_system_user",
            groups="base.group_user,base.group_system",
        )
        IrDefaultAsSystem = self.env["ir.default"].with_user(system_user)
        IrDefaultAsSystem.set(model_name, field_name, "record", user_id=True)
        self.assertEqual(
            IrDefaultAsSystem._get(model_name, field_name, user_id=True),
            "record",
        )

    def test_set_allows_writable_field_for_plain_user(self):
        plain_user = new_test_user(
            self.env, login="ird_writer", groups="base.group_user"
        )
        IrDefaultAsUser = self.env["ir.default"].with_user(plain_user)
        IrDefaultAsUser.set("res.partner", "comment", "hello", user_id=True)
        self.assertEqual(
            IrDefaultAsUser._get("res.partner", "comment", user_id=True), "hello"
        )
