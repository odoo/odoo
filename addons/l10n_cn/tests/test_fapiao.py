# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nCnFapiao(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='cn'):
        super().setUpClass(chart_template_ref=chart_template_ref)

    def _create_vendor_bill(self):
        return self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
        })

    def test_fapiao_paper_eight_digits(self):
        bill = self._create_vendor_bill()
        bill.fapiao = '83182151'

    def test_fapiao_fully_digitized_twenty_digits(self):
        bill = self._create_vendor_bill()
        bill.fapiao = '26442000006283182151'

    def test_fapiao_invalid_length(self):
        bill = self._create_vendor_bill()
        with self.assertRaises(ValidationError):
            bill.fapiao = '123456789'

    def test_fapiao_non_numeric(self):
        bill = self._create_vendor_bill()
        with self.assertRaises(ValidationError):
            bill.fapiao = '1234567A'
