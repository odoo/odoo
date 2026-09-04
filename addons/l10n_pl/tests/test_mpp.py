from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestL10nPlMPP(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('pl')
    def setUpClass(cls):
        super().setUpClass()

        cls.split_payment_product = cls._create_product(
            name='split_payment_product',
            l10n_pl_subject_to_split_payment=True,
        )
        cls.split_payment_category = cls.env['product.category'].create({
            'name': 'split_payment_category',
            'l10n_pl_subject_to_split_payment': True,
        })
        cls.split_payment_category_product = cls._create_product(
            name='split_payment_product',
            categ_id=cls.split_payment_category.id,
        )
        cls.partner_a.write({
            'country_id': cls.env.ref('base.pl'),
            'vat': 'PL1234567883',
        })

    @classmethod
    def _create_invoice_line(cls, move_id, product_id=None, price_unit=None):
        assert price_unit is not None or product_id is not None, "Either `price_unit` or `product_id` must be filled!"
        return cls.env['account.move.line'].create({
            'move_id': move_id,
            'product_id': product_id,
            'price_unit': price_unit,
        })

    def test_mpp_product_subject_to_split_payment(self):
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=1000),
                self._prepare_invoice_line(product_id=self.product_b, price_unit=1000),
            ],
        )
        self.assertFalse(invoice.l10n_pl_mpp)
        self.assertEqual(invoice.l10n_pl_mpp_mode, 'auto')

        # Adding a line with sensitive product
        invoice.invoice_line_ids += self.env['account.move.line'].create({
            'move_id': invoice.id,
            'product_id': self.split_payment_product.id,
            'price_unit': 10,
        })

        self.assertFalse(invoice.l10n_pl_mpp)
        self.assertEqual(invoice.l10n_pl_mpp_mode, 'auto')

        # Adding a line to have total > 15000
        invoice.invoice_line_ids += self.env['account.move.line'].create({
            'move_id': invoice.id,
            'product_id': self.product_a.id,
            'price_unit': 13000,
        })

        self.assertTrue(invoice.l10n_pl_mpp)
        self.assertEqual(invoice.l10n_pl_mpp_mode, 'auto')

        # Change the partner to a person and not a company
        invoice.partner_id = self.partner_b
        self.assertFalse(invoice.l10n_pl_mpp)
        self.assertEqual(invoice.l10n_pl_mpp_mode, 'auto')

    def test_mpp_product_category_subject_to_split_payment(self):
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=10000),
                self._prepare_invoice_line(product_id=self.product_b, price_unit=10000),
            ],
        )
        self.assertFalse(invoice.l10n_pl_mpp)
        self.assertEqual(invoice.l10n_pl_mpp_mode, 'auto')

        # Adding a line with product having a sensitive category
        invoice.invoice_line_ids += self.env['account.move.line'].create({
            'move_id': invoice.id,
            'product_id': self.split_payment_category_product.id,
            'price_unit': 10,
        })
        self.assertTrue(invoice.l10n_pl_mpp)
        self.assertEqual(invoice.l10n_pl_mpp_mode, 'auto')

    def test_mpp_manually_change_value(self):
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=1000),
                self._prepare_invoice_line(product_id=self.product_b, price_unit=1000),
            ],
        )
        self.assertFalse(invoice.l10n_pl_mpp)
        self.assertEqual(invoice.l10n_pl_mpp_mode, 'auto')

        # Adding a line with expensive sensitive product
        invoice.invoice_line_ids += self.env['account.move.line'].create({
            'move_id': invoice.id,
            'product_id': self.split_payment_product.id,
            'price_unit': 15000,
        })
        self.assertTrue(invoice.l10n_pl_mpp)
        self.assertEqual(invoice.l10n_pl_mpp_mode, 'auto')

        # Manually uncheck the MPP
        invoice.l10n_pl_mpp = False
        self.assertFalse(invoice.l10n_pl_mpp)
        self.assertEqual(invoice.l10n_pl_mpp_mode, 'manual')

        # Even if we add a new line with sensitive product, MPP must stay at False
        invoice.invoice_line_ids += self.env['account.move.line'].create({
            'move_id': invoice.id,
            'product_id': self.split_payment_product.id,
            'price_unit': 100,
        })
        self.assertFalse(invoice.l10n_pl_mpp)
        self.assertEqual(invoice.l10n_pl_mpp_mode, 'manual')

        # MPP must stay False after posting the invoice
        invoice.action_post()
        self.assertFalse(invoice.l10n_pl_mpp)
        self.assertEqual(invoice.l10n_pl_mpp_mode, 'manual')
