# -*- coding: utf-8 -*-
# pylint: disable=C0326
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields
from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class BelgiumPartnerVatListingTest(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref='be_comp'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.partner_a_be = cls.env['res.partner'].create({
            'name': 'Partner A (BE)',
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0246697724',
        })

        cls.partner_b_be = cls.env['res.partner'].create({
            'name': 'Partner B (BE)',
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0766998497',
        })

        cls.partner_c_be = cls.env['res.partner'].create({
            'name': 'Partner C (BE)',
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0477472701',
        })

        cls.report = cls.env.ref('l10n_be_reports.l10n_be_partner_vat_listing')

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        res = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        res['company'].update({
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0477472701',
        })
        res['company'].partner_id.update({
            'email': 'jsmith@mail.com',
            'phone': '+32475123456',
        })
        return res

    @classmethod
    def create_and_post_account_move(cls, move_type, partner_id, invoice_date, product_quantity, product_price_unit):
        move = cls.env['account.move'].create({
            'move_type': move_type,
            'partner_id': partner_id,
            'invoice_date': invoice_date,
            'date': fields.Date.from_string(invoice_date),
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'quantity': product_quantity,
                'name': 'Product 1',
                'price_unit': product_price_unit,
                'tax_ids': cls.tax_sale_a.ids,
            })]
        })

        move.action_post()
        return move

    def test_simple_invoice(self):
        self.env.companies = self.env.company
        options = self._generate_options(self.report, fields.Date.from_string('2022-06-01'), fields.Date.from_string('2022-06-30'))

        # Foreign partners invoices should not show
        self.create_and_post_account_move('out_invoice', self.partner_a.id, '2022-06-01', product_quantity=100, product_price_unit=50)

        # Belgian partners with out-of-date range invoices should not be shown
        self.create_and_post_account_move('out_invoice', self.partner_b_be.id, '2022-07-01', product_quantity=10, product_price_unit=200)

        # Invoices from Belgian partners should show up ordered by vat number
        self.create_and_post_account_move('out_invoice', self.partner_b_be.id, '2022-06-01', product_quantity=10, product_price_unit=200)
        self.create_and_post_account_move('out_invoice', self.partner_a_be.id, '2022-06-01', product_quantity=10, product_price_unit=100)

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                        VAT number          Turnover            VAT amount
            [   0,                          1,                  2,                  3],
            [
                ('Partner VAT Listing',     '',                 3000.0,             630.0),
                ('Partner A (BE)',          'BE0246697724',     1000.0,             210.0),
                ('Partner B (BE)',          'BE0766998497',     2000.0,             420.0),
            ],
            options,
        )

    def test_report_load_more_limit(self):
        """ The aim of this test is to ensure that we load report columns/lines
            correctly when we have a load more limit.
            If we have 3 moves for 3 different partners, with a load more
            limit sets to 2 elements, the report should give us 4 report lines.
            1 parent line containing the totals
            2 lines (one per partner)
            and a load more line to load the last partner.
            The test is also verifying that the XML is correctly generated and that
            the load_more_limit doesn't impact it at all.
        """
        self.env.companies = self.env.company
        self.report.load_more_limit = 2
        options = self._generate_options(
            self.report,
            '2022-06-01',
            '2022-06-30',
        )

        self.create_and_post_account_move('out_invoice', self.partner_a_be.id, '2022-06-01', product_quantity=10, product_price_unit=100)
        self.create_and_post_account_move('out_invoice', self.partner_b_be.id, '2022-06-01', product_quantity=10, product_price_unit=200)
        self.create_and_post_account_move('out_invoice', self.partner_c_be.id, '2022-06-01', product_quantity=10, product_price_unit=300)

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                        VAT number          Turnover            VAT amount
            [0,                             1,                  2,                  3],
            [
                ('Partner VAT Listing',     '',                 6000.0,             1260.0),
                ('Partner A (BE)',          'BE0246697724',     1000.0,             210.0),
                ('Partner B (BE)',          'BE0766998497',     2000.0,             420.0),
                ('Load more...',            '',                 '',                 ''),
            ],
            options,
        )

        # The sequence changes between executions of the test. To handle that, we increase it by 1 more, so we can get its value here
        sequence_number = self.env['ir.sequence'].next_by_code('declarantnum')
        ref = f"0477472701{str(int(sequence_number) + 1).zfill(4)[-4:]}"

        expected_xml = f"""
            <ns2:ClientListingConsignment xmlns="http://www.minfin.fgov.be/InputCommon" xmlns:ns2="http://www.minfin.fgov.be/ClientListingConsignment" ClientListingsNbr="1">
                <ns2:ClientListing SequenceNumber="1" ClientsNbr="3" DeclarantReference="{ref}" TurnOverSum="6000.00" VATAmountSum="1260.00">
                    <ns2:Declarant>
                        <VATNumber>0477472701</VATNumber>
                        <Name>company_1_data</Name>
                        <Street></Street>
                        <PostCode></PostCode>
                        <City></City>
                        <CountryCode>BE</CountryCode>
                        <EmailAddress>jsmith@mail.com</EmailAddress>
                        <Phone>+32475123456</Phone>
                    </ns2:Declarant>
                    <ns2:Period>2022</ns2:Period>
                    <ns2:Client SequenceNumber="1">
                        <ns2:CompanyVATNumber issuedBy="BE">0246697724</ns2:CompanyVATNumber>
                        <ns2:TurnOver>1000.00</ns2:TurnOver>
                        <ns2:VATAmount>210.00</ns2:VATAmount>
                    </ns2:Client>
                    <ns2:Client SequenceNumber="2">
                        <ns2:CompanyVATNumber issuedBy="BE">0766998497</ns2:CompanyVATNumber>
                        <ns2:TurnOver>2000.00</ns2:TurnOver>
                        <ns2:VATAmount>420.00</ns2:VATAmount>
                    </ns2:Client>
                    <ns2:Client SequenceNumber="3">
                        <ns2:CompanyVATNumber issuedBy="BE">0477472701</ns2:CompanyVATNumber>
                        <ns2:TurnOver>3000.00</ns2:TurnOver>
                        <ns2:VATAmount>630.00</ns2:VATAmount>
                    </ns2:Client>
                    <ns2:Comment></ns2:Comment>
                </ns2:ClientListing>
            </ns2:ClientListingConsignment>
        """

        # Following what export_file function does
        options['export_mode'] = 'file'
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self.env[self.report._get_custom_handler_model()].partner_vat_listing_export_to_xml(options)['file_content']),
            self.get_xml_tree_from_string(expected_xml)
        )

    def test_report_2_different_partners_with_same_vat(self):
        """ The aim of this test is to ensure that two different partners
            with the same vat number are correctly represented in the report.
            The report should have one line per partner even if they have the same
            vat number.
            However, for the XML generation, the logic is a bit different and the
            report should give us one line per vat number instead of per partner.
        """
        self.env.companies = self.env.company
        options = self._generate_options(
            self.report,
            '2022-06-01',
            '2022-06-30',
        )

        # Copy an existing partner to have the same VAT but not the same name
        # The idea behind this is verifying that even if lines are not sorted on the vat number,
        # when we do the grouping for the XML generation (based on the vat number),
        # we still have the Partner A and Z batched in one partner.
        partner_a_be_copy = self.partner_a_be.copy()
        partner_a_be_copy.name = 'Partner Z (BE)'

        self.create_and_post_account_move('out_invoice', self.partner_a_be.id, '2022-06-01', product_quantity=10, product_price_unit=300)
        self.create_and_post_account_move('out_invoice', self.partner_b_be.id, '2022-06-01', product_quantity=10, product_price_unit=200)
        self.create_and_post_account_move('out_invoice', partner_a_be_copy.id, '2022-06-01', product_quantity=10, product_price_unit=400)

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                        VAT number          Turnover            VAT amount
            [0,                             1,                  2,                  3],
            [
                ('Partner VAT Listing',     '',                 9000.0,             1890.0),
                ('Partner A (BE)',          'BE0246697724',     3000.0,             630.0),
                ('Partner B (BE)',          'BE0766998497',     2000.0,             420.0),
                ('Partner Z (BE)',          'BE0246697724',     4000.0,             840.0),
            ],
            options,
        )

        # The sequence changes between executions of the test. To handle that, we increase it by 1 more, so we can get its value here
        sequence_number = self.env['ir.sequence'].next_by_code('declarantnum')
        ref = f"0477472701{str(int(sequence_number) + 1).zfill(4)[-4:]}"

        expected_xml = f"""
            <ns2:ClientListingConsignment xmlns="http://www.minfin.fgov.be/InputCommon" xmlns:ns2="http://www.minfin.fgov.be/ClientListingConsignment" ClientListingsNbr="1">
                <ns2:ClientListing SequenceNumber="1" ClientsNbr="2" DeclarantReference="{ref}" TurnOverSum="9000.00" VATAmountSum="1890.00">
                    <ns2:Declarant>
                        <VATNumber>0477472701</VATNumber>
                        <Name>company_1_data</Name>
                        <Street></Street>
                        <PostCode></PostCode>
                        <City></City>
                        <CountryCode>BE</CountryCode>
                        <EmailAddress>jsmith@mail.com</EmailAddress>
                        <Phone>+32475123456</Phone>
                    </ns2:Declarant>
                    <ns2:Period>2022</ns2:Period>
                    <ns2:Client SequenceNumber="1">
                        <ns2:CompanyVATNumber issuedBy="BE">0246697724</ns2:CompanyVATNumber>
                        <ns2:TurnOver>7000.00</ns2:TurnOver>
                        <ns2:VATAmount>1470.00</ns2:VATAmount>
                    </ns2:Client>
                    <ns2:Client SequenceNumber="2">
                        <ns2:CompanyVATNumber issuedBy="BE">0766998497</ns2:CompanyVATNumber>
                        <ns2:TurnOver>2000.00</ns2:TurnOver>
                        <ns2:VATAmount>420.00</ns2:VATAmount>
                    </ns2:Client>
                    <ns2:Comment></ns2:Comment>
                </ns2:ClientListing>
            </ns2:ClientListingConsignment>
        """

        # Following what export_file function does
        options['export_mode'] = 'file'
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self.env[self.report._get_custom_handler_model()].partner_vat_listing_export_to_xml(options)['file_content']),
            self.get_xml_tree_from_string(expected_xml)
        )

    def test_misc_operation(self):
        self.env.companies = self.env.company
        options = self._generate_options(self.report, fields.Date.from_string('2022-06-01'), fields.Date.from_string('2022-06-30'))

        move_1 = self.create_and_post_account_move('out_invoice', self.partner_b_be.id, '2022-06-01', product_quantity=10, product_price_unit=200)
        move_2 = self.create_and_post_account_move('out_invoice', self.partner_a_be.id, '2022-06-01', product_quantity=10, product_price_unit=100)

        # Those moves are misc operations that are identical to invoices
        (move_1 + move_2).write({'move_type': 'entry', 'date': '2022-06-01'})

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                        VAT number          Turnover            VAT amount
            [   0,                          1,                  2,                  3],
            [
                ('Partner VAT Listing',     '',                 3000.0,             630.0),
                ('Partner A (BE)',          'BE0246697724',     1000.0,             210.0),
                ('Partner B (BE)',          'BE0766998497',     2000.0,             420.0),
            ],
            options,
        )

    def test_invoices_with_refunds(self):
        self.env.companies = self.env.company
        options = self._generate_options(self.report, fields.Date.from_string('2022-06-01'), fields.Date.from_string('2022-06-30'))

        # Partial refund
        self.create_and_post_account_move('out_invoice', self.partner_a_be.id, '2022-06-01', product_quantity=10, product_price_unit=100)
        self.create_and_post_account_move('out_refund', self.partner_a_be.id, '2022-06-02', product_quantity=2, product_price_unit=100)

        # Full refund
        self.create_and_post_account_move('out_invoice', self.partner_b_be.id, '2022-06-01', product_quantity=10, product_price_unit=200)
        self.create_and_post_account_move('out_refund', self.partner_b_be.id, '2022-06-01', product_quantity=10, product_price_unit=200)

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                        VAT number          Turnover            VAT amount
            [   0,                          1,                  2,                  3],
            [
                ('Partner VAT Listing',     '',                 800.0,              168.0),
                ('Partner A (BE)',          'BE0246697724',     800.0,              168.0),
                ('Partner B (BE)',          'BE0766998497',     0.0,                0.0),
            ],
            options,
        )

    def test_refunds_without_invoices(self):
        self.env.companies = self.env.company
        options = self._generate_options(self.report, fields.Date.from_string('2022-06-01'), fields.Date.from_string('2022-06-30'))

        self.create_and_post_account_move('out_refund', self.partner_a_be.id, '2022-06-02', product_quantity=10, product_price_unit=100)

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                        VAT number          Turnover            VAT amount
            [   0,                          1,                  2,                  3],
            [
                ('Partner VAT Listing',     '',                 -1000.0,            -210.0),
                ('Partner A (BE)',          'BE0246697724',     -1000.0,            -210.0),
            ],
            options,
        )

    def test_zero_tax(self):
        self.env.companies = self.env.company
        options = self._generate_options(self.report, fields.Date.from_string('2022-06-01'), fields.Date.from_string('2022-06-30'))

        self.tax_sale_a.amount = 0
        self.init_invoice('out_invoice', partner=self.partner_a_be, post=True, amounts=[1000], taxes=[self.tax_sale_a], invoice_date='2022-06-29')

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                        VAT number          Turnover            VAT amount
            [   0,                          1,                  2,                  3],
            [
                ('Partner VAT Listing',     '',                 1000.0,            0.0),
                ('Partner A (BE)',          'BE0246697724',     1000.0,            0.0),
            ],
            options,
        )

    def test_turnover_custom_groupby(self):
        def get_base_line_name(invoice):
            return invoice.line_ids.filtered(lambda x: x.account_id.internal_group == 'income').display_name

        def get_tax_line_name(invoice):
            return invoice.line_ids.filtered('tax_line_id').display_name

        self.report.filter_unfold_all = True
        self.env.ref('l10n_be_reports.l10n_be_partner_vat_listing_line').user_groupby = 'account_id, partner_id, id'
        options = self._generate_options(self.report, '2022-06-01', '2022-06-30', default_options={'unfold_all': True})

        invoice_1 = self.init_invoice('out_invoice', partner=self.partner_a_be, post=True, amounts=[100], taxes=[self.tax_sale_a], invoice_date='2022-06-29')
        invoice_2 = self.init_invoice('out_invoice', partner=self.partner_c_be, post=True, amounts=[1000], taxes=[self.tax_sale_a], invoice_date='2022-06-29')

        new_income_account = self.env['account.account'].create({
            'name': 'NEW.INCOME',
            'code': 'NEW.INCOME',
            'account_type': 'income',
            'company_id': self.env.company.id,
        })
        invoice_3 = self.init_invoice('out_invoice', partner=self.partner_a_be, amounts=[200], taxes=[self.tax_sale_a], invoice_date='2022-06-29')
        income_line = invoice_3.line_ids.filtered(lambda x: x.account_id.internal_group == 'income')
        income_line.account_id = new_income_account
        invoice_3.action_post()

        # Create one additional invoice that does not reach the threshold
        self.init_invoice('out_invoice', partner=self.partner_b_be, post=True, amounts=[10], taxes=[self.tax_sale_a], invoice_date='2022-06-29')

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                                             VAT number          Turnover         VAT amount
            [   0,                                                                       1,                  2,              3],
            [
                ('Partner VAT Listing',                                                 '',             1300.0,          273.0),

                (self.company_data['default_account_tax_sale'].display_name,            '',                0.0,          273.0),
                ('Partner A (BE)',                                          'BE0246697724',                0.0,           63.0),
                (get_tax_line_name(invoice_3),                                          '',                0.0,           42.0),
                (get_tax_line_name(invoice_1),                                          '',                0.0,           21.0),
                ('Partner C (BE)',                                          'BE0477472701',                0.0,          210.0),
                (get_tax_line_name(invoice_2),                                          '',                0.0,          210.0),

                (self.company_data['default_account_revenue'].display_name,             '',             1100.0,            0.0),
                ('Partner A (BE)',                                          'BE0246697724',              100.0,            0.0),
                (get_base_line_name(invoice_1),                                         '',              100.0,            0.0),
                ('Partner C (BE)',                                          'BE0477472701',             1000.0,            0.0),
                (get_base_line_name(invoice_2),                                         '',             1000.0,            0.0),

                (new_income_account.display_name,                                       '',              200.0,            0.0),
                ('Partner A (BE)',                                          'BE0246697724',              200.0,            0.0),
                (get_base_line_name(invoice_3),                                         '',              200.0,            0.0),
            ],
            options,
        )


    @freeze_time('2019-12-31')
    def test_generate_xml_minimal(self):
        options = self.report.get_options(None)

        # The sequence changes between execution of the test. To handle that, we increase by 1 more, so we can get its value here
        sequence_number = self.env['ir.sequence'].next_by_code('declarantnum')
        ref = f"0477472701{str(int(sequence_number) + 1).zfill(4)[-4:]}"

        # This is the minimum expected from the belgian tax report xml.
        # As no values are in the report, we only find the grid 71 which is always expected to be present.
        expected_xml = """
            <ns2:ClientListingConsignment xmlns="http://www.minfin.fgov.be/InputCommon" xmlns:ns2="http://www.minfin.fgov.be/ClientListingConsignment" ClientListingsNbr="1">
                <ns2:ClientListing SequenceNumber="1" ClientsNbr="0" DeclarantReference="%s" TurnOverSum="0.00" VATAmountSum="0.00">
                    <ns2:Declarant>
                        <VATNumber>0477472701</VATNumber>
                        <Name>company_1_data</Name>
                        <Street></Street>
                        <PostCode></PostCode>
                        <City></City>
                        <CountryCode>BE</CountryCode>
                        <EmailAddress>jsmith@mail.com</EmailAddress>
                        <Phone>+32475123456</Phone>
                    </ns2:Declarant>
                    <ns2:Period>2018</ns2:Period>
                    <ns2:Comment></ns2:Comment>
                </ns2:ClientListing>
            </ns2:ClientListingConsignment>
        """ % ref

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self.env[self.report._get_custom_handler_model()].partner_vat_listing_export_to_xml(options)['file_content']),
            self.get_xml_tree_from_string(expected_xml)
        )

    def test_no_vat(self):
        """
        Test whether when there is partner's vat starting with "be", the report does not crash
        """
        self.env['res.partner'].search([]).write({'vat': False})
        options = self.report.get_options(None)
        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                        VAT number          Turnover            VAT amount
            [   0,                          1,                  2,                  3],
            [
                ('Partner VAT Listing',     '',                 0,                  0),
            ],
            options,
        )

    @freeze_time('2019-12-31')
    def test_generate_xml_with_company_without_be_in_vat_number(self):
        """ The aim of this test is verifying that we generate the Partner VAT Listing
            XML correctly, even if the company vat number doesn't start with 'BE'.
        """
        self.company_data['company'].vat = self.company_data['company'].vat.upper().replace('BE', '')
        options = self._generate_options(self.report, '2019-12-01', '2019-12-31')

        # The sequence changes between execution of the test. To handle that, we increase by 1 more, so we can get its value here
        sequence_number = self.env['ir.sequence'].next_by_code('declarantnum')
        ref = f"0477472701{str(int(sequence_number) + 1).zfill(4)[-4:]}"

        partner_be = self.env['res.partner'].create({
            'name': 'Belgian Partner',
            'vat': 'BE0694545041',
            'country_id': self.env.ref('base.be').id,
        })

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-12-22',
            'partner_id': partner_be.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'test',
                    'price_unit': 3500.0,
                    'quantity': 1,
                    'tax_ids': [Command.link(self.tax_sale_a.id)],
                })
            ]
        })
        move.action_post()

        expected_xml = f"""
            <ns2:ClientListingConsignment xmlns="http://www.minfin.fgov.be/InputCommon" xmlns:ns2="http://www.minfin.fgov.be/ClientListingConsignment" ClientListingsNbr="1">
                <ns2:ClientListing SequenceNumber="1" ClientsNbr="1" DeclarantReference="{ref}" TurnOverSum="3500.00" VATAmountSum="735.00">
                    <ns2:Declarant>
                        <VATNumber>0477472701</VATNumber>
                        <Name>company_1_data</Name>
                        <Street></Street>
                        <PostCode></PostCode>
                        <City></City>
                        <CountryCode>BE</CountryCode>
                        <EmailAddress>jsmith@mail.com</EmailAddress>
                        <Phone>+32475123456</Phone>
                    </ns2:Declarant>
                    <ns2:Period>2019</ns2:Period>
                    <ns2:Client SequenceNumber="1">
                        <ns2:CompanyVATNumber issuedBy="BE">0694545041</ns2:CompanyVATNumber>
                        <ns2:TurnOver>3500.00</ns2:TurnOver>
                        <ns2:VATAmount>735.00</ns2:VATAmount>
                    </ns2:Client>
                    <ns2:Comment></ns2:Comment>
                </ns2:ClientListing>
            </ns2:ClientListingConsignment>
        """

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self.env[self.report._get_custom_handler_model()].partner_vat_listing_export_to_xml(options)['file_content']),
            self.get_xml_tree_from_string(expected_xml)
        )

    @freeze_time('2019-12-31')
    def test_generate_xml_minimal_with_representative(self):
        company = self.env.company
        options = self.report.get_options(None)

        # Create a new partner for the representative and link it to the company.
        representative = self.env['res.partner'].create({
            'company_type': 'company',
            'name': 'Fidu BE',
            'street': 'Fidu Street 123',
            'city': 'Brussels',
            'zip': '1000',
            'country_id': self.env.ref('base.be').id,
            'vat': 'BE0477472701',
            'mobile': '+32470123456',
            'email': 'info@fidu.be',
        })
        company.account_representative_id = representative.id

        # The sequence changes between execution of the test. To handle that, we increase by 1 more, so we can get its value here
        sequence_number = self.env['ir.sequence'].next_by_code('declarantnum')
        ref = f"0477472701{str(int(sequence_number) + 1).zfill(4)[-4:]}"

        # This is the minimum expected from the belgian tax report XML.
        # Only the representative node has been added to make sure it appears in the XML.
        expected_xml = """
            <ns2:ClientListingConsignment xmlns="http://www.minfin.fgov.be/InputCommon" xmlns:ns2="http://www.minfin.fgov.be/ClientListingConsignment" ClientListingsNbr="1">
                <ns2:Representative>
                    <RepresentativeID identificationType="NVAT" issuedBy="BE">0477472701</RepresentativeID>
                    <Name>Fidu BE</Name>
                    <Street>Fidu Street 123</Street>
                    <PostCode>1000</PostCode>
                    <City>Brussels</City>
                    <CountryCode>BE</CountryCode>
                    <EmailAddress>info@fidu.be</EmailAddress>
                    <Phone>+32470123456</Phone>
                </ns2:Representative>
                <ns2:ClientListing SequenceNumber="1" ClientsNbr="0" DeclarantReference="%s" TurnOverSum="0.00" VATAmountSum="0.00">
                    <ns2:Declarant>
                        <VATNumber>0477472701</VATNumber>
                        <Name>company_1_data</Name>
                        <Street></Street>
                        <PostCode></PostCode>
                        <City></City>
                        <CountryCode>BE</CountryCode>
                        <EmailAddress>jsmith@mail.com</EmailAddress>
                        <Phone>+32475123456</Phone>
                    </ns2:Declarant>
                    <ns2:Period>2018</ns2:Period>
                    <ns2:Comment></ns2:Comment>
                </ns2:ClientListing>
            </ns2:ClientListingConsignment>
        """ % ref

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self.env[self.report._get_custom_handler_model()].partner_vat_listing_export_to_xml(options)['file_content']),
            self.get_xml_tree_from_string(expected_xml)
        )
