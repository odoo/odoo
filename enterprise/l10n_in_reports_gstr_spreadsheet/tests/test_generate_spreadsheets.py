from odoo.tests.common import TransactionCase, new_test_user
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGstr1Spreadsheet(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.regular_user = new_test_user(
            cls.env,
            login='user_gstr1',
            groups='base.group_user',
        )

        cls.admin_user = cls.env.ref('base.user_admin')

        cls.gstr_return_period = cls.env["l10n_in.gst.return.period"].create({
            'return_period_month_year': '042024',
        })

    def test_regenerate_promoted_admin(self):
        self.regular_user.groups_id += self.env.ref("account.group_account_manager")

        self.gstr_return_period.with_user(self.regular_user).generate_gstr1_spreadsheet()
        first_doc = self.gstr_return_period.gstr1_spreadsheet
        self.gstr_return_period.with_user(self.regular_user).generate_gstr1_spreadsheet()
        second_doc = self.gstr_return_period.gstr1_spreadsheet

        self.assertNotEqual(first_doc.id, second_doc.id, "Spreadsheet was not regenerated.")
        self.assertFalse(first_doc.active, "Old spreadsheet should be archived.")
