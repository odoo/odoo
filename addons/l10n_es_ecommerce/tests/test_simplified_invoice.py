from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestSimplifiedInvoice(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # 1. Company with Spanish localization.
        cls.company = cls.env.company
        cls.company.write({
            'country_id': cls.env.ref('base.es').id,
            'account_fiscal_country_id': cls.env.ref('base.es').id,
            'l10n_es_simplified_invoice_limit': 400.0,
        })

        # 2. Spanish partner without VAT (so simplified invoices apply).
        cls.partner_es = cls.env['res.partner'].create({
            'name': 'Spanish Customer',
            'country_id': cls.env.ref('base.es').id,
        })

        # 3. Products without taxes: this test targets journal selection and the
        #    simplified flag, not tax logic.
        cls.product_cheap = cls.env['product.product'].create({
            'name': 'Cheap Product',
            'list_price': 100.0,
            'invoice_policy': 'order',
            'taxes_id': [(5,)],
        })
        cls.product_expensive = cls.env['product.product'].create({
            'name': 'Expensive Product',
            'list_price': 500.0,
            'invoice_policy': 'order',
            'taxes_id': [(5,)],
        })

        # 4. Simplified journal created by the Chart of Accounts.
        cls.simplified_journal = cls.env['account.journal'].search([
            *cls.env['account.journal']._check_company_domain(cls.company),
            ('type', '=', 'sale'),
            ('code', '=', 'SINV'),
        ], limit=1)

    def test_01_invoice_below_limit(self):
        """Orders at or below the limit use the simplified journal and flag."""
        so = self.env['sale.order'].create({
            'partner_id': self.partner_es.id,
            'order_line': [(0, 0, {
                'product_id': self.product_cheap.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        so.action_confirm()
        invoice = so._create_invoices()

        self.assertTrue(
            invoice.l10n_es_is_simplified,
            "The invoice should be flagged as simplified when below the limit.",
        )
        self.assertEqual(
            invoice.journal_id,
            self.simplified_journal,
            "The invoice should use the simplified journal when below the limit.",
        )

    def test_02_invoice_above_limit(self):
        """Orders above the limit keep the regular journal and are not simplified."""
        so = self.env['sale.order'].create({
            'partner_id': self.partner_es.id,
            'order_line': [(0, 0, {
                'product_id': self.product_expensive.id,
                'product_uom_qty': 1,
                'price_unit': 500.0,
            })],
        })
        so.action_confirm()
        invoice = so._create_invoices()

        self.assertFalse(
            invoice.l10n_es_is_simplified,
            "The invoice should not be simplified when above the limit.",
        )
        self.assertNotEqual(
            invoice.journal_id,
            self.simplified_journal,
            "The invoice should not use the simplified journal when above the limit.",
        )
