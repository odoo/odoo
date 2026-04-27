# -*- coding: utf-8 -*-
# pylint: disable=C0326
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import os
from freezegun import freeze_time
from unittest import skipIf

from odoo import fields
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestNlICPSBR(AccountSalesReportCommon):
    @classmethod
    @AccountSalesReportCommon.setup_country('nl')
    def setUpClass(cls):
        super().setUpClass()

        company_vals = {
            'vat': 'NL123456782B90',
        }
        omzetbelasting_module = cls.env['ir.module.module']._get('l10n_nl_reports_sbr_ob_nummer')
        if omzetbelasting_module.state == 'installed':
            company_vals['l10n_nl_reports_sbr_ob_nummer'] = '987654321B09'
        cls.env.company.write(company_vals)

        cls.partner_c = cls.env['res.partner'].create({
            'name': 'Partner C',
            'country_id': cls.env.ref('base.de').id,
            'vat': 'DE123456788',
        })

    @freeze_time('2019-02-23 18:45')
    def test_icp_xbrl_export(self):
        # Create a new partner for the representative and link it to the company.
        representative = self.env['res.partner'].create({
            'company_type': 'company',
            'name': 'Fidu NL',
            'street': 'Fidu Street 123',
            'city': 'Amsterdam',
            'zip': '1019',
            'country_id': self.env.ref('base.nl').id,
            'vat': 'NL123456782B90',
            'mobile': '+31470123456',
            'email': 'info@fidu.nl',
        })
        self.env.company.account_representative_id = representative.id
        self.env.user.phone = '+31432112345'
        t_tax = self.env.ref(f'account.{self.env.company.id}_btw_X0_ABC_levering')
        s_tax = self.env.ref(f'account.{self.env.company.id}_btw_X0_diensten')
        product_service = self.env['product.product'].create({
            'name': 'product_service',
            'lst_price': 750.0,
            'taxes_id': [s_tax.id],
            'type': 'service',
        })
        product_triangular = self.env['product.product'].create({
            'name': 'product_triangular',
            'lst_price': 500.0,
            'taxes_id': [t_tax.id],
        })
        self.init_invoice('out_invoice', partner=self.partner_a, invoice_date=fields.Date.from_string('2019-02-15'), post=True, products=[self.product_a, product_service, product_triangular])
        self.init_invoice('out_invoice', partner=self.partner_b, invoice_date=fields.Date.from_string('2019-06-20'), post=True, products=[self.product_a, product_service])
        # Credit note for a fictitious invoice in a previous month, tests that negative values are also included in the export
        self.init_invoice('out_refund', partner=self.partner_c, invoice_date=fields.Date.from_string('2019-06-30'), post=True, products=[product_triangular])
        self.env['account.move.line'].flush_model()

        report = self.env.ref('l10n_nl_intrastat.dutch_icp_report')
        date_from = fields.Date.from_string('2019-01-01')
        date_to = fields.Date.from_string('2019-12-31')
        options = self._generate_options(report, date_from, date_to)
        wizard = self.env['l10n_nl_reports_sbr_icp.icp.wizard']\
            .with_context(default_date_from=date_from, default_date_to=date_to, options=options)\
            .create({ 'tax_consultant_number': '123456' })

        omzetbelasting_module = self.env['ir.module.module']._get('l10n_nl_reports_sbr_ob_nummer')
        if omzetbelasting_module.state == 'installed':
            omzetbelastingnummer = '987654321B09'
        else:
            omzetbelastingnummer = self.env.company.vat[2:] if self.env.company.vat.startswith('NL') else self.env.company.vat

        # This call will add the wanted values in the options
        wizard.action_download_xbrl_file()
        generated_xbrl = self.get_xml_tree_from_string(self.env['l10n_nl.ec.sales.report.handler'].export_icp_report_to_xbrl(options).get('file_content'))
        expected_xbrl = self.get_xml_tree_from_string(f'''
            <xbrli:xbrl xmlns:bd-i="http://www.nltaxonomie.nl/nt20/bd/20251210/dictionary/bd-data" xmlns:xbrldi="http://xbrl.org/2006/xbrldi" xmlns:bd-axes="http://www.nltaxonomie.nl/nt20/bd/20251210/validation/bd-axes" xmlns:link="http://www.xbrl.org/2003/linkbase" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:bd-domains="http://www.nltaxonomie.nl/nt20/bd/20251210/validation/bd-domains" xmlns:iso4217="http://www.xbrl.org/2003/iso4217" xml:lang="nl">
                <link:schemaRef xlink:type="simple" xlink:href="http://www.nltaxonomie.nl/nt20/bd/20251210/entrypoints/bd-rpt-icp-opgaaf-2026.xsd" />
                <xbrli:context id="CD_Opgaaf">
                    <xbrli:entity>
                        <xbrli:identifier scheme="www.belastingdienst.nl/omzetbelastingnummer">{omzetbelastingnummer}</xbrli:identifier>
                    </xbrli:entity>
                    <xbrli:period>
                        <xbrli:startDate>2019-01-01</xbrli:startDate>
                        <xbrli:endDate>2019-12-31</xbrli:endDate>
                    </xbrli:period>
                </xbrli:context>
                <xbrli:context id="Msg_PASN1">
                    <xbrli:entity>
                        <xbrli:identifier scheme="www.belastingdienst.nl/omzetbelastingnummer">{omzetbelastingnummer}</xbrli:identifier>
                    </xbrli:entity>
                    <xbrli:period>
                        <xbrli:startDate>2019-01-01</xbrli:startDate>
                        <xbrli:endDate>2019-12-31</xbrli:endDate>
                    </xbrli:period>
                    <xbrli:scenario>
                        <xbrldi:typedMember dimension="bd-axes:ProfessionalAssociationSerialNumberDimension">
                            <bd-domains:ProfessionalAssociationSerialNumberDomain>1</bd-domains:ProfessionalAssociationSerialNumberDomain>
                        </xbrldi:typedMember>
                    </xbrli:scenario>
                </xbrli:context>
                <xbrli:context id="ICP_FR_23334175221">
                    <xbrli:entity>
                        <xbrli:identifier scheme="www.belastingdienst.nl/omzetbelastingnummer">{omzetbelastingnummer}</xbrli:identifier>
                    </xbrli:entity>
                    <xbrli:period>
                        <xbrli:startDate>2019-01-01</xbrli:startDate>
                        <xbrli:endDate>2019-12-31</xbrli:endDate>
                    </xbrli:period>
                    <xbrli:scenario>
                        <xbrldi:typedMember dimension="bd-axes:VATNumberDimension">
                            <bd-domains:VATNumberDomain>23334175221</bd-domains:VATNumberDomain>
                        </xbrldi:typedMember>
                        <xbrldi:typedMember dimension="bd-axes:CountryCodeEUDimension">
                            <bd-domains:CountryCodeEUDomain>FR</bd-domains:CountryCodeEUDomain>
                        </xbrldi:typedMember>
                    </xbrli:scenario>
                </xbrli:context>
                <xbrli:context id="ICP_BE_0477472701">
                    <xbrli:entity>
                        <xbrli:identifier scheme="www.belastingdienst.nl/omzetbelastingnummer">{omzetbelastingnummer}</xbrli:identifier>
                    </xbrli:entity>
                    <xbrli:period>
                        <xbrli:startDate>2019-01-01</xbrli:startDate>
                        <xbrli:endDate>2019-12-31</xbrli:endDate>
                    </xbrli:period>
                    <xbrli:scenario>
                        <xbrldi:typedMember dimension="bd-axes:VATNumberDimension">
                            <bd-domains:VATNumberDomain>0477472701</bd-domains:VATNumberDomain>
                        </xbrldi:typedMember>
                        <xbrldi:typedMember dimension="bd-axes:CountryCodeEUDimension">
                            <bd-domains:CountryCodeEUDomain>BE</bd-domains:CountryCodeEUDomain>
                        </xbrldi:typedMember>
                    </xbrli:scenario>
                </xbrli:context>
                <xbrli:context id="ICP_DE_123456788">
                    <xbrli:entity>
                        <xbrli:identifier scheme="www.belastingdienst.nl/omzetbelastingnummer">{omzetbelastingnummer}</xbrli:identifier>
                    </xbrli:entity>
                    <xbrli:period>
                        <xbrli:startDate>2019-01-01</xbrli:startDate>
                        <xbrli:endDate>2019-12-31</xbrli:endDate>
                    </xbrli:period>
                    <xbrli:scenario>
                        <xbrldi:typedMember dimension="bd-axes:VATNumberDimension">
                            <bd-domains:VATNumberDomain>123456788</bd-domains:VATNumberDomain>
                        </xbrldi:typedMember>
                        <xbrldi:typedMember dimension="bd-axes:CountryCodeEUDimension">
                            <bd-domains:CountryCodeEUDomain>DE</bd-domains:CountryCodeEUDomain>
                        </xbrldi:typedMember>
                    </xbrli:scenario>
                </xbrli:context>
                <xbrli:unit id="EUR">
                    <xbrli:measure>iso4217:EUR</xbrli:measure>
                </xbrli:unit>
                <bd-i:MessageReferenceSupplierICP contextRef="CD_Opgaaf">___ignore___</bd-i:MessageReferenceSupplierICP>
                <bd-i:SoftwareVendorAccountNumber contextRef="CD_Opgaaf">swo02770</bd-i:SoftwareVendorAccountNumber>
                <bd-i:SoftwarePackageName contextRef="CD_Opgaaf">Odoo</bd-i:SoftwarePackageName>
                <bd-i:SoftwarePackageVersion contextRef="CD_Opgaaf">___ignore___</bd-i:SoftwarePackageVersion>
                <bd-i:DateTimeCreation contextRef="CD_Opgaaf">201902231845</bd-i:DateTimeCreation>
                <bd-i:ProfessionalAssociationForTaxServiceProvidersName contextRef="Msg_PASN1">NBA</bd-i:ProfessionalAssociationForTaxServiceProvidersName>
                <bd-i:TaxConsultantNumber contextRef="CD_Opgaaf">123456</bd-i:TaxConsultantNumber>
                <bd-i:ContactInitials contextRef="CD_Opgaaf">BIAA</bd-i:ContactInitials>
                <bd-i:ContactPrefix contextRef="CD_Opgaaf">I am</bd-i:ContactPrefix>
                <bd-i:ContactSurname contextRef="CD_Opgaaf">accountman!</bd-i:ContactSurname>
                <bd-i:ContactTelephoneNumber contextRef="CD_Opgaaf">+31432112345</bd-i:ContactTelephoneNumber>
                <bd-i:VATIdentificationNumberNLFiscalEntityDivision contextRef="CD_Opgaaf">123456782B90</bd-i:VATIdentificationNumberNLFiscalEntityDivision>
                <bd-i:SuppliesAmount unitRef="EUR" decimals="INF" contextRef="ICP_FR_23334175221">1000</bd-i:SuppliesAmount>
                <bd-i:SuppliesAmount unitRef="EUR" decimals="INF" contextRef="ICP_BE_0477472701">1000</bd-i:SuppliesAmount>
                <bd-i:ServicesAmount unitRef="EUR" decimals="INF" contextRef="ICP_FR_23334175221">750</bd-i:ServicesAmount>
                <bd-i:ServicesAmount unitRef="EUR" decimals="INF" contextRef="ICP_BE_0477472701">750</bd-i:ServicesAmount>
                <bd-i:ABCSuppliesAmount unitRef="EUR" decimals="INF" contextRef="ICP_FR_23334175221">500</bd-i:ABCSuppliesAmount>
                <bd-i:ABCSuppliesAmount unitRef="EUR" decimals="INF" contextRef="ICP_DE_123456788">-500</bd-i:ABCSuppliesAmount>
            </xbrli:xbrl>
        ''')
        self.assertXmlTreeEqual(generated_xbrl, expected_xbrl)


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
@skipIf(not os.getenv("NL_SBR_CERT"), "No SBR certificate")
class TestNlSBRFlow(TestAccountReportsCommon):
    @classmethod
    @TestAccountReportsCommon.setup_country('nl')
    def setUpClass(cls):
        super().setUpClass()

        company_vals = {
            'vat': 'NL123456782B90',
        }
        omzetbelasting_module = cls.env['ir.module.module']._get('l10n_nl_reports_sbr_ob_nummer')
        if omzetbelasting_module.state == 'installed':
            company_vals['l10n_nl_reports_sbr_ob_nummer'] = '987654321B09'
        cls.env.company.write(company_vals)

        cls.NL_SBR_CERT = os.getenv("NL_SBR_CERT")
        cls.NL_SBR_PWD = os.getenv("NL_SBR_PWD")

    def test_sbr_flow(self):
        # Load the certificate and key in the company
        certificate = self.env['certificate.certificate'].create({
            'name': 'SBR NL certificate',
            'content': self.NL_SBR_CERT.encode(),
            'pkcs12_password': self.NL_SBR_PWD,
            'company_id': self.env.company.id,
        })
        self.assertTrue(certificate.private_key_id)
        self.env.company.l10n_nl_reports_sbr_cert_id = certificate

        date_from = fields.Date.from_string('2019-01-01')
        date_to = fields.Date.from_string('2019-12-31')
        report = self.env.ref('l10n_nl_intrastat.dutch_icp_report')
        options = self._generate_options(report, date_from, date_to)

        wizard = self.env['l10n_nl_reports_sbr_icp.icp.wizard']\
            .with_context(default_date_from=date_from, default_date_to=date_to, options=options)\
            .create({'is_test': True})
        res = wizard.send_xbrl()
        self.assertTrue(res)
