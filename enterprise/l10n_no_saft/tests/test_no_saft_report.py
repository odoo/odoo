# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests.common import test_xsd
from odoo.tests import tagged
from odoo import Command, fields

from freezegun import freeze_time


class TestNoSaftReportCommon(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('no')
    def setUpClass(cls):
        super().setUpClass()

        (cls.partner_a + cls.partner_b).write({
            'city': 'Garnich',
            'zip': 'L-8353',
            'country_id': cls.env.ref('base.lu').id,
            'phone': '+352 24 11 11 11',
        })

        cls.company_data['company'].write({
            'city': 'OSLO',
            'zip': 'N-0104',
            'company_registry': '123456',
            'phone': '+47 11 11 11 11',
            'l10n_no_bronnoysund_number': '987654325',
        })

        cls.env['res.partner'].create({
            'name': 'Mr Big CEO',
            'is_company': False,
            'phone': '+47 11 11 12 34',
            'parent_id': cls.company_data['company'].partner_id.id,
        })

        cls.product_a.default_code = 'PA'
        cls.product_b.default_code = 'PB'

        # Create invoices

        cls.invoices = cls.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'invoice_date': '2019-01-01',
                'date': '2019-01-01',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': cls.product_a.id,
                    'quantity': 5.0,
                    'price_unit': 1000.0,
                    'tax_ids': [(6, 0, cls.company_data['default_tax_sale'].ids)],
                })],
            },
            {
                'move_type': 'out_refund',
                'invoice_date': '2019-03-01',
                'date': '2019-03-01',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': cls.product_a.id,
                    'quantity': 3.0,
                    'price_unit': 1000.0,
                    'tax_ids': [(6, 0, cls.company_data['default_tax_sale'].ids)],
                })],
            },
            {
                'move_type': 'in_invoice',
                'invoice_date': '2018-12-31',
                'date': '2018-12-31',
                'partner_id': cls.partner_b.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': cls.product_b.id,
                    'quantity': 10.0,
                    'price_unit': 800.0,
                    'tax_ids': [(6, 0, cls.company_data['default_tax_purchase'].ids)],
                })],
            },
            {
                # this entry is added to ensure that the XML will have CreditAmount tag
                # CreditAmount (or DebitAmount) is necessary for the SAF-T XML validator (even if the entry is empty)
                'move_type': 'entry',
                'date': '2019-11-30',
                'partner_id': cls.partner_a.id,
                'line_ids': [Command.create({
                    'debit': 0.0,
                    'credit': 0.0,
                    'account_id': cls.company_data['default_account_revenue'].id,
                })],
            },
        ])
        cls.invoices.action_post()


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestNoSaftReport(TestNoSaftReportCommon):
    @freeze_time('2019-12-31')
    def test_saft_report_values(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = self._generate_options(report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self.env[report.custom_handler_model_name].l10n_no_export_saft_to_xml(options)['file_content']),
            self.get_xml_tree_from_string(f'''
                <AuditFile xmlns="urn:StandardAuditFile-Taxation-Financial:NO">
                    <Header>
                        <AuditFileVersion>1.30</AuditFileVersion>
                        <AuditFileCountry>NO</AuditFileCountry>
                        <AuditFileDateCreated>2019-12-31</AuditFileDateCreated>
                        <SoftwareCompanyName>Odoo SA</SoftwareCompanyName>
                        <SoftwareID>Odoo</SoftwareID>
                        <SoftwareVersion>___ignore___</SoftwareVersion>
                        <Company>
                            <RegistrationNumber>123456</RegistrationNumber>
                            <Name>company_1_data</Name>
                            <Address>
                                <City>OSLO</City>
                                <PostalCode>N-0104</PostalCode>
                                <Country>NO</Country>
                            </Address>
                            <Contact>
                                <ContactPerson>
                                    <FirstName>NotUsed</FirstName>
                                    <LastName>Mr Big CEO</LastName>
                                </ContactPerson>
                                <Telephone>+47 11 11 12 34</Telephone>
                            </Contact>
                        </Company>
                        <DefaultCurrencyCode>NOK</DefaultCurrencyCode>
                        <SelectionCriteria>
                            <SelectionStartDate>2019-01-01</SelectionStartDate>
                            <SelectionEndDate>2019-12-31</SelectionEndDate>
                        </SelectionCriteria>
                        <TaxAccountingBasis>A</TaxAccountingBasis>
                    </Header>
                    <MasterFiles>
                        <GeneralLedgerAccounts>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Accounts receivable</AccountDescription>
                                <GroupingCategory>RF-1167</GroupingCategory>
                                <GroupingCode>1500</GroupingCode>
                                <AccountType>GL</AccountType>
                                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                                <ClosingDebitBalance>2500.00</ClosingDebitBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Retained result</AccountDescription>
                                <GroupingCategory>RF-1167</GroupingCategory>
                                <GroupingCode>2099</GroupingCode>
                                <AccountType>GL</AccountType>
                                <OpeningDebitBalance>8000.00</OpeningDebitBalance>
                                <ClosingDebitBalance>8000.00</ClosingDebitBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Trade creditors (copy)</AccountDescription>
                                <GroupingCategory>RF-1167</GroupingCategory>
                                <GroupingCode>2401</GroupingCode>
                                <AccountType>GL</AccountType>
                                <OpeningCreditBalance>10000.00</OpeningCreditBalance>
                                <ClosingCreditBalance>10000.00</ClosingCreditBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Output VAT, high rate</AccountDescription>
                                <GroupingCategory>RF-1167</GroupingCategory>
                                <GroupingCode>2700</GroupingCode>
                                <AccountType>GL</AccountType>
                                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                                <ClosingCreditBalance>500.00</ClosingCreditBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Input VAT, high rate</AccountDescription>
                                <GroupingCategory>RF-1167</GroupingCategory>
                                <GroupingCode>2710</GroupingCode>
                                <AccountType>GL</AccountType>
                                <OpeningDebitBalance>2000.00</OpeningDebitBalance>
                                <ClosingDebitBalance>2000.00</ClosingDebitBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Sales revenue, merchandise, subject to VAT, high rate</AccountDescription>
                                <GroupingCategory>RF-1167</GroupingCategory>
                                <GroupingCode>3000</GroupingCode>
                                <AccountType>GL</AccountType>
                                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                                <ClosingCreditBalance>2000.00</ClosingCreditBalance>
                            </Account>
                        </GeneralLedgerAccounts>
                        <Customers>
                            <Customer>
                                <Name>partner_a</Name>
                                <Address>
                                    <City>Garnich</City>
                                    <PostalCode>L-8353</PostalCode>
                                    <Country>LU</Country>
                                </Address>
                                <Contact>
                                    <ContactPerson>
                                        <FirstName>NotUsed</FirstName>
                                        <LastName>partner_a</LastName>
                                    </ContactPerson>
                                    <Telephone>+352 24 11 11 11</Telephone>
                                </Contact>
                                <CustomerID>___ignore___</CustomerID>
                                <BalanceAccount>
                                    <AccountID>___ignore___</AccountID>
                                    <OpeningDebitBalance>0.00</OpeningDebitBalance>
                                    <ClosingDebitBalance>2500.00</ClosingDebitBalance>
                                </BalanceAccount>
                            </Customer>
                        </Customers>
                        <TaxTable>
                            <TaxTableEntry>
                                <TaxType>MVA</TaxType>
                                <Description>Merverdiavgift</Description>
                                <TaxCodeDetails>
                                    <TaxCode>___ignore___</TaxCode>
                                    <Description>25%</Description>
                                    <TaxPercentage>25.0</TaxPercentage>
                                    <Country>NO</Country>
                                    <StandardTaxCode>3</StandardTaxCode>
                                    <BaseRate>100</BaseRate>
                                </TaxCodeDetails>
                            </TaxTableEntry>
                        </TaxTable>
                        <Owners>
                            <Owner>
                                <RegistrationNumber>123456</RegistrationNumber>
                                <Name>company_1_data</Name>
                                <Address>
                                    <City>OSLO</City>
                                    <PostalCode>N-0104</PostalCode>
                                    <Country>NO</Country>
                                </Address>
                                <Contact>
                                    <ContactPerson>
                                        <FirstName>NotUsed</FirstName>
                                        <LastName>Mr Big CEO</LastName>
                                    </ContactPerson>
                                    <Telephone>+47 11 11 12 34</Telephone>
                                </Contact>
                                <OwnerID>___ignore___</OwnerID>
                            </Owner>
                        </Owners>
                    </MasterFiles>
                    <GeneralLedgerEntries>
                        <NumberOfEntries>3</NumberOfEntries>
                        <TotalDebit>10000.00</TotalDebit>
                        <TotalCredit>10000.00</TotalCredit>
                        <Journal>
                            <JournalID>___ignore___</JournalID>
                            <Description>Customer Invoices</Description>
                            <Type>sale</Type>
                            <Transaction>
                                <TransactionID>___ignore___</TransactionID>
                                <Period>01</Period>
                                <PeriodYear>2019</PeriodYear>
                                <TransactionDate>2019-01-01</TransactionDate>
                                <TransactionType>out_invoi</TransactionType>
                                <Description>INV/2019/00001</Description>
                                <SystemEntryDate>___ignore___</SystemEntryDate>
                                <GLPostingDate>2019-01-01</GLPostingDate>
                                <CustomerID>___ignore___</CustomerID>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-01-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>[PA] product_a</Description>
                                    <CreditAmount>
                                        <Amount>5000.00</Amount>
                                    </CreditAmount>
                                    <TaxInformation>
                                        <TaxType>MVA</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>25.0</TaxPercentage>
                                        <TaxBaseDescription>25%</TaxBaseDescription>
                                        <CreditTaxAmount>
                                            <Amount>1250.00</Amount>
                                        </CreditTaxAmount>
                                    </TaxInformation>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-01-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>25%</Description>
                                    <CreditAmount>
                                        <Amount>1250.00</Amount>
                                    </CreditAmount>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-01-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>{self.invoices[0]._get_kid_number()}</Description>
                                    <DebitAmount>
                                        <Amount>6250.00</Amount>
                                    </DebitAmount>
                                </Line>
                            </Transaction>
                            <Transaction>
                                <TransactionID>___ignore___</TransactionID>
                                <Period>03</Period>
                                <PeriodYear>2019</PeriodYear>
                                <TransactionDate>2019-03-01</TransactionDate>
                                <TransactionType>out_refun</TransactionType>
                                <Description>RINV/2019/00001</Description>
                                <SystemEntryDate>___ignore___</SystemEntryDate>
                                <GLPostingDate>2019-03-01</GLPostingDate>
                                <CustomerID>___ignore___</CustomerID>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-03-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>[PA] product_a</Description>
                                    <DebitAmount>
                                        <Amount>3000.00</Amount>
                                    </DebitAmount>
                                    <TaxInformation>
                                        <TaxType>MVA</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>25.0</TaxPercentage>
                                        <TaxBaseDescription>25%</TaxBaseDescription>
                                        <DebitTaxAmount>
                                            <Amount>750.00</Amount>
                                        </DebitTaxAmount>
                                    </TaxInformation>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-03-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>25%</Description>
                                    <DebitAmount>
                                        <Amount>750.00</Amount>
                                    </DebitAmount>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-03-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>RINV/2019/00001</Description>
                                    <CreditAmount>
                                        <Amount>3750.00</Amount>
                                    </CreditAmount>
                                </Line>
                            </Transaction>
                        </Journal>
                        <Journal>
                            <JournalID>___ignore___</JournalID>
                            <Description>Miscellaneous Operations</Description>
                            <Type>general</Type>
                            <Transaction>
                                <TransactionID>___ignore___</TransactionID>
                                <Period>11</Period>
                                <PeriodYear>2019</PeriodYear>
                                <TransactionDate>2019-11-30</TransactionDate>
                                <TransactionType>entry</TransactionType>
                                <Description>MISC/2019/11/0001</Description>
                                <SystemEntryDate>___ignore___</SystemEntryDate>
                                <GLPostingDate>2019-11-30</GLPostingDate>
                                <CustomerID>___ignore___</CustomerID>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-11-30</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>MISC/2019/11/0001</Description>
                                    <CreditAmount>
                                        <Amount>0.00</Amount>
                                    </CreditAmount>
                                </Line>
                            </Transaction>
                        </Journal>
                    </GeneralLedgerEntries>
                </AuditFile>
            '''),
        )


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestNoSaftReportXmlValidity(TestNoSaftReportCommon):
    @test_xsd(url='https://raw.githubusercontent.com/Skatteetaten/saf-t/master/SAF-T_Financial_1.3/Norwegian_SAF-T_Financial_Schema_v_1.30.xsd')
    def test_xml_validity(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = self._generate_options(report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))
        return self.get_xml_tree_from_string(self.env[report.custom_handler_model_name].l10n_no_export_saft_to_xml(options)['file_content'])
