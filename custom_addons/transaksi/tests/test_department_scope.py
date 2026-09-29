from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestTransaksiDepartmentScope(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent_company = cls.env["res.company"].create({"name": "Transfer Scope Foundation"})
        cls.company_a = cls.env["res.company"].create({
            "name": "Transfer Scope Branch A",
            "parent_id": cls.parent_company.id,
        })
        cls.company_b = cls.env["res.company"].create({
            "name": "Transfer Scope Branch B",
            "parent_id": cls.parent_company.id,
        })
        cls.department_a = cls.env["hr.department"].create({
            "name": "Transfer Department A",
            "company_id": cls.company_a.id,
        })
        cls.department_b = cls.env["hr.department"].create({
            "name": "Transfer Department B",
            "company_id": cls.company_b.id,
        })
        cls.user_a = cls.env["res.users"].create({
            "name": "Transfer Scope User A",
            "login": "transfer_scope_user_a",
            "company_id": cls.company_a.id,
            "company_ids": [(6, 0, [cls.company_a.id])],
            "department_id": cls.department_a.id,
            "group_ids": [(6, 0, [cls.env.ref("transaksi.group_transaksi_finance").id])],
        })
        cls.finance_central = cls.env["res.users"].create({
            "name": "Transfer Finance Central",
            "login": "transfer_scope_finance_central",
            "company_id": cls.company_a.id,
            "company_ids": [(6, 0, [cls.company_a.id, cls.company_b.id])],
            "group_ids": [(6, 0, [cls.env.ref("sif_keuangan.group_sif_keuangan_central_readonly").id])],
        })

    def _transaction_values(self, company, department):
        return {
            "company_id": company.id,
            "department_id": department.id,
            "transfer_type": "single",
            "single_destination_account": "1234567890",
            "single_rupiah": 10000.0,
            "single_transfer_method": "bi_fast",
            "purpose": "operational",
        }

    def test_transfer_cannot_use_department_from_another_company(self):
        model = self.env["transaksi.transaction"].sudo().with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id],
        )
        with self.assertRaises(ValidationError):
            model.create(self._transaction_values(self.company_a, self.department_b))

    def test_transfer_finance_user_only_sees_allowed_branch(self):
        transactions = self.env["transaksi.transaction"].sudo().with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id],
        )
        transaction_a = transactions.create(self._transaction_values(self.company_a, self.department_a))
        transaction_b = transactions.create(self._transaction_values(self.company_b, self.department_b))

        visible = self.env["transaksi.transaction"].with_user(self.user_a).with_context(
            allowed_company_ids=[self.company_a.id],
        ).search([("id", "in", [transaction_a.id, transaction_b.id])])
        self.assertEqual(visible.ids, [transaction_a.id])

        central = self.env["transaksi.transaction"].with_user(self.finance_central).with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id],
        )
        self.assertEqual(
            set(central.search([("id", "in", [transaction_a.id, transaction_b.id])]).ids),
            {transaction_a.id, transaction_b.id},
        )
        with self.assertRaises(AccessError):
            central.browse(transaction_a.id).write({"remark": "Tidak boleh diubah"})
