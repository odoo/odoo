from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import TestHrCommon
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestEmployeeBankAccountAccess(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.officer = mail_new_test_user(
            cls.env,
            login="bank_officer",
            groups="base.group_user,hr.group_hr_user,base.group_partner_manager",
            name="Officer With Contact Creation",
        )
        cls.contact_creator = mail_new_test_user(
            cls.env,
            login="bank_contact_creator",
            groups="base.group_user,base.group_partner_manager",
            name="Contact Creation Only",
        )
        cls.employee = cls.env["hr.employee"].create({"name": "Banked Employee"})
        cls.customer = cls.env["res.partner"].create({"name": "Banked Customer"})

    def _create_account(self, user, partner, number):
        return (
            self.env["res.partner.bank.account"]
            .with_user(user)
            .create({"acc_number": number, "partner_id": partner.id})
        )

    def test_an_hr_officer_creates_and_edits_an_employee_s_bank_account(self):
        account = self._create_account(
            self.officer, self.employee.partner_id, "HR-0001"
        )
        account.write({"acc_number": "HR-0002"})
        self.assertEqual(account.sudo().acc_number, "HR-0002")

    def test_contact_creation_alone_keeps_out_of_employee_bank_accounts(self):
        with self.assertRaises(AccessError):
            self._create_account(
                self.contact_creator, self.employee.partner_id, "CC-0001"
            )
        account = self._create_account(
            self.officer, self.employee.partner_id, "CC-0002"
        )
        with self.assertRaises(AccessError):
            account.with_user(self.contact_creator).write({"acc_number": "CC-0003"})
        self.assertTrue(
            self._create_account(self.contact_creator, self.customer, "CC-0004")
        )
