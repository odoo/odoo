# -*- coding: utf-8 -*-
from openerp.tests.common import HttpCase

class AccountingTestCase(HttpCase):
    """ This class extends the base TransactionCase, in order to test the
    accounting with localization setups. It is configured to run the tests after
    the installation of all modules, and will SKIP TESTS ifit  cannot find an already
    configured accounting (which means no localization module has been installed).
    """

    post_install = True
    at_install = False

    def setUp(self):
        super(AccountingTestCase, self).setUp()
        domain = [('company_id', '=', self.env.ref('base.main_company').id)]
        if not self.env['account.account'].search_count(domain):
            self.skipTest("No Chart of account found")
