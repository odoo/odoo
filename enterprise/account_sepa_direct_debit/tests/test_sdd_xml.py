from lxml import etree

from odoo import fields
from odoo.addons.account_sepa_direct_debit.tests.common import SDDTestCommon
from odoo.tests import tagged, test_xsd


@tagged('external_l10n', 'post_install', '-at_install', '-standard')
class SDDTestXML(SDDTestCommon):
    @test_xsd(path='account_sepa_direct_debit/schemas/pain.008.001.02.xsd')
    def test_xml_pain_008_001_02_generation(self):
        self.sdd_company_bank_journal.debit_sepa_pain_version = 'pain.008.001.02'

        xml_files = []
        for invoice in (self.invoice_agrolait, self.invoice_china_export, self.invoice_no_bic):
            payment = invoice.line_ids.mapped('matched_credit_ids.credit_move_id.payment_id')
            xml_files.append(etree.fromstring(payment.generate_xml(self.sdd_company, fields.Date.today(), True)))
        return xml_files

    @test_xsd(path='account_sepa_direct_debit/schemas/EPC131-08_2019_V1.0_pain.008.001.02.xsd')
    def test_xml_pain_008_001_02_b2b_generation(self):
        self.sdd_company_bank_journal.debit_sepa_pain_version = 'pain.008.001.02'
        self.mandate_agrolait.sdd_scheme = 'B2B'
        self.mandate_china_export.sdd_scheme = 'B2B'
        self.mandate_no_bic.sdd_scheme = 'B2B'

        xml_files = []
        for invoice in (self.invoice_agrolait, self.invoice_china_export, self.invoice_no_bic):
            payment = invoice.line_ids.mapped('matched_credit_ids.credit_move_id.payment_id')
            xml_files.append(etree.fromstring(payment.generate_xml(self.sdd_company, fields.Date.today(), True)))
        return xml_files

    @test_xsd(path='account_sepa_direct_debit/schemas/pain.008.001.08.xsd')
    def test_xml_pain_008_001_08_generation(self):
        self.sdd_company_bank_journal.debit_sepa_pain_version = 'pain.008.001.08'

        xml_files = []
        for invoice in (self.invoice_agrolait, self.invoice_china_export, self.invoice_no_bic):
            payment = invoice.line_ids.mapped('matched_credit_ids.credit_move_id.payment_id')
            xml_files.append(etree.fromstring(payment.generate_xml(self.sdd_company, fields.Date.today(), True)))

        return xml_files
