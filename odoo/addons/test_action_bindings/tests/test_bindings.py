from odoo.tests import common


class TestActionBindings(common.TransactionCase):
    def test_bindings(self):
        Actions = self.env["ir.actions.actions"]

        partner_model = self.env["ir.model"]._get("res.partner")
        self.env["ir.actions.actions"].search(
            [
                ("binding_model_id", "=", partner_model.id),
            ]
        ).binding_model_id = False
        bindings = Actions.get_bindings("res.partner")
        self.assertFalse(bindings.get("action"))
        self.assertFalse(bindings.get("report"))

        action1 = self.env.ref("base.action_attachment")
        action2 = self.env.ref("base.ir_default_menu_action")
        action3 = self.env["ir.actions.report"].create(
            {
                "name": "tab-bindings report",
                "model": "res.partner",
                "report_name": "test_action_bindings.report_none",
                "report_type": "qweb-html",
            }
        )
        action1.binding_model_id = action2.binding_model_id = (
            action3.binding_model_id
        ) = self.env["ir.model"]._get("res.partner")

        bindings = Actions.get_bindings("res.partner")
        self.assertItemsEqual(
            bindings["action"],
            (action1 + action2).read(list(Actions._BINDING_READ_FIELDS)),
            "Wrong action bindings",
        )
        self.assertItemsEqual(
            bindings["report"],
            action3.read(list(Actions._BINDING_READ_FIELDS)),
            "Wrong action bindings",
        )

        group = self.env.ref("base.group_system")
        action2.group_ids += group
        self.env.user.group_ids -= group

        bindings = Actions.get_bindings("res.partner")
        self.assertItemsEqual(
            bindings["action"],
            action1.read(list(Actions._BINDING_READ_FIELDS)),
            "Wrong action bindings",
        )
        self.assertItemsEqual(
            bindings["report"],
            action3.read(list(Actions._BINDING_READ_FIELDS)),
            "Wrong action bindings",
        )


class TestBindingViewFilters(common.TransactionCase):
    def test_view_filters(self):
        for model_name, label in (("tab.a", "Action"), ("tab.b", "Record")):
            with self.subTest(model=model_name):
                Model = self.env[model_name]

                form_act = Model.get_views([(False, "form")], {"toolbar": True})[
                    "views"
                ]["form"]["toolbar"]["action"]
                self.assertEqual(
                    [a["name"] for a in form_act],
                    [f"{label} 1", f"{label} 2", f"{label} 3"],
                    "forms should have all actions",
                )

                list_act = Model.get_views([(False, "list")], {"toolbar": True})[
                    "views"
                ]["list"]["toolbar"]["action"]
                self.assertEqual(
                    [a["name"] for a in list_act],
                    [f"{label} 1", f"{label} 3"],
                    "lists should not have the form-only action",
                )

                kanban_act = Model.get_views([(False, "kanban")], {"toolbar": True})[
                    "views"
                ]["kanban"]["toolbar"]["action"]
                self.assertEqual(
                    [a["name"] for a in kanban_act],
                    [f"{label} 1"],
                    "kanban should only have the universal action",
                )
