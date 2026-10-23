# Copyright 2016 Serpent Consulting Services Pvt. Ltd. (support@serpentcs.com)
# Copyright 2018 Aitor Bouzas <aitor.bouzas@adaptivecity.com)
# Copyrithg 2020 Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from ast import literal_eval

import psycopg2

from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, common, new_test_user
from odoo.tools.misc import mute_logger

from odoo.addons.base.models.ir_actions import IrActionsServer


def fake_onchange_model_id(self):
    result = {
        "warning": {
            "title": "This is a fake onchange",
        },
    }
    return result


@common.tagged("-at_install", "post_install")
class TestMassEditing(common.TransactionCase):
    def setUp(self):
        super().setUp()

        self.MassEditingWizard = self.env["mass.editing.wizard"]
        self.ResPartnerTitle = self.env["res.partner.title"]
        self.ResPartner = self.env["res.partner"]
        self.ResLang = self.env["res.lang"]
        self.IrActionsActWindow = self.env["ir.actions.act_window"]

        self.mass_editing_user = self.env.ref(
            "server_action_mass_edit.mass_editing_user"
        )
        self.mass_editing_partner = self.env.ref(
            "server_action_mass_edit.mass_editing_partner"
        )
        self.mass_editing_partner_title = self.env.ref(
            "server_action_mass_edit.mass_editing_partner_title"
        )
        user_admin = self.env.ref("base.user_admin")
        user_demo = self.env.ref("base.user_demo")
        self.users = self.env["res.users"].search(
            [("id", "not in", (user_admin.id, user_demo.id))]
        )
        self.user = new_test_user(
            self.env,
            login="test-mass_editing-user",
            groups="base.group_system",
        )
        self.partner_title = self._create_partner_title()
        self.invoice_partner = self._create_invoice_partner()

    def _create_partner_title(self):
        """Create a Partner Title."""
        # Loads German to work with translations
        self.ResLang._activate_lang("de_DE")
        # Creating the title in English
        partner_title = self.ResPartnerTitle.create(
            {"name": "Ambassador", "shortcut": "Amb."}
        )
        # Adding translated terms
        partner_title.with_context(lang="de_DE").write(
            {"name": "Botschafter", "shortcut": "Bots."}
        )
        return partner_title

    def _create_invoice_partner(self):
        invoice_partner = self.ResPartner.create(
            {
                "type": "invoice",
            }
        )
        return invoice_partner

    def _create_wizard_and_apply_values(self, server_action, items, vals):
        action = server_action.with_context(
            active_model=items._name,
            active_ids=items.ids,
        ).run()
        wizard = (
            self.env[action["res_model"]]
            .with_context(
                **literal_eval(action["context"]),
            )
            .create(vals)
        )
        wizard.button_apply()
        return wizard

    def test_wzd_default_get(self):
        """Test whether `operation_description_danger` is correct"""
        wzd_obj = self.MassEditingWizard.with_context(
            server_action_id=self.mass_editing_user.id,
            active_ids=[1],
            original_active_ids=[1],
        )
        result = wzd_obj.default_get(
            fields=[],
        )
        self.assertEqual(
            result["operation_description_info"],
            "The treatment will be processed on the 1 selected record(s).",
        )
        self.assertFalse(
            result["operation_description_warning"],
        )
        self.assertFalse(
            result["operation_description_danger"],
        )

        result = wzd_obj.with_context(active_ids=[]).default_get(
            fields=[],
        )
        self.assertFalse(
            result["operation_description_info"],
        )
        self.assertEqual(
            result["operation_description_warning"],
            (
                "You have selected 1 record(s) that can not be processed.\n"
                "Only 0 record(s) will be processed."
            ),
        )
        self.assertFalse(
            result["operation_description_danger"],
        )

        result = wzd_obj.with_context(original_active_ids=[]).default_get(
            fields=[],
        )
        self.assertFalse(
            result["operation_description_info"],
        )
        self.assertFalse(
            result["operation_description_warning"],
        )
        self.assertEqual(
            result["operation_description_danger"],
            "None of the 1 record(s) you have selected can be processed.",
        )

    def test_wiz_fields_view_get(self):
        """Test whether fields_view_get method returns arch.
        with dynamic fields.
        """
        result = self.MassEditingWizard.with_context(
            active_ids=[],
        ).get_view()
        arch = result.get("arch", "")
        self.assertTrue(
            "selection__email" not in arch,
            "Fields view get must return architecture w/o fields" "created dynamicaly",
        )

        result = self.MassEditingWizard.with_context(
            server_action_id=self.mass_editing_user.id,
            active_ids=[],
        ).get_view()
        arch = result.get("arch", "")
        self.assertTrue(
            "selection__email" in arch,
            "Fields view get must return architecture with fields" "created dynamicaly",
        )

        # test the code path where we extract an embedded tree for o2m fields
        self.env["ir.ui.view"].search(
            [
                ("model", "in", ("res.partner.bank", "res.partner", "res.users")),
                ("id", "!=", self.env.ref("base.res_partner_view_form_private").id),
            ]
        ).unlink()
        self.env.ref("base.res_partner_view_form_private").model = "res.users"
        result = self.MassEditingWizard.with_context(
            server_action_id=self.mass_editing_user.id,
            active_ids=[],
        ).get_view()
        arch = result.get("arch", "")
        self.assertIn(
            "<tree editable=",
            arch,
            "Fields view get must return architecture with embedded tree",
        )

    def test_wzd_clean_check_company_field_domain(self):
        """
        Test company field domain replacement
        """
        model_name = "res.partner"
        field_domain = [
            ("model", "=", model_name),
            ("name", "=", "company_id"),
        ]
        field = self.env["ir.model.fields"].search(
            field_domain,
        )
        field_info = {
            "name": "company_id",
        }
        result = self.MassEditingWizard._clean_check_company_field_domain(
            self.env[model_name],
            field=field,
            field_info=field_info,
        )
        self.assertDictEqual(
            result,
            field_info,
        )

        model_name = "res.partner"
        field_name = "parent_id"
        field_domain = [
            ("model", "=", model_name),
            ("name", "=", field_name),
        ]
        field = self.env["ir.model.fields"].search(
            field_domain,
        )
        field_info = {
            "name": field_name,
        }
        model = self.env[model_name]
        model._fields[field_name].check_company = True
        result = self.MassEditingWizard._clean_check_company_field_domain(
            model,
            field=field,
            field_info=field_info,
        )
        self.assertEqual(
            result.get("domain"),
            "[]",
        )

    def test_wiz_read_fields(self):
        """Test whether read method returns all fields or not."""
        fields = self.MassEditingWizard.with_context(
            server_action_id=self.mass_editing_user.id,
            active_ids=[],
        ).fields_get()
        fields = list(fields.keys())
        # add a real field
        fields.append("display_name")
        vals = {"selection__email": "remove", "selection__phone": "remove"}
        mass_wizard = self._create_wizard_and_apply_values(
            self.mass_editing_user, self.users, vals
        )
        result = mass_wizard.read(fields)[0]
        self.assertTrue(
            all([field in result for field in fields]), "Read must return all fields."
        )

        result = mass_wizard.read(fields=[])[0]
        self.assertTrue(
            "selection__email" not in result,
        )

    def test_mass_edit_partner_title(self):
        """Test Case for MASS EDITING which will check if translation
        was loaded for new partner title, and if they are removed
        as well as the value for the abbreviation for the partner title."""
        self.assertEqual(
            self.partner_title.with_context(lang="de_DE").shortcut,
            "Bots.",
            "Translation for Partner Title's Abbreviation " "was not loaded properly.",
        )
        # Removing partner title with mass edit action
        vals = {"selection__shortcut": "remove"}
        self._create_wizard_and_apply_values(
            self.mass_editing_partner_title, self.partner_title, vals
        )
        self.assertEqual(
            self.partner_title.shortcut,
            False,
            "Partner Title's Abbreviation should be removed.",
        )
        # Checking if translations were also removed
        self.assertEqual(
            self.partner_title.with_context(lang="de_DE").shortcut,
            False,
            "Translation for Partner Title's Abbreviation " "was not removed properly.",
        )

    def test_mass_edit_email(self):
        """Test Case for MASS EDITING which will remove and after add
        User's email and will assert the same."""
        # Remove email and phone
        vals = {"selection__email": "remove", "selection__phone": "remove"}
        self._create_wizard_and_apply_values(self.mass_editing_user, self.user, vals)
        self.assertEqual(self.user.email, False, "User's Email should be removed.")
        # Set email address
        vals = {"selection__email": "set", "email": "sample@mycompany.com"}
        self._create_wizard_and_apply_values(self.mass_editing_user, self.user, vals)
        self.assertNotEqual(self.user.email, False, "User's Email should be set.")

    def test_mass_edit_o2m_banks(self):
        """Test Case for MASS EDITING which will remove and add
        Partner's bank o2m."""
        # Set another bank (must replace existing one)
        bank_vals = {"acc_number": "account number"}
        self.user.write(
            {
                "bank_ids": [(6, 0, []), (0, 0, bank_vals)],
            }
        )
        vals = {
            "selection__bank_ids": "set_o2m",
            "bank_ids": [(0, 0, dict(bank_vals, acc_number="new number"))],
        }
        self._create_wizard_and_apply_values(self.mass_editing_user, self.user, vals)
        self.assertEqual(self.user.bank_ids.acc_number, "new number")
        # Add bank (must keep existing one)
        vals = {
            "selection__bank_ids": "add_o2m",
            "bank_ids": [(0, 0, dict(bank_vals, acc_number="new number2"))],
        }
        self._create_wizard_and_apply_values(self.mass_editing_user, self.user, vals)
        self.assertEqual(
            self.user.bank_ids.mapped("acc_number"), ["new number", "new number2"]
        )
        # Set empty list (must remove all banks)
        vals = {"selection__bank_ids": "set_o2m"}
        self._create_wizard_and_apply_values(self.mass_editing_user, self.user, vals)
        self.assertFalse(self.user.bank_ids)

    def test_mass_edit_m2m_categ(self):
        """Test Case for MASS EDITING which will remove and add
        Partner's category m2m."""
        # Remove m2m categories
        vals = {"selection__category_id": "remove_m2m"}
        self._create_wizard_and_apply_values(self.mass_editing_user, self.user, vals)
        self.assertNotEqual(
            self.user.category_id, False, "User's category should be removed."
        )
        # Add m2m categories
        dist_categ_id = self.env.ref("base.res_partner_category_14").id
        vend_categ_id = self.env.ref("base.res_partner_category_0").id
        vals = {
            "selection__category_id": "add",
            "category_id": [[6, 0, [dist_categ_id, vend_categ_id]]],
        }
        self._create_wizard_and_apply_values(self.mass_editing_user, self.user, vals)
        self.assertTrue(
            all(
                item in self.user.category_id.ids
                for item in [dist_categ_id, vend_categ_id]
            ),
            "Partner's category should be added.",
        )
        # Remove one m2m category
        vals = {
            "selection__category_id": "remove_m2m",
            "category_id": [[6, 0, [vend_categ_id]]],
        }
        self._create_wizard_and_apply_values(self.mass_editing_user, self.user, vals)
        self.assertTrue(
            [dist_categ_id] == self.user.category_id.ids,
            "User's category should be removed.",
        )

    def test_check_field_model_constraint(self):
        """Test that it's not possible to create inconsistent mass edit actions"""
        with self.assertRaises(ValidationError):
            self.mass_editing_user.write(
                {"model_id": self.env.ref("base.model_res_country").id}
            )

    def test_onchanges(self):
        """Test that form onchanges do what they're supposed to"""
        # Test change on server_action.model_id : clear mass_edit_line_ids
        server_action_form = Form(self.mass_editing_user)
        self.assertGreater(
            len(server_action_form.mass_edit_line_ids),
            0,
            "Mass Editing User demo data should have lines",
        )
        server_action_form.model_id = self.env.ref("base.model_res_country")
        self.assertEqual(
            len(server_action_form.mass_edit_line_ids),
            0,
            "Mass edit lines should be removed when changing model",
        )
        # Test change on mass_edit_line field_id : set widget_option
        mass_edit_line_form = Form(
            self.env.ref("server_action_mass_edit.mass_editing_user_line_1")
        )
        mass_edit_line_form.field_id = self.env.ref(
            "base.field_res_partner__category_id"
        )
        self.assertEqual(mass_edit_line_form.widget_option, "many2many_tags")
        mass_edit_line_form.field_id = self.env.ref(
            "base.field_res_partner__image_1920"
        )
        self.assertEqual(mass_edit_line_form.widget_option, "image")
        mass_edit_line_form.field_id = self.env.ref("base.field_res_company__logo")
        self.assertEqual(mass_edit_line_form.widget_option, "image")
        # binary
        mass_edit_line_form.field_id = self.env.ref("base.field_res_company__favicon")
        self.assertEqual(mass_edit_line_form.widget_option, False)

        mass_edit_line_form.field_id = self.env.ref("base.field_res_users__country_id")
        self.assertFalse(mass_edit_line_form.widget_option)

    def test_onchange_model_id(self):
        """Test super call of `_onchange_model_id`"""

        IrActionsServer._onchange_model_id = fake_onchange_model_id
        result = self.env["ir.actions.server"]._onchange_model_id()
        self.assertEqual(
            result,
            fake_onchange_model_id(self),
        )

        del IrActionsServer._onchange_model_id
        result = self.env["ir.actions.server"]._onchange_model_id()
        self.assertEqual(
            result,
            None,
        )

    def test_mass_edit_partner_user_error(self):
        vals = {
            "selection__parent_id": "set",
            "parent_id": self.invoice_partner.id,
            "write_record_by_record": True,
        }
        action = self.mass_editing_partner.with_context(
            active_model=self.invoice_partner._name,
            active_ids=self.invoice_partner.ids,
        ).run()
        try:
            self.env[action["res_model"]].with_context(
                **literal_eval(action["context"]),
            ).create(vals)
        except Exception as e:
            self.assertEqual(type(e), UserError)

    def test_mass_edit_partner_sql_error(self):
        vals = {
            "selection__type": "set",
            "type": "contact",
            "write_record_by_record": True,
            "selection__name": "remove",
        }
        action = self.mass_editing_partner.with_context(
            active_model=self.invoice_partner._name,
            active_ids=self.invoice_partner.ids,
        ).run()
        with self.assertRaises(psycopg2.IntegrityError):
            with mute_logger("odoo.sql_db"), self.cr.savepoint():
                self.env[action["res_model"]].with_context(
                    **literal_eval(action["context"]),
                ).create(vals)
