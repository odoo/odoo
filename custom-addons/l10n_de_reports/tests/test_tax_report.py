# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon
from odoo.tests import tagged
from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class GermanTaxReportTest(AccountSalesReportCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='de_skr03'):
        super().setUpClass(chart_template_ref=chart_template_ref)

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        res = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        res['company'].write({
            'country_id': cls.env.ref('base.de').id,
            'vat': 'DE123456788',
            'state_id': cls.env.ref('base.state_de_th').id,
            'l10n_de_stnr': '151/815/08156',
        })
        res['company'].partner_id.write({
            'email': 'jsmith@mail.com',
            'phone': '+32475123456',
        })
        return res

    @freeze_time('2019-12-31')
    def test_generate_xml(self):
        first_tax = self.env['account.tax'].search([('name', '=', '19%'), ('company_id', '=', self.company_data['company'].id)], limit=1)
        second_tax = self.env['account.tax'].search([('name', '=', '19% EU'), ('company_id', '=', self.company_data['company'].id)], limit=1)

        # Create and post a move with two move lines to get some data in the report
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self.company_data['default_journal_purchase'].id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-11-12',
            'date': '2019-11-12',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'quantity': 1.0,
                'name': 'product test 1',
                'price_unit': 150,
                'tax_ids': first_tax.ids,
            }), (0, 0, {
                'product_id': self.product_b.id,
                'quantity': 1.0,
                'name': 'product test 2',
                'price_unit': 75,
                'tax_ids': second_tax.ids,
            })]
        })
        move.action_post()

        report = self.env.ref('l10n_de.tax_report')
        options = report.get_options()

        expected_xml = """
        <Anmeldungssteuern art="UStVA" version="2019">
            <Erstellungsdatum>20191231</Erstellungsdatum>
            <DatenLieferant>
                <Name>company_1_data</Name>
                <Strasse />
                <PLZ />
                <Ort />
                <Telefon>+32475123456</Telefon>
                <Email>jsmith@mail.com</Email>
            </DatenLieferant>
            <Steuerfall>
                <Unternehmer>
                    <Bezeichnung>company_1_data</Bezeichnung>
                    <Str />
                    <Ort />
                    <PLZ />
                    <Telefon>+32475123456</Telefon>
                    <Email>jsmith@mail.com</Email>
                </Unternehmer>
                <Umsatzsteuervoranmeldung>
                    <Jahr>2019</Jahr>
                    <Zeitraum>11</Zeitraum>
                    <Steuernummer>4151081508156</Steuernummer>
                    <Kz81>150</Kz81>
                    <Kz89>75</Kz89>
                    <Kz61>14,25</Kz61>
                    <Kz83>0,00</Kz83>
                </Umsatzsteuervoranmeldung>
            </Steuerfall>
        </Anmeldungssteuern>
        """
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self.env[report.custom_handler_model_name].export_tax_report_to_xml(options)['file_content']),
            self.get_xml_tree_from_string(expected_xml)
        )
