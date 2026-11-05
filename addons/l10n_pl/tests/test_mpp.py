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
            l10n_pl_split_payment=True,
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

    def test_mpp_value_on_invoice(self):
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=1000),
                self._prepare_invoice_line(product_id=self.product_b, price_unit=1000),
            ],
        )
        self.assertTrue(invoice.l10n_pl_mpp == 'no_mpp')

        # Adding a line with sensitive product
        invoice.invoice_line_ids += self.env['account.move.line'].create({
            'move_id': invoice.id,
            'product_id': self.split_payment_product.id,
            'price_unit': 10,
        })

        self.assertTrue(invoice.l10n_pl_mpp == 'no_mpp')

        # Adding a line to have total > 15000 PLN
        invoice.invoice_line_ids += self.env['account.move.line'].create({
            'move_id': invoice.id,
            'product_id': self.product_a.id,
            'price_unit': 13000,
        })

        self.assertTrue(invoice.l10n_pl_mpp == 'mpp')

        # Change the partner to a person and not a company
        invoice.partner_id = self.partner_b
        self.assertTrue(invoice.l10n_pl_mpp == 'no_mpp')

    def test_mpp_manually_change_value(self):
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=1000),
                self._prepare_invoice_line(product_id=self.product_b, price_unit=1000),
            ],
        )
        self.assertTrue(invoice.l10n_pl_mpp == 'no_mpp')

        # Adding a line with expensive sensitive product
        invoice.invoice_line_ids += self.env['account.move.line'].create({
            'move_id': invoice.id,
            'product_id': self.split_payment_product.id,
            'price_unit': 15000,
        })
        self.assertTrue(invoice.l10n_pl_mpp == 'mpp')

        # Manually uncheck the MPP
        invoice.l10n_pl_mpp = 'no_mpp'
        self.assertTrue(invoice.l10n_pl_mpp == 'no_mpp')

        # Adding a sensitive line should re-trigger the computation of MPP
        invoice.invoice_line_ids += self.env['account.move.line'].create({
            'move_id': invoice.id,
            'product_id': self.split_payment_product.id,
            'price_unit': 100,
        })
        self.assertTrue(invoice.l10n_pl_mpp == 'mpp')

        # We must be able to uncheck MPP after posting the invoice
        invoice.action_post()
        invoice.l10n_pl_mpp = 'no_mpp'
        self.assertTrue(invoice.l10n_pl_mpp == 'no_mpp')

    def test_split_payment_product(self):
        product = self._create_product()

        self.assertFalse(product.l10n_pl_split_payment)

        pkwiu_split_payment_code_id = self.env.ref('l10n_pl.pkwiu_code_2015_05').id
        product.l10n_pl_pkwiu_code_id = pkwiu_split_payment_code_id

        self.assertTrue(product.l10n_pl_split_payment)

        pkwiu_non_split_payment_code_id = self.env.ref('l10n_pl.pkwiu_code_2015_01').id
        product.l10n_pl_pkwiu_code_id = pkwiu_non_split_payment_code_id

        self.assertFalse(product.l10n_pl_split_payment)
