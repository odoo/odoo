import uuid
from freezegun import freeze_time
from unittest.mock import patch

from odoo import fields, sql_db, tools, Command
from odoo.tests import new_test_user, tagged
from odoo.addons.l10n_it_edi.tests.common import TestItEdi

import logging
_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdiImportNdd(TestItEdi):

    def test_l10n_it_payment_method_correctly_imported(self):
        self._assert_import_invoice('IT01234567890_FPR01.xml', [{
            'move_type': 'in_invoice',
            'invoice_date': fields.Date.from_string('2014-12-18'),
            'amount_untaxed': 5.0,
            'amount_tax': 1.1,
            'invoice_line_ids': [{
                'quantity': 5.0,
                'price_unit': 1.0,
                'debit': 5.0,
            }],
            'l10n_it_payment_method': 'MP01',
        }])
