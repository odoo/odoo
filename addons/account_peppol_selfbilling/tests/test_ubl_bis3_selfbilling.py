from odoo import Command
from odoo.addons.account_edi_ubl_cii.tests.common import TestUblBis3Common, TestUblCiiBECommon

from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install', *TestUblBis3Common.extra_tags)
class TestUblBis3SelfBilling(TestUblBis3Common, TestUblCiiBECommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.self_billing_journal = cls.env['account.journal'].create({
            'name': 'Self Billing',
            'code': 'SB',
            'type': 'purchase',
            'is_self_billing': True,
        })
        # Set up partner_be with peppol_endpoint for self-billing tests
        cls.partner_be.write({
            'peppol_eas': '0208',
            'peppol_endpoint': '0477472701',
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
            'peppol_eas': '9938',
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

    def test_self_billing_sequence_per_partner(self):
        """Test that self-billing invoices in a self-billing journal get a unique sequence per partner."""

        partner_a = self.partner_a
        partner_b = self.partner_b

        # Create and post invoice for partner_a
        invoice_a = self.env['account.move'].create({
            'partner_id': partner_a.id,
            'move_type': 'in_invoice',
            'journal_id': self.self_billing_journal.id,
            'invoice_date': '2026-04-20',
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id})],
        })
        invoice_a.action_post()

        # Create and post invoice for partner_b
        invoice_b = self.env['account.move'].create({
            'partner_id': partner_b.id,
            'move_type': 'in_invoice',
            'journal_id': self.self_billing_journal.id,
            'invoice_date': '2026-04-20',
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id})],
        })
        invoice_b.action_post()

        partner_a_id = str(partner_a.commercial_partner_id.id).zfill(5)
        partner_b_id = str(partner_b.commercial_partner_id.id).zfill(5)

        # Sequences should contain the partner id
        self.assertTrue((invoice_a.name.split('/')[0] or '').endswith(partner_a_id))
        self.assertTrue((invoice_b.name.split('/')[0] or '').endswith(partner_b_id))

        # Both should be 0001 since sequences are independent per partner
        self.assertTrue(invoice_a.name.endswith('0001'))
        self.assertTrue(invoice_b.name.endswith('0001'))
