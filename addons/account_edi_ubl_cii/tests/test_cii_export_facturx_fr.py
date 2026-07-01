from odoo.addons.account_edi_ubl_cii.tests.common import TestCiiFacturXCommon, TestUblCiiFRCommon
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class CiiExportFacturXFR(TestCiiFacturXCommon, TestUblCiiFRCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.recipient_bank = cls.env['res.partner.bank'].create({
            'acc_number': 'FR7630004028379876543210943',
            'partner_id': cls.partner_fr.id,
            'allow_out_payment': True,
        })

    @classmethod
    def _create_company(cls, **create_values):
        company = super()._create_company(**create_values)

        # Mandatory fields for Factur-x
        company.partner_id.write({
            'email': 'mycompany@company.com',
            'phone': '+33 499 65 43 21',
        })
        return company

    @classmethod
    def subfolders(cls):
        subfolder_format, _subfolder_document, subfolder_country = super().subfolders()
        return subfolder_format, 'invoice', subfolder_country

    @classmethod
    def _create_partner_fr(cls, **kwargs):
        partner = super()._create_partner_fr(**kwargs)
        partner.write({'invoice_edi_format': 'facturx'})
        return partner

    @freeze_time('2026-01-01')
    def test_invoice_document_header(self):
        tax_20 = self.percent_tax(20.0)

        invoice = self._create_invoice_one_line(
            partner_id=self.partner_fr,
            product_id=self.product,
            tax_ids=tax_20,
            partner_bank_id=self.recipient_bank,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_document_header')

    def test_invoice_multiple_taxes(self):
        tax_20 = self.percent_tax(20.0)
        tax_15 = self.percent_tax(15.0)
        tax_0 = self.percent_tax(0.0)

        invoice = self._create_invoice(
            partner_id=self.partner_fr,
            partner_bank_id=self.recipient_bank,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=100, product_id=self.product, tax_ids=tax_20),
                self._prepare_invoice_line(price_unit=25, product_id=self.product, tax_ids=tax_20),
                self._prepare_invoice_line(price_unit=50, product_id=self.product, tax_ids=tax_15),
                self._prepare_invoice_line(price_unit=500, product_id=self.product, tax_ids=tax_0),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_multiple_taxes')

    def test_invoice_price_amount_rounding_precision(self):
        """
        Ensures amounts are correctly rounded (max 2 decimals)
        """
        tax_20 = self.percent_tax(20.0)

        invoice = self._create_invoice(
            partner_id=self.partner_fr,
            partner_bank_id=self.recipient_bank,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=123.123, product_id=self.product, quantity=5, tax_ids=tax_20),
                self._prepare_invoice_line(price_unit=10.125, product_id=self.product, quantity=1, tax_ids=tax_20),
                self._prepare_invoice_line(price_unit=100.126, product_id=self.product, quantity=2, tax_ids=tax_20),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_price_amount_rounding_precision')

    def test_invoice_price_amount_rounding_precision_with_price_included_taxes(self):
        tax_20 = self.percent_tax(20.0, price_include_override='tax_included')

        invoice = self._create_invoice_one_line(
            price_unit=1039.99,
            product_id=self.product,
            partner_id=self.partner_fr,
            tax_ids=tax_20,
            partner_bank_id=self.recipient_bank,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_price_amount_rounding_precision_with_price_included_taxes')

    def test_invoice_product_uom_and_discounts(self):
        tax_20 = self.percent_tax(20.0)

        invoice = self._create_invoice(
            partner_id=self.partner_fr,
            partner_bank_id=self.recipient_bank,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    price_unit=990,
                    product_id=self.product,
                    quantity=2,
                    product_uom_id=self.env.ref('uom.product_uom_dozen').id,
                    discount=10,
                    tax_ids=tax_20,
                ),
                self._prepare_invoice_line(
                    price_unit=100,
                    product_id=self.product,
                    quantity=10,
                    product_uom_id=self.env.ref('uom.product_uom_unit').id,
                    tax_ids=tax_20,
                ),
                self._prepare_invoice_line(
                    price_unit=100,
                    product_id=self.product,
                    quantity=-1,
                    product_uom_id=self.env.ref('uom.product_uom_unit').id,
                    tax_ids=tax_20,
                ),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_product_uom_and_discounts')

    def test_invoice_product_description_name(self):
        tax_20 = self.percent_tax(20.0)

        product = self._create_product(
            lst_price=100.0,
            default_code='P123',
            barcode='1234567890123',
            description='A simple product description',
            taxes_id=tax_20,
        )
        invoice = self._create_invoice_one_line(
            product_id=product,
            partner_id=self.partner_fr,
            partner_bank_id=self.recipient_bank,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_product_description_name')

    def test_invoice_negative_price_unit(self):
        """ Ensure the price_unit and the quantity sign are inversed during the generation of the
        xml because 'ChargeAmount' cannot be negative.
        """
        tax_20 = self.percent_tax(20.0)

        invoice = self._create_invoice(
            partner_id=self.partner_fr,
            partner_bank_id=self.recipient_bank,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=100.0, product_id=self.product, tax_ids=tax_20),
                self._prepare_invoice_line(price_unit=-10.0, product_id=self.product, tax_ids=tax_20),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_negative_price_unit')

    def test_invoice_partner_info(self):
        self.partner_fr.write({
            'company_registry': '123456789',
            'phone': '+33 499 12 34 56',
            'email': 'partner_fr@company.com',
        })
        self.company.write({
            'company_registry': '987654321',
        })
        tax_20 = self.percent_tax(20)

        invoice = self._create_invoice_one_line(
            product_id=self.product,
            tax_ids=tax_20,
            partner_id=self.partner_fr,
            partner_bank_id=self.recipient_bank,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_partner_info')

    def test_invoice_partner_siret(self):
        self.ensure_installed("l10n_fr")
        self.partner_fr.write({
            'siret': '12345678900012',
        })
        self.company.write({
            'siret': '98765432100012',
        })
        tax_20 = self.percent_tax(20)

        invoice = self._create_invoice_one_line(
            product_id=self.product,
            tax_ids=tax_20,
            partner_id=self.partner_fr,
            partner_bank_id=self.recipient_bank,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_partner_siret')

    def test_invoice_tax_included(self):
        tax_20_incl = self.percent_tax(20, price_include_override='tax_included')
        tax_20 = self.percent_tax(20)

        invoice = self._create_invoice(
            partner_id=self.partner_fr,
            partner_bank_id=self.recipient_bank,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=100, product_id=self.product, quantity=2, tax_ids=tax_20_incl),
                self._prepare_invoice_line(price_unit=100, product_id=self.product, tax_ids=tax_20_incl),
                self._prepare_invoice_line(price_unit=100, product_id=self.product, tax_ids=tax_20),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_tax_included')

    def test_invoice_allowance_charge_fixed_tax_recycling_contribution(self):
        """ Ensure the recycling contribution taxes are turned into allowance/charges at the document line level. """
        tax_recupel = self.fixed_tax(1.0, name="RECUPEL", include_base_amount=True)
        tax_auvibel = self.fixed_tax(2.0, name="AUVIBEL", include_base_amount=True)
        tax_bebat = self.fixed_tax(3.0, name="BEBAT", include_base_amount=True)
        tax_20 = self.percent_tax(20.0)

        invoice = self._create_invoice(
            partner_id=self.partner_fr,
            partner_bank_id=self.recipient_bank,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    price_unit=99.0,
                    product_id=self.product,
                    tax_ids=tax_recupel + tax_20,
                ),
                self._prepare_invoice_line(
                    price_unit=98.0,
                    product_id=self.product,
                    quantity=4.0,
                    discount=25.0,
                    tax_ids=tax_auvibel + tax_20,
                ),
                self._prepare_invoice_line(
                    price_unit=97.0,
                    product_id=self.product,
                    tax_ids=tax_bebat + tax_20,
                ),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_allowance_charge_fixed_tax_recycling_contribution')

    def test_invoice_allowance_charge_fixed_tax_included_recycling_contribution(self):
        tax_recupel = self.fixed_tax(1.0, name="RECUPEL", include_base_amount=True, price_include_override='tax_included')
        tax_20 = self.percent_tax(20.0, price_include_override='tax_included')

        # Price TTC = 120 = (99 + 1 ) * 1.20
        invoice = self._create_invoice(
            partner_id=self.partner_fr,
            partner_bank_id=self.recipient_bank,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    price_unit=120,
                    product_id=self.product,
                    tax_ids=tax_recupel + tax_20,
                ),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_allowance_charge_fixed_tax_included_recycling_contribution')

    def test_invoice_with_fixed_tax_on_negative_line(self):
        """ simple invoice with a recupel tax, with one negative line.
        1) Subtotal (price without taxes): (10+1) * 5 + (10+1) * -3 = 22.00
        2) Taxes:
            - recupel = 5 - 3 = 2
            - VAT = (20 + 2) * 0.2 = 4.4
        3) Total = 20 + 2 + 4.4 = 26.4
        """
        tax_recupel = self.fixed_tax(1.0, name="RECUPEL", include_base_amount=True)
        tax_20 = self.percent_tax(20.0)

        invoice = self._create_invoice(
            partner_id=self.partner_fr,
            partner_bank_id=self.recipient_bank,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product,
                    price_unit=10.0,
                    quantity=5.0,
                    tax_ids=tax_recupel + tax_20,
                ),
                self._prepare_invoice_line(
                    product_id=self.product,
                    price_unit=10.0,
                    quantity=-3.0,
                    tax_ids=tax_recupel + tax_20,
                ),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_with_fixed_tax_on_negative_line')

    @freeze_time('2026-01-01')
    def test_invoice_immediate_payment_term(self):
        tax_15 = self.percent_tax(15.0)
        tax_20 = self.percent_tax(20.0)

        invoice = self._create_invoice(
            partner_id=self.partner_fr,
            invoice_payment_term_id=self.pay_terms_a.id,
            partner_bank_id=self.recipient_bank,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=100.0, product_id=self.product, tax_ids=tax_15),
                self._prepare_invoice_line(price_unit=100.0, product_id=self.product, tax_ids=tax_20),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_immediate_payment_term')

    @freeze_time('2026-01-01')
    def test_invoice_end_following_month_payment_term(self):
        tax_15 = self.percent_tax(15.0)
        tax_20 = self.percent_tax(20.0)

        invoice = self._create_invoice(
            partner_id=self.partner_fr,
            invoice_payment_term_id=self.pay_terms_b.id,
            partner_bank_id=self.recipient_bank,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=100.0, product_id=self.product, tax_ids=tax_15),
                self._prepare_invoice_line(price_unit=100.0, product_id=self.product, tax_ids=tax_20),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_end_following_month_payment_term')

    @freeze_time('2026-01-01')
    def test_invoice_early_pay_discount(self):
        tax_15 = self.percent_tax(15.0)
        tax_20 = self.percent_tax(20.0)
        early_payment_term = self._create_early_payment_term()

        invoice = self._create_invoice(
            partner_id=self.partner_fr,
            invoice_payment_term_id=early_payment_term.id,
            partner_bank_id=self.recipient_bank,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=100.0, product_id=self.product, tax_ids=tax_15),
                self._prepare_invoice_line(price_unit=100.0, product_id=self.product, tax_ids=tax_20),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_early_pay_discount')

    def test_invoice_in_foreign_currency(self):
        tax_20 = self.percent_tax(20.0)
        foreign_currency = self.setup_other_currency('RON')

        invoice = self._create_invoice(
            partner_id=self.partner_fr,
            currency_id=foreign_currency.id,
            partner_bank_id=self.recipient_bank,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    price_unit=10.0,
                    product_id=self.product,
                    quantity=5.0,
                    tax_ids=tax_20,
                ),
                self._prepare_invoice_line(
                    price_unit=100.0,
                    product_id=self.product,
                    quantity=3.0,
                    discount=10.0,
                    tax_ids=tax_20,
                ),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_in_foreign_currency')

    def test_invoice_cash_rounding_add_invoice_line(self):
        tax_20 = self.percent_tax(20.0)
        cash_rounding = self._create_add_invoice_line_cash_rounding()

        invoice = self._create_invoice_one_line(
            partner_id=self.partner_fr,
            price_unit=1039.99,
            product_id=self.product,
            tax_ids=tax_20,
            invoice_cash_rounding_id=cash_rounding,
            partner_bank_id=self.recipient_bank,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_cash_rounding_add_invoice_line')

    def test_invoice_cash_rounding_biggest_tax(self):
        tax_20 = self.percent_tax(20.0)
        cash_rounding = self._create_biggest_tax_cash_rounding()

        invoice = self._create_invoice_one_line(
            partner_id=self.partner_fr,
            price_unit=1039.99,
            product_id=self.product,
            tax_ids=tax_20,
            invoice_cash_rounding_id=cash_rounding,
            partner_bank_id=self.recipient_bank,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_cash_rounding_biggest_tax')

    @freeze_time('2026-01-01')
    def test_invoice_deferred_dates(self):
        tax_20 = self.percent_tax(20.0)

        invoice = self._create_invoice(
            partner_id=self.partner_fr,
            partner_bank_id=self.recipient_bank,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    price_unit=1000.0,
                    product_id=self.product,
                    tax_ids=tax_20,
                    deferred_start_date="2026-02-01",
                    deferred_end_date="2026-05-01",
                ),
                self._prepare_invoice_line(
                    price_unit=2000.0,
                    product_id=self.product,
                    tax_ids=tax_20,
                    deferred_start_date="2026-03-01",
                    deferred_end_date="2026-06-01",
                ),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_deferred_dates')

    @freeze_time("2026-01-01")
    def test_invoice_delivery_date_and_address(self):
        partner_shipping = self.env['res.partner'].create({
            'name': 'FR Partner Delivery',
            'type': 'delivery',
            'street': "Rue Napoléon, 55",
            'zip': "75000",
            'city': "Paris",
            'country_id': self.env.ref('base.fr').id,
        })
        self.partner_fr.write({'child_ids': partner_shipping})
        tax_20 = self.percent_tax(20.0)

        invoice = self._create_invoice_one_line(
            partner_id=self.partner_fr,
            partner_bank_id=self.recipient_bank,
            product_id=self.product,
            tax_ids=tax_20,
            invoice_date_due="2026-01-31",
            delivery_date="2026-02-10",
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_delivery_date_and_address')

    def test_invoice_financial_account_iban(self):
        partner_bank = self.env['res.partner.bank'].create({
            'acc_number': 'FR7730004028379876543210943',
            'partner_id': self.partner_fr.id,
        })
        partner_bank.write({'acc_type': 'iban', 'allow_out_payment': True})
        tax_20 = self.percent_tax(20.0)

        invoice = self._create_invoice_one_line(
            partner_id=self.partner_fr,
            partner_bank_id=partner_bank,
            product_id=self.product,
            tax_ids=tax_20,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_financial_account_iban')

    def test_invoice_financial_account_bank(self):
        tax_20 = self.percent_tax(20.0)

        invoice = self._create_invoice_one_line(
            partner_id=self.partner_fr,
            partner_bank_id=self.recipient_bank,
            product_id=self.product,
            tax_ids=tax_20,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_financial_account_bank')

    @freeze_time("2026-01-01")
    def test_invoice_without_chorus_pro_fields(self):
        self.partner_fr.write({'ref': 'CLI-2026-0042'})
        tax_20 = self.percent_tax(20.0)

        invoice = self._create_invoice_one_line(
            partner_id=self.partner_fr,
            partner_bank_id=self.recipient_bank,
            product_id=self.product,
            tax_ids=tax_20,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_without_chorus_pro_fields')

    @freeze_time("2026-01-01")
    def test_invoice_with_chorus_pro_fields(self):
        self.ensure_installed("l10n_fr_facturx_chorus_pro")
        self.partner_fr.write({'ref': 'CLI-2026-0042'})
        tax_20 = self.percent_tax(20.0)

        invoice = self._create_invoice_one_line(
            partner_id=self.partner_fr,
            partner_bank_id=self.recipient_bank,
            product_id=self.product,
            tax_ids=tax_20,
            buyer_reference="COMPTA-SEC",
            purchase_order_reference="4500098765",
            contract_reference="MARCHE-2026-01",
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_with_chorus_pro_fields')

    @freeze_time("2026-01-01")
    def test_invoice_global_location_number(self):
        partner_shipping = self.env['res.partner'].create({
            'name': 'FR Partner Delivery',
            'type': 'delivery',
            'street': "Rue Napoléon, 55",
            'zip': "75000",
            'city': "Paris",
            'country_id': self.env.ref('base.fr').id,
            'global_location_number': 5412345000008,
        })
        self.partner_fr.write({'child_ids': partner_shipping})
        tax_20 = self.percent_tax(20.0)

        invoice = self._create_invoice_one_line(
            partner_id=self.partner_fr,
            partner_bank_id=self.recipient_bank,
            product_id=self.product,
            tax_ids=tax_20,
            invoice_date_due="2026-01-31",
            delivery_date="2026-02-10",
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_global_location_number')
