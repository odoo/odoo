from datetime import date
from unittest.mock import patch

import requests
from markupsafe import Markup
from psycopg import IntegrityError

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.libs.json import OPT_SORT_KEYS
from odoo.libs.json import dumps as json_dumps
from odoo.service.transaction import _integrity_error_to_validation_error
from odoo.tests import common, tagged
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo


class TestServerActionsBase(TransactionCaseWithUserDemo):
    def setUp(self):
        super().setUp()

        self.test_country = self.env["res.country"].create(
            {
                "name": "TestingCountry",
                "code": "TY",
                "address_format": "SuperFormat",
                "name_position": "before",
            }
        )
        self.test_partner = self.env["res.partner"].create(
            {
                "city": "OrigCity",
                "country_id": self.test_country.id,
                "email": "test.partner@test.example.com",
                "name": "TestingPartner",
            }
        )
        self.context = {
            "active_model": "res.partner",
            "active_id": self.test_partner.id,
        }

        Model = self.env["ir.model"]
        Fields = self.env["ir.model.fields"]
        self.comment_html = "<p>MyComment</p>"
        self.res_partner_model = Model.search([("model", "=", "res.partner")])
        self.res_partner_name_field = Fields.search(
            [("model", "=", "res.partner"), ("name", "=", "name")]
        )
        self.res_partner_city_field = Fields.search(
            [("model", "=", "res.partner"), ("name", "=", "city")]
        )
        self.res_partner_country_field = Fields.search(
            [("model", "=", "res.partner"), ("name", "=", "country_id")]
        )
        self.res_partner_parent_field = Fields.search(
            [("model", "=", "res.partner"), ("name", "=", "parent_id")]
        )
        self.res_partner_children_field = Fields.search(
            [("model", "=", "res.partner"), ("name", "=", "child_ids")]
        )
        self.res_partner_tag_field = Fields.search(
            [("model", "=", "res.partner"), ("name", "=", "tag_ids")]
        )
        self.res_country_model = Model.search([("model", "=", "res.country")])
        self.res_country_name_field = Fields.search(
            [("model", "=", "res.country"), ("name", "=", "name")]
        )
        self.res_country_code_field = Fields.search(
            [("model", "=", "res.country"), ("name", "=", "code")]
        )
        self.res_country_name_position_field = Fields.search(
            [("model", "=", "res.country"), ("name", "=", "name_position")]
        )
        self.res_partner_tag_model = Model.search([("model", "=", "res.partner.tag")])
        self.res_partner_tag_name_field = Fields.search(
            [("model", "=", "res.partner.tag"), ("name", "=", "name")]
        )

        self.action = self.env["ir.actions.server"].create(
            {
                "name": "TestAction",
                "model_id": self.res_partner_model.id,
                "model_name": "res.partner",
                "state": "code",
                "code": 'record.write({"comment": "%s"})' % self.comment_html,
            }
        )

        server_action_model = Model.search([("model", "=", "ir.actions.server")])
        self.test_server_action = self.env["ir.actions.server"].create(
            {
                "name": "TestDummyServerAction",
                "model_id": server_action_model.id,
                "state": "code",
                "code": """
_logger.log(10, "This is a %s debug %s", "test", "log")
_logger.info("This is a %s info %s", "test", "log")
_logger.warning("This is a %s warning %s", "test", "log")
_logger.error("This is a %s error %s", "test", "log")
try:
    0/0
except:
    _logger.exception("This is a %s exception %s", "test", "log")
""",
            }
        )


class TestServerActions(TestServerActionsBase):
    def test_00_server_action(self):
        with self.assertLogs(
            "odoo.addons.base.models.ir_actions.server_action_safe_eval",
            level="DEBUG",
        ) as log_catcher:
            self.test_server_action.run()
            self.assertEqual(
                log_catcher.output,
                [
                    "DEBUG:odoo.addons.base.models.ir_actions.server_action_safe_eval:This is a test debug log",
                    "INFO:odoo.addons.base.models.ir_actions.server_action_safe_eval:This is a test info log",
                    "WARNING:odoo.addons.base.models.ir_actions.server_action_safe_eval:This is a test warning log",
                    "ERROR:odoo.addons.base.models.ir_actions.server_action_safe_eval:This is a test error log",
                    """ERROR:odoo.addons.base.models.ir_actions.server_action_safe_eval:This is a test exception log
Traceback (most recent call last):
  File "ir.actions.server(%d,)", line 6, in <module>
ZeroDivisionError: division by zero"""
                    % self.test_server_action.id,
                ],
            )

    def test_00_action(self):
        self.action.with_context(self.context).run()
        self.assertEqual(
            self.test_partner.comment,
            self.comment_html,
            "ir_actions_server: invalid condition check",
        )
        self.test_partner.write({"comment": False})

        self.action.create_action()
        self.assertEqual(self.action.binding_model_id.model, "res.partner")

        self.action.unlink_action()
        self.assertFalse(self.action.binding_model_id)

    def test_10_code(self):
        self.action.write(
            {
                "state": "code",
                "code": (
                    "partner_name = record.name + '_code'\nrecord.env['res.partner'].create({'name': partner_name})"
                ),
            }
        )
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: code server action correctly finished should return False",
        )

        partners = self.test_partner.search([("name", "ilike", "TestingPartner_code")])
        self.assertEqual(
            len(partners),
            1,
            "ir_actions_server: 1 new partner should have been created",
        )

    def test_20_crud_create(self):
        self.action.write(
            {
                "state": "object_create",
                "crud_model_id": self.res_partner_model.id,
                "link_field_id": False,
                "value": "TestingPartner2",
            }
        )
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: create record action correctly finished should return False",
        )
        partner = self.test_partner.search([("name", "ilike", "TestingPartner2")])
        self.assertEqual(len(partner), 1, "ir_actions_server: TODO")

    def test_20_crud_create_link_many2one(self):

        self.action.write(
            {
                "state": "object_create",
                "crud_model_id": self.res_partner_model.id,
                "link_field_id": self.res_partner_parent_field.id,
                "value": "TestNew",
            }
        )
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: create record action correctly finished should return False",
        )
        partner = self.test_partner.search([("name", "ilike", "TestNew")])
        self.assertEqual(len(partner), 1, "ir_actions_server: TODO")
        self.assertEqual(
            self.test_partner.parent_id, partner, "ir_actions_server: TODO"
        )

    def test_20_crud_create_link_one2many(self):

        self.action.write(
            {
                "state": "object_create",
                "crud_model_id": self.res_partner_model.id,
                "link_field_id": self.res_partner_children_field.id,
                "value": "TestNew",
            }
        )
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: create record action correctly finished should return False",
        )
        partner = self.test_partner.search([("name", "ilike", "TestNew")])
        self.assertEqual(len(partner), 1, "ir_actions_server: TODO")
        self.assertEqual(partner.name, "TestNew", "ir_actions_server: TODO")
        self.assertIn(partner, self.test_partner.child_ids, "ir_actions_server: TODO")

    def test_20_crud_create_link_many2many(self):
        self.action.write(
            {
                "state": "object_create",
                "crud_model_id": self.res_partner_tag_model.id,
                "link_field_id": self.res_partner_tag_field.id,
                "value": "TestingPartner",
            }
        )
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: create record action correctly finished should return False",
        )
        category = self.env["res.partner.tag"].search(
            [("name", "ilike", "TestingPartner")]
        )
        self.assertEqual(len(category), 1, "ir_actions_server: TODO")
        self.assertIn(category, self.test_partner.tag_ids)

    def test_25_crud_copy(self):
        self.action.write(
            {
                "state": "object_copy",
                "crud_model_id": self.res_partner_model.id,
                "resource_ref": self.test_partner,
            }
        )
        partner = self.env["res.partner"].search(
            [("name", "ilike", self.test_partner.name)]
        )
        self.assertEqual(len(partner), 1)
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: duplicate record action correctly finished should return False",
        )
        partner = self.env["res.partner"].search(
            [("name", "ilike", self.test_partner.name)]
        )
        self.assertEqual(len(partner), 2)

    def test_25_crud_copy_link_many2one(self):
        self.action.write(
            {
                "state": "object_copy",
                "crud_model_id": self.res_partner_model.id,
                "resource_ref": self.test_partner,
                "link_field_id": self.res_partner_parent_field.id,
            }
        )
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: duplicate record action correctly finished should return False",
        )
        dupe = self.test_partner.search(
            [
                ("name", "ilike", self.test_partner.name),
                ("id", "!=", self.test_partner.id),
            ]
        )
        self.assertEqual(len(dupe), 1)
        self.assertEqual(self.test_partner.parent_id, dupe)

    def test_25_crud_copy_link_one2many(self):
        self.action.write(
            {
                "state": "object_copy",
                "crud_model_id": self.res_partner_model.id,
                "resource_ref": self.test_partner,
                "link_field_id": self.res_partner_children_field.id,
            }
        )
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: duplicate record action correctly finished should return False",
        )
        dupe = self.test_partner.search(
            [
                ("name", "ilike", self.test_partner.name),
                ("id", "!=", self.test_partner.id),
            ]
        )
        self.assertEqual(len(dupe), 1)
        self.assertIn(dupe, self.test_partner.child_ids)

    def test_25_crud_copy_link_many2many(self):
        tag_id = self.env["res.partner.tag"].name_create("CategoryToDuplicate")[0]
        self.action.write(
            {
                "state": "object_copy",
                "crud_model_id": self.res_partner_tag_model.id,
                "link_field_id": self.res_partner_tag_field.id,
                "resource_ref": f"res.partner.tag,{tag_id}",
            }
        )
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: duplicate record action correctly finished should return False",
        )
        dupe = self.env["res.partner.tag"].search(
            [
                ("name", "ilike", "CategoryToDuplicate"),
                ("id", "!=", tag_id),
            ]
        )
        self.assertEqual(len(dupe), 1)
        self.assertIn(dupe, self.test_partner.tag_ids)

    def test_30_crud_write(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "name",
                "value": "TestNew",
            }
        )
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: create record action correctly finished should return False",
        )
        partner = self.test_partner.search([("name", "ilike", "TestNew")])
        self.assertEqual(len(partner), 1, "ir_actions_server: TODO")
        self.assertEqual(partner.city, "OrigCity", "ir_actions_server: TODO")

    def test_31_crud_write_html(self):
        self.assertEqual(self.action.value, False)
        self.action.write(
            {
                "state": "object_write",
                "update_path": "comment",
                "html_value": "<p>MyComment</p>",
            }
        )
        self.assertEqual(self.action.html_value, Markup("<p>MyComment</p>"))
        self.assertEqual(self.test_partner.comment, False)
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: create record action correctly finished should return False",
        )
        self.assertEqual(self.test_partner.comment, Markup("<p>MyComment</p>"))

    def test_object_write_equation(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "city",
                "evaluation_type": "equation",
                "value": "record.id",
            }
        )
        partners = self.test_partner + self.test_partner.copy()
        self.action.with_context(self.context, active_ids=partners.ids).run()
        self.assertEqual(partners[0].city, str(partners[0].id))
        self.assertEqual(partners[1].city, str(partners[1].id))

    def test_object_write_ignores_ids_of_another_model(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "city",
                "evaluation_type": "value",
                "value": "Elsewhere",
            }
        )
        self.test_partner.city = "OrigCity"
        self.action.with_context(
            active_model="res.users",
            active_id=self.test_partner.id,
            active_ids=self.test_partner.ids,
        ).run()
        self.assertEqual(
            self.test_partner.city,
            "OrigCity",
            "ids selected in another model must not be read as ours",
        )
        self.action.with_context(self.context).run()
        self.assertEqual(self.test_partner.city, "Elsewhere", "and ours still work")

    def test_35_crud_write_selection(self):
        selection_value = self.res_country_name_position_field.selection_ids.filtered(
            lambda s: s.value == "after"
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "TestAction",
                "model_id": self.res_country_model.id,
                "model_name": "res.country",
                "state": "object_write",
                "update_path": "name_position",
                "selection_value": selection_value.id,
            }
        )
        action._inverse_selection_value()
        self.assertEqual(action.value, selection_value.value)
        context = {
            "active_model": "res.country",
            "active_id": self.test_country.id,
        }
        run_res = action.with_context(context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: update record action correctly finished should return False",
        )
        self.assertEqual(self.test_country.name_position, "after")

    def test_36_crud_write_m2m_ops(self):
        categ_1 = self.env["res.partner.tag"].create({"name": "TestCateg1"})
        categ_2 = self.env["res.partner.tag"].create({"name": "TestCateg2"})
        self.action.write(
            {
                "state": "object_write",
                "update_path": "tag_ids",
                "update_m2m_operation": "set",
                "resource_ref": categ_1,
            }
        )
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: update record action correctly finished should return False",
        )
        self.assertIn(
            categ_1,
            self.test_partner.tag_ids,
            "ir_actions_server: tag should have been set",
        )

        self.action.write(
            {
                "state": "object_write",
                "update_path": "tag_ids",
                "update_m2m_operation": "add",
                "resource_ref": categ_2,
            }
        )
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: update record action correctly finished should return False",
        )
        self.assertIn(
            categ_2,
            self.test_partner.tag_ids,
            "ir_actions_server: new tag should have been added",
        )
        self.assertIn(
            categ_1,
            self.test_partner.tag_ids,
            "ir_actions_server: old tag should still be there",
        )

        self.action.write(
            {
                "state": "object_write",
                "update_path": "tag_ids",
                "update_m2m_operation": "remove",
                "resource_ref": categ_1,
            }
        )
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: update record action correctly finished should return False",
        )
        self.assertNotIn(
            categ_1,
            self.test_partner.tag_ids,
            "ir_actions_server: tag should have been removed",
        )
        self.assertIn(
            categ_2,
            self.test_partner.tag_ids,
            "ir_actions_server: tag should still be there",
        )

        self.action.write(
            {
                "state": "object_write",
                "update_path": "tag_ids",
                "update_m2m_operation": "clear",
            }
        )
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: update record action correctly finished should return False",
        )
        self.assertFalse(
            self.test_partner.tag_ids,
            "ir_actions_server: tags should have been cleared",
        )

    def test_37_field_path_traversal(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "country_id.name",
                "value": "TestUpdatedCountry",
            }
        )
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: update record action correctly finished should return False",
        )
        self.assertEqual(
            self.test_partner.country_id.name,
            "TestUpdatedCountry",
            "ir_actions_server: country name should have been updated through relation",
        )

        self.action.write(
            {
                "state": "object_write",
                "update_path": "country_id.image_url",
                "value": "/base/static/img/country_flags/be.png",
            }
        )
        self.assertEqual(
            self.test_partner.country_id.image_url,
            "/base/static/img/country_flags/ty.png",
            "ir_actions_server: country flag has this value before the update",
        )
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: update record action correctly finished should return False",
        )
        self.assertEqual(
            self.test_partner.country_id.image_url,
            "/base/static/img/country_flags/be.png",
            "ir_actions_server: country should have been updated through a readonly field",
        )
        self.assertEqual(
            self.test_partner.country_id.code,
            "TY",
            "ir_actions_server: country code is still TY",
        )

        with self.assertRaises(ValidationError):
            self.action.write(
                {
                    "state": "object_write",
                    "update_path": "country_id.name.foo",
                    "value": "DoesNotMatter",
                }
            )
            self.action.flush_recordset(["update_path", "update_field_id"])

    def test_39_boolean_update(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "active",
                "update_boolean_value": "false",
            }
        )
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: update record action correctly finished should return False",
        )
        self.assertFalse(
            self.test_partner.active,
            "ir_actions_server: partner should have been deactivated",
        )
        self.action.write(
            {
                "state": "object_write",
                "update_path": "active",
                "update_boolean_value": "true",
            }
        )
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(
            run_res,
            "ir_actions_server: update record action correctly finished should return False",
        )
        self.assertTrue(
            self.test_partner.active,
            "ir_actions_server: partner should have been reactivated",
        )

    @mute_logger("odoo.addons.base.models.ir_model", "odoo.models")
    def test_40_multi(self):
        action1 = self.action.create(
            {
                "name": "Subaction1",
                "sequence": 1,
                "model_id": self.res_partner_model.id,
                "state": "code",
                "code": 'action = {"type": "ir.actions.act_window"}',
            }
        )
        action2 = self.action.create(
            {
                "name": "Subaction2",
                "sequence": 2,
                "model_id": self.res_partner_model.id,
                "crud_model_id": self.res_partner_model.id,
                "state": "object_create",
                "value": "RaoulettePoiluchette",
            }
        )
        action3 = self.action.create(
            {
                "name": "Subaction2",
                "sequence": 3,
                "model_id": self.res_partner_model.id,
                "state": "object_write",
                "update_path": "city",
                "value": "RaoulettePoiluchette",
            }
        )
        action4 = self.action.create(
            {
                "name": "Subaction3",
                "sequence": 4,
                "model_id": self.res_partner_model.id,
                "state": "code",
                "code": 'action = {"type": "ir.actions.act_url"}',
            }
        )
        self.action.write(
            {
                "state": "multi",
                "child_ids": [
                    Command.set([action1.id, action2.id, action3.id, action4.id])
                ],
            }
        )

        res = self.action.with_context(self.context).run()

        partner = self.test_partner.search([("name", "ilike", "RaoulettePoiluchette")])
        self.assertEqual(len(partner), 1)
        self.assertEqual(res.get("type"), "ir.actions.act_url")

        with self.assertRaises(ValidationError):
            self.action.write({"child_ids": [Command.set([self.action.id])]})

    def test_50_groups(self):
        Actions = self.env["ir.actions.actions"]

        group0 = self.env["res.groups"].create({"name": "country group"})

        self.context = {
            "active_model": "res.country",
            "active_id": self.test_country.id,
        }

        self.action.write(
            {
                "model_id": self.res_country_model.id,
                "binding_model_id": self.res_country_model.id,
                "group_ids": [Command.link(group0.id)],
                "code": 'record.write({"vat_label": "VatFromTest"})',
            }
        )

        bindings = Actions.get_bindings("res.country")
        self.assertFalse(bindings)

        with self.assertRaises(AccessError):
            self.action.with_context(self.context).run()
        self.assertFalse(self.test_country.vat_label)

        self.env.user.write({"group_ids": [Command.link(group0.id)]})

        bindings = Actions.get_bindings("res.country")
        self.assertItemsEqual(
            bindings.get("action"),
            self.action.read(
                ["name", "binding_view_types", "binding_sequence", "binding_icon"]
            ),
        )

        self.action.with_context(self.context).run()
        self.assertEqual(
            self.test_country.vat_label,
            "VatFromTest",
            "vat label should be changed to VatFromTest",
        )

    def test_60_sort(self):
        Actions = self.env["ir.actions.actions"]

        self.action.write(
            {
                "model_id": self.res_country_model.id,
                "binding_model_id": self.res_country_model.id,
            }
        )
        self.action2 = self.action.copy({"name": "TestAction2", "binding_sequence": 1})

        bindings = Actions.get_bindings("res.country")
        self.assertEqual(
            [vals.get("name") for vals in bindings["action"]],
            ["TestAction2", "TestAction"],
        )
        self.assertEqual(
            [vals.get("binding_sequence") for vals in bindings["action"]], [1, 10]
        )

    def test_70_copy_action(self):
        r = self.env["ir.actions.todo"].create(
            {
                "action_id": self.action.id,
                "state": "done",
            }
        )
        self.assertEqual(r.state, "done")
        self.assertEqual(
            r.copy().state, "open", "by default state should be reset by copy"
        )

        self.assertEqual(
            self.action.copy().state,
            "code",
            "copying a server action should not reset the state",
        )

    def test_80_permission(self):
        self.action.write(
            {
                "state": "code",
                "code": """record.write({'name': str(datetime.date.today())})""",
            }
        )

        user_demo = self.user_demo
        self_demo = self.action.with_user(user_demo.id)

        self.test_partner.type = "contact"
        self.test_partner.with_user(user_demo.id).check_access("write")

        self_demo.with_context(self.context).run()
        self.assertEqual(self.test_partner.name, str(date.today()))

    def test_90_webhook(self):
        self.action.write(
            {
                "state": "webhook",
                "webhook_field_ids": [
                    Command.link(self.res_partner_name_field.id),
                    Command.link(self.res_partner_city_field.id),
                    Command.link(self.res_partner_country_field.id),
                ],
                "webhook_url": "http://example.com/webhook",
            }
        )
        num_requests = 0

        def _patched_post(_session, url, **kwargs):
            nonlocal num_requests
            response = requests.Response()
            response.status_code = 200 if num_requests == 0 else 400
            self.assertEqual(url, "http://example.com/webhook")
            self.assertEqual(
                kwargs["data"],
                json_dumps(
                    {
                        "_action": "%s(#%s)" % (self.action.name, self.action.id),
                        "_id": self.test_partner.id,
                        "_model": self.test_partner._name,
                        "city": self.test_partner.city,
                        "country_id": self.test_partner.country_id.id,
                        "id": self.test_partner.id,
                        "name": self.test_partner.name,
                    },
                    default=str,
                    option=OPT_SORT_KEYS,
                ),
            )
            num_requests += 1
            return response

        with (
            patch.object(requests.Session, "post", _patched_post),
            mute_logger("odoo.addons.base.models.ir_actions_server"),
        ):
            self.action.with_context(self.context).run()
            self.env.cr.postcommit.run()
            self.action.with_context(self.context).run()
            self.env.cr.postcommit.run()
        self.assertEqual(num_requests, 2)

    def test_90_convert_to_float(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "partner_latitude",
                "value": "20.99",
            }
        )
        self.assertEqual(self.action._eval_value()[self.action.id], 20.99)

    def test_91_update_related_model_cleared_on_state_change(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "country_id",
                "evaluation_type": "value",
            }
        )
        self.action.flush_recordset()
        self.assertTrue(
            self.action.update_related_model_id,
            "update_related_model_id should be set for a relational update_path",
        )
        self.action.write({"state": "object_create"})
        self.action.flush_recordset()
        self.assertFalse(
            self.action.update_related_model_id,
            "update_related_model_id should be cleared when state changes to object_create",
        )

    def test_92_relation_chain_duplicate_field_names(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "parent_id.parent_id",
            }
        )
        self.action.flush_recordset()
        self.assertEqual(
            self.action.update_field_id.name,
            "parent_id",
            "update_field_id should be the last field in the path",
        )
        self.assertEqual(
            self.action.crud_model_id.model,
            "res.partner",
            "crud_model_id should be res.partner (parent_id is self-referential)",
        )

    def test_93_webhook_timeout(self):
        self.action.write(
            {
                "state": "webhook",
                "webhook_url": "http://example.com/webhook",
            }
        )

        def _patched_post(_session, _url, **kwargs):
            raise requests.exceptions.ReadTimeout("timed out")

        with patch.object(requests.Session, "post", _patched_post):
            self.action.with_context(self.context).run()
            with self.assertLogs("odoo.libs.webhook", level="WARNING") as log_catcher:
                self.env.cr.postcommit.run()
        self.assertTrue(
            any("timed out" in line for line in log_catcher.output),
            "the read timeout should be logged as a warning",
        )

    def test_94_webhook_connection_error(self):
        self.action.write(
            {
                "state": "webhook",
                "webhook_url": "http://example.com/webhook",
            }
        )

        def _patched_post(_session, _url, **kwargs):
            raise requests.exceptions.ConnectionError("connection refused")

        with patch.object(requests.Session, "post", _patched_post):
            self.action.with_context(self.context).run()
            with self.assertLogs("odoo.libs.webhook", level="WARNING") as log_catcher:
                self.env.cr.postcommit.run()
        output = "\n".join(log_catcher.output)
        self.assertIn(self.action.name, output, "the action must be identifiable")
        self.assertIn(
            "NOT be retried",
            output,
            "a connection error is not ambiguous: nothing arrived, and nothing "
            "will try again",
        )

    def test_95_code_sandbox_blocked(self):
        with self.assertRaises(ValidationError):
            self.action.write(
                {
                    "state": "code",
                    "code": "import os\nos.system('echo pwned')",
                }
            )
        self.action.write(
            {
                "state": "code",
                "code": "open('/etc/passwd').read()",
            }
        )
        with self.assertRaises(ValueError):
            self.action.with_context(self.context).run()

    def test_96_eval_value_m2m_bad_value(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "tag_ids",
                "update_m2m_operation": "add",
                "value": "not-an-int",
            }
        )
        with self.assertRaises(UserError):
            self.action._eval_value()
        with self.assertRaises(UserError):
            self.action.with_context(self.context).run()

    def test_97_eval_value_m2m_unknown_operation(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "tag_ids",
                "update_m2m_operation": False,
                "value": "1",
            }
        )
        self.assertEqual(self.action._eval_value()[self.action.id], [])

    def test_98_object_write_no_path_errors(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "name",
                "value": "X",
            }
        )
        self.action.update_path = False
        with self.assertRaises(UserError):
            self.action.with_context(self.context).run()

    def test_99_object_copy_no_resource_ref_errors(self):
        self.action.write(
            {
                "state": "object_copy",
                "crud_model_id": self.res_partner_model.id,
                "resource_ref": self.test_partner,
            }
        )
        self.action.resource_ref = False
        with self.assertRaises(UserError):
            self.action.with_context(self.context).run()

    def test_a0_relation_chain_unknown_field(self):
        with self.assertRaises(ValidationError):
            self.action.write(
                {
                    "state": "object_write",
                    "update_path": "does_not_exist",
                    "value": "X",
                }
            )
            self.action.flush_recordset(["update_path", "update_field_id"])

    def test_a1_create_action_access(self):
        self.action.write(
            {
                "model_id": self.res_partner_model.id,
                "binding_model_id": False,
            }
        )
        with self.assertRaises(AccessError):
            self.action.with_user(self.user_demo.id).create_action()

    def test_a2_write_blank_code_records_history(self):
        History = self.env["ir.actions.server.history"]
        before = History.search_count([("action_id", "=", self.action.id)])
        self.action.write({"code": ""})
        after = History.search_count([("action_id", "=", self.action.id)])
        self.assertEqual(
            after,
            before + 1,
            "clearing the code should record a history entry",
        )

    def test_a3_active_less_non_code_run_warns(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "name",
                "value": "ShouldNotApply",
            }
        )
        original_name = self.test_partner.name
        logger = "odoo.addons.base.models.ir_actions_server"
        with self.assertLogs(logger, level="WARNING") as log_catcher:
            self.action.run()
        self.assertTrue(
            any("was triggered with no target record" in m for m in log_catcher.output),
            "an active-less non-code action must warn, not silently no-op",
        )
        self.assertEqual(
            self.test_partner.name,
            original_name,
            "no record was targeted, so nothing should have been written",
        )

    def test_a4_active_less_code_run_does_not_warn(self):
        code_action = self.env["ir.actions.server"].create(
            {
                "name": "ActiveLessCode",
                "model_id": self.res_partner_model.id,
                "state": "code",
                "code": "x = 1",
            }
        )
        logger = "odoo.addons.base.models.ir_actions_server"
        with self.assertNoLogs(logger, level="WARNING"):
            code_action.run()

    def test_b0_eval_value_bad_integer_raises_clean_error(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "color",
                "evaluation_type": "value",
                "value": "not_a_number",
            }
        )
        with self.assertRaises(UserError):
            self.action._eval_value()

    def test_b1_eval_value_bad_float_raises_clean_error(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "partner_latitude",
                "evaluation_type": "value",
                "value": "not_a_number",
            }
        )
        with self.assertRaises(UserError):
            self.action._eval_value()

    def test_b2_eval_value_blank_numeric_is_typed_zero(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "color",
                "evaluation_type": "value",
                "value": "",
            }
        )
        self.assertEqual(self.action._eval_value()[self.action.id], 0)
        self.action.write({"update_path": "parent_id", "value": ""})
        self.assertIs(self.action._eval_value()[self.action.id], False)

    def test_b3_relation_chain_degrades_without_raising_on_read(self):
        action = self.env["ir.actions.server"].new(
            {
                "model_id": self.res_partner_model.id,
                "state": "object_write",
                "update_path": "totally_not_a_field",
            }
        )
        self.assertEqual(action._get_relation_chain("update_path"), [])
        self.assertFalse(action.update_field_id)

    def test_b3b_relation_chain_label_reads_as_a_path(self):
        action = self.action.copy(
            {
                "model_id": self.res_partner_model.id,
                "state": "object_write",
                "update_path": "country_id.name",
            }
        )
        chain = action._get_relation_chain("update_path")
        self.assertEqual([field.name for field in chain], ["country_id", "name"])
        self.assertEqual(
            action._get_relation_chain_label(chain),
            " > ".join(field.get_description(self.env)["string"] for field in chain),
        )
        self.assertIn(" > ", action._get_relation_chain_label(chain))
        self.assertEqual(action._get_relation_chain_label([]), "")

    def test_b4_empty_path_segment_raises_clear_error_on_save(self):
        with self.assertRaises(ValidationError) as cm:
            self.action.write(
                {
                    "state": "object_write",
                    "update_path": "parent_id..name",
                    "value": "X",
                }
            )
            self.action.flush_recordset(["update_path", "update_field_id"])
        self.assertIn("empty", str(cm.exception).lower())

    def test_b5_available_models_not_state_dependent(self):
        from odoo.addons.base.models.ir_actions_server import IrActionsServer

        compute = IrActionsServer._compute_available_model_ids
        self.assertNotIn("state", getattr(compute, "_depends", ()))

    def test_b6_equation_evaluates_without_sudo_privilege(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "color",
                "evaluation_type": "equation",
                "value": "1 if env.su else 0",
                "group_ids": [Command.set(self.env.ref("base.group_user").ids)],
            }
        )
        self.action.with_user(self.user_demo.id).with_context(self.context).run()
        self.assertEqual(
            self.test_partner.color,
            0,
            "expressions must evaluate with su=False (user ACLs), not elevated",
        )

    def test_b7_onchange_new_record_writes_cache_only(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "function",
                "evaluation_type": "value",
                "value": "Set By Action",
            }
        )
        new_record = self.env["res.partner"].new({"name": "New Guy"})
        self.assertFalse(new_record._origin.id, "precondition: unsaved record")
        self.action.with_context(
            active_model="res.partner", onchange_self=new_record
        ).run()
        self.assertEqual(new_record.function, "Set By Action")

    def test_b8_onchange_existing_record_writes_cache_not_db(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "function",
                "evaluation_type": "value",
                "value": "Set By Action",
            }
        )
        onchange_record = self.env["res.partner"].new(
            {"name": self.test_partner.name}, origin=self.test_partner
        )
        self.assertTrue(onchange_record._origin.id, "precondition: has origin")
        self.action.with_context(
            active_model="res.partner", onchange_self=onchange_record
        ).run()
        self.assertEqual(onchange_record.function, "Set By Action")
        self.assertFalse(
            self.test_partner.function,
            "onchange must not persist to the database record",
        )

    def test_c0_eval_value_sequence(self):
        sequence = self.env["ir.sequence"].create(
            {"name": "Test Seq", "prefix": "SEQ-", "padding": 4, "number_next": 1}
        )
        self.action.write(
            {
                "state": "object_write",
                "update_path": "ref",
                "evaluation_type": "sequence",
                "sequence_id": sequence.id,
            }
        )
        value = self.action._eval_value()[self.action.id]
        self.assertEqual(value, "SEQ-0001")

    def test_c1_eval_value_blank_float_is_typed_zero(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "partner_latitude",
                "evaluation_type": "value",
                "value": "",
            }
        )
        result = self.action._eval_value()[self.action.id]
        self.assertEqual(result, 0.0)
        self.assertIsInstance(result, float)

    def test_c2_eval_value_m2o_parsed_zero_is_false(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "country_id",
                "evaluation_type": "value",
                "value": "0",
            }
        )
        self.assertIs(self.action._eval_value()[self.action.id], False)

    def test_c3_gc_histories_prunes_to_max(self):
        History = self.env["ir.actions.server.history"]
        action = self.env["ir.actions.server"].create(
            {
                "name": "GC target",
                "model_id": self.res_partner_model.id,
                "state": "code",
                "code": "x = 1",
            }
        )
        History.search([("action_id", "=", action.id)]).unlink()
        cap = History._max_entries_per_action
        History.create(
            [{"action_id": action.id, "code": str(i)} for i in range(cap + 5)]
        )
        self.assertEqual(History.search_count([("action_id", "=", action.id)]), cap + 5)
        History._gc_histories()
        self.assertEqual(
            History.search_count([("action_id", "=", action.id)]),
            cap,
            "GC must prune each action's history down to the cap",
        )

    def test_c4_webhook_sample_payload_structure(self):
        import json

        self.action.write(
            {
                "state": "webhook",
                "webhook_url": "http://example.invalid/hook",
                "webhook_field_ids": [Command.set([self.res_partner_name_field.id])],
            }
        )
        payload = json.loads(self.action.webhook_sample_payload)
        self.assertEqual(payload["_model"], "res.partner")
        self.assertIn("_id", payload)
        self.assertIn("_action", payload)
        self.assertIn("name", payload)

    def _hidden_partner_for_demo(self):
        self.user_demo.write(
            {"group_ids": [Command.link(self.env.ref("base.group_partner_manager").id)]}
        )
        other_company = self.env["res.company"].create({"name": "Other Company"})
        hidden = self.env["res.partner"].create(
            {"name": "Hidden", "company_id": other_company.id}
        )
        self.assertTrue(
            self.env["res.partner"].with_user(self.user_demo).has_access("write"),
            "precondition: demo user has model-level write on res.partner",
        )
        with self.assertRaises(AccessError):
            hidden.with_user(self.user_demo).check_access("write")
        return hidden

    def _run_as_demo_on(self, action, record):
        return (
            action.with_user(self.user_demo)
            .with_context(
                active_model=record._name, active_id=record.id, active_ids=record.ids
            )
            .run()
        )

    def test_c5_record_level_acl_is_the_live_gate(self):
        hidden = self._hidden_partner_for_demo()
        self.action.write(
            {
                "state": "object_write",
                "update_path": "name",
                "evaluation_type": "value",
                "value": "pwned",
            }
        )
        with (
            self.assertRaises(AccessError),
            mute_logger("odoo.addons.base.models.ir_actions_server"),
        ):
            self._run_as_demo_on(self.action, hidden)
        self.assertEqual(hidden.name, "Hidden")

    def test_c5_record_level_acl_gates_the_children_of_a_multi_action(self):
        hidden = self._hidden_partner_for_demo()
        self.action.write(
            {
                "state": "object_write",
                "update_path": "name",
                "evaluation_type": "value",
                "value": "pwned",
            }
        )
        parent = self.env["ir.actions.server"].create(
            {
                "name": "Parent",
                "model_id": self.res_partner_model.id,
                "state": "multi",
                "child_ids": [Command.set(self.action.ids)],
            }
        )
        with (
            self.assertRaises(AccessError),
            mute_logger("odoo.addons.base.models.ir_actions_server"),
        ):
            self._run_as_demo_on(parent, hidden)
        self.assertEqual(hidden.name, "Hidden")

    def test_c6_multi_children_run_with_the_caller_privileges(self):
        child = self.env["ir.actions.server"].create(
            {
                "name": "Child",
                "model_id": self.res_partner_model.id,
                "state": "code",
                "code": "action = {'su': env.su, 'uid': env.uid}",
            }
        )
        parent = self.env["ir.actions.server"].create(
            {
                "name": "Parent",
                "model_id": self.res_partner_model.id,
                "state": "multi",
                "child_ids": [Command.set(child.ids)],
            }
        )
        res = self._run_as_demo_on(parent, self.test_partner)
        self.assertEqual(res, {"su": False, "uid": self.user_demo.id})

    def test_c7_update_related_model_follows_evaluation_type(self):
        self.action.write(
            {
                "state": "object_write",
                "update_path": "parent_id",
                "evaluation_type": "equation",
                "value": "False",
            }
        )
        self.assertFalse(self.action.update_related_model_id)
        self.action.evaluation_type = "value"
        self.assertEqual(self.action.update_related_model_id, self.res_partner_model)

    def test_c8_create_does_not_mutate_the_caller_vals(self):
        vals = {"name": "Kept", "model_id": self.res_partner_model.id, "state": "code"}
        snapshot = dict(vals)
        self.env["ir.actions.server"].create(vals)
        self.assertEqual(vals, snapshot)


@tagged("post_install", "-at_install")
class TestActionsPath(common.TransactionCase):
    def _make_window(self, path):
        return self.env["ir.actions.act_window"].create(
            {
                "name": "PathWindow",
                "res_model": "res.partner",
                "path": path,
            }
        )

    def test_path_invalid_format(self):
        for bad in ("Foo", "1abc", "a b", "-abc"):
            with self.subTest(path=bad), self.assertRaises(ValidationError):
                self._make_window(bad)

    def test_path_reserved_prefixes(self):
        for bad in ("m-foo", "action-foo", "new"):
            with self.subTest(path=bad), self.assertRaises(ValidationError):
                self._make_window(bad)

    def test_path_valid(self):
        action = self._make_window("my-valid_path1")
        self.assertEqual(action.path, "my-valid_path1")

    def test_path_unique_cross_table(self):
        self._make_window("shared-path")
        with self.assertRaises(IntegrityError), mute_logger("odoo.db.cursor"):
            with self.env.cr.savepoint():
                self.env["ir.actions.act_url"].create(
                    {
                        "name": "PathUrl",
                        "url": "https://example.com",
                        "path": "shared-path",
                    }
                )
                self.env.flush_all()

    def test_the_cross_table_rejection_names_the_path_field(self):
        self._make_window("shared-path-msg")
        try:
            with self.env.cr.savepoint(), mute_logger("odoo.db.cursor"):
                self.env["ir.actions.act_url"].create(
                    {
                        "name": "PathUrl2",
                        "url": "https://example.com",
                        "path": "shared-path-msg",
                    }
                )
                self.env.flush_all()
        except IntegrityError as exc:
            message = str(_integrity_error_to_validation_error(self.env, exc))
        else:
            self.fail("a duplicate path must be rejected")
        self.assertIn("unique", message.lower())


class TestActionsReadAndXmlId(common.TransactionCase):
    def test_placeholder_with_bad_context(self):
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "HelpWindow",
                "res_model": "res.partner",
                "context": "[1, 2, 3]",
                "help": "<p>Custom help</p>",
            }
        )
        self.assertIsNotNone(action._get_action_dict()["help"])

    def test_placeholder_with_raising_context(self):
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "HelpWindow2",
                "res_model": "res.partner",
                "context": "{'k': undefined_name}",
                "help": "<p>Custom help</p>",
            }
        )
        self.assertIsNotNone(action._get_action_dict()["help"])

    PLACEHOLDER = "<p>GENERATED PLACEHOLDER</p>"

    def _action_on_a_model_that_generates_a_placeholder(self, help_text):
        self.patch(
            type(self.env["res.partner"]),
            "get_empty_list_help",
            lambda records, help_message: self.PLACEHOLDER,
        )
        return self.env["ir.actions.act_window"].create(
            {"name": "HelpStored", "res_model": "res.partner", "help": help_text}
        )

    def test_read_returns_the_stored_help_verbatim(self):
        action = self._action_on_a_model_that_generates_a_placeholder(
            "<p>MY OWN HELP</p>"
        )
        self.env.flush_all()
        self.assertEqual(action.read(["help"])[0]["help"], "<p>MY OWN HELP</p>")

        action.write({"help": action.read(["help"])[0]["help"]})
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(action.help, "<p>MY OWN HELP</p>")

    def test_the_launch_payload_still_carries_the_placeholder(self):
        action = self._action_on_a_model_that_generates_a_placeholder(False)
        self.assertEqual(action._get_action_dict()["help"], self.PLACEHOLDER)

    def test_get_action_dict_by_xml_id_valid_window(self):
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "XmlIdWindow",
                "res_model": "res.partner",
            }
        )
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "test_action_dict_by_xml_id_window_action",
                "model": "ir.actions.act_window",
                "res_id": action.id,
            }
        )
        xml_id = "base.test_action_dict_by_xml_id_window_action"
        result = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(xml_id)
        self.assertIsInstance(result, dict)
        readable = action._get_fields_readable()
        self.assertTrue(set(result.keys()).issubset(readable))

    def test_get_action_dict_by_xml_id_non_action_raises(self):
        with self.assertRaises(ValueError) as caught:
            self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
                "base.model_res_partner"
            )
        self.assertIn("ir.model", str(caught.exception))

    def test_get_action_dict_act_url_no_invalid_field_warning(self):
        action = self.env["ir.actions.act_url"].create(
            {"name": "UrlAction", "url": "https://example.com"}
        )
        self.assertNotIn("close", action._fields)
        with self.assertNoLogs("odoo.models", "WARNING"):
            result = action._get_action_dict()
        self.assertNotIn("close", result)
        self.assertTrue(set(result) <= action._get_fields_readable())
        self.assertTrue(set(result) <= set(action._fields))

    def test_get_action_dict_window_close_no_invalid_field_warning(self):
        action = self.env["ir.actions.act_window_close"].create({"name": "CloseAction"})
        self.assertNotIn("effect", action._fields)
        self.assertNotIn("infos", action._fields)
        with self.assertNoLogs("odoo.models", "WARNING"):
            result = action._get_action_dict()
        self.assertNotIn("effect", result)
        self.assertNotIn("infos", result)

    def test_write_binding_irrelevant_field_skips_cache_clear(self):
        action = self.env["ir.actions.act_url"].create(
            {"name": "CacheAction", "url": "https://example.com"}
        )
        Registry = type(self.env.registry)

        def clears_for(vals, record=action):
            with patch.object(Registry, "clear_cache") as spy:
                record.write(vals)
            return spy.call_count

        self.assertEqual(
            clears_for({"help": "<p>irrelevant to bindings</p>"}),
            0,
            "writing only binding-irrelevant fields should not clear the cache",
        )
        self.assertEqual(
            clears_for({"name": "Renamed"}),
            0,
            "an unbound, unpathed action is in no registry cache to stale",
        )
        self.assertGreaterEqual(
            clears_for(
                {"binding_model_id": self.env["ir.model"]._get_id("res.partner")}
            ),
            1,
            "acquiring a binding puts the action in a cache, so it must clear",
        )
        self.assertGreaterEqual(
            clears_for({"name": "RenamedAgain"}),
            1,
            "writing a binding input of a bound action must clear the cache",
        )

    def test_write_server_action_value_field_skips_cache_clear(self):
        model = self.env["ir.model"]._get("res.partner")
        action = self.env["ir.actions.server"].create(
            {
                "name": "SrvCacheAction",
                "model_id": model.id,
                "state": "code",
                "code": "records.write({})",
            }
        )
        Registry = type(self.env.registry)

        def clears_for(vals):
            with patch.object(Registry, "clear_cache") as spy:
                action.write(vals)
            return spy.call_count

        self.assertEqual(
            clears_for({"code": "records.write({'active': True})"}),
            0,
            "editing a server action's code must not clear the registry cache",
        )
        self.assertGreaterEqual(
            clears_for({"binding_model_id": model.id}),
            1,
            "writing a binding input must clear the cache",
        )


class TestClientActionParams(common.TransactionCase):
    def test_params_roundtrip_dict(self):
        action = self.env["ir.actions.client"].create(
            {"name": "ClientAction", "tag": "some_tag", "params": {"a": 1, "b": "x"}}
        )
        action.invalidate_recordset(["params"])
        self.assertEqual(action.params, {"a": 1, "b": "x"})

    def test_params_empty_store(self):
        action = self.env["ir.actions.client"].create(
            {"name": "ClientAction2", "tag": "some_tag"}
        )
        self.assertFalse(action.params)

    def test_params_arriving_as_text_or_bytes_are_evaluated(self):
        for source in (
            "{'default_active_id': 'mail.box_inbox'}",
            b"{'default_active_id': 'mail.box_inbox'}",
        ):
            with self.subTest(source=source):
                action = self.env["ir.actions.client"].create(
                    {"name": "ClientAction5", "tag": "some_tag", "params": source}
                )
                action.invalidate_recordset(["params"])
                self.assertEqual(action.params, {"default_active_id": "mail.box_inbox"})

    def test_params_that_are_not_a_dict_are_refused(self):
        for params in ([1, 2], "x", b"env"):
            with self.subTest(params=params), self.assertRaises(ValidationError):
                self.env["ir.actions.client"].create(
                    {"name": "ClientAction4", "tag": "some_tag", "params": params}
                )

    def test_params_corrupt_store_degrades(self):
        action = self.env["ir.actions.client"].create(
            {"name": "ClientAction3", "tag": "some_tag"}
        )
        action.params_store = "this is ( not valid python"
        action.invalidate_recordset(["params"])
        self.assertFalse(action.params)
        with self.assertNoLogs("odoo.models", "WARNING"):
            data = action._get_action_dict()
        self.assertIn("params", data)


class TestActionsBindings(common.TransactionCase):
    def _partner_model_id(self):
        return self.env["ir.model"]._get_id("res.partner")

    def _server(self, name, binding_type, sequence):
        return self.env["ir.actions.server"].create(
            {
                "name": name,
                "model_id": self._partner_model_id(),
                "state": "code",
                "code": "pass",
                "binding_model_id": self._partner_model_id(),
                "binding_type": binding_type,
                "binding_sequence": sequence,
            }
        )

    def _binding_names(self, bucket):
        self.env.registry.clear_cache()
        bindings = self.env["ir.actions.actions"]._get_bindings("res.partner")
        return [d["name"] for d in bindings.get(bucket, ())]

    def test_report_bucket_sorted_by_sequence(self):
        self._server("Zeta report", "report", 30)
        self._server("Alpha report", "report", 10)
        ordered = [
            n
            for n in self._binding_names("report")
            if n in ("Zeta report", "Alpha report")
        ]
        self.assertEqual(ordered, ["Alpha report", "Zeta report"])

    def test_action_bucket_sorted_by_sequence(self):
        self._server("Zeta action", "action", 30)
        self._server("Alpha action", "action", 10)
        ordered = [
            n
            for n in self._binding_names("action")
            if n in ("Zeta action", "Alpha action")
        ]
        self.assertEqual(ordered, ["Alpha action", "Zeta action"])

    def test_fields_invalidating_when_cached_cover_binding_inputs(self):
        binding_inputs = {
            "name",
            "type",
            "binding_model_id",
            "binding_type",
            "binding_view_types",
            "res_model",
            "group_ids",
            "binding_sequence",
            "binding_icon",
            "domain",
        }
        invalidating = self.env["ir.actions.actions"]._get_fields_read_by_bindings()
        missing = binding_inputs - invalidating
        self.assertFalse(
            missing,
            "binding inputs %s are not cache-invalidating; writing them would "
            "leave stale bindings" % sorted(missing),
        )

    def test_rename_bound_action_invalidates_bindings(self):
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "BindOrig",
                "res_model": "res.partner",
                "binding_model_id": self._partner_model_id(),
            }
        )
        self.assertIn("BindOrig", self._binding_names("action"))
        action.write({"name": "BindRenamed"})
        names = self._binding_names("action")
        self.assertIn("BindRenamed", names)
        self.assertNotIn("BindOrig", names)

    def test_group_ids_stay_database_ids(self):
        gid = self.env.ref("base.group_user").id
        for i in range(3):
            self.env["ir.actions.act_window"].create(
                {
                    "name": "Grp%d" % i,
                    "res_model": "res.partner",
                    "binding_model_id": self._partner_model_id(),
                    "group_ids": [Command.set([gid])],
                }
            )
        self.env.registry.clear_cache()
        raw = self.env["ir.actions.actions"]._get_bindings("res.partner")
        ours = [d for d in raw.get("action", ()) if d["name"].startswith("Grp")]
        self.assertEqual(len(ours), 3)
        for data in ours:
            self.assertEqual(data["group_ids"], (gid,))


class TestCommonCustomFields(common.TransactionCase):
    MODEL = "res.partner"
    COMODEL = "res.users"

    def setUp(self):
        fnames = set(self.registry[self.MODEL]._fields)

        @self.addCleanup
        def check_registry():
            assert set(self.registry[self.MODEL]._fields) == fnames

        self.addCleanup(self.registry.reset_changes)
        self.addCleanup(self.registry.clear_all_caches)

        super().setUp()

    def create_field(self, name, *, field_type="char"):
        model = self.env["ir.model"].search([("model", "=", self.MODEL)])
        field = self.env["ir.model.fields"].create(
            {
                "model_id": model.id,
                "name": name,
                "field_description": name,
                "ttype": field_type,
            }
        )
        self.assertIn(name, self.env[self.MODEL]._fields)
        return field

    def create_view(self, name):
        return self.env["ir.ui.view"].create(
            {
                "name": "yet another view",
                "model": self.MODEL,
                "arch": '<list string="X"><field name="%s"/></list>' % name,
            }
        )


class TestCustomFields(TestCommonCustomFields):
    def test_create_custom(self):
        with self.assertRaises(IntegrityError), mute_logger("odoo.db"):
            self.create_field("xyz")

    def test_rename_custom(self):
        field = self.create_field("x_xyz")
        with self.assertRaises(IntegrityError), mute_logger("odoo.db"):
            field.name = "xyz"

    def test_create_valid(self):
        with self.assertRaises(ValidationError):
            self.create_field("x_foo bar")

    def test_rename_valid(self):
        field = self.create_field("x_foo")
        with self.assertRaises(ValidationError):
            field.name = "x_foo bar"

    def test_create_unique(self):
        self.create_field("x_foo")
        with self.assertRaises(IntegrityError), mute_logger("odoo.db"):
            self.create_field("x_foo")

    def test_rename_unique(self):
        field1 = self.create_field("x_foo")
        field2 = self.create_field("x_bar")
        with self.assertRaises(IntegrityError), mute_logger("odoo.db"):
            field2.name = field1.name

    def test_remove_without_view(self):
        field = self.create_field("x_foo")
        field.unlink()

    def test_rename_without_view(self):
        field = self.create_field("x_foo")
        field.name = "x_bar"

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_remove_with_view(self):
        field = self.create_field("x_foo")
        self.create_view("x_foo")

        with self.assertRaises(UserError):
            field.unlink()
        self.assertIn("x_foo", self.env[self.MODEL]._fields)

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_rename_with_view(self):
        field = self.create_field("x_foo")
        self.create_view("x_foo")

        with self.assertRaises(UserError):
            field.name = "x_bar"
        self.assertIn("x_foo", self.env[self.MODEL]._fields)

    def test_unlink_base(self):
        field = self.env["ir.model.fields"]._get(self.MODEL, "ref")
        self.assertTrue(field)

        with self.assertRaisesRegex(UserError, "This column contains module data"):
            field.unlink()

        field.with_context(_force_unlink=True).unlink()

    def test_unlink_with_inverse(self):
        model = self.env["ir.model"]._get(self.MODEL)
        comodel = self.env["ir.model"]._get(self.COMODEL)

        m2o_field = self.env["ir.model.fields"].create(
            {
                "model_id": comodel.id,
                "name": "x_my_m2o",
                "field_description": "my_m2o",
                "ttype": "many2one",
                "relation": self.MODEL,
            }
        )

        o2m_field = self.env["ir.model.fields"].create(
            {
                "model_id": model.id,
                "name": "x_my_o2m",
                "field_description": "my_o2m",
                "ttype": "one2many",
                "relation": self.COMODEL,
                "relation_field": m2o_field.name,
            }
        )

        with self.assertRaises(UserError):
            m2o_field.unlink()

        m2o_field.with_context(_force_unlink=True).unlink()
        self.assertFalse(o2m_field.exists())

    def test_unlink_with_dependant(self):
        comodel = self.env["ir.model"].search([("model", "=", self.COMODEL)])

        field = self.create_field("x_my_char")

        dependant = self.env["ir.model.fields"].create(
            {
                "model_id": comodel.id,
                "name": "x_oh_boy",
                "field_description": "x_oh_boy",
                "ttype": "char",
                "related": "partner_id.x_my_char",
            }
        )

        with self.assertRaises(UserError):
            field.unlink()

        field.with_context(_force_unlink=True).unlink()
        self.assertFalse(dependant.exists())

    def test_unlink_inherited_custom(self):
        field = self.create_field("x_foo")
        self.assertEqual(field.state, "manual")

        inherited_field = self.env["ir.model.fields"]._get(self.COMODEL, "x_foo")
        self.assertTrue(inherited_field)
        self.assertEqual(inherited_field.state, "base")

        with self.assertRaises(UserError):
            inherited_field.unlink()

        field.unlink()
        self.assertFalse(field.exists())
        self.assertFalse(inherited_field.exists())
        self.assertFalse(
            self.env["ir.model.fields"].search_count(
                [
                    ("model", "in", [self.MODEL, self.COMODEL]),
                    ("name", "=", "x_foo"),
                ]
            )
        )

    def test_create_binary(self):
        self.create_field("x_image", field_type="binary")
        custom_binary = self.env[self.MODEL]._fields["x_image"]

        self.assertTrue(custom_binary.attachment)

    def test_related_field(self):

        countries = self.env["res.country"].search([("code", "!=", False)], limit=100)
        self.assertEqual(
            len(countries), 100, "Not enough records in comodel 'res.country'"
        )

        partners = self.env["res.partner"].create(
            [{"name": country.code, "country_id": country.id} for country in countries]
        )
        self.env.flush_all()

        model_id = self.env["ir.model"]._get_id("res.partner")
        # a partner field is also a company field (res.company _inherits
        # res.partner), set up and fetched with the company's row
        query_count = 62
        with self.assertQueryCount(query_count):
            self.env.registry.clear_cache()
            self.env["ir.model.fields"].create(
                {
                    "model_id": model_id,
                    "name": "x_oh_box",
                    "field_description": "x_oh_box",
                    "ttype": "char",
                    "store": True,
                }
            )

        with self.assertQueryCount(query_count + 7):
            self.env.registry.clear_cache()
            self.env["ir.model.fields"].create(
                {
                    "model_id": model_id,
                    "name": "x_oh_boy",
                    "field_description": "x_oh_boy",
                    "ttype": "char",
                    "related": "country_id.code",
                    "store": True,
                }
            )

        for partner in partners:
            self.assertEqual(partner.x_oh_boy, partner.country_id.code)

    def test_relation_of_a_custom_field(self):
        model = self.env["ir.model"].search([("model", "=", self.MODEL)])
        field = self.env["ir.model.fields"].create(
            {
                "name": "x_foo",
                "model_id": model.id,
                "field_description": "x_foo",
                "ttype": "many2many",
                "relation": self.COMODEL,
            }
        )

        with self.assertRaises(ValidationError):
            field.relation = "foo"

    def test_selection(self):
        Model = self.env[self.MODEL]
        model = self.env["ir.model"].search([("model", "=", self.MODEL)])
        field = self.env["ir.model.fields"].create(
            {
                "model_id": model.id,
                "name": "x_sel",
                "field_description": "Custom Selection",
                "ttype": "selection",
                "selection_ids": [
                    Command.create({"value": "foo", "name": "Foo", "sequence": 0}),
                    Command.create({"value": "bar", "name": "Bar", "sequence": 1}),
                ],
            }
        )

        x_sel = Model._fields["x_sel"]
        self.assertEqual(x_sel.type, "selection")
        self.assertEqual(x_sel.selection, [("foo", "Foo"), ("bar", "Bar")])

        field.selection_ids.create(
            {
                "field_id": field.id,
                "value": "baz",
                "name": "Baz",
                "sequence": 2,
            }
        )
        x_sel = Model._fields["x_sel"]
        self.assertEqual(x_sel.type, "selection")
        self.assertEqual(
            x_sel.selection, [("foo", "Foo"), ("bar", "Bar"), ("baz", "Baz")]
        )

        rec1 = Model.create({"name": "Rec1", "x_sel": "foo"})
        rec2 = Model.create({"name": "Rec2", "x_sel": "bar"})
        rec3 = Model.create({"name": "Rec3", "x_sel": "baz"})
        self.assertEqual(rec1.x_sel, "foo")
        self.assertEqual(rec2.x_sel, "bar")
        self.assertEqual(rec3.x_sel, "baz")

        field.selection_ids[0].unlink()
        x_sel = Model._fields["x_sel"]
        self.assertEqual(x_sel.type, "selection")
        self.assertEqual(x_sel.selection, [("bar", "Bar"), ("baz", "Baz")])

        self.assertEqual(rec1.x_sel, False)
        self.assertEqual(rec2.x_sel, "bar")
        self.assertEqual(rec3.x_sel, "baz")

        field.selection_ids[0].value = "quux"
        x_sel = Model._fields["x_sel"]
        self.assertEqual(x_sel.type, "selection")
        self.assertEqual(x_sel.selection, [("quux", "Bar"), ("baz", "Baz")])

        self.assertEqual(rec1.x_sel, False)
        self.assertEqual(rec2.x_sel, "quux")
        self.assertEqual(rec3.x_sel, "baz")


@tagged("post_install", "-at_install")
class TestCustomFieldsPostInstall(TestCommonCustomFields):
    def test_add_field_valid(self):
        field = self.create_field("x_foo")
        self.env.cr.execute(
            "ALTER TABLE ir_model_fields DROP CONSTRAINT ir_model_fields_name_manual_field"
        )
        self.env.cr.execute(
            "UPDATE ir_model_fields SET name = 'foo' WHERE id = %s", [field.id]
        )
        with self.assertLogs("odoo.registry") as log_catcher:
            self.env.registry.setup_models(self.cr, [self.MODEL])
            self.assertIn(
                f"The field `{field.name}` is not defined in the `{field.model}` Python class",
                log_catcher.output[0],
            )
