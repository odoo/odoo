from lxml import etree

from odoo.addons.device.tests.common import DeviceTransactionCase


class TestDeviceScreens(DeviceTransactionCase):
    def _rendered(self, action_xmlid):
        action = self.env.ref(action_xmlid)
        views = self.env["device.device"].get_views(action.views)["views"]
        rendered = {}
        for view_type, view in views.items():
            data = self.env["ir.model.data"].search(
                [("model", "=", "ir.ui.view"), ("res_id", "=", view["id"])], limit=1
            )
            rendered[view_type] = f"{data.module}.{data.name}" if data else view["id"]
        return rendered

    def test_the_device_action_renders_this_modules_views(self):
        rendered = self._rendered("device.action_device_device")
        self.assertEqual(rendered["list"], "device.view_device_device_list")
        self.assertEqual(rendered["kanban"], "device.view_device_device_kanban")
        self.assertEqual(rendered["form"], "device.view_device_device_form")

    def test_the_dashboard_action_renders_the_dashboard_views(self):
        rendered = self._rendered("device.action_device_dashboard")
        self.assertEqual(rendered["kanban"], "device.device_dashboard_kanban_view")
        self.assertEqual(rendered["graph"], "device.device_dashboard_graph_view")
        self.assertEqual(rendered["pivot"], "device.device_dashboard_pivot_view")

    def test_every_measure_of_the_dashboard_pivot_can_aggregate(self):
        view = self.env.ref("device.device_dashboard_pivot_view")
        arch = etree.fromstring(view.arch)
        for node in arch.xpath("//field[@type='measure']"):
            name = node.get("name")
            with self.subTest(measure=name):
                self.env["device.device"]._read_group(
                    [], groupby=[], aggregates=[f"{name}:sum"]
                )

    def test_a_menu_item_leads_to_the_dashboard(self):
        action = self.env.ref("device.action_device_dashboard")
        menus = self.env["ir.ui.menu"].search(
            [("action", "=", f"ir.actions.act_window,{action.id}")]
        )
        self.assertTrue(menus, "the dashboard action is reachable from no menu")

    def test_the_plain_kanban_is_what_the_model_answers_with(self):
        default = self.env["device.device"].get_view(view_type="kanban")
        self.assertEqual(
            default["id"],
            self.env.ref("device.view_device_device_kanban").id,
            "the dashboard kanban silently answers for the whole model",
        )

    _OWN_ACTIONS = (
        "device.action_device_device",
        "device.action_device_dashboard",
    )

    def _own_actions(self):
        return self.env["ir.actions.act_window"].browse(
            [self.env.ref(xmlid).id for xmlid in self._OWN_ACTIONS]
        )

    def test_every_primary_device_view_is_reachable(self):
        actions = self._own_actions()
        reachable = set(actions.mapped("search_view_id").ids)
        for action in actions:
            views = self.env["device.device"].get_views(action.views)["views"]
            reachable.update(view["id"] for view in views.values())

        unreachable = []
        for view in self.env["ir.ui.view"].search(
            [("model", "=", "device.device"), ("inherit_id", "=", False)]
        ):
            data = self.env["ir.model.data"].search(
                [("model", "=", "ir.ui.view"), ("res_id", "=", view.id)], limit=1
            )
            if view.id in reachable or data.module != "device":
                continue
            unreachable.append(f"{data.module}.{data.name}" if data else str(view.id))
        self.assertFalse(
            unreachable, f"views no action can display: {sorted(unreachable)}"
        )

    def test_every_device_action_pins_its_search_view(self):
        unpinned = [
            action.display_name
            for action in self._own_actions()
            if not action.search_view_id
        ]
        self.assertFalse(unpinned, f"actions with no search_view_id: {unpinned}")


class TestAutoReconnectOverride(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls._create_device_profile(name="Reconnect Config")
        assert cls.config.auto_reconnect, "fixture: the profile ships auto-reconnect ON"

    def test_no_override_inherits_the_profile(self):
        device = self._create_device_device(config=self.config, identifier="AR-INHERIT")
        self.assertTrue(device.use_auto_reconnect)
        self.config.auto_reconnect = False
        device.invalidate_recordset()
        self.assertFalse(device.use_auto_reconnect)
        self.config.auto_reconnect = True

    def test_a_device_can_be_switched_off_while_the_profile_is_on(self):
        device = self._create_device_device(
            config=self.config,
            identifier="AR-OFF",
            auto_reconnect_override="off",
        )
        self.assertTrue(self.config.auto_reconnect, "the profile is still ON")
        self.assertFalse(
            device.use_auto_reconnect,
            "a decommissioned device cannot be taken out of the reconnect cron",
        )

    def test_a_device_can_be_switched_on_while_the_profile_is_off(self):
        self.config.auto_reconnect = False
        device = self._create_device_device(
            config=self.config, identifier="AR-ON", auto_reconnect_override="on"
        )
        self.assertTrue(device.use_auto_reconnect)
        self.config.auto_reconnect = True

    def test_the_cron_domain_honours_the_off_switch(self):
        off = self._create_device_device(
            config=self.config,
            identifier="AR-CRON-OFF",
            auto_reconnect_override="off",
            connection_state="error",
        )
        eligible = self.env["device.device"].search(
            [
                ("use_auto_reconnect", "=", True),
                ("connection_state", "in", ["disconnected", "error"]),
            ]
        )
        self.assertNotIn(off, eligible)


class TestReconnectStateIsVisible(DeviceTransactionCase):
    def test_the_backoff_state_appears_on_the_device_form(self):
        arch = etree.fromstring(
            self.env["device.device"].get_view(
                view_id=self.env.ref("device.view_device_device_form").id
            )["arch"]
        )
        shown = {node.get("name") for node in arch.xpath("//field")}
        for name in ("use_auto_reconnect", "connection_id", "link_mode"):
            with self.subTest(field=name):
                self.assertIn(
                    name,
                    shown,
                    "an administrator cannot see why a device is not reconnecting",
                )
