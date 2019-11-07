from odoo.addons.account.tests.account_test_classes import AccountingTestCase


class AccountTestUsers(AccountingTestCase):

    """Tests for diffrent type of user 'Accountant/Adviser' and added groups"""

    @classmethod
    def setUpClass(cls):
        super(AccountTestUsers, cls).setUpClass()
        cls.res_user_model = cls.env['res.users']
        cls.main_company = cls.env.ref('base.main_company')
        cls.main_partner = cls.env.ref('base.main_partner')
        cls.main_bank = cls.env.ref('base.res_bank_1')
        res_users_account_user = cls.env.ref('account.group_account_invoice')
        res_users_account_manager = cls.env.ref('account.group_account_manager')
        partner_manager = cls.env.ref('base.group_partner_manager')
        cls.tax_model = cls.env['account.tax']
        cls.account_model = cls.env['account.account']
        cls.account_type_model = cls.env['account.account.type']
        cls.currency_euro = cls.env.ref('base.EUR')

        cls.account_user = cls.res_user_model.with_context({'no_reset_password': True}).create(dict(
            name="Accountant",
            company_id=cls.main_company.id,
            login="acc",
            email="accountuser@yourcompany.com",
            groups_id=[(6, 0, [res_users_account_user.id, partner_manager.id])]
        ))
        cls.account_manager = cls.res_user_model.with_context({'no_reset_password': True}).create(dict(
            name="Adviser",
            company_id=cls.main_company.id,
            login="fm",
            email="accountmanager@yourcompany.com",
            groups_id=[(6, 0, [res_users_account_manager.id, partner_manager.id])]
        ))
