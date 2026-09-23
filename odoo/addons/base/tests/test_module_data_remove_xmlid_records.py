from odoo.tests.common import TransactionCase, tagged
from odoo.tools.module_data import remove_xmlid_records


@tagged("post_install", "-at_install")
class TestRemoveXmlidRecords(TransactionCase):
    def _xmlid(self, module, name, record):
        self.env["ir.model.data"].create(
            {
                "module": module,
                "name": name,
                "model": record._name,
                "res_id": record.id,
            }
        )

    def _names(self, record):
        return set(
            self.env["ir.model.data"]
            .search([("model", "=", record._name), ("res_id", "=", record.id)])
            .mapped("complete_name")
        )

    def test_a_record_only_the_module_names_is_deleted(self):
        view = self.env["ir.ui.view"].create(
            {"name": "probe", "type": "qweb", "arch": "<t t-name='probe'/>"}
        )
        self._xmlid("probe_gone", "probe_view", view)
        remove_xmlid_records(self.env.cr, "probe_gone", ["probe_view"])
        self.env.invalidate_all()
        self.assertFalse(view.exists())

    def test_a_record_another_module_names_keeps_living_without_the_xmlid(self):
        model = self.env["ir.model"]._get("res.partner")
        self._xmlid("probe_gone", "model_res_partner", model)
        remove_xmlid_records(self.env.cr, "probe_gone", ["model_res_partner"])
        self.env.invalidate_all()
        self.assertTrue(model.exists())
        self.assertNotIn("probe_gone.model_res_partner", self._names(model))
        self.assertIn("base.model_res_partner", self._names(model))

    def test_an_action_is_deleted_from_the_table_its_model_names(self):
        action = self.env["ir.actions.act_window"].create(
            {"name": "probe", "res_model": "res.partner"}
        )
        self._xmlid("probe_gone", "probe_action", action)
        self.assertEqual(
            remove_xmlid_records(self.env.cr, "probe_gone", ["probe_action"]), 1
        )
        self.env.invalidate_all()
        self.assertFalse(action.exists())
        self.assertFalse(self._names(action))

    def test_names_handed_as_a_generator_delete_the_record_and_its_xmlid(self):
        view = self.env["ir.ui.view"].create(
            {"name": "probe", "type": "qweb", "arch": "<t t-name='probe'/>"}
        )
        self._xmlid("probe_gone", "probe_view", view)
        remove_xmlid_records(self.env.cr, "probe_gone", (n for n in ["probe_view"]))
        self.env.invalidate_all()
        self.assertFalse(view.exists())
        self.assertFalse(self._names(view))

    def _cron(self, name):
        return self.env["ir.cron"].create(
            {
                "name": name,
                "model_id": self.env.ref("base.model_res_partner").id,
                "state": "code",
                "code": "model.browse()",
                "repeat_unit": "day",
                "repeat_interval": 1,
            }
        )

    def test_a_cron_goes_with_its_server_action_whichever_was_named_first(self):
        cron = self._cron("probe")
        action = cron.ir_actions_server_id
        other = self.env["ir.actions.server"].create(
            {
                "name": "probe",
                "model_id": self.env.ref("base.model_res_partner").id,
                "state": "code",
                "code": "model.browse()",
            }
        )
        # loading a cron from XML names its server action first, and a module's
        # plain server actions may sort before its crons
        self._xmlid("probe_gone", "probe_action", other)
        self._xmlid("probe_gone", "probe_cron_ir_actions_server", action)
        self._xmlid("probe_gone", "probe_cron", cron)
        names = ["probe_action", "probe_cron_ir_actions_server", "probe_cron"]
        self.env.flush_all()
        self.assertEqual(remove_xmlid_records(self.env.cr, "probe_gone", names), 3)
        self.env.invalidate_all()
        self.assertFalse(cron.exists())
        self.assertFalse(action.exists())
        self.assertFalse(other.exists())
        self.assertEqual(self._probe_names(), [])

    def test_a_record_still_referenced_is_kept_with_its_xmlid_and_named(self):
        cron = self._cron("probe kept")
        action = cron.ir_actions_server_id
        view = self.env["ir.ui.view"].create(
            {"name": "probe", "type": "qweb", "arch": "<t t-name='probe'/>"}
        )
        self._xmlid("probe_gone", "probe_action", action)
        self._xmlid("probe_gone", "probe_view", view)
        self.env.flush_all()
        with self.assertLogs("odoo.tools.module_data", "WARNING") as logs:
            removed = remove_xmlid_records(
                self.env.cr, "probe_gone", ["probe_action", "probe_view"]
            )
        self.assertEqual(removed, 1)
        self.assertIn("probe_gone.probe_action", logs.output[0])
        self.assertIn("ir_cron_ir_actions_server_id_fkey", logs.output[0])
        self.env.invalidate_all()
        self.assertTrue(action.exists())
        self.assertTrue(cron.exists())
        self.assertFalse(view.exists())
        self.assertEqual(self._probe_names(), ["probe_action"])

    def _raw_xmlid(self, name, model):
        self.env.cr.execute(
            "INSERT INTO ir_model_data (module, name, model, res_id) "
            "VALUES ('probe_gone', %s, %s, 1)",
            [name, model],
        )

    def _probe_names(self):
        self.env.cr.execute(
            "SELECT name FROM ir_model_data WHERE module = 'probe_gone' ORDER BY name"
        )
        return [name for (name,) in self.env.cr.fetchall()]

    def test_a_live_model_whose_table_is_not_found_keeps_its_xmlids(self):
        self.env.cr.execute(
            'INSERT INTO ir_model (model, name, "order", state) '
            "VALUES ('probe.ghost', '{\"en_US\": \"probe\"}', 'id', 'base')"
        )
        self._raw_xmlid("probe_ghost_record", "probe.ghost")
        with self.assertLogs("odoo.tools.module_data", "WARNING") as logs:
            remove_xmlid_records(self.env.cr, "probe_gone", ["probe_ghost_record"])
        self.assertIn("probe.ghost", logs.output[0])
        self.assertEqual(self._probe_names(), ["probe_ghost_record"])

    def test_the_xmlid_of_a_model_gone_with_its_table_is_dropped(self):
        self._raw_xmlid("probe_gone_record", "probe.long.gone")
        remove_xmlid_records(self.env.cr, "probe_gone", ["probe_gone_record"])
        self.assertEqual(self._probe_names(), [])
