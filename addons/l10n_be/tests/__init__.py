from . import test_do
from openerp.addons.account.tests import test_bank_statement_reconciliation

fast_suite = [
    test_bank_statement_reconciliation,
    test_do,
]
