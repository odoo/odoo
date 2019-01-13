#Accounting tests written in python should extend the class AccountingTestCase.
#See its doc for more info.

from . import test_account_customer_invoice
from . import test_account_move_closed_period
from . import test_account_supplier_invoice
from . import test_account_validate_account_move
from . import test_account_invoice_rounding
from . import test_bank_statement_reconciliation
from . import test_fiscal_position
from . import test_invoice_onchange
from . import test_reconciliation_widget
from . import test_payment
from . import test_product_id_change
from . import test_reconciliation
from . import test_search
from . import test_tax
from . import test_account_move_taxes_edition
from . import test_templates_consistency
from . import test_account_fiscal_year
from . import test_account_all_l10n
from . import test_reconciliation_matching_rules
