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
    def setUpClass(cls, chart_template_ref='nl'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        company_vals = {
            'vat': 'NL123456782B90',
            'country_id': cls.env.ref('base.nl').id,
        }
        omzetbelasting_module = cls.env['ir.module.module']._get('l10n_nl_reports_sbr_ob_nummer')
        if omzetbelasting_module.state == 'installed':
            company_vals['l10n_nl_reports_sbr_ob_nummer'] = '987654321B09'
        cls.env.company.write(company_vals)

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
            'detailed_type': 'service',
        })
        product_triangular = self.env['product.product'].create({
            'name': 'product_triangular',
            'lst_price': 500.0,
            'taxes_id': [t_tax.id],
        })
        self.init_invoice('out_invoice', partner=self.partner_a, invoice_date=fields.Date.from_string('2019-02-15'), post=True, products=[self.product_a, product_service, product_triangular])
        self.init_invoice('out_invoice', partner=self.partner_b, invoice_date=fields.Date.from_string('2019-06-20'), post=True, products=[self.product_a, product_service])
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
            <xbrli:xbrl xmlns:link="http://www.xbrl.org/2003/linkbase"
                xmlns:xlink="http://www.w3.org/1999/xlink"
                xmlns:bd-t="http://www.nltaxonomie.nl/nt16/bd/20211208/dictionary/bd-tuples"
                xmlns:bd-i="http://www.nltaxonomie.nl/nt16/bd/20211208/dictionary/bd-data"
                xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:iso4217="http://www.xbrl.org/2003/iso4217"
                xml:lang="nl">
                <link:schemaRef xlink:type="simple"
                    xlink:href="http://www.nltaxonomie.nl/nt16/bd/20211208/entrypoints/bd-rpt-icp-opgaaf-2022.xsd" />
                <xbrli:context id="CD_Opgaaf">
                    <xbrli:entity>
                        <xbrli:identifier scheme="www.belastingdienst.nl/omzetbelastingnummer">{omzetbelastingnummer}</xbrli:identifier>
                    </xbrli:entity>
                    <xbrli:period>
                        <xbrli:startDate>2019-01-01</xbrli:startDate>
                        <xbrli:endDate>2019-12-31</xbrli:endDate>
                    </xbrli:period>
                </xbrli:context>
                <xbrli:unit id="EUR">
                    <xbrli:measure>iso4217:EUR</xbrli:measure>
                </xbrli:unit>
                <bd-i:MessageReferenceSupplierICP contextRef="CD_Opgaaf">___ignore___</bd-i:MessageReferenceSupplierICP>
                <bd-i:SoftwareVendorAccountNumber contextRef="CD_Opgaaf">swo02770</bd-i:SoftwareVendorAccountNumber>
                <bd-i:SoftwarePackageName contextRef="CD_Opgaaf">Odoo</bd-i:SoftwarePackageName>
                <bd-i:SoftwarePackageVersion contextRef="CD_Opgaaf">___ignore___</bd-i:SoftwarePackageVersion>
                <bd-i:DateTimeCreation contextRef="CD_Opgaaf">201902231845</bd-i:DateTimeCreation>
                <bd-t:ProfessionalAssociationForTaxServiceProvidersSpecification>
                    <bd-i:ProfessionalAssociationForTaxServiceProvidersName contextRef="CD_Opgaaf">Fidu NL</bd-i:ProfessionalAssociationForTaxServiceProvidersName>
                </bd-t:ProfessionalAssociationForTaxServiceProvidersSpecification>
                <bd-i:TaxConsultantNumber contextRef="CD_Opgaaf">123456</bd-i:TaxConsultantNumber>
                <bd-i:ContactInitials contextRef="CD_Opgaaf">BIAA</bd-i:ContactInitials>
                <bd-i:ContactPrefix contextRef="CD_Opgaaf">I am</bd-i:ContactPrefix>
                <bd-i:ContactSurname contextRef="CD_Opgaaf">accountman!</bd-i:ContactSurname>
                <bd-i:ContactTelephoneNumber contextRef="CD_Opgaaf">+31432112345</bd-i:ContactTelephoneNumber>
                <bd-i:VATIdentificationNumberNLFiscalEntityDivision contextRef="CD_Opgaaf">123456782B90</bd-i:VATIdentificationNumberNLFiscalEntityDivision>
                <bd-t:IntraCommunitySupplies>
                    <bd-i:CountryCodeISO-EC contextRef="CD_Opgaaf">FR</bd-i:CountryCodeISO-EC>
                    <bd-i:SuppliesAmount contextRef="CD_Opgaaf" unitRef="EUR" decimals="INF">1000</bd-i:SuppliesAmount>
                    <bd-i:VATIdentificationNumberNational contextRef="CD_Opgaaf">23334175221</bd-i:VATIdentificationNumberNational>
                </bd-t:IntraCommunitySupplies>
                <bd-t:IntraCommunitySupplies>
                    <bd-i:CountryCodeISO-EC contextRef="CD_Opgaaf">BE</bd-i:CountryCodeISO-EC>
                    <bd-i:SuppliesAmount contextRef="CD_Opgaaf" unitRef="EUR" decimals="INF">1000</bd-i:SuppliesAmount>
                    <bd-i:VATIdentificationNumberNational contextRef="CD_Opgaaf">0477472701</bd-i:VATIdentificationNumberNational>
                </bd-t:IntraCommunitySupplies>
                <bd-t:IntraCommunityServices>
                    <bd-i:CountryCodeISO-EC contextRef="CD_Opgaaf">FR</bd-i:CountryCodeISO-EC>
                    <bd-i:ServicesAmount contextRef="CD_Opgaaf" unitRef="EUR" decimals="INF">750</bd-i:ServicesAmount>
                    <bd-i:VATIdentificationNumberNational contextRef="CD_Opgaaf">23334175221</bd-i:VATIdentificationNumberNational>
                </bd-t:IntraCommunityServices>
                <bd-t:IntraCommunityServices>
                    <bd-i:CountryCodeISO-EC contextRef="CD_Opgaaf">BE</bd-i:CountryCodeISO-EC>
                    <bd-i:ServicesAmount contextRef="CD_Opgaaf" unitRef="EUR" decimals="INF">750</bd-i:ServicesAmount>
                    <bd-i:VATIdentificationNumberNational contextRef="CD_Opgaaf">0477472701</bd-i:VATIdentificationNumberNational>
                </bd-t:IntraCommunityServices>
                <bd-t:IntraCommunityABCSupplies>
                    <bd-i:CountryCodeISO-EC contextRef="CD_Opgaaf">FR</bd-i:CountryCodeISO-EC>
                    <bd-i:SuppliesAmount contextRef="CD_Opgaaf" unitRef="EUR" decimals="INF">500</bd-i:SuppliesAmount>
                    <bd-i:VATIdentificationNumberNational contextRef="CD_Opgaaf">23334175221</bd-i:VATIdentificationNumberNational>
                </bd-t:IntraCommunityABCSupplies>
            </xbrli:xbrl>
        ''')
        self.assertXmlTreeEqual(generated_xbrl, expected_xbrl)


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
@skipIf(not os.getenv("NL_SBR_CERT"), "No SBR certificate")
class TestNlSBRFlow(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref='nl'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        company_vals = {
            'vat': 'NL123456782B90',
            'country_id': cls.env.ref('base.nl').id,
        }
        omzetbelasting_module = cls.env['ir.module.module']._get('l10n_nl_reports_sbr_ob_nummer')
        if omzetbelasting_module.state == 'installed':
            company_vals['l10n_nl_reports_sbr_ob_nummer'] = '987654321B09'
        cls.env.company.write(company_vals)

        cls.NL_SBR_CERT = os.getenv("NL_SBR_CERT")
        cls.NL_SBR_PWD = os.getenv("NL_SBR_PWD")

    def test_sbr_flow(self):
        # Load the certificate and key in the company
        config = self.env["res.config.settings"].create({
            "l10n_nl_reports_sbr_cert": self.NL_SBR_CERT,
            "l10n_nl_reports_sbr_password": self.NL_SBR_PWD
        })
        config.execute()
        self.assertTrue(config.l10n_nl_reports_sbr_cert)
        self.assertTrue(config.l10n_nl_reports_sbr_key)

        date_from = fields.Date.from_string('2019-01-01')
        date_to = fields.Date.from_string('2019-12-31')
        report = self.env.ref('l10n_nl_intrastat.dutch_icp_report')
        options = self._generate_options(report, date_from, date_to)

        wizard = self.env['l10n_nl_reports_sbr_icp.icp.wizard']\
            .with_context(default_date_from=date_from, default_date_to=date_to, options=options)\
            .create({
                'password': self.NL_SBR_PWD,
                'is_test': True,
            })
        res = wizard.send_xbrl()
        self.assertTrue(res)
