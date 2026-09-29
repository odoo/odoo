from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAssetDepartmentScope(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent_company = cls.env["res.company"].create({"name": "Asset Scope Test Foundation"})
        cls.company_a = cls.env["res.company"].create({
            "name": "Asset Scope Test Branch A",
            "parent_id": cls.parent_company.id,
        })
        cls.company_b = cls.env["res.company"].create({
            "name": "Asset Scope Test Branch B",
            "parent_id": cls.parent_company.id,
        })
        cls.department_a = cls.env["hr.department"].create({
            "name": "Asset Department A",
            "company_id": cls.company_a.id,
        })
        cls.department_b = cls.env["hr.department"].create({
            "name": "Asset Department B",
            "company_id": cls.company_b.id,
        })
        cls.category = cls.env["sifnext.asset.category"].create({
            "name": "Asset Department Test Category",
            "useful_life_years": 1,
        })
        cls.asset_account = cls.env["sif.coa"].create({
            "code": "ASSET-DEPT-TEST",
            "name": "Asset Department Test",
            "account_type": "asset",
        })
        cls.cash_account = cls.env["sif.coa"].create({
            "code": "ASSET-CASH-TEST",
            "name": "Asset Cash Test",
            "account_type": "asset",
        })

    def _asset_values(self, company, department):
        return {
            "name": "Asset Department Scope Test",
            "category_id": self.category.id,
            "company_id": company.id,
            "owner_department_id": department.id,
            "project_code": "ASSETTEST",
            "acquisition_date": "2026-09-01",
            "depreciation_start_date": "2026-09-01",
            "acquisition_value": 1200.0,
            "currency_id": company.currency_id.id,
            "account_asset_id": self.asset_account.id,
            "account_cash_id": self.cash_account.id,
        }

    def test_asset_rejects_department_from_other_branch(self):
        model = self.env["sifnext.asset"].sudo().with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id],
        )
        with self.assertRaises(ValidationError):
            model.create(self._asset_values(self.company_a, self.department_b))

    def test_asset_posting_keeps_company_and_department_on_journal(self):
        asset = self.env["sifnext.asset"].sudo().with_context(
            allowed_company_ids=[self.company_a.id],
        ).create(self._asset_values(self.company_a, self.department_a))

        asset.action_post_acquisition()

        self.assertEqual(asset.purchase_journal_id.company_id, self.company_a)
        self.assertEqual(asset.purchase_journal_id.department_id, self.department_a)

    def test_finance_central_can_read_branches_but_cannot_edit_assets(self):
        asset_a = self.env["sifnext.asset"].sudo().with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id],
        ).create(self._asset_values(self.company_a, self.department_a))
        asset_b = self.env["sifnext.asset"].sudo().with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id],
        ).create(self._asset_values(self.company_b, self.department_b))
        finance_central = self.env["res.users"].create({
            "name": "Asset Finance Central",
            "login": "asset_scope_finance_central",
            "company_id": self.company_a.id,
            "company_ids": [(6, 0, [self.company_a.id, self.company_b.id])],
            "group_ids": [(6, 0, [self.env.ref("sif_keuangan.group_sif_keuangan_central_readonly").id])],
        })

        scoped = self.env["sifnext.asset"].with_user(finance_central).with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id],
        )
        self.assertEqual(set(scoped.search([("id", "in", [asset_a.id, asset_b.id])]).ids), {
            asset_a.id,
            asset_b.id,
        })
        with self.assertRaises(AccessError):
            scoped.browse(asset_a.id).write({"name": "Tidak boleh diubah"})
