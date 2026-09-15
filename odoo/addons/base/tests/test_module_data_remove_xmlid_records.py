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
