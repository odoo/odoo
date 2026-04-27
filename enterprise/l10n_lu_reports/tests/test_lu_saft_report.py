# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.account_saft.tests.common import TestSaftReport
from odoo.tests import tagged

from freezegun import freeze_time
from itertools import starmap


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestLuSaftReport(TestSaftReport):

    @classmethod
    @TestSaftReport.setup_country('lu')
    def setUpClass(cls):
        super().setUpClass()

        (cls.partner_a + cls.partner_b).write({
            'city': 'Garnich',
            'zip': 'L-8353',
            'country_id': cls.env.ref('base.lu').id,
            'phone': '+352 24 11 11 11',
        })

        cls.company_data['company'].write({
            'city': 'Garnich',
            'zip': 'L-8353',
            'company_registry': '123456',
            'phone': '+352 11 11 11 11',
            'country_id': cls.env.ref('base.lu').id,
        })

        cls.env['res.partner'].create({
            'name': 'Mr Big CEO',
            'is_company': False,
            'phone': '+352 24 11 12 34',
            'parent_id': cls.company_data['company'].partner_id.id,
        })

        cls.product_a.default_code = 'PA'
        cls.product_b.default_code = 'PB'
        cls.product_c = cls._create_product(name='product_c', lst_price=1000.0, standard_price=800.0, default_code='PA')
        cls.product_d = cls._create_product(name='product_d', lst_price=1000.0, standard_price=800.0, default_code=False)

        tax_10 = cls.company_data['default_tax_sale'].copy({
            'name': '10% S',
            'amount': 10.0,
            'include_base_amount': True,
        })
        cls.company_data['default_tax_sale'].sequence += 1

        # Create invoices

        invoices = cls.env['account.move'].create(
            list(starmap(cls._l10n_lu_saft_invoice_data, [
                ('out_invoice', '2019-01-01', cls.partner_a, [
                    {'product': cls.product_a, 'quantity': 5.0, 'price_unit': 1000.0, 'tax_ids': cls.company_data['default_tax_sale'].ids + tax_10.ids},
                    {'product': cls.product_b, 'quantity': 1.0, 'price_unit': 500.0, 'tax_ids': cls.company_data['default_tax_sale'].ids + tax_10.ids},
                ]),
                ('out_refund', '2019-03-01', cls.partner_a, [{'product': cls.product_a, 'quantity': 3.0, 'price_unit': 1000.0}]),
                ('in_invoice', '2018-12-31', cls.partner_b, [{'product': cls.product_b, 'quantity': 10.0, 'price_unit': 800.0}]),
                ('in_invoice', '2019-01-01', cls.partner_b, [{'product': cls.product_b, 'quantity': 10.0, 'price_unit': 800.0}]),
            ])))
        invoices.action_post()

    @classmethod
    def _l10n_lu_saft_invoice_data(cls, move_type, invoice_date, partner, lines_data):
        tax_type = 'purchase' if move_type == 'in_invoice' else 'sale'
        return {
            'move_type': move_type,
            'invoice_date': invoice_date,
            'date': invoice_date,
            'partner_id': partner.id,
            'invoice_line_ids': [Command.create({
                'product_id': line_data['product'].id,
                'quantity': line_data['quantity'],
                'price_unit': line_data['price_unit'],
                'tax_ids': [Command.set(line_data.get('tax_ids') or cls.company_data[f"default_tax_{tax_type}"].ids)]
            }) for line_data in lines_data],
        }

    def _l10n_lu_saft_generate_report(self, date_from='2019-01-01', date_to='2019-12-31'):
        options = self._generate_options(date_from, date_to)
        with freeze_time('2019-12-31'):
            return self.report_handler.l10n_lu_export_saft_to_xml(options)['file_content']

    def test_saft_report_errors(self):
        invoice_data = list(starmap(self._l10n_lu_saft_invoice_data, [
            ('out_invoice', '2019-01-01', self.partner_a, [{'product': self.product_c, 'quantity': 5.0, 'price_unit': 1000.0}]),
            ('out_invoice', '2019-01-01', self.partner_a, [{'product': self.product_d, 'quantity': 5.0, 'price_unit': 1000.0}]),
        ]))
        new_invoices = self.env['account.move'].create(invoice_data)
        new_invoices.action_post()
        with self.assertRaises(self.ReportException) as cm:
            self._l10n_lu_saft_generate_report()
        self.assertEqual(set(cm.exception.errors), {'product_duplicate_ref', 'product_missing_ref'})

    def test_saft_report_values(self):
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self._l10n_lu_saft_generate_report()),
            self.get_xml_tree_from_string('''
                <AuditFile xmlns="urn:OECD:StandardAuditFile-Taxation/2.00">
                    <Header>
                        <AuditFileVersion>2.01</AuditFileVersion>
                        <AuditFileCountry>LU</AuditFileCountry>
                        <AuditFileDateCreated>2019-12-31</AuditFileDateCreated>
                        <SoftwareCompanyName>Odoo SA</SoftwareCompanyName>
                        <SoftwareID>Odoo</SoftwareID>
                        <SoftwareVersion>___ignore___</SoftwareVersion>
                        <Company>
                            <RegistrationNumber>123456</RegistrationNumber>
                            <Name>company_1_data</Name>
                            <Address>
                                <City>Garnich</City>
                                <PostalCode>L-8353</PostalCode>
                                <Country>LU</Country>
                            </Address>
                            <Contact>
                                <ContactPerson>
                                    <FirstName>NotUsed</FirstName>
                                    <LastName>Mr Big CEO</LastName>
                                </ContactPerson>
                                <Telephone>+352 24 11 12 34</Telephone>
                            </Contact>
                        </Company>
                        <DefaultCurrencyCode>EUR</DefaultCurrencyCode>
                        <SelectionCriteria>
                            <SelectionStartDate>2019-01-01</SelectionStartDate>
                            <SelectionEndDate>2019-12-31</SelectionEndDate>
                        </SelectionCriteria>
                        <TaxAccountingBasis>Invoice Accounting</TaxAccountingBasis>
                    </Header>
                    <MasterFiles>
                        <GeneralLedgerAccounts>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Result for the financial year</AccountDescription>
                                <StandardAccountID>142000</StandardAccountID>
                                <AccountType>Current Year Earni</AccountType>
                                <OpeningDebitBalance>8000.00</OpeningDebitBalance>
                                <ClosingDebitBalance>8000.00</ClosingDebitBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Customers</AccountDescription>
                                <StandardAccountID>401100</StandardAccountID>
                                <AccountType>Receivable</AccountType>
                                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                                <ClosingDebitBalance>3568.50</ClosingDebitBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>VAT paid and recoverable</AccountDescription>
                                <StandardAccountID>421611</StandardAccountID>
                                <AccountType>Current Assets</AccountType>
                                <OpeningDebitBalance>1360.00</OpeningDebitBalance>
                                <ClosingDebitBalance>2720.00</ClosingDebitBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Suppliers (copy)</AccountDescription>
                                <StandardAccountID>441111</StandardAccountID>
                                <AccountType>Payable</AccountType>
                                <OpeningCreditBalance>9360.00</OpeningCreditBalance>
                                <ClosingCreditBalance>18720.00</ClosingCreditBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>VAT received</AccountDescription>
                                <StandardAccountID>461411</StandardAccountID>
                                <AccountType>Current Liabilitie</AccountType>
                                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                                <ClosingCreditBalance>1068.50</ClosingCreditBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Purchases of raw materials</AccountDescription>
                                <StandardAccountID>601000.1</StandardAccountID>
                                <AccountType>Expenses</AccountType>
                                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                                <ClosingDebitBalance>8000.00</ClosingDebitBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Sales of finished goods</AccountDescription>
                                <StandardAccountID>702100</StandardAccountID>
                                <AccountType>Income</AccountType>
                                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                                <ClosingCreditBalance>2000.00</ClosingCreditBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Sales of finished goods</AccountDescription>
                                <StandardAccountID>702100.1</StandardAccountID>
                                <AccountType>Income</AccountType>
                                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                                <ClosingCreditBalance>500.00</ClosingCreditBalance>
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
                                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                                <ClosingDebitBalance>3568.50</ClosingDebitBalance>
                            </Customer>
                        </Customers>
                        <Suppliers>
                            <Supplier>
                                <Name>partner_b</Name>
                                <Address>
                                    <City>Garnich</City>
                                    <PostalCode>L-8353</PostalCode>
                                    <Country>LU</Country>
                                </Address>
                                <Contact>
                                    <ContactPerson>
                                        <FirstName>NotUsed</FirstName>
                                        <LastName>partner_b</LastName>
                                    </ContactPerson>
                                    <Telephone>+352 24 11 11 11</Telephone>
                                </Contact>
                                <SupplierID>___ignore___</SupplierID>
                                <OpeningCreditBalance>9360.00</OpeningCreditBalance>
                                <ClosingCreditBalance>18720.00</ClosingCreditBalance>
                            </Supplier>
                        </Suppliers>
                        <TaxTable>
                            <TaxTableEntry>
                                <TaxType>___ignore___</TaxType>
                                <Description>Taxe sur la valeur ajoutée</Description>
                                <TaxCodeDetails>
                                    <TaxCode>___ignore___</TaxCode>
                                    <Description>17% S</Description>
                                    <TaxPercentage>17.0</TaxPercentage>
                                    <Country>LU</Country>
                                </TaxCodeDetails>
                            </TaxTableEntry>
                            <TaxTableEntry>
                                <TaxType>___ignore___</TaxType>
                                <Description>Taxe sur la valeur ajoutée</Description>
                                <TaxCodeDetails>
                                    <TaxCode>___ignore___</TaxCode>
                                    <Description>10% S</Description>
                                    <TaxPercentage>10.0</TaxPercentage>
                                    <Country>LU</Country>
                                </TaxCodeDetails>
                            </TaxTableEntry>
                            <TaxTableEntry>
                                <TaxType>___ignore___</TaxType>
                                <Description>Taxe sur la valeur ajoutée</Description>
                                <TaxCodeDetails>
                                    <TaxCode>___ignore___</TaxCode>
                                    <Description>17% S</Description>
                                    <TaxPercentage>17.0</TaxPercentage>
                                    <Country>LU</Country>
                                </TaxCodeDetails>
                            </TaxTableEntry>
                        </TaxTable>
                        <UOMTable>
                            <UOMTableEntry>
                                <UnitOfMeasure>Units</UnitOfMeasure>
                                <Description>Unit</Description>
                            </UOMTableEntry>
                            <UOMTableEntry>
                                <UnitOfMeasure>Dozens</UnitOfMeasure>
                                <Description>Unit</Description>
                            </UOMTableEntry>
                        </UOMTable>
                        <Products>
                            <Product>
                                <ProductCode>PA</ProductCode>
                                <ProductGroup>Test Category</ProductGroup>
                                <Description>product_a</Description>
                                <UOMBase>Units</UOMBase>
                            </Product>
                            <Product>
                                <ProductCode>PB</ProductCode>
                                <ProductGroup>Test Category</ProductGroup>
                                <Description>product_b</Description>
                                <UOMBase>Units</UOMBase>
                                <UOMStandard>Dozens</UOMStandard>
                                <UOMToUOMBaseConversionFactor>0.08333333</UOMToUOMBaseConversionFactor>
                            </Product>
                        </Products>
                        <Owners>
                            <Owner>
                                <RegistrationNumber>123456</RegistrationNumber>
                                <Name>company_1_data</Name>
                                <Address>
                                    <City>Garnich</City>
                                    <PostalCode>L-8353</PostalCode>
                                    <Country>LU</Country>
                                </Address>
                                <Contact>
                                    <ContactPerson>
                                        <FirstName>NotUsed</FirstName>
                                        <LastName>Mr Big CEO</LastName>
                                    </ContactPerson>
                                    <Telephone>+352 24 11 12 34</Telephone>
                                </Contact>
                                <OwnerID>___ignore___</OwnerID>
                            </Owner>
                        </Owners>
                    </MasterFiles>
                    <GeneralLedgerEntries>
                        <NumberOfEntries>3</NumberOfEntries>
                        <TotalDebit>19948.50</TotalDebit>
                        <TotalCredit>19948.50</TotalCredit>
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
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>5500.00</TaxBase>
                                        <TaxBaseDescription>17% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>935.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>10.0</TaxPercentage>
                                        <TaxBase>5000.00</TaxBase>
                                        <TaxBaseDescription>10% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>500.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-01-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>[PB] product_b</Description>
                                    <CreditAmount>
                                        <Amount>500.00</Amount>
                                    </CreditAmount>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>550.00</TaxBase>
                                        <TaxBaseDescription>17% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>93.50</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>10.0</TaxPercentage>
                                        <TaxBase>500.00</TaxBase>
                                        <TaxBaseDescription>10% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>50.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-01-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>10% S</Description>
                                    <CreditAmount>
                                        <Amount>550.00</Amount>
                                    </CreditAmount>
                                </Line><Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-01-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>17% S</Description>
                                    <CreditAmount>
                                        <Amount>1028.50</Amount>
                                    </CreditAmount>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-01-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>INV/2019/00001</Description>
                                    <DebitAmount>
                                        <Amount>7078.50</Amount>
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
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>3000.00</TaxBase>
                                        <TaxBaseDescription>17% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>510.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-03-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>17% S</Description>
                                    <DebitAmount>
                                        <Amount>510.00</Amount>
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
                                        <Amount>3510.00</Amount>
                                    </CreditAmount>
                                </Line>
                            </Transaction>
                        </Journal>
                        <Journal>
                            <JournalID>___ignore___</JournalID>
                            <Description>Vendor Bills</Description>
                            <Type>purchase</Type>
                            <Transaction>
                                <TransactionID>___ignore___</TransactionID>
                                <Period>01</Period>
                                <PeriodYear>2019</PeriodYear>
                                <TransactionDate>2019-01-01</TransactionDate>
                                <TransactionType>in_invoic</TransactionType>
                                <Description>BILL/2019/01/0001</Description>
                                <SystemEntryDate>___ignore___</SystemEntryDate>
                                <GLPostingDate>2019-01-01</GLPostingDate>
                                <SupplierID>___ignore___</SupplierID>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-01-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <SupplierID>___ignore___</SupplierID>
                                    <Description>[PB] product_b</Description>
                                    <DebitAmount>
                                        <Amount>8000.00</Amount>
                                    </DebitAmount>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>8000.00</TaxBase>
                                        <TaxBaseDescription>17% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>1360.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-01-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <SupplierID>___ignore___</SupplierID>
                                    <Description>17% S</Description>
                                    <DebitAmount>
                                        <Amount>1360.00</Amount>
                                    </DebitAmount>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-01-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <SupplierID>___ignore___</SupplierID>
                                    <Description>installment #1</Description>
                                    <CreditAmount>
                                        <Amount>2808.00</Amount>
                                    </CreditAmount>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-01-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <SupplierID>___ignore___</SupplierID>
                                    <Description>installment #2</Description>
                                    <CreditAmount>
                                        <Amount>6552.00</Amount>
                                    </CreditAmount>
                                </Line>
                            </Transaction>
                        </Journal>
                    </GeneralLedgerEntries>
                    <SourceDocuments>
                        <SalesInvoices>
                            <NumberOfEntries>2</NumberOfEntries>
                            <TotalDebit>3000.00</TotalDebit>
                            <TotalCredit>5500.00</TotalCredit>
                            <Invoice>
                                <InvoiceNo>INV/2019/00001</InvoiceNo>
                                <CustomerInfo>
                                    <CustomerID>___ignore___</CustomerID>
                                    <BillingAddress>
                                        <City>Garnich</City>
                                        <PostalCode>L-8353</PostalCode>
                                        <Country>LU</Country>
                                    </BillingAddress>
                                </CustomerInfo>
                                <Period>01</Period>
                                <PeriodYear>2019</PeriodYear>
                                <InvoiceDate>2019-01-01</InvoiceDate>
                                <InvoiceType>out_invoi</InvoiceType>
                                <GLPostingDate>2019-01-01</GLPostingDate>
                                <TransactionID>___ignore___</TransactionID>
                                <Line>
                                    <AccountID>___ignore___</AccountID>
                                    <OrderReferences>
                                        <OriginatingON>INV/2019/00001</OriginatingON>
                                        <OrderDate>2019-01-01</OrderDate>
                                    </OrderReferences>
                                    <ProductCode>PA</ProductCode>
                                    <ProductDescription>[PA] product_a</ProductDescription>
                                    <Quantity>5.0</Quantity>
                                    <InvoiceUOM>Units</InvoiceUOM>
                                    <UnitPrice>1000.00</UnitPrice>
                                    <TaxPointDate>2019-01-01</TaxPointDate>
                                    <Description>[PA] product_a</Description>
                                    <InvoiceLineAmount>
                                        <Amount>5000.00</Amount>
                                    </InvoiceLineAmount>
                                    <DebitCreditIndicator>C</DebitCreditIndicator>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>5500.00</TaxBase>
                                        <TaxBaseDescription>17% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>935.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>10.0</TaxPercentage>
                                        <TaxBase>5000.00</TaxBase>
                                        <TaxBaseDescription>10% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>500.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <Line>
                                    <AccountID>___ignore___</AccountID>
                                    <OrderReferences>
                                        <OriginatingON>INV/2019/00001</OriginatingON>
                                        <OrderDate>2019-01-01</OrderDate>
                                    </OrderReferences>
                                    <ProductCode>PB</ProductCode>
                                    <ProductDescription>[PB] product_b</ProductDescription>
                                    <Quantity>1.0</Quantity>
                                    <InvoiceUOM>Dozens</InvoiceUOM>
                                    <UnitPrice>500.00</UnitPrice>
                                    <TaxPointDate>2019-01-01</TaxPointDate>
                                    <Description>[PB] product_b</Description>
                                    <InvoiceLineAmount>
                                        <Amount>500.00</Amount>
                                    </InvoiceLineAmount>
                                    <DebitCreditIndicator>C</DebitCreditIndicator>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>550.00</TaxBase>
                                        <TaxBaseDescription>17% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>93.50</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>10.0</TaxPercentage>
                                        <TaxBase>500.00</TaxBase>
                                        <TaxBaseDescription>10% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>50.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <DocumentTotals>
                                    <TaxInformationTotals>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>10.0</TaxPercentage>
                                        <TaxBase>5500.00</TaxBase>
                                        <TaxBaseDescription>10% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>550.00</Amount>
                                        </TaxAmount>
                                    </TaxInformationTotals>
                                    <TaxInformationTotals>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>6050.00</TaxBase>
                                        <TaxBaseDescription>17% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>1028.50</Amount>
                                        </TaxAmount>
                                    </TaxInformationTotals>
                                    <NetTotal>5500.00</NetTotal>
                                    <GrossTotal>7078.50</GrossTotal>
                                </DocumentTotals>
                            </Invoice>
                            <Invoice>
                                <InvoiceNo>RINV/2019/00001</InvoiceNo>
                                <CustomerInfo>
                                    <CustomerID>___ignore___</CustomerID>
                                    <BillingAddress>
                                        <City>Garnich</City>
                                        <PostalCode>L-8353</PostalCode>
                                        <Country>LU</Country>
                                    </BillingAddress>
                                </CustomerInfo>
                                <Period>03</Period>
                                <PeriodYear>2019</PeriodYear>
                                <InvoiceDate>2019-03-01</InvoiceDate>
                                <InvoiceType>out_refun</InvoiceType>
                                <GLPostingDate>2019-03-01</GLPostingDate>
                                <TransactionID>___ignore___</TransactionID>
                                <Line>
                                    <AccountID>___ignore___</AccountID>
                                    <OrderReferences>
                                        <OriginatingON>RINV/2019/00001</OriginatingON>
                                        <OrderDate>2019-03-01</OrderDate>
                                    </OrderReferences>
                                    <ProductCode>PA</ProductCode>
                                    <ProductDescription>[PA] product_a</ProductDescription>
                                    <Quantity>3.0</Quantity>
                                    <InvoiceUOM>Units</InvoiceUOM>
                                    <UnitPrice>1000.00</UnitPrice>
                                    <TaxPointDate>2019-03-01</TaxPointDate>
                                    <Description>[PA] product_a</Description>
                                    <InvoiceLineAmount>
                                        <Amount>3000.00</Amount>
                                    </InvoiceLineAmount>
                                    <DebitCreditIndicator>D</DebitCreditIndicator>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>3000.00</TaxBase>
                                        <TaxBaseDescription>17% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>510.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <DocumentTotals>
                                    <TaxInformationTotals>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>3000.00</TaxBase>
                                        <TaxBaseDescription>17% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>510.00</Amount>
                                        </TaxAmount>
                                    </TaxInformationTotals>
                                    <NetTotal>-3000.00</NetTotal>
                                    <GrossTotal>-3510.00</GrossTotal>
                                </DocumentTotals>
                            </Invoice>
                        </SalesInvoices>
                        <PurchaseInvoices>
                        <NumberOfEntries>1</NumberOfEntries>
                        <TotalDebit>8000.00</TotalDebit>
                        <TotalCredit>0.00</TotalCredit>
                        <Invoice>
                            <InvoiceNo>BILL/2019/01/0001</InvoiceNo>
                            <SupplierInfo>
                                <SupplierID>___ignore___</SupplierID>
                                <BillingAddress>
                                    <City>Garnich</City>
                                    <PostalCode>L-8353</PostalCode>
                                    <Country>LU</Country>
                                </BillingAddress>
                            </SupplierInfo>
                            <Period>01</Period>
                            <PeriodYear>2019</PeriodYear>
                            <InvoiceDate>2019-01-01</InvoiceDate>
                            <InvoiceType>in_invoic</InvoiceType>
                            <GLPostingDate>2019-01-01</GLPostingDate>
                            <TransactionID>___ignore___</TransactionID>
                            <Line>
                                <AccountID>___ignore___</AccountID>
                                <OrderReferences>
                                    <OriginatingON>BILL/2019/01/0001</OriginatingON>
                                    <OrderDate>2019-01-01</OrderDate>
                                </OrderReferences>
                                <ProductCode>PB</ProductCode>
                                <ProductDescription>[PB] product_b</ProductDescription>
                                <Quantity>10.0</Quantity>
                                <InvoiceUOM>Dozens</InvoiceUOM>
                                <UnitPrice>800.00</UnitPrice>
                                <TaxPointDate>2019-01-01</TaxPointDate>
                                <Description>[PB] product_b</Description>
                                <InvoiceLineAmount>
                                    <Amount>8000.00</Amount>
                                </InvoiceLineAmount>
                                <DebitCreditIndicator>D</DebitCreditIndicator>
                                <TaxInformation>
                                    <TaxType>___ignore___</TaxType>
                                    <TaxCode>___ignore___</TaxCode>
                                    <TaxPercentage>17.0</TaxPercentage>
                                    <TaxBase>8000.00</TaxBase>
                                    <TaxBaseDescription>17% S</TaxBaseDescription>
                                    <TaxAmount>
                                        <Amount>1360.00</Amount>
                                    </TaxAmount>
                                </TaxInformation>
                            </Line>
                            <DocumentTotals>
                                <TaxInformationTotals>
                                    <TaxType>___ignore___</TaxType>
                                    <TaxCode>___ignore___</TaxCode>
                                    <TaxPercentage>17.0</TaxPercentage>
                                    <TaxBase>8000.00</TaxBase>
                                    <TaxBaseDescription>17% S</TaxBaseDescription>
                                    <TaxAmount>
                                        <Amount>1360.00</Amount>
                                    </TaxAmount>
                                </TaxInformationTotals>
                                <NetTotal>-8000.00</NetTotal>
                                <GrossTotal>-9360.00</GrossTotal>
                            </DocumentTotals>
                        </Invoice>
                        </PurchaseInvoices>
                    </SourceDocuments>
                </AuditFile>
            '''),
        )

    @freeze_time('2025-12-30')
    def test_partner_classification_faia_report(self):
        """
        Test that partners are correctly classified as both customers and suppliers in the FAIA report,
        and that credit notes are not classified as suppliers.
        """

        partner_c = self.env['res.partner'].create({
            'name': 'partner c',
            'city': 'Garnich',
            'zip': 'L-8353',
            'country_id': self.env.ref('base.lu').id,
            'phone': '+352 24 11 11 11',
        })

        last_month_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2025-11-01',
            'invoice_date': '2025-11-01',
            'partner_id': partner_c.id,
            'line_ids': [Command.create({
                'product_id': self.product_a.id,
                'quantity': 300.0,
                'price_unit': 1.0,
                'tax_ids': [(6, 0, self.company_data['default_tax_sale'].ids)],
            })]
        })
        last_month_invoice.action_post()

        credit_note_wizard = self.env['account.move.reversal'].create({
            'move_ids': last_month_invoice.ids,
            'reason': 'test',
            'date': '2025-12-01',
            'journal_id': self.company_data['default_journal_sale'].id,
        })

        refund = self.env['account.move'].browse(credit_note_wizard.refund_moves()['res_id'])
        refund.action_post()

        this_month_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2025-12-01',
            'invoice_date': '2025-12-01',
            'partner_id': partner_c.id,
            'line_ids': [Command.create({
                'product_id': self.product_a.id,
                'quantity': 100.0,
                'price_unit': 1.0,
                'tax_ids': [(6, 0, self.company_data['default_tax_sale'].ids)],
            })]
        })
        this_month_invoice.action_post()

        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2025-12-01',
            'invoice_date': '2025-12-01',
            'partner_id': partner_c.id,
            'line_ids': [Command.create({
                'product_id': self.product_a.id,
                'quantity': 200.0,
                'price_unit': 1.0,
                'tax_ids': [(6, 0, self.company_data['default_tax_purchase'].ids)],
            })]
        })
        bill.action_post()
        foreign_currency = self.setup_other_currency('USD', rates=[
            ('2016-01-01', 3.0),
            ('2017-01-01', 2.0),
        ])
        bill_forex = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2025-12-06',
            'invoice_date': '2025-12-03',
            'partner_id': partner_c.id,
            'currency_id': foreign_currency.id,
            'line_ids': [Command.create({
                'product_id': self.product_a.id,
                'quantity': 200.0,
                'price_unit': 1.0,
                'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
            })]
        })

        bill_forex.action_post()

        self.env.flush_all()

        report = self.env.ref('account_reports.general_ledger_report')
        options = self._generate_options('2025-12-01', '2025-12-31')
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self.env[report.custom_handler_model_name].l10n_lu_export_saft_to_xml(options)['file_content']),
            self.get_xml_tree_from_string('''
                <AuditFile xmlns="urn:OECD:StandardAuditFile-Taxation/2.00">
                    <Header>
                        <AuditFileVersion>2.01</AuditFileVersion>
                        <AuditFileCountry>LU</AuditFileCountry>
                        <AuditFileDateCreated>2025-12-30</AuditFileDateCreated>
                        <SoftwareCompanyName>Odoo SA</SoftwareCompanyName>
                        <SoftwareID>Odoo</SoftwareID>
                        <SoftwareVersion>___ignore___</SoftwareVersion>
                        <Company>
                            <RegistrationNumber>123456</RegistrationNumber>
                            <Name>company_1_data</Name>
                            <Address>
                                <City>Garnich</City>
                                <PostalCode>L-8353</PostalCode>
                                <Country>LU</Country>
                            </Address>
                            <Contact>
                                <ContactPerson>
                                    <FirstName>NotUsed</FirstName>
                                    <LastName>Mr Big CEO</LastName>
                                </ContactPerson>
                                <Telephone>+352 24 11 12 34</Telephone>
                            </Contact>
                        </Company>
                        <DefaultCurrencyCode>EUR</DefaultCurrencyCode>
                        <SelectionCriteria>
                            <SelectionStartDate>___ignore___</SelectionStartDate>
                            <SelectionEndDate>___ignore___</SelectionEndDate>
                        </SelectionCriteria>
                        <TaxAccountingBasis>Invoice Accounting</TaxAccountingBasis>
                    </Header>
                    <MasterFiles>
                        <GeneralLedgerAccounts>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Result for the financial year</AccountDescription>
                                <StandardAccountID>142000</StandardAccountID>
                                <AccountType>Current Year Earni</AccountType>
                                <OpeningDebitBalance>13500.00</OpeningDebitBalance>
                                <ClosingDebitBalance>13500.00</ClosingDebitBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Customers</AccountDescription>
                                <StandardAccountID>401100</StandardAccountID>
                                <AccountType>Receivable</AccountType>
                                <OpeningDebitBalance>3919.50</OpeningDebitBalance>
                                <ClosingDebitBalance>3685.50</ClosingDebitBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>VAT paid and recoverable</AccountDescription>
                                <StandardAccountID>421611</StandardAccountID>
                                <AccountType>Current Assets</AccountType>
                                <OpeningDebitBalance>2720.00</OpeningDebitBalance>
                                <ClosingDebitBalance>2771.00</ClosingDebitBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Suppliers</AccountDescription>
                                <StandardAccountID>___ignore___</StandardAccountID>
                                <AccountType>Payable</AccountType>
                                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                                <ClosingCreditBalance>351.00</ClosingCreditBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Suppliers (copy)</AccountDescription>
                                <StandardAccountID>___ignore___</StandardAccountID>
                                <AccountType>Payable</AccountType>
                                <OpeningCreditBalance>18720.00</OpeningCreditBalance>
                                <ClosingCreditBalance>18720.00</ClosingCreditBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>VAT received</AccountDescription>
                                <StandardAccountID>___ignore___</StandardAccountID>
                                <AccountType>Current Liabilitie</AccountType>
                                <OpeningCreditBalance>1119.50</OpeningCreditBalance>
                                <ClosingCreditBalance>1085.50</ClosingCreditBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Purchases of raw materials</AccountDescription>
                                <StandardAccountID>601000</StandardAccountID>
                                <AccountType>Expenses</AccountType>
                                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                                <ClosingDebitBalance>300.00</ClosingDebitBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Sales of finished goods</AccountDescription>
                                <StandardAccountID>702100</StandardAccountID>
                                <AccountType>Income</AccountType>
                                <OpeningCreditBalance>300.00</OpeningCreditBalance>
                                <ClosingCreditBalance>100.00</ClosingCreditBalance>
                            </Account>
                        </GeneralLedgerAccounts>
                        <Customers>
                            <Customer>
                                <Name>partner c</Name>
                                <Address>
                                    <City>Garnich</City>
                                    <PostalCode>L-8353</PostalCode>
                                    <Country>LU</Country>
                                </Address>
                                <Contact>
                                    <ContactPerson>
                                        <FirstName>NotUsed</FirstName>
                                        <LastName>partner c</LastName>
                                    </ContactPerson>
                                    <Telephone>+352 24 11 11 11</Telephone>
                                </Contact>
                                <CustomerID>___ignore___</CustomerID>
                                <OpeningDebitBalance>351.00</OpeningDebitBalance>
                                <ClosingDebitBalance>117.00</ClosingDebitBalance>
                            </Customer>
                        </Customers>
                        <Suppliers>
                            <Supplier>
                                <Name>partner c</Name>
                                <Address>
                                    <City>Garnich</City>
                                    <PostalCode>L-8353</PostalCode>
                                    <Country>LU</Country>
                                </Address>
                                <Contact>
                                    <ContactPerson>
                                        <FirstName>NotUsed</FirstName>
                                        <LastName>partner c</LastName>
                                    </ContactPerson>
                                    <Telephone>+352 24 11 11 11</Telephone>
                                </Contact>
                                <SupplierID>___ignore___</SupplierID>
                                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                                <ClosingCreditBalance>351.00</ClosingCreditBalance>
                            </Supplier>
                        </Suppliers>
                        <TaxTable>
                            <TaxTableEntry>
                                <TaxType>___ignore___</TaxType>
                                <Description>Taxe sur la valeur ajoutée</Description>
                                <TaxCodeDetails>
                                    <TaxCode>___ignore___</TaxCode>
                                    <Description>___ignore___</Description>
                                    <TaxPercentage>17.0</TaxPercentage>
                                    <Country>LU</Country>
                                </TaxCodeDetails>
                            </TaxTableEntry>
                            <TaxTableEntry>
                                <TaxType>___ignore___</TaxType>
                                <Description>Taxe sur la valeur ajoutée</Description>
                                <TaxCodeDetails>
                                    <TaxCode>___ignore___</TaxCode>
                                    <Description>___ignore___</Description>
                                    <TaxPercentage>17.0</TaxPercentage>
                                    <Country>LU</Country>
                                </TaxCodeDetails>
                            </TaxTableEntry>
                        </TaxTable>
                        <UOMTable>
                            <UOMTableEntry>
                                <UnitOfMeasure>Units</UnitOfMeasure>
                                <Description>Unit</Description>
                            </UOMTableEntry>
                        </UOMTable>
                        <Products>
                            <Product>
                                <ProductCode>PA</ProductCode>
                                <ProductGroup>___ignore___</ProductGroup>
                                <Description>product_a</Description>
                                <UOMBase>Units</UOMBase>
                            </Product>
                        </Products>
                        <Owners>
                            <Owner>
                                <RegistrationNumber>123456</RegistrationNumber>
                                <Name>company_1_data</Name>
                                <Address>
                                    <City>Garnich</City>
                                    <PostalCode>L-8353</PostalCode>
                                    <Country>LU</Country>
                                </Address>
                                <Contact>
                                    <ContactPerson>
                                        <FirstName>NotUsed</FirstName>
                                        <LastName>Mr Big CEO</LastName>
                                    </ContactPerson>
                                    <Telephone>+352 24 11 12 34</Telephone>
                                </Contact>
                                <OwnerID>___ignore___</OwnerID>
                            </Owner>
                        </Owners>
                    </MasterFiles>
                    <GeneralLedgerEntries>
                        <NumberOfEntries>4</NumberOfEntries>
                        <TotalDebit>819.00</TotalDebit>
                        <TotalCredit>819.00</TotalCredit>
                        <Journal>
                            <JournalID>___ignore___</JournalID>
                            <Description>Customer Invoices</Description>
                            <Type>sale</Type>
                            <Transaction>
                                <TransactionID>___ignore___</TransactionID>
                                <Period>12</Period>
                                <PeriodYear>2025</PeriodYear>
                                <TransactionDate>2025-12-01</TransactionDate>
                                <TransactionType>out_refun</TransactionType>
                                <Description>RINV/2025/00001</Description>
                                <SystemEntryDate>___ignore___</SystemEntryDate>
                                <GLPostingDate>2025-12-01</GLPostingDate>
                                <CustomerID>___ignore___</CustomerID>
                                <SupplierID>___ignore___</SupplierID>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2025-12-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>[PA] product_a</Description>
                                    <DebitAmount>
                                        <Amount>300.00</Amount>
                                    </DebitAmount>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>300.00</TaxBase>
                                        <TaxBaseDescription>___ignore___</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>51.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2025-12-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>___ignore___</Description>
                                    <CreditAmount>
                                        <Amount>351.00</Amount>
                                    </CreditAmount>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2025-12-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>___ignore___</Description>
                                    <DebitAmount>
                                        <Amount>51.00</Amount>
                                    </DebitAmount>
                                </Line>
                            </Transaction>
                            <Transaction>
                                <TransactionID>___ignore___</TransactionID>
                                <Period>12</Period>
                                <PeriodYear>2025</PeriodYear>
                                <TransactionDate>2025-12-01</TransactionDate>
                                <TransactionType>out_invoi</TransactionType>
                                <Description>INV/2025/00002</Description>
                                <SystemEntryDate>___ignore___</SystemEntryDate>
                                <GLPostingDate>2025-12-01</GLPostingDate>
                                <CustomerID>___ignore___</CustomerID>
                                <SupplierID>___ignore___</SupplierID>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2025-12-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>[PA] product_a</Description>
                                    <CreditAmount>
                                        <Amount>100.00</Amount>
                                    </CreditAmount>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>100.00</TaxBase>
                                        <TaxBaseDescription>___ignore___</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>17.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2025-12-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>___ignore___</Description>
                                    <CreditAmount>
                                        <Amount>17.00</Amount>
                                    </CreditAmount>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2025-12-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>INV/2025/00002</Description>
                                    <DebitAmount>
                                        <Amount>117.00</Amount>
                                    </DebitAmount>
                                </Line>
                            </Transaction>
                        </Journal>
                        <Journal>
                            <JournalID>___ignore___</JournalID>
                            <Description>Vendor Bills</Description>
                            <Type>purchase</Type>
                            <Transaction>
                                <TransactionID>___ignore___</TransactionID>
                                <Period>12</Period>
                                <PeriodYear>2025</PeriodYear>
                                <TransactionDate>2025-12-01</TransactionDate>
                                <TransactionType>in_invoic</TransactionType>
                                <Description>BILL/2025/12/0001</Description>
                                <SystemEntryDate>___ignore___</SystemEntryDate>
                                <GLPostingDate>2025-12-01</GLPostingDate>
                                <CustomerID>___ignore___</CustomerID>
                                <SupplierID>___ignore___</SupplierID>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2025-12-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>[PA] product_a</Description>
                                    <DebitAmount>
                                        <Amount>200.00</Amount>
                                    </DebitAmount>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>200.00</TaxBase>
                                        <TaxBaseDescription>___ignore___</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>34.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2025-12-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>___ignore___</Description>
                                    <DebitAmount>
                                        <Amount>34.00</Amount>
                                    </DebitAmount>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2025-12-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>BILL/2025/12/0001</Description>
                                    <CreditAmount>
                                        <Amount>234.00</Amount>
                                    </CreditAmount>
                                </Line>
                            </Transaction>
                            <Transaction>
                                <TransactionID>___ignore___</TransactionID>
                                <Period>12</Period>
                                <PeriodYear>2025</PeriodYear>
                                <TransactionDate>2025-12-06</TransactionDate>
                                <TransactionType>in_invoic</TransactionType>
                                <Description>BILL/2025/12/0002</Description>
                                <SystemEntryDate>___ignore___</SystemEntryDate>
                                <GLPostingDate>2025-12-06</GLPostingDate>
                                <CustomerID>___ignore___</CustomerID>
                                <SupplierID>___ignore___</SupplierID>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2025-12-06</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>[PA] product_a</Description>
                                    <DebitAmount>
                                        <Amount>100.00</Amount>
                                        <CurrencyCode>USD</CurrencyCode>
                                        <CurrencyAmount>200.00</CurrencyAmount>
                                        <ExchangeRate>2.00000000</ExchangeRate>
                                    </DebitAmount>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>100.00</TaxBase>
                                        <TaxBaseDescription>___ignore___</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>17.00</Amount>
                                            <CurrencyCode>USD</CurrencyCode>
                                            <CurrencyAmount>17.00</CurrencyAmount>
                                            <ExchangeRate>2.00000000</ExchangeRate>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2025-12-06</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>___ignore___</Description>
                                    <DebitAmount>
                                        <Amount>17.00</Amount>
                                        <CurrencyCode>USD</CurrencyCode>
                                        <CurrencyAmount>34.00</CurrencyAmount>
                                        <ExchangeRate>2.00000000</ExchangeRate>
                                    </DebitAmount>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2025-12-06</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>BILL/2025/12/0002</Description>
                                    <CreditAmount>
                                        <Amount>117.00</Amount>
                                        <CurrencyCode>USD</CurrencyCode>
                                        <CurrencyAmount>234.00</CurrencyAmount>
                                        <ExchangeRate>2.00000000</ExchangeRate>
                                    </CreditAmount>
                                </Line>
                            </Transaction>
                        </Journal>
                    </GeneralLedgerEntries>
                    <SourceDocuments>
                        <SalesInvoices>
                            <NumberOfEntries>2</NumberOfEntries>
                            <TotalDebit>300.00</TotalDebit>
                            <TotalCredit>100.00</TotalCredit>
                            <Invoice>
                                <InvoiceNo>RINV/2025/00001</InvoiceNo>
                                <CustomerInfo>
                                    <CustomerID>___ignore___</CustomerID>
                                    <BillingAddress>
                                        <City>Garnich</City>
                                        <PostalCode>L-8353</PostalCode>
                                        <Country>LU</Country>
                                    </BillingAddress>
                                </CustomerInfo>
                                <SupplierInfo>
                                    <SupplierID>___ignore___</SupplierID>
                                    <BillingAddress>
                                        <City>Garnich</City>
                                        <PostalCode>L-8353</PostalCode>
                                        <Country>LU</Country>
                                    </BillingAddress>
                                </SupplierInfo>
                                <Period>12</Period>
                                <PeriodYear>2025</PeriodYear>
                                <InvoiceDate>2025-12-01</InvoiceDate>
                                <InvoiceType>out_refun</InvoiceType>
                                <GLPostingDate>___ignore___</GLPostingDate>
                                <TransactionID>___ignore___</TransactionID>
                                <Line>
                                    <AccountID>___ignore___</AccountID>
                                    <OrderReferences>
                                        <OriginatingON>RINV/2025/00001</OriginatingON>
                                        <OrderDate>2025-12-01</OrderDate>
                                    </OrderReferences>
                                    <ProductCode>PA</ProductCode>
                                    <ProductDescription>[PA] product_a</ProductDescription>
                                    <Quantity>300.0</Quantity>
                                    <InvoiceUOM>Units</InvoiceUOM>
                                    <UnitPrice>1.00</UnitPrice>
                                    <TaxPointDate>2025-12-01</TaxPointDate>
                                    <Description>[PA] product_a</Description>
                                    <InvoiceLineAmount>
                                        <Amount>300.00</Amount>
                                    </InvoiceLineAmount>
                                    <DebitCreditIndicator>D</DebitCreditIndicator>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>300.00</TaxBase>
                                        <TaxBaseDescription>___ignore___</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>51.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <DocumentTotals>
                                    <TaxInformationTotals>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>300.00</TaxBase>
                                        <TaxBaseDescription>___ignore___</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>51.00</Amount>
                                        </TaxAmount>
                                    </TaxInformationTotals>
                                    <NetTotal>-300.00</NetTotal>
                                    <GrossTotal>-351.00</GrossTotal>
                                </DocumentTotals>
                            </Invoice>
                            <Invoice>
                                <InvoiceNo>INV/2025/00002</InvoiceNo>
                                <CustomerInfo>
                                    <CustomerID>___ignore___</CustomerID>
                                    <BillingAddress>
                                        <City>Garnich</City>
                                        <PostalCode>L-8353</PostalCode>
                                        <Country>LU</Country>
                                    </BillingAddress>
                                </CustomerInfo>
                                <SupplierInfo>
                                    <SupplierID>___ignore___</SupplierID>
                                    <BillingAddress>
                                        <City>Garnich</City>
                                        <PostalCode>L-8353</PostalCode>
                                        <Country>LU</Country>
                                    </BillingAddress>
                                </SupplierInfo>
                                <Period>12</Period>
                                <PeriodYear>2025</PeriodYear>
                                <InvoiceDate>2025-12-01</InvoiceDate>
                                <InvoiceType>out_invoi</InvoiceType>
                                <GLPostingDate>___ignore___</GLPostingDate>
                                <TransactionID>___ignore___</TransactionID>
                                <Line>
                                    <AccountID>___ignore___</AccountID>
                                    <OrderReferences>
                                        <OriginatingON>INV/2025/00002</OriginatingON>
                                        <OrderDate>2025-12-01</OrderDate>
                                    </OrderReferences>
                                    <ProductCode>PA</ProductCode>
                                    <ProductDescription>[PA] product_a</ProductDescription>
                                    <Quantity>100.0</Quantity>
                                    <InvoiceUOM>Units</InvoiceUOM>
                                    <UnitPrice>1.00</UnitPrice>
                                    <TaxPointDate>2025-12-01</TaxPointDate>
                                    <Description>[PA] product_a</Description>
                                    <InvoiceLineAmount>
                                        <Amount>100.00</Amount>
                                    </InvoiceLineAmount>
                                    <DebitCreditIndicator>C</DebitCreditIndicator>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>100.00</TaxBase>
                                        <TaxBaseDescription>___ignore___</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>17.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <DocumentTotals>
                                    <TaxInformationTotals>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>100.00</TaxBase>
                                        <TaxBaseDescription>___ignore___</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>17.00</Amount>
                                        </TaxAmount>
                                    </TaxInformationTotals>
                                    <NetTotal>100.00</NetTotal>
                                    <GrossTotal>117.00</GrossTotal>
                                </DocumentTotals>
                            </Invoice>
                        </SalesInvoices>
                        <PurchaseInvoices>
                            <NumberOfEntries>2</NumberOfEntries>
                            <TotalDebit>300.00</TotalDebit>
                            <TotalCredit>0.00</TotalCredit>
                            <Invoice>
                                <InvoiceNo>BILL/2025/12/0001</InvoiceNo>
                                <CustomerInfo>
                                    <CustomerID>___ignore___</CustomerID>
                                    <BillingAddress>
                                        <City>Garnich</City>
                                        <PostalCode>L-8353</PostalCode>
                                        <Country>LU</Country>
                                    </BillingAddress>
                                </CustomerInfo>
                                <SupplierInfo>
                                    <SupplierID>___ignore___</SupplierID>
                                    <BillingAddress>
                                        <City>Garnich</City>
                                        <PostalCode>L-8353</PostalCode>
                                        <Country>LU</Country>
                                    </BillingAddress>
                                </SupplierInfo>
                                <Period>12</Period>
                                <PeriodYear>2025</PeriodYear>
                                <InvoiceDate>2025-12-01</InvoiceDate>
                                <InvoiceType>in_invoic</InvoiceType>
                                <GLPostingDate>___ignore___</GLPostingDate>
                                <TransactionID>___ignore___</TransactionID>
                                <Line>
                                    <AccountID>___ignore___</AccountID>
                                    <OrderReferences>
                                        <OriginatingON>BILL/2025/12/0001</OriginatingON>
                                        <OrderDate>2025-12-01</OrderDate>
                                    </OrderReferences>
                                    <ProductCode>PA</ProductCode>
                                    <ProductDescription>[PA] product_a</ProductDescription>
                                    <Quantity>200.0</Quantity>
                                    <InvoiceUOM>Units</InvoiceUOM>
                                    <UnitPrice>1.00</UnitPrice>
                                    <TaxPointDate>2025-12-01</TaxPointDate>
                                    <Description>[PA] product_a</Description>
                                    <InvoiceLineAmount>
                                        <Amount>200.00</Amount>
                                    </InvoiceLineAmount>
                                    <DebitCreditIndicator>D</DebitCreditIndicator>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>200.00</TaxBase>
                                        <TaxBaseDescription>___ignore___</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>34.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <DocumentTotals>
                                    <TaxInformationTotals>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>200.00</TaxBase>
                                        <TaxBaseDescription>___ignore___</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>34.00</Amount>
                                        </TaxAmount>
                                    </TaxInformationTotals>
                                    <NetTotal>-200.00</NetTotal>
                                    <GrossTotal>-234.00</GrossTotal>
                                </DocumentTotals>
                            </Invoice>
                            <Invoice>
                                <InvoiceNo>BILL/2025/12/0002</InvoiceNo>
                                <CustomerInfo>
                                    <CustomerID>___ignore___</CustomerID>
                                    <BillingAddress>
                                        <City>Garnich</City>
                                        <PostalCode>L-8353</PostalCode>
                                        <Country>LU</Country>
                                    </BillingAddress>
                                </CustomerInfo>
                                <SupplierInfo>
                                    <SupplierID>___ignore___</SupplierID>
                                    <BillingAddress>
                                        <City>Garnich</City>
                                        <PostalCode>L-8353</PostalCode>
                                        <Country>LU</Country>
                                    </BillingAddress>
                                </SupplierInfo>
                                <Period>12</Period>
                                <PeriodYear>2025</PeriodYear>
                                <InvoiceDate>2025-12-03</InvoiceDate>
                                <InvoiceType>in_invoic</InvoiceType>
                                <GLPostingDate>___ignore___</GLPostingDate>
                                <TransactionID>___ignore___</TransactionID>
                                <Line>
                                    <AccountID>___ignore___</AccountID>
                                    <OrderReferences>
                                        <OriginatingON>BILL/2025/12/0002</OriginatingON>
                                        <OrderDate>2025-12-03</OrderDate>
                                    </OrderReferences>
                                    <ProductCode>PA</ProductCode>
                                    <ProductDescription>[PA] product_a</ProductDescription>
                                    <Quantity>200.0</Quantity>
                                    <InvoiceUOM>Units</InvoiceUOM>
                                    <UnitPrice>0.50</UnitPrice>
                                    <TaxPointDate>2025-12-03</TaxPointDate>
                                    <Description>[PA] product_a</Description>
                                    <InvoiceLineAmount>
                                        <Amount>100.00</Amount>
                                        <CurrencyCode>USD</CurrencyCode>
                                        <CurrencyAmount>200.00</CurrencyAmount>
                                        <ExchangeRate>2.00000000</ExchangeRate>
                                    </InvoiceLineAmount>
                                    <DebitCreditIndicator>D</DebitCreditIndicator>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>100.00</TaxBase>
                                        <TaxBaseDescription>___ignore___</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>17.00</Amount>
                                            <CurrencyCode>USD</CurrencyCode>
                                            <CurrencyAmount>17.00</CurrencyAmount>
                                            <ExchangeRate>2.00000000</ExchangeRate>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <DocumentTotals>
                                    <TaxInformationTotals>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBase>100.00</TaxBase>
                                        <TaxBaseDescription>___ignore___</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>17.00</Amount>
                                            <CurrencyCode>USD</CurrencyCode>
                                            <CurrencyAmount>34.00</CurrencyAmount>
                                            <ExchangeRate>2.00000000</ExchangeRate>
                                        </TaxAmount>
                                    </TaxInformationTotals>
                                    <NetTotal>-100.00</NetTotal>
                                    <GrossTotal>-117.00</GrossTotal>
                                </DocumentTotals>
                            </Invoice>
                        </PurchaseInvoices>
                    </SourceDocuments>
                </AuditFile>
            ''')
        )
