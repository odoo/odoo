from odoo.addons.account.tests.account_test_classes import AccountingTestCase


class AccountTestUsers(AccountingTestCase):

    """Tests for diffrent type of user 'Accountant/Adviser' and added groups"""

    def setUp(self):
        super(AccountTestUsers, self).setUp()
        self.res_user_model = self.env['res.users']
        self.main_company = self.env.ref('base.main_company')
        self.main_partner = self.env.ref('base.main_partner')
        self.main_bank = self.env.ref('base.res_bank_1')
        res_users_account_user = self.env.ref('account.group_account_invoice')
        res_users_account_manager = self.env.ref('account.group_account_manager')
        partner_manager = self.env.ref('base.group_partner_manager')
        self.tax_model = self.env['account.tax']
        self.account_model = self.env['account.account']
        self.account_type_model = self.env['account.account.type']
        self.currency_euro = self.env.ref('base.EUR')

        self.account_user = self.res_user_model.with_context({'no_reset_password': True}).create(dict(
            name="Accountant",
            company_id=self.main_company.id,
            login="acc",
            email="accountuser@yourcompany.com",
            groups_id=[(6, 0, [res_users_account_user.id, partner_manager.id])]
        ))
        self.account_manager = self.res_user_model.with_context({'no_reset_password': True}).create(dict(
            name="Adviser",
            company_id=self.main_company.id,
            login="fm",
            email="accountmanager@yourcompany.com",
            groups_id=[(6, 0, [res_users_account_manager.id, partner_manager.id])]
        ))
