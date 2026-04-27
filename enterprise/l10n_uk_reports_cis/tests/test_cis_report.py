from odoo.tests import tagged
from odoo.fields import Command
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestCisReport(TestAccountReportsCommon):
    """
    HMRC provides us 6 scenarios to test to be recognised by them as a software supporting CIS.

    See: https://www.gov.uk/government/publications/construction-industry-scheme-schema-and-technical-specifications Under section CIS recognition
    """

    @classmethod
    @AccountTestInvoicingCommon.setup_country('gb')
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env.ref('l10n_uk_reports_cis.tax_report_cis')

        cls.vat_tax = cls.env.ref(f'account.{cls.env.company.id}_PT_20_S')
        cls.cis_purchase_tax_unmatched = cls.env.ref(f'account.{cls.env.company.id}_CISP30')
        cls.cis_purchase_tax_matched = cls.env.ref(f'account.{cls.env.company.id}_CISP20')
        cls.cis_purchase_tax_gross = cls.env.ref(f'account.{cls.env.company.id}_CISP0')

    def create_invoice_and_post(self, partner, date, line_amounts):
        match partner.l10n_uk_reports_cis_deduction_rate:
            case 'unmatched':
                cis_tax = self.cis_purchase_tax_unmatched.id
            case 'net':
                cis_tax = self.cis_purchase_tax_matched.id
            case 'gross':
                cis_tax = self.cis_purchase_tax_gross.id

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': date,
            'invoice_line_ids': [
                Command.create({
                    'quantity': 1,
                    'price_unit': amount,
                    'tax_ids': [self.vat_tax.id, cis_tax] if is_cis_line else [self.vat_tax.id],
                }) for amount, is_cis_line in line_amounts
            ],
        })
        invoice.action_post()
        return invoice

    def test_scenario_1_2(self):
        """
        Testing report empty
        """
        warnings = {}
        options = self._generate_options(self.report, '2009-04-06', '2009-05-05')
        lines = self.report._get_lines(options, None, warnings)

        self.assertTrue('l10n_uk_reports_cis.warning_cis_unregistered_partner' not in warnings)
        self.assertLinesValues(
            lines,
            [1, 2, 3],
            [],
            options,
        )

    def test_scenario_3(self):
        """
        Testing report scenario 3 with 2 partners with unmatched tax rate (30% deduction)

        One invoice has materials cost line and the other not. Both have labour cost.
        """
        partner_a = self.env['res.partner'].create({
            'name': 'John Peter Brown',
            'is_company': False,
            'l10n_uk_cis_enabled': True,
            'l10n_uk_reports_cis_verification_number': 'V6499876214A',
            'l10n_uk_reports_cis_deduction_rate': 'unmatched',
            'l10n_uk_reports_cis_forename': 'John',
            'l10n_uk_reports_cis_second_forename': 'Peter',
            'l10n_uk_reports_cis_surname': 'Brown',
        })

        partner_b = self.env['res.partner'].create({
            'name': 'TA Plumbing',
            'is_company': True,
            'l10n_uk_cis_enabled': True,
            'l10n_uk_reports_cis_verification_number': 'V8745678309AA',
            'l10n_uk_reports_cis_deduction_rate': 'unmatched',
        })

        self.create_invoice_and_post(partner_a, '2009-04-15', [(1500, True), (500, False)])
        self.create_invoice_and_post(partner_b, '2009-04-18', [(2750, True)])

        options = self._generate_options(self.report, '2009-04-06', '2009-05-05')

        self.assertLinesValues(
            self.report._get_lines(options),
            # Name                              Payment     Materials   Deduction
            [0,                                 1,          2,          3],
            [
                ('CIS Deduction Purchase',      4750,       500,        1275),
                ('John Peter Brown',            2000,       500,        450),
                ('TA Plumbing',                 2750,       0,          825),
            ],
            options,
        )

    def test_scenario_4(self):
        """
        Testing report scenario 4 with a partner (individual) with matched tax rate so 20% deduction

        Invoice has only the labour cost line
        """
        partner = self.env['res.partner'].create({
            'name': 'Adam George',
            'is_company': False,
            'l10n_uk_cis_enabled': True,
            'l10n_uk_reports_cis_verification_number': 'V6499876214',
            'l10n_uk_reports_cis_deduction_rate': 'net',
            'l10n_uk_hmrc_national_insurance_number': 'AA357654A',
            'l10n_uk_hmrc_unique_taxpayer_reference': '2384921857',
            'l10n_uk_reports_cis_forename': 'Adam',
            'l10n_uk_reports_cis_surname': 'George',
        })

        self.create_invoice_and_post(partner, '2009-04-18', [(3000, True)])

        options = self._generate_options(self.report, '2009-04-06', '2009-05-05')

        self.assertLinesValues(
            self.report._get_lines(options),
            # Name                              Payment     Materials   Deduction
            [0,                                 1,          2,          3],
            [
                ('CIS Deduction Purchase',      3000,       0,          600),
                ('Adam George',                 3000,       0,          600),
            ],
            options,
        )

    def test_scenario_5(self):
        """
        Testing report scenario 5 with a partner (company) with matched tax rate so 20% deduction

        Invoice has the labour cost line plus another line for the material cost
        """
        partner = self.env['res.partner'].create({
            'name': 'Factory and Warehouse Fabrication Services',
            'is_company': True,
            'l10n_uk_cis_enabled': True,
            'l10n_uk_reports_cis_verification_number': 'V6499876214',
            'l10n_uk_reports_cis_deduction_rate': 'net',
            'l10n_uk_hmrc_company_registration_number': 'NI839475',
            'l10n_uk_hmrc_unique_taxpayer_reference': '2983286482',
        })
        self.create_invoice_and_post(partner, '2009-04-18', [(5001, True), (999, False)])

        options = self._generate_options(self.report, '2009-04-06', '2009-05-05')

        self.assertLinesValues(
            self.report._get_lines(options),
            # Name                                                  Payment     Materials   Deduction
            [0,                                                     1,          2,          3],
            [
                ('CIS Deduction Purchase',                          6000,       999,        1000.20),
                ('Factory and Warehouse Fabrication Services',      6000,       999,        1000.20),
            ],
            options,
        )

    def test_scenario_6(self):
        """
        Testing report scenario 6 with a partner (individual) with a gross tax rate (0% deduction)
        """
        partner = self.env['res.partner'].create({
            'name': 'George Bailey',
            'is_company': False,
            'l10n_uk_cis_enabled': True,
            'l10n_uk_reports_cis_verification_number': 'V6499876214',
            'l10n_uk_reports_cis_deduction_rate': 'gross',
            'l10n_uk_hmrc_national_insurance_number': 'YW000002',
            'l10n_uk_hmrc_unique_taxpayer_reference': '1982759152',
            'l10n_uk_reports_cis_forename': 'George',
            'l10n_uk_reports_cis_surname': 'Bailey',
        })

        self.create_invoice_and_post(partner, '2009-04-18', [(17500, True)])

        options = self._generate_options(self.report, '2009-04-06', '2009-05-05')

        self.assertLinesValues(
            self.report._get_lines(options),
            # Name                              Payment     Materials   Deduction
            [0,                                 1,          2,          3],
            [
                ('CIS Deduction Purchase',      17500,      0,          0),
                ('George Bailey',               17500,      0,          0),
            ],
            options,
        )

    def test_partner_hierarchy(self):
        """
        Test that partners with a parent take CIS configuration from parent
        """
        partner_parent = self.env['res.partner'].create({
            'name': 'Lumber Inc',
            'is_company': True,
            'l10n_uk_cis_enabled': True,
        })
        partner_child = self.env['res.partner'].create({
            'name': 'Lumber Inc, George Bailey',
            'is_company': False,
            'parent_id': partner_parent.id,
        })

        self.create_invoice_and_post(partner_child, '2009-04-18', [(3000, True)])

        options = self._generate_options(self.report, '2009-04-06', '2009-05-05')

        self.assertLinesValues(
            self.report._get_lines(options),
            # Name                              Payment     Materials   Deduction
            [0,                                 1,          2,          3],
            [
                ('CIS Deduction Purchase',      3000,       0,          900),
                ('Lumber Inc',                  3000,       0,          900),
            ],
            options,
        )

    def test_move_use_wrong_taxes(self):
        """
        Check that when we use the wrong cis tax than the one configured for the partner on a bill, we get a warning.

        For instance (warning is raised):
        - Partner has unmatched tax rate (30% deduction)
        - Invoice use 20% CIS deduction instead of 30%
        """
        partner = self.env['res.partner'].create({
            'name': 'Lumber Inc',
            'is_company': True,
            'l10n_uk_cis_enabled': True,
        })

        move0 = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': '2009-04-18',
            'invoice_line_ids': [
                Command.create({
                    'quantity': 1,
                    'price_unit': 3000,
                    'tax_ids': [self.vat_tax.id, self.cis_purchase_tax_matched.id],
                }),
            ],
        })
        self.assertTrue(move0.l10n_uk_cis_wrong_taxes)

        move1 = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': '2009-04-18',
            'invoice_line_ids': [
                Command.create({
                    'quantity': 1,
                    'price_unit': 3000,
                    'tax_ids': [self.vat_tax.id, self.cis_purchase_tax_gross.id],
                }),
            ],
        })
        self.assertTrue(move1.l10n_uk_cis_wrong_taxes)

        move2 = self.create_invoice_and_post(partner, '2009-04-18', [(3000, True)])
        self.assertFalse(move2.l10n_uk_cis_wrong_taxes)

    def test_warning_unregistered_partner(self):
        """
        Test if the l10n_uk_cis_inactive_partner flag is set on the invoice and in the report's warning if the partner use CIS deduction without having it enabled on the partner form view
        """
        partner = self.env['res.partner'].create({
            'name': 'Lumber Inc',
            'is_company': True,
        })

        move = self.create_invoice_and_post(partner, '2009-04-18', [(3000, True)])

        warnings = {}
        report_options = self._generate_options(self.report, '2009-04-06', '2009-05-05')
        self.report._get_lines(report_options, None, warnings)
        self.assertTrue(move.l10n_uk_cis_inactive_partner)
        self.assertTrue('l10n_uk_reports_cis.warning_cis_unregistered_partner' in warnings)

        warnings = {}
        partner.l10n_uk_cis_enabled = True
        self.report._get_lines(report_options, None, warnings)
        self.assertFalse(move.l10n_uk_cis_inactive_partner)
        self.assertTrue('l10n_uk_reports_cis.warning_cis_unregistered_partner' not in warnings)

    def test_cis_report_rounded_values(self):
        partner = self.env['res.partner'].create({
            'name': 'Factory and Warehouse Fabrication Services',
            'is_company': True,
            'l10n_uk_cis_enabled': True,
            'l10n_uk_reports_cis_verification_number': 'V6499876214',
            'l10n_uk_reports_cis_deduction_rate': 'net',
            'l10n_uk_hmrc_company_registration_number': 'NI839475',
            'l10n_uk_hmrc_unique_taxpayer_reference': '2983286482',
        })
        self.create_invoice_and_post(partner, '2009-04-18', [(1029.33, True), (5489.99, False)])
        options = self._generate_options(self.report, '2009-04-06', '2009-05-05')

        self.assertLinesValues(
            self.report._get_lines(options),
            # Name                                                  Payment     Materials   Deduction
            [0,                                                     1,          2,          3],
            [
                ('CIS Deduction Purchase',                          6519,       5489,       205.87),
                ('Factory and Warehouse Fabrication Services',      6519,       5489,       205.87),
            ],
            options,
        )
