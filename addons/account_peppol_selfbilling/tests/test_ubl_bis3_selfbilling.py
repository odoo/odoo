from odoo import Command
from odoo.addons.account_edi_ubl_cii.tests.common import TestUblBis3Common, TestUblCiiBECommon

from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install', *TestUblBis3Common.extra_tags)
class TestUblBis3SelfBilling(TestUblBis3Common, TestUblCiiBECommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.self_billing_journal = cls.env['account.journal'].create({
            'name': 'Self Billing',
            'code': 'SB',
            'type': 'purchase',
            'is_self_billing': True,
        })

    def subfolder(self):
        return ''

    def test_export_selfbilling(self):
        tax_21 = self.percent_tax(21.0)
        product = self._create_product(lst_price=100.0, taxes_id=tax_21)
        invoice = self._create_invoice_one_line(
            move_type='in_invoice',
            journal_id=self.self_billing_journal.id,
            product_id=product,
            price_unit=100.0,
            tax_ids=tax_21,
            partner_id=self.partner_be,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_selfbilling')

    def test_export_selfbilling_reverse_charge(self):
        # We add a VAT number so that the reverse-charge tax is correctly given TaxCategoryCode K (intra-community supply)
        self.partner_lu_dig.write({
            'peppol_endpoint': 'LU12345613',
            'vat': 'LU12345613',
        })
        tax_21_reverse_charge = self.percent_tax(
            21.0,
            invoice_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
            refund_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
        )
        product = self._create_product(lst_price=100.0, taxes_id=tax_21_reverse_charge)

        invoice = self._create_invoice_one_line(
            move_type='in_invoice',
            journal_id=self.self_billing_journal.id,
            product_id=product,
            price_unit=100.0,
            tax_ids=tax_21_reverse_charge,
            partner_id=self.partner_lu_dig,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_selfbilling_reverse_charge')

    def test_export_selfbilling_credit_note(self):
        tax_21 = self.percent_tax(21.0)
        product = self._create_product(lst_price=100.0, taxes_id=tax_21)

        invoice = self._create_invoice_one_line(
            move_type='in_refund',
            journal_id=self.self_billing_journal.id,
            product_id=product,
            price_unit=100.0,
            tax_ids=tax_21,
            partner_id=self.partner_be,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_selfbilling_credit_note')
