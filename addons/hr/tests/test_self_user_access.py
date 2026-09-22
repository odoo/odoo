from collections import OrderedDict
from itertools import chain

from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import Form, new_test_user, tagged

from odoo.addons.hr.models.res_users import HR_READABLE_FIELDS
from odoo.addons.hr.tests.common import TestHrCommon


@tagged("post_install", "-at_install")
class TestSelfAccessPreferences(TestHrCommon):
    def test_access_preferences_view(self):
        james = new_test_user(
            self.env,
            login="hel",
            groups="base.group_user",
            name="Simple employee",
            email="ric@example.com",
        )
        james = james.with_user(james)
        james_bank_account = self.env["res.partner.bank.account"].create(
            {"acc_number": "BE1234567890", "partner_id": james.partner_id.id}
        )
        self.env["hr.employee"].create(
            {
                "name": "James",
                "user_id": james.id,
                "salary_bank_account_ids": [Command.link(james_bank_account.id)],
            }
        )
        view = self.env.ref("hr.res_users_view_form_preferences")
        view_infos = james.get_view(view.id)
        fields = [
            el.get("name")
            for el in etree.fromstring(view_infos["arch"]).xpath(
                "//field[not(ancestor::field)]"
            )
        ]
        james.read(fields)

    def test_preferences_view_fields(self):
        view = self.env.ref("hr.res_users_view_form_preferences")

        all_groups_xml_ids = chain(
            *[
                field.groups.split(",")
                for field in self.env["res.users"]._fields.values()
                if field.groups
                if field.groups != "."
            ]
        )
        all_groups = self.env["res.groups"]
        for xml_id in all_groups_xml_ids:
            all_groups |= self.env.ref(xml_id.strip())
        user_all_groups = new_test_user(
            self.env, groups="base.group_user", login="hel", name="God"
        )
        user_all_groups.write(
            {"group_ids": [(4, group.id, False) for group in all_groups]}
        )
        view_infos = self.env["res.users"].with_user(user_all_groups).get_view(view.id)
        full_fields = [
            el.get("name")
            for el in etree.fromstring(view_infos["arch"]).xpath(
                "//field[not(ancestor::field)]"
            )
        ]

        user = new_test_user(self.env, login="gro", name="Grouillot")
        view_infos = self.env["res.users"].with_user(user).get_view(view.id)
        fields = [
            el.get("name")
            for el in etree.fromstring(view_infos["arch"]).xpath(
                "//field[not(ancestor::field)]"
            )
        ]

        self.assertEqual(
            full_fields, fields, "View fields should not depend on user's groups"
        )

    def test_access_preferences_view_toolbar(self):
        james = new_test_user(
            self.env,
            login="jam",
            groups="base.group_user",
            name="Simple employee",
            email="jam@example.com",
        )
        james = james.with_user(james)
        self.env["hr.employee"].create(
            {
                "name": "James",
                "user_id": james.id,
            }
        )
        view = self.env.ref("hr.res_users_view_form_preferences")
        available_actions = james.get_views([(view.id, "form")], {"toolbar": True})[
            "views"
        ]["form"]["toolbar"].get("action", {})
        change_password_action = self.env.ref("base.change_password_wizard_action")

        self.assertFalse(
            any(x["id"] == change_password_action.id for x in available_actions)
        )

        john = new_test_user(
            self.env,
            login="joh",
            groups="base.group_erp_manager",
            name="ERP Manager",
            email="joh@example.com",
        )
        john = john.with_user(john)
        self.env["hr.employee"].create(
            {
                "name": "John",
                "user_id": john.id,
            }
        )
        view = self.env.ref("hr.res_users_view_form_preferences")
        available_actions = john.get_views([(view.id, "form")], {"toolbar": True})[
            "views"
        ]["form"]["toolbar"]["action"]
        self.assertTrue(
            any(x["id"] == change_password_action.id for x in available_actions)
        )

    def test_employee_fields_groups(self):
        internal_user = new_test_user(
            self.env,
            login="mireille",
            groups="base.group_user",
            name="Mireille",
            email="mireille@example.com",
        )
        self.env["hr.employee"].with_user(internal_user).search([]).read([])

    def test_open_preferences_with_group_without_external_id(self):
        self.env["hr.employee"].create(
            {
                "name": "John",
                "user_id": self.env.user.id,
            }
        )
        group = self.env["res.groups"].create(
            {
                "name": "Test Group",
            }
        )
        self.env.user.group_ids = [Command.link(group.id)]
        action = self.env.user.action_get()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["display_name"], "Change my Preferences")


class TestSelfAccessRights(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.richard = new_test_user(
            cls.env,
            login="ric",
            groups="base.group_user",
            name="Simple employee",
            email="ric@example.com",
        )
        cls.richard_emp = cls.env["hr.employee"].create(
            {
                "name": "Richard",
                "user_id": cls.richard.id,
                "private_phone_ids": [
                    Command.create({"number": "21454", "type": "landline"})
                ],
            }
        )
        cls.hubert = new_test_user(
            cls.env,
            login="hub",
            groups="base.group_user",
            name="Simple employee",
            email="hub@example.com",
        )
        cls.hubert_emp = cls.env["hr.employee"].create(
            {
                "name": "Hubert",
                "user_id": cls.hubert.id,
            }
        )

        cls.protected_fields_emp = OrderedDict(
            [
                (k, v)
                for k, v in cls.env["hr.employee"]._fields.items()
                if v.groups == "hr.group_hr_user"
            ]
        )
        cls.read_protected_fields_emp = OrderedDict(
            [
                (k, v)
                for k, v in cls.env["hr.employee"]._fields.items()
                if not v.compute and k != "id"
            ]
        )
        cls.self_protected_fields_user = OrderedDict(
            [
                (k, v)
                for k, v in cls.env["res.users"]._fields.items()
                if v.groups == "hr.group_hr_user"
                and k in cls.env["res.users"].SELF_READABLE_FIELDS
            ]
        )

    def testReadSelfEmployee(self):
        with self.assertRaises(AccessError):
            self.hubert_emp.with_user(self.richard).read(
                self.protected_fields_emp.keys()
            )

    def testReadOtherEmployee(self):
        with self.assertRaises(AccessError):
            self.hubert_emp.with_user(self.richard).read(
                self.protected_fields_emp.keys()
            )
        public_fields = list(
            self.env["hr.employee"].with_user(self.richard).fields_get()
        )
        res = self.hubert_emp.with_user(self.richard).read(public_fields)
        self.assertEqual(len(public_fields), len(res[0]))

    def testWriteSelfEmployee(self):
        for f in self.protected_fields_emp:
            with self.assertRaises(AccessError):
                self.richard_emp.with_user(self.richard).write({f: "dummy"})

    def testWriteOtherEmployee(self):
        for f in self.protected_fields_emp:
            with self.assertRaises(AccessError):
                self.hubert_emp.with_user(self.richard).write({f: "dummy"})

    def testReadSelfUserEmployee(self):
        for f in self.self_protected_fields_user:
            self.richard.with_user(self.richard).read([f])

    def testReadOtherUserEmployee(self):
        with self.assertRaises(AccessError):
            self.hubert.with_user(self.richard).read(self.self_protected_fields_user)

    def testWriteSelfUserEmployee(self):
        """Decided 2026-09-07: a user does not edit their own HR information.

        This wrote each of these fields on oneself and expected it to land.
        Reading them is untouched -- testReadSelfUserEmployee still passes.
        """
        for f, v in self.self_protected_fields_user.items():
            val = None
            if v.type in {"char", "text"}:
                val = "0000" if f in ["pin", "barcode"] else "dummy"
            if val is not None:
                with self.subTest(field=f), self.assertRaises(AccessError):
                    self.richard.with_user(self.richard).write({f: val})

    def testWriteOtherUserEmployee(self):
        for f in self.self_protected_fields_user:
            with self.assertRaises(AccessError):
                self.hubert.with_user(self.richard).write({f: "dummy"})

    def testSearchUserEMployee(self):
        self.env["res.users"].with_user(self.richard).search(
            [("employee_id", "ilike", "Hubert")]
        )

    def testWriteDepartmentEmployee(self):
        with self.assertRaises(AccessError):
            self.env["hr.department"].with_user(self.richard).create(
                {"name": "New Dept"}
            )
        dept = self.env["hr.department"].create({"name": "New Dept"})
        with self.assertRaises(AccessError):
            dept.with_user(self.richard).write({"name": "Renamed Dept"})

    def test_onchange_readable_fields_with_no_access(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        with Form(
            self.richard.with_user(self.richard),
            view="hr.res_users_view_form_preferences",
        ) as form:
            form.lang = "fr_FR"
            form.tz = "Europe/Brussels"

    def test_access_employee_account(self):
        hubert = new_test_user(
            self.env,
            login="hubert",
            groups="base.group_user",
            name="Hubert Bonisseur de La Bath",
            email="hubert@oss.fr",
        )
        hubert = hubert.with_user(hubert)
        hubert_acc = self.env["res.partner.bank.account"].create(
            {"acc_number": "FR1234567890", "partner_id": hubert.partner_id.id}
        )
        hubert_emp = self.env["hr.employee"].create(
            {
                "name": "Hubert",
                "user_id": hubert.id,
                "salary_bank_account_ids": [Command.link(hubert_acc.id)],
            }
        )
        hubert.partner_id.sudo().employee_ids = hubert_emp

        self.assertFalse(hubert.env.user.has_group("hr.group_hr_user"))
        self.assertFalse(hubert.env.su)
        self.assertEqual(
            hubert.sudo().salary_bank_account_ids.display_name, "FR******7890"
        )
        self.assertEqual(
            hubert_emp.with_user(hubert).sudo().salary_bank_account_ids.display_name,
            "FR******7890",
        )

        hubert_acc.invalidate_recordset(["display_name"])
        self.assertEqual(
            hubert_emp.with_user(hubert)
            .sudo()
            .salary_bank_account_ids.sudo(False)
            .display_name,
            "FR******7890",
        )


@tagged("post_install", "-at_install")
class TestSelfWritableFieldsAreWritable(TestHrCommon):
    def test_every_self_writable_field_can_actually_be_written(self):
        users = self.env["res.users"]
        unwritable = [
            fname
            for fname in users.SELF_WRITEABLE_FIELDS
            if (field := users._fields.get(fname)) and field.readonly
        ]
        self.assertFalse(
            unwritable,
            "SELF_WRITEABLE_FIELDS grants a write on fields that are readonly, "
            "so the write is silently dropped rather than refused: "
            f"{unwritable}",
        )

    def test_hr_grants_no_self_write_at_all(self):
        """Decided 2026-09-07: an internal user does not edit their own HR data.

        This class used to assert the opposite -- that a self-write of
        `private_street` reached the employee. It did, and that was the
        behaviour withdrawn: personal facts now change through
        hr.employee.change.request, with an HR user approving.
        """
        users = self.env["res.users"]
        self.assertFalse(
            set(HR_READABLE_FIELDS) & set(users.SELF_WRITEABLE_FIELDS),
            "hr contributes a self-writable field again",
        )

    def test_a_user_cannot_edit_their_own_personal_information(self):
        user = new_test_user(
            self.env, login="selfwrite", groups="base.group_user", name="Self Writer"
        )
        employee = self.env["hr.employee"].create(
            {"name": "Self Writer", "user_id": user.id, "private_street": "Seeded 1"}
        )
        as_self = user.with_user(user)
        for fname, value in (
            ("private_street", "Own Street 1"),
            ("private_email", "me@home.test"),
            ("emergency_contact", "Someone"),
            ("pin", "4321"),
        ):
            with self.subTest(field=fname), self.assertRaises(AccessError):
                as_self.write({fname: value})
        employee.invalidate_recordset(["private_street"])
        self.assertEqual(employee.private_street, "Seeded 1")

    def test_a_user_still_reads_their_own_personal_information(self):
        user = new_test_user(
            self.env, login="selfread", groups="base.group_user", name="Self Reader"
        )
        self.env["hr.employee"].create(
            {"name": "Self Reader", "user_id": user.id, "private_street": "Seeded 2"}
        )
        as_self = user.with_user(user)
        self.assertEqual(
            as_self.read(["private_street"])[0]["private_street"], "Seeded 2"
        )
