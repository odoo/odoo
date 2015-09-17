import logging

from openerp.tests.common import TransactionCase
from openerp import SUPERUSER_ID
from openerp import api
from openerp.modules.registry import RegistryManager
from openerp.tools import config
DB = config['db_name']

_logger = logging.getLogger(__name__)

class AccountingTestCase(TransactionCase):
    """ This class extends the base TransactionCase, in order to test the
    accounting with localization setups. It is configured to run the tests after
    the installation of all modules, and will SKIP TESTS and return a success if
    it cannot find an already configured accounting (which means no localization
    module has been installed).
    """

    post_install = True
    at_install = False

    def _check_accounting_configured(self):
        # minimal setUp() similar to the one of TransactionCase, although we
        # can't use the regular setUp() because we want to assume the accounting
        # is already configured when making the setUp of tests.
        self.registry = RegistryManager.get(DB)
        self.cr = self.cursor()
        self.uid = SUPERUSER_ID
        self.env = api.Environment(self.cr, self.uid, {})
        # having at least one account created means the accounting is ready to be tested
        domain = [('company_id', '=', self.env.ref('base.main_company').id)]
        res = bool(self.env['account.account'].search_count(domain))
        # rollback and close the cursor, and reset the environment
        self.tearDown()
        return res

    def run(self, result=None):
        if not self._check_accounting_configured():
            # no chart of account is available, so skip the tests and consider
            # it as a success
            _logger.warning("No chart of account, skip %s", self)
            return
        super(AccountingTestCase, self).run(result=result)
