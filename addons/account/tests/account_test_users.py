from openerp.tests.common import TransactionCase

class AccountTestUsers(TransactionCase):
    """Tests for diffrent type of user 'Accountant/Financial Manager' and added groups"""

    def setUp(self):
        super(AccountTestUsers, self).setUp()
        self.res_user_model = self.env['res.users']
        self.main_company = self.env.ref('base.main_company')
        self.main_partner = self.env.ref('base.main_partner')
        self.main_bank = self.env.ref('base.res_bank_1')
        res_users_account_user = self.ref('account.group_account_user')
        res_users_account_manager = self.ref('account.group_account_user')
        partner_manager = self.ref('base.group_partner_manager')
        self.account_user = (int(self.res_user_model.create(dict(
            name="Accountant",
            company_id=self.main_company.id,
            login="acc",
            password="acc",
            email="accountuser@yourcompany.com",
            groups_id=[(6, 0, [res_users_account_user, partner_manager])]
        ))))
        self.account_manager = (int(self.res_user_model.create(dict(
            name="Financial Manager",
            company_id=self.main_company.id,
            login="fm",
            password="fm",
            email="accountmanager@yourcompany.com",
            groups_id=[(6, 0, [res_users_account_manager, partner_manager])]
        ))))
