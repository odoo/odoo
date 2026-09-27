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

        # 5. Website: simplified-invoice journal selection only applies to
        #    orders coming from the website, so tests exercising that
        #    behavior need an order attached to one.
        cls.website = cls.env['website'].create({
            'name': 'Test Website',
            'company_id': cls.company.id,
        })

    def test_01_invoice_below_limit(self):
        """Website orders at or below the limit use the simplified journal and flag."""
        so = self.env['sale.order'].create({
            'partner_id': self.partner_es.id,
            'website_id': self.website.id,
            'order_line': [(0, 0, {
                'product_id': self.product_cheap.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        so.action_confirm()
        invoice = so._create_invoices()

        self.assertTrue(
            invoice.l10n_es_invoice_type in ('F2', 'R5')
        )
        self.assertEqual(
            invoice.journal_id,
            self.simplified_journal,
            "The invoice should use the simplified journal when below the limit.",
        )

    def test_02_invoice_above_limit(self):
        """Website orders above the limit keep the regular journal and are not simplified."""
        # Above the limit, VAT is mandatory at checkout (see ResPartner.
        # _get_mandatory_billing_address_fields), so the customer has one here too.
        partner_with_vat = self.env['res.partner'].create({
            'name': 'Spanish Customer With VAT',
            'country_id': self.env.ref('base.es').id,
            'vat': 'ESA12345674',
        })
        so = self.env['sale.order'].create({
            'partner_id': partner_with_vat.id,
            'website_id': self.website.id,
            'order_line': [(0, 0, {
                'product_id': self.product_expensive.id,
                'product_uom_qty': 1,
                'price_unit': 500.0,
            })],
        })
        so.action_confirm()
        invoice = so._create_invoices()

        self.assertTrue(invoice.l10n_es_invoice_type == 'F1')
        self.assertNotEqual(
            invoice.journal_id,
            self.simplified_journal,
            "The invoice should not use the simplified journal when above the limit.",
        )

    def test_03_backend_order_below_limit_not_simplified(self):
        """Orders with no website stay on the regular journal, even below the limit."""
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

        self.assertNotEqual(
            invoice.journal_id,
            self.simplified_journal,
            "A non-website order should not use the simplified journal, "
            "even when its amount is below the limit.",
        )
