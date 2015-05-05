from openerp.tests.common import TransactionCase
from openerp import SUPERUSER_ID
from openerp import api
from openerp.modules.registry import RegistryManager
from openerp.tools import config
DB = config['db_name']

class AccountingTestCase(TransactionCase):
    """
    This class extends the base TransactionCase, in order to test the accounting with localization setups.
    It is configured to run the tests after the installation of all modules, and will always return a success
    if it cannot find an already configured accounting (which means no localization module has been installed).
    """

    post_install = True
    at_install = False

    def _check_accounting_configured(self):
        #minimal setUp() similar to the one of TransactionCase, although we can't use the regular setUp()
        #because we want to assume the accounting is already configured when making the setUp of tests.
        self.registry = RegistryManager.get(DB)
        self.cr = self.cursor()
        self.uid = SUPERUSER_ID
        self.env = api.Environment(self.cr, self.uid, {})
        #having at least one account created means the accounting is ready to be tested
        res = bool(self.env['account.account'].search([('company_id', '=', self.env.ref('base.main_company').id)]))
        #close the cursor, eventually rolleback and reset the environment
        self.tearDown()
        return res

    def run(self, result=None):
        if not self._check_accounting_configured():
            #if the accounting if not ready to be tested, consider this test as a success
            return
        #once at least one localization is installed, we can run the tests
        super(AccountingTestCase, self).run(result=result)
