from odoo.tests import new_test_user, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestSetupWizard(AccountTestInvoicingCommon):
    def test_setup_bank_account(self):
        wizard = self.env["account.setup.bank.manual.config"].create(
            [
                {
                    "num_journals_without_account_bank": 1,
                    "linked_journal_id": False,
                    "acc_number": "BE15001559627230",
                    "bank_id": self.env["res.bank"].create({"name": "Test bank"}).id,
                    "bank_bic": False,
                }
            ]
        )
        self.assertTrue(wizard)

    def test_an_accounting_manager_sets_up_a_bank_account_without_contact_rights(self):
        manager = new_test_user(
            self.env,
            login="bank_setup_manager",
            groups="base.group_user,account.group_account_manager",
            company_id=self.env.company.id,
        )
        bank = self.env["res.bank"].create({"name": "Manager bank"})
        wizard = (
            self.env["account.setup.bank.manual.config"]
            .with_user(manager)
            .create(
                {
                    "num_journals_without_account_bank": 1,
                    "linked_journal_id": False,
                    "acc_number": "BE71096123456769",
                    "bank_id": bank.id,
                }
            )
        )
        self.assertEqual(
            wizard.sudo().bank_account_id.partner_id, self.env.company.partner_id
        )
        customer_account = self.env["res.partner.bank.account"].create(
            {"acc_number": "BE68539007547034", "partner_id": self.partner_a.id}
        )
        self.assertFalse(customer_account.with_user(manager).has_access("write"))
