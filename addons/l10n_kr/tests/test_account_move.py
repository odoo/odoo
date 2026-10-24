# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nKrAccountMove(AccountTestInvoicingCommon):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    @AccountTestInvoicingCommon.setup_country('kr')
    def setUpClass(cls):
        super().setUpClass()

    def test_issuance_type_protected_by_tax_lock_date(self):
        bill = self._create_invoice(
            move_type='in_invoice',
            invoice_date='2024-01-15',
            l10n_kr_issuance_type='tax_invoice',
            invoice_line_ids=[self._prepare_invoice_line(
                price_unit=1000.0,
                tax_ids=self.env['account.chart.template'].ref('l10n_kr_Purchase_10'),
            )],
            post=True,
        )
        bill.company_id.tax_lock_date = fields.Date.from_string('2024-01-31')

        # The proof of issuance decides the VAT report box: it can't change once the period is locked.
        with self.assertRaisesRegex(UserError, "already issued tax statement"):
            bill.l10n_kr_issuance_type = 'card_payment'

        # Writing the same value is not a change.
        bill.l10n_kr_issuance_type = 'tax_invoice'

    def test_edocument_number_not_copied(self):
        invoice = self._create_invoice(
            move_type='out_invoice',
            invoice_date='2024-01-15',
            l10n_kr_edocument_number='202401154100000012345678',
            post=True,
        )

        self.assertFalse(invoice.copy().l10n_kr_edocument_number)
        self.assertFalse(invoice._reverse_moves().l10n_kr_edocument_number)
