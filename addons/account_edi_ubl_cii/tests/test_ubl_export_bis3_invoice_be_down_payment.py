from odoo.tests import tagged

from odoo.addons.account_edi_ubl_cii.tests.test_ubl_export_bis3_be import TestUblExportBis3BE


@tagged('post_install_l10n', 'post_install', '-at_install', *TestUblExportBis3BE.extra_tags)
class TestUblExportBis3InvoiceBEDownPayment(TestUblExportBis3BE):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ensure_installed('sale')

    @classmethod
    def get_default_groups(cls):
        groups = super().get_default_groups()
        return groups | cls.quick_ref('sales_team.group_sale_manager')

    def test_sale_order_down_payment(self):
        tax_21 = self.percent_tax(21.0)
        product = self._create_product(lst_price=3015.19, taxes_id=tax_21)
        sale_order = self._create_sale_order_one_line(
            partner_id=self.partner_be.id,
            product_id=product,
        )
        self.assertRecordValues(sale_order, [{
            'amount_untaxed': 3015.19,
            'amount_tax': 633.19,
            'amount_total': 3648.38,
        }])

        invoice = self._create_down_payment_invoice(
            sale_order=sale_order,
            amount_type='percentage',
            amount=40.0,
            post=True,
        )
        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_sale_order_down_payment_first_invoice')
