from . import account_test_users
from . import test_account_customer_invoice
from . import test_account_supplier_invoice
from . import test_chart_of_account
from . import test_account_validate_account_move
from . import test_tax
from . import test_search
# from . import test_reconciliation

fast_suite = [
    account_test_users,
    test_account_customer_invoice,
    test_account_supplier_invoice,
    test_chart_of_account,
    test_account_validate_account_move,
    test_tax,
    test_search,
    # test_reconciliation,
]
