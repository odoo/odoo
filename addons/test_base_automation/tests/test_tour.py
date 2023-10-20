# Part of Odoo. See LICENSE file for full copyright and licensing details.
from urllib.parse import urlencode
import ast

from odoo import Command

from odoo.tests import HttpCase, tagged


def _urlencode_kwargs(**kwargs):
    return urlencode(kwargs)


@tagged("post_install_l10n", "post_install", "-at_install")
class BaseAutomationTestUi(HttpCase):
    def _neutralize_preexisting_automations(self, neutralize_action=True):
        self.env["base.automation"].with_context(active_test=False).search([]).write({"active": False})
        if neutralize_action:
            context = ast.literal_eval(self.env.ref("base_automation.base_automation_act").context)
            del context["active_test"]
            self.env.ref("base_automation.base_automation_act").context = str(context)

    def test_01_base_automation_tour(self):
        self._neutralize_preexisting_automations()
        self.start_tour(f"/web?debug=tests#{_urlencode_kwargs(action=self.env.ref('base_automation.base_automation_act').id)}", "test_base_automation", login="admin")
        base_automation = self.env["base.automation"].search([])
        self.assertEqual(base_automation.model_id.model, "res.partner")
        self.assertEqual(base_automation.trigger, "on_create_or_write")
        self.assertEqual(base_automation.action_server_ids.state, "object_write")  # only one action
        self.assertEqual(base_automation.action_server_ids.model_name, "res.partner")
        self.assertEqual(base_automation.action_server_ids.update_field_id.name, "function")
        self.assertEqual(base_automation.action_server_ids.value, "Test")

    def test_base_automation_on_tag_added(self):
        self._neutralize_preexisting_automations()
        self.env["test_base_automation.tag"].create({"name": "test"})
        self.start_tour(f"/web?debug=tests#{_urlencode_kwargs(action=self.env.ref('base_automation.base_automation_act').id)}", "test_base_automation_on_tag_added", login="admin")

    def test_open_automation_from_grouped_kanban(self):
        self._neutralize_preexisting_automations()

        test_view = self.env["ir.ui.view"].create(
            {
                "name": "test_view",
                "model": "test_base_automation.project",
                "type": "kanban",
                "arch": """
                    <kanban default_group_by="tag_ids">
                        <templates>
                            <t t-name="kanban-box">
                                <div class="oe_kanban_global_click">
                                    <div class="o_kanban_card_content">
                                        <field name="name" />
                                    </div>
                                </div>
                            </t>
                        </templates>
                    </kanban>
                """,
            }
        )
        test_action = self.env["ir.actions.act_window"].create(
            {
                "name": "test action",
                "res_model": "test_base_automation.project",
                "view_ids": [Command.create({"view_id": test_view.id, "view_mode": "kanban"})],
            }
        )
        tag = self.env["test_base_automation.tag"].create({"name": "test tag"})
        self.env["test_base_automation.project"].create({"name": "test", "tag_ids": [Command.link(tag.id)]})

        _hash = _urlencode_kwargs(action=test_action.id)
        self.start_tour(f"/web?debug=0#{_hash}", "test_open_automation_from_grouped_kanban", login="admin")
        base_auto = self.env["base.automation"].search([])
        self.assertEqual(base_auto.name, "From Tour")
        self.assertEqual(base_auto.model_name, "test_base_automation.project")
        self.assertEqual(base_auto.trigger_field_ids.name, "tag_ids")
        self.assertEqual(base_auto.trigger, "on_tag_set")
        self.assertEqual(base_auto.trg_field_ref_model_name, "test_base_automation.tag")
        self.assertEqual(base_auto.trg_field_ref, tag.id)

    def test_kanban_automation_view_stage_trigger(self):
        self._neutralize_preexisting_automations()

        project_model = self.env.ref('test_base_automation.model_test_base_automation_project')
        stage_field = self.env['ir.model.fields'].search([
            ('model_id', '=', project_model.id),
            ('name', '=', 'stage_id'),
        ])
        test_stage = self.env['test_base_automation.stage'].create({'name': 'Stage value'})

        automation = self.env["base.automation"].create({
            "name": "Test Stage",
            "trigger": "on_stage_set",
            "model_id": project_model.id,
            "trigger_field_ids": [stage_field.id],
            "trg_field_ref": test_stage,
        })

        action = {
            "name": "Set Active To False",
            "base_automation_id": automation.id,
            "state": "object_write",
            "update_path": "user_ids.active",
            "value": False,
            "model_id": project_model.id
        }
        automation.write({"action_server_ids": [Command.create(action)]})

        self.start_tour(
            f"/web#{_urlencode_kwargs(action=self.env.ref('base_automation.base_automation_act').id)}",
            "test_kanban_automation_view_stage_trigger", login="admin"
        )

    def test_kanban_automation_view_time_trigger(self):
        self._neutralize_preexisting_automations()
        model = self.env.ref("base.model_res_partner")

        date_field = self.env['ir.model.fields'].search([
            ('model_id', '=', model.id),
            ('name', '=', 'date'),
        ])

        self.env["base.automation"].create({
            "name": "Test Date",
            "trigger": "on_time",
            "model_id": model.id,
            "trg_date_range": 1,
            "trg_date_range_type": "hour",
            "trg_date_id": date_field.id,
        })

        self.start_tour(
            f"/web#{_urlencode_kwargs(action=self.env.ref('base_automation.base_automation_act').id)}",
            "test_kanban_automation_view_time_trigger", login="admin"
        )

    def test_kanban_automation_view_time_updated_trigger(self):
        self._neutralize_preexisting_automations()
        model = self.env.ref("base.model_res_partner")

        self.env["base.automation"].create({
            "name": "Test Date",
            "trigger": "on_time_updated",
            "model_id": model.id,
            "trg_date_range": 1,
            "trg_date_range_type": "hour",
        })

        self.start_tour(
            f"/web#{_urlencode_kwargs(action=self.env.ref('base_automation.base_automation_act').id)}",
            "test_kanban_automation_view_time_updated_trigger", login="admin"
        )

    def test_kanban_automation_view_create_action(self):
        self._neutralize_preexisting_automations()
        model = self.env.ref("base.model_res_partner")

        automation = self.env["base.automation"].create({
            "name": "Test",
            "trigger": "on_create_or_write",
            "model_id": model.id,
        })

        action = {
            "name": "This name should not survive :)",
            "base_automation_id": automation.id,
            "state": "object_create",
            "value": "NameX",
            "model_id": model.id
        }

        automation.write({"action_server_ids": [Command.create(action)]})

        self.start_tour(
            f"/web#{_urlencode_kwargs(action=self.env.ref('base_automation.base_automation_act').id)}",
            "test_kanban_automation_view_create_action", login="admin"
        )

    def test_resize_kanban(self):
        self._neutralize_preexisting_automations()
        model = self.env.ref("base.model_res_partner")

        automation = self.env["base.automation"].create(
            {
                "name": "Test",
                "trigger": "on_create_or_write",
                "model_id": model.id,
            }
        )

        action = {
            "name": "Set Active To False",
            "base_automation_id": automation.id,
            "state": "object_write",
            "update_path": "active",
            "value": False,
            "model_id": model.id,
        }
        automation.write({"action_server_ids": [Command.create(action) for i in range(3)]})

        self.start_tour(
            f"/web#{_urlencode_kwargs(action=self.env.ref('base_automation.base_automation_act').id)}",
            "test_resize_kanban",
            login="admin",
        )

    def test_form_view(self):
        model = self.env.ref("base.model_res_partner")
        automation = self.env["base.automation"].create(
            {
                "name": "Test",
                "trigger": "on_create_or_write",
                "model_id": model.id,
            }
        )
        action = {
            "name": "Update Active",
            "base_automation_id": automation.id,
            "state": "object_write",
            "update_path": "active",
            "update_boolean_value": "false",
            "model_id": model.id,
        }
        automation.write(
            {"action_server_ids": [Command.create(dict(action, name=action["name"] + f" {i}", sequence=i)) for i in range(3)]}
        )
        self.assertEqual(
            automation.action_server_ids.mapped("name"),
            ["Update Active 0", "Update Active 1", "Update Active 2"],
        )

        onchange_link_passes = 0
        origin_link_onchange = type(self.env["ir.actions.server"]).onchange

        def _onchange_base_auto_link(self_model, *args):
            nonlocal onchange_link_passes
            onchange_link_passes += 1
            res = origin_link_onchange(self_model, *args)
            if onchange_link_passes == 1:
                default_keys = {k: v for k, v in self_model._context.items() if k.startswith("default_")}
                self.assertEqual(
                    default_keys,
                    {"default_model_id": model.id, "default_usage": "base_automation"},
                )
            if onchange_link_passes == 2:
                self.assertFalse(res["value"], "No change should be triggered here")
            if onchange_link_passes == 3:
                self.assertEqual(res["value"]["name"], "Add followers: ")

            return res

        self.patch(type(self.env["ir.actions.server"]), "onchange", _onchange_base_auto_link)

        self.start_tour(
            (
                f"/web?debug=0#{_urlencode_kwargs(action=self.env.ref('base_automation.base_automation_act').id, id=automation.id, view_type='form')}"
            ),
            "test_form_view_resequence_actions",
            login="admin",
        )
        self.assertEqual(onchange_link_passes, 3)
        self.assertEqual(
            automation.action_server_ids.mapped("name"),
            ["Update Active 2", "Update Active 0", "Update Active 1"],
        )

    def test_form_view_model_id(self):
        self.start_tour(
            (
                f"/web?debug=0#{_urlencode_kwargs(action=self.env.ref('base_automation.base_automation_act').id, view_type='form')}"
            ),
            "test_form_view_model_id",
            login="admin",
        )

    def test_form_view_custom_reference_field(self):
        self.env["test_base_automation.stage"].create({"name": "test stage"})
        self.env["test_base_automation.tag"].create({"name": "test tag"})
        self.start_tour(
            (
                f"/web?debug=0#{_urlencode_kwargs(action=self.env.ref('base_automation.base_automation_act').id, view_type='form')}"
            ),
            "test_form_view_custom_reference_field",
            login="admin",
        )

    def test_form_view_mail_triggers(self):
        self.start_tour(
            (
                f"/web?debug=0#{_urlencode_kwargs(action=self.env.ref('base_automation.base_automation_act').id, view_type='form')}"
            ),
            "test_form_view_mail_triggers",
            login="admin",
        )
