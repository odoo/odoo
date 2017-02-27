#Accounting tests written in python should extend the class AccountingTestCase.
#See its doc for more info.

from . import test_account_customer_invoice
from . import test_account_move_closed_period
from . import test_account_supplier_invoice
from . import test_account_validate_account_move
from . import test_bank_statement_reconciliation
#TODO re-enableand fix this test
#from . import test_bank_stmt_reconciliation_widget_ui
from . import test_fiscal_position
from . import test_manual_reconciliation
from . import test_payment
from . import test_product_id_change
from . import test_reconciliation
from . import test_search
from . import test_tax
