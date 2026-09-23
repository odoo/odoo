from odoo.tests.common import TransactionCase, tagged
from odoo.tools.module_data import _table_of, remove_xmlid_records


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

    def test_the_table_of_every_registered_model_is_known(self):
        wrong = {
            name: (model._table, _table_of(name))
            for name, model in self.env.registry.items()
            if not model._abstract and model._auto and model._table != _table_of(name)
        }
        self.assertEqual(wrong, {})

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
