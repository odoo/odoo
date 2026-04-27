# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import test_xsd


class TestNlXafExportCommon(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('nl')
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.write({
            'vat': 'NL123456782B90',
        })

        products = [cls.product_a, cls.product_b]

        # Verify if the country code validation when generating a XAF report at the very least allows
        # the Netherlands itself on a partner when no XSD is downloaded
        cls.partner_a.write({'country_id': cls.env.ref('base.nl').id})

        # Create three invoices, one refund and one bill in 2019
        partner_a_invoice1 = cls.init_invoice('out_invoice', products=products)
        partner_a_invoice2 = cls.init_invoice('out_invoice', products=products)
        partner_a_invoice3 = cls.init_invoice('out_invoice', products=products)
        partner_a_refund = cls.init_invoice('out_refund', products=products)

        partner_b_bill = cls.init_invoice('in_invoice', products=products, partner=cls.partner_b)

        # Create one invoice for partner B in 2018
        partner_b_invoice1 = cls.init_invoice('out_invoice', products=products, partner=cls.partner_b, invoice_date=fields.Date.from_string('2018-01-01'))

        # Create one MISC entry in 2018
        bank_account_id = cls.company_data['default_journal_bank'].default_account_id.id
        receivable_account_id = cls.company_data['default_account_receivable'].id
        partner_a_misc = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2018-01-01'),
            'journal_id': cls.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0, 'credit': 0.0, 'account_id': receivable_account_id, 'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0, 'credit': 100.0, 'account_id': bank_account_id, 'partner_id': cls.partner_a.id}),
            ],
        })

        # init_invoice has hardcoded 2019 year's date, we are resetting it to current year's one.
        (partner_a_invoice1 + partner_a_invoice2 + partner_a_invoice3 + partner_b_invoice1 + partner_a_refund + partner_b_bill + partner_a_misc).action_post()


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestNlXafExport(TestNlXafExportCommon):

    @freeze_time('2019-12-31')
    def test_xaf_export(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = self._generate_options(report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))

        expected_xaf = self.get_xml_tree_from_string('''
            <auditfile xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.auditfiles.nl/XAF/3.2">
                <header>
                    <fiscalYear>2019</fiscalYear>
                    <startDate>2019-01-01</startDate>
                    <endDate>2019-12-31</endDate>
                    <curCode>EUR</curCode>
                    <dateCreated>2019-12-31</dateCreated>
                    <softwareDesc>Odoo</softwareDesc>
                    <softwareVersion>___ignore___</softwareVersion>
                </header>
                <company>
                    <companyName>company_1_data</companyName>
                    <taxRegistrationCountry>NL</taxRegistrationCountry>
                    <taxRegIdent>NL123456782B90</taxRegIdent>
                    <streetAddress>
                        <country>NL</country>
                    </streetAddress>
                    <customersSuppliers>
                        <customerSupplier>
                            <custSupID>___ignore___</custSupID>
                            <custSupName>partner_a</custSupName>
                            <custSupTp>S</custSupTp>
                            <streetAddress>
                            </streetAddress>
                            <changeInfo>
                                <userID>___ignore___</userID>
                                <changeDateTime>___ignore___</changeDateTime>
                                <changeDescription>___ignore___</changeDescription>
                            </changeInfo>
                        </customerSupplier><customerSupplier>
                            <custSupID>___ignore___</custSupID>
                            <custSupName>partner_b</custSupName>
                            <custSupTp>B</custSupTp>
                            <streetAddress>
                            </streetAddress>
                            <changeInfo>
                                <userID>___ignore___</userID>
                                <changeDateTime>___ignore___</changeDateTime>
                                <changeDescription>___ignore___</changeDescription>
                            </changeInfo>
                        </customerSupplier>
                    </customersSuppliers>
                    <generalLedger>
                        <ledgerAccount>
                            <accID>103001</accID>
                            <accDesc>Bank</accDesc>
                            <accTp>B</accTp>
                            <changeInfo>
                                <userID>___ignore___</userID>
                                <changeDateTime>___ignore___</changeDateTime>
                                <changeDescription>___ignore___</changeDescription>
                            </changeInfo>
                        </ledgerAccount><ledgerAccount>
                            <accID>110000</accID>
                            <accDesc>Debtors</accDesc>
                            <accTp>B</accTp>
                            <changeInfo>
                                <userID>___ignore___</userID>
                                <changeDateTime>___ignore___</changeDateTime>
                                <changeDescription>___ignore___</changeDescription>
                            </changeInfo>
                        </ledgerAccount><ledgerAccount>
                            <accID>110001</accID>
                            <accDesc>Debtors (copy)</accDesc>
                            <accTp>B</accTp>
                            <changeInfo>
                                <userID>___ignore___</userID>
                                <changeDateTime>___ignore___</changeDateTime>
                                <changeDescription>___ignore___</changeDescription>
                            </changeInfo>
                        </ledgerAccount><ledgerAccount>
                            <accID>130001</accID>
                            <accDesc>Creditors (copy)</accDesc>
                            <accTp>B</accTp>
                            <changeInfo>
                                <userID>___ignore___</userID>
                                <changeDateTime>___ignore___</changeDateTime>
                                <changeDescription>___ignore___</changeDescription>
                            </changeInfo>
                        </ledgerAccount><ledgerAccount>
                            <accID>150000</accID>
                            <accDesc>Deferred VAT high rate</accDesc>
                            <accTp>B</accTp>
                            <changeInfo>
                                <userID>___ignore___</userID>
                                <changeDateTime>___ignore___</changeDateTime>
                                <changeDescription>___ignore___</changeDescription>
                            </changeInfo>
                        </ledgerAccount><ledgerAccount>
                            <accID>152000</accID>
                            <accDesc>Pre-tax high</accDesc>
                            <accTp>B</accTp>
                            <changeInfo>
                                <userID>___ignore___</userID>
                                <changeDateTime>___ignore___</changeDateTime>
                                <changeDescription>___ignore___</changeDescription>
                            </changeInfo>
                        </ledgerAccount><ledgerAccount>
                            <accID>400100.1</accID>
                            <accDesc>Gross wages</accDesc>
                            <accTp>P</accTp>
                            <changeInfo>
                                <userID>___ignore___</userID>
                                <changeDateTime>___ignore___</changeDateTime>
                                <changeDescription>___ignore___</changeDescription>
                            </changeInfo>
                        </ledgerAccount><ledgerAccount>
                            <accID>800100</accID>
                            <accDesc>Turnover NL trade goods 1</accDesc>
                            <accTp>P</accTp>
                            <changeInfo>
                                <userID>___ignore___</userID>
                                <changeDateTime>___ignore___</changeDateTime>
                                <changeDescription>___ignore___</changeDescription>
                            </changeInfo>
                        </ledgerAccount><ledgerAccount>
                            <accID>800100.1</accID>
                            <accDesc>Turnover NL trade goods 1</accDesc>
                            <accTp>P</accTp>
                            <changeInfo>
                                <userID>___ignore___</userID>
                                <changeDateTime>___ignore___</changeDateTime>
                                <changeDescription>___ignore___</changeDescription>
                            </changeInfo>
                        </ledgerAccount>
                    </generalLedger>
                    <vatCodes>
                        <vatCode>
                            <vatID>___ignore___</vatID>
                            <vatDesc>21% (Copy)</vatDesc>
                        </vatCode><vatCode>
                            <vatID>___ignore___</vatID>
                            <vatDesc>21% ST</vatDesc>
                        </vatCode><vatCode>
                            <vatID>___ignore___</vatID>
                            <vatDesc>21% ST (Copy)</vatDesc>
                        </vatCode>
                    </vatCodes>
                    <periods>
                        <period>
                            <periodNumber>01</periodNumber>
                            <periodDesc>January 2019</periodDesc>
                            <startDatePeriod>2019-01-01</startDatePeriod>
                            <endDatePeriod>2019-01-31</endDatePeriod>
                        </period><period>
                            <periodNumber>02</periodNumber>
                            <periodDesc>February 2019</periodDesc>
                            <startDatePeriod>2019-02-01</startDatePeriod>
                            <endDatePeriod>2019-02-28</endDatePeriod>
                        </period><period>
                            <periodNumber>03</periodNumber>
                            <periodDesc>March 2019</periodDesc>
                            <startDatePeriod>2019-03-01</startDatePeriod>
                            <endDatePeriod>2019-03-31</endDatePeriod>
                        </period><period>
                            <periodNumber>04</periodNumber>
                            <periodDesc>April 2019</periodDesc>
                            <startDatePeriod>2019-04-01</startDatePeriod>
                            <endDatePeriod>2019-04-30</endDatePeriod>
                        </period><period>
                            <periodNumber>05</periodNumber>
                            <periodDesc>May 2019</periodDesc>
                            <startDatePeriod>2019-05-01</startDatePeriod>
                            <endDatePeriod>2019-05-31</endDatePeriod>
                        </period><period>
                            <periodNumber>06</periodNumber>
                            <periodDesc>June 2019</periodDesc>
                            <startDatePeriod>2019-06-01</startDatePeriod>
                            <endDatePeriod>2019-06-30</endDatePeriod>
                        </period><period>
                            <periodNumber>07</periodNumber>
                            <periodDesc>July 2019</periodDesc>
                            <startDatePeriod>2019-07-01</startDatePeriod>
                            <endDatePeriod>2019-07-31</endDatePeriod>
                        </period><period>
                            <periodNumber>08</periodNumber>
                            <periodDesc>August 2019</periodDesc>
                            <startDatePeriod>2019-08-01</startDatePeriod>
                            <endDatePeriod>2019-08-31</endDatePeriod>
                        </period><period>
                            <periodNumber>09</periodNumber>
                            <periodDesc>September 2019</periodDesc>
                            <startDatePeriod>2019-09-01</startDatePeriod>
                            <endDatePeriod>2019-09-30</endDatePeriod>
                        </period><period>
                            <periodNumber>10</periodNumber>
                            <periodDesc>October 2019</periodDesc>
                            <startDatePeriod>2019-10-01</startDatePeriod>
                            <endDatePeriod>2019-10-31</endDatePeriod>
                        </period><period>
                            <periodNumber>11</periodNumber>
                            <periodDesc>November 2019</periodDesc>
                            <startDatePeriod>2019-11-01</startDatePeriod>
                            <endDatePeriod>2019-11-30</endDatePeriod>
                        </period><period>
                            <periodNumber>12</periodNumber>
                            <periodDesc>December 2019</periodDesc>
                            <startDatePeriod>2019-12-01</startDatePeriod>
                            <endDatePeriod>2019-12-31</endDatePeriod>
                        </period>
                    </periods>
                    <openingBalance>
                        <opBalDate>2019-01-01</opBalDate>
                        <linesCount>5</linesCount>
                        <totalDebit>1552.0</totalDebit>
                        <totalCredit>352.0</totalCredit>
                        <obLine>
                            <nr>___ignore___</nr>
                            <accID>110000</accID>
                            <amnt>100.0</amnt>
                            <amntTp>D</amntTp>
                        </obLine><obLine>
                            <nr>___ignore___</nr>
                            <accID>150000</accID>
                            <amnt>252.0</amnt>
                            <amntTp>C</amntTp>
                        </obLine><obLine>
                            <nr>___ignore___</nr>
                            <accID>103001</accID>
                            <amnt>100.0</amnt>
                            <amntTp>C</amntTp>
                        </obLine><obLine>
                            <nr>___ignore___</nr>
                            <accID>110001</accID>
                            <amnt>1452.0</amnt>
                            <amntTp>D</amntTp>
                        </obLine>
                    </openingBalance>
                    <transactions>
                        <linesCount>25</linesCount>
                        <totalDebit>7137.6</totalDebit>
                        <totalCredit>7137.6</totalCredit>
                        <journal>
                            <jrnID>INV</jrnID>
                            <desc>Customer Invoices</desc>
                            <jrnTp>S</jrnTp>
                            <transaction>
                                <nr>___ignore___</nr>
                                <desc>INV/2019/00001</desc>
                                <periodNumber>01</periodNumber>
                                <trDt>2019-01-01</trDt>
                                <amnt>1494.0</amnt>
                                <trLine>
                                    <nr>___ignore___</nr>
                                    <accID>800100</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>product_a</desc>
                                    <amnt>1000.0</amnt>
                                    <amntTp>C</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>INV/2019/00001</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>-1000.0</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>800100.1</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>product_b</desc>
                                    <amnt>200.0</amnt>
                                    <amntTp>C</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>INV/2019/00001</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>-200.0</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>150000</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>21% ST</desc>
                                    <amnt>252.0</amnt>
                                    <amntTp>C</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>INV/2019/00001</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>-252.0</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>150000</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>21% ST (Copy)</desc>
                                    <amnt>42.0</amnt>
                                    <amntTp>C</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>INV/2019/00001</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>-42.0</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>110000</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>INV/2019/00001</desc>
                                    <amnt>1494.0</amnt>
                                    <amntTp>D</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>INV/2019/00001</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>1494.0</curAmnt>
                                    </currency>
                                </trLine>
                            </transaction><transaction>
                                <nr>___ignore___</nr>
                                <desc>INV/2019/00002</desc>
                                <periodNumber>01</periodNumber>
                                <trDt>2019-01-01</trDt>
                                <amnt>1494.0</amnt>
                                <trLine>
                                    <nr>___ignore___</nr>
                                    <accID>800100</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>product_a</desc>
                                    <amnt>1000.0</amnt>
                                    <amntTp>C</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>INV/2019/00002</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>-1000.0</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>800100.1</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>product_b</desc>
                                    <amnt>200.0</amnt>
                                    <amntTp>C</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>INV/2019/00002</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>-200.0</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>150000</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>21% ST</desc>
                                    <amnt>252.0</amnt>
                                    <amntTp>C</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>INV/2019/00002</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>-252.0</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>150000</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>21% ST (Copy)</desc>
                                    <amnt>42.0</amnt>
                                    <amntTp>C</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>INV/2019/00002</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>-42.0</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>110000</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>INV/2019/00002</desc>
                                    <amnt>1494.0</amnt>
                                    <amntTp>D</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>INV/2019/00002</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>1494.0</curAmnt>
                                    </currency>
                                </trLine>
                            </transaction><transaction>
                                <nr>___ignore___</nr>
                                <desc>INV/2019/00003</desc>
                                <periodNumber>01</periodNumber>
                                <trDt>2019-01-01</trDt>
                                <amnt>1494.0</amnt>
                                <trLine>
                                    <nr>___ignore___</nr>
                                    <accID>800100</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>product_a</desc>
                                    <amnt>1000.0</amnt>
                                    <amntTp>C</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>INV/2019/00003</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>-1000.0</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>800100.1</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>product_b</desc>
                                    <amnt>200.0</amnt>
                                    <amntTp>C</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>INV/2019/00003</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>-200.0</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>150000</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>21% ST</desc>
                                    <amnt>252.0</amnt>
                                    <amntTp>C</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>INV/2019/00003</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>-252.0</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>150000</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>21% ST (Copy)</desc>
                                    <amnt>42.0</amnt>
                                    <amntTp>C</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>INV/2019/00003</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>-42.0</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>110000</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>INV/2019/00003</desc>
                                    <amnt>1494.0</amnt>
                                    <amntTp>D</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>INV/2019/00003</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>1494.0</curAmnt>
                                    </currency>
                                </trLine>
                            </transaction><transaction>
                                <nr>___ignore___</nr>
                                <desc>RINV/2019/00001</desc>
                                <periodNumber>01</periodNumber>
                                <trDt>2019-01-01</trDt>
                                <amnt>1494.0</amnt>
                                <trLine>
                                    <nr>___ignore___</nr>
                                    <accID>800100</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>product_a</desc>
                                    <amnt>1000.0</amnt>
                                    <amntTp>D</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>RINV/2019/00001</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>1000.0</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>800100.1</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>product_b</desc>
                                    <amnt>200.0</amnt>
                                    <amntTp>D</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>RINV/2019/00001</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>200.0</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>150000</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>21% ST</desc>
                                    <amnt>252.0</amnt>
                                    <amntTp>D</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>RINV/2019/00001</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>252.0</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>150000</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>21% ST (Copy)</desc>
                                    <amnt>42.0</amnt>
                                    <amntTp>D</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>RINV/2019/00001</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>42.0</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>110000</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc></desc>
                                    <amnt>1494.0</amnt>
                                    <amntTp>C</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>RINV/2019/00001</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>-1494.0</curAmnt>
                                    </currency>
                                </trLine>
                            </transaction>
                        </journal><journal>
                            <jrnID>BILL</jrnID>
                            <desc>Vendor Bills</desc>
                            <jrnTp>P</jrnTp>
                            <transaction>
                                <nr>___ignore___</nr>
                                <desc>BILL/2019/01/0001</desc>
                                <periodNumber>01</periodNumber>
                                <trDt>2019-01-01</trDt>
                                <amnt>1161.6</amnt>
                                <trLine>
                                    <nr>___ignore___</nr>
                                    <accID>400100.1</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>product_a</desc>
                                    <amnt>800.0</amnt>
                                    <amntTp>D</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>BILL/2019/01/0001</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>800.0</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>400100.1</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>product_b</desc>
                                    <amnt>160.0</amnt>
                                    <amntTp>D</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>BILL/2019/01/0001</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>160.0</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>152000</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>21% (Copy)</desc>
                                    <amnt>201.6</amnt>
                                    <amntTp>D</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>BILL/2019/01/0001</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>201.6</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>130001</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>installment #1</desc>
                                    <amnt>348.48</amnt>
                                    <amntTp>C</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>BILL/2019/01/0001</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>-348.48</curAmnt>
                                    </currency>
                                </trLine><trLine>
                                    <nr>___ignore___</nr>
                                    <accID>130001</accID>
                                    <docRef>/</docRef>
                                    <effDate>2019-01-01</effDate>
                                    <desc>installment #2</desc>
                                    <amnt>813.12</amnt>
                                    <amntTp>C</amntTp>
                                    <custSupID>___ignore___</custSupID>
                                    <invRef>BILL/2019/01/0001</invRef>
                                    <currency>
                                        <curCode>EUR</curCode>
                                        <curAmnt>-813.12</curAmnt>
                                    </currency>
                                </trLine>
                            </transaction>
                        </journal>
                    </transactions>
                </company>
            </auditfile>
        ''')

        try:
            self.env.registry.enter_test_mode(self.cr)
            # Set the batch size to 10 to make sure the generator will iterate more than once.
            self.env['ir.config_parameter'].set_param('l10n_nl_reports.general_ledger_batch_size', 10)
            xaf_stream = self.env[report.custom_handler_model_name].l10n_nl_get_xaf(options).get('file_content')
            generated_xaf = self.get_xml_tree_from_string(b''.join(xaf_stream))
            self.assertXmlTreeEqual(generated_xaf, expected_xaf)
        finally:
            self.env.registry.leave_test_mode()


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestNlXafExportXmlValidity(TestNlXafExportCommon):
    @test_xsd(url='https://www.softwarepakketten.nl/upload/auditfiles/xaf/20140402_AuditfileFinancieelVersie_3_2.zip')
    def test_xml_validity(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = self._generate_options(report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))
        try:
            self.env.registry.enter_test_mode(self.cr)
            xaf_stream = self.env[report.custom_handler_model_name].l10n_nl_get_xaf(options).get('file_content')
            generated_xaf = self.get_xml_tree_from_string(b''.join(xaf_stream))
        finally:
            self.env.registry.leave_test_mode()
        return generated_xaf
