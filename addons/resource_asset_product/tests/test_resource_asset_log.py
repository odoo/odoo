from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestResourceAssetLog(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Log = cls.env["resource.asset.log"]
        cls.kind = cls.env.ref("resource_asset.kind_tool")
        cls.company_b = cls.env["res.company"].create({"name": "Ledger B"})
        cls.service_category = cls.env["product.category"].create(
            {"name": "Workshop", "log_type": "service"}
        )
        cls.service = cls.env["product.product"].create(
            {"name": "Oil change", "categ_id": cls.service_category.id}
        )

    def _asset(self, **vals):
        return self.env["resource.asset"].create(
            {"name": "Compressor", "kind_id": self.kind.id, **vals}
        )

    def test_the_log_type_comes_from_the_product_category(self):
        log = self.Log.create(
            {"asset_id": self._asset().id, "product_id": self.service.id}
        )

        self.assertEqual(log.log_type, "service")
        self.assertIn(log, log.asset_id.log_ids)

    def test_a_log_belongs_to_its_assets_company(self):
        asset = self._asset(company_id=self.company_b.id)

        log = self.Log.create({"asset_id": asset.id})

        self.assertEqual(log.company_id, self.company_b)

    def test_a_log_is_not_born_cancelled(self):
        with self.assertRaises(UserError):
            self.Log.create({"asset_id": self._asset().id, "state": "cancelled"})

    def test_a_cancelled_log_returns_to_new_before_anything_else(self):
        log = self.Log.create({"asset_id": self._asset().id})
        log.action_set_cancelled()

        with self.assertRaises(UserError):
            log.action_set_done()

        log.action_set_new()
        log.action_set_done()
        self.assertEqual(log.state, "done")

    def test_an_assets_ledger_stays_in_one_company(self):
        asset = self._asset(company_id=False)
        self.Log.create({"asset_id": asset.id, "company_id": self.env.company.id})

        with (
            self.assertRaises(ValidationError),
            self.assertLogs(
                "odoo.addons.resource_asset_product.models.resource_asset_log",
                level="WARNING",
            ),
        ):
            self.Log.create({"asset_id": asset.id, "company_id": self.company_b.id})
