# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from freezegun import freeze_time
import logging
from pytz import timezone

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestSaEdiCommon

_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestAccountMove(TestSaEdiCommon):

    def testMismatchedCompaniesInvoice(self):
        with freeze_time(datetime(year=2022, month=9, day=5, hour=8, minute=20, second=2, tzinfo=timezone('Etc/GMT-3'))):
            invoice = self._create_invoice(name='INV/2022/00014', date='2022-09-05', date_due='2022-09-22', partner_id=self.partner_us,
                                        product_id=self.product_a, price=320.0, state='draft')
            invoice.write({
                'company_id': self.branch.id,
            })
            with self.assertRaises(UserError):
                invoice.action_post()
