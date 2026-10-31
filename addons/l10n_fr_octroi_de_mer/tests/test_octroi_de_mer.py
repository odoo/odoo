from lxml import etree

from odoo import Command
from odoo.tests.common import tagged
from odoo.tools.misc import file_path

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestOctroiDeMer(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('fr')
    def setUpClass(cls):
        super().setUpClass()
        cls.om_tax_group = cls.env['account.tax.group'].search([('l10n_fr_om_rate', '=', 'general')])
        cls.omr_tax_group = cls.env['account.tax.group'].search([('l10n_fr_om_rate', '=', 'regional')])
        cls.rate_1, cls.rate_2 = cls.env['l10n_fr.octroi.de.mer.code'].create([{
            'code': '1234',
            'description': 'Rate 1',
            'om_rate_id': cls.env['account.chart.template'].ref('oms_105_percent').id,
            'omr_rate_id': cls.env['account.chart.template'].ref('omrs_2_percent').id,
        }, {
            'code': '5678',
            'description': 'Rate 2',
            'om_rate_id': cls.env['account.chart.template'].ref('oms_0_percent').id,
            'omr_rate_id': cls.env['account.chart.template'].ref('omrs_0_percent').id,
        }])
        cls.product_a.l10n_fr_border_reference = cls.rate_1
        cls.product_b.l10n_fr_border_reference = cls.rate_2
        cls.company_data['company'].write({
            'street': 'Rue Abbé Huet',
            'city': 'Rennes',
            'zip': '35043',
            'vat': 'FR74968515759',
            'phone': '+33612345678',
            'pdp_identifier': '968515759_96851575905899',
        })
        cls.french_partner = cls.env['res.partner'].create({
            'name': 'French Customer',
            'street': 'Rue Fabricy, 16',
            'zip': '59000',
            'city': 'Lille',
            'country_id': cls.env.ref('base.fr').id,
            'phone': '+33 1 23 45 67 89',
            'vat': 'FR23334175221',
            'siret': '33417522105821',
            'invoice_edi_format': 'ubl_21_fr',
            'peppol_eas': '0225',
            'peppol_endpoint': '334175221_33417522105821',
        })

    def test_octroi_de_mer_tax_computation(self):
        invoice = self._create_invoice(
            partner_id=self.french_partner.id,
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100,
                }),
            ],
        )
        self.assertTrue(self.product_a.l10n_fr_rate_id in invoice.invoice_line_ids.tax_ids)
        self.assertTrue(self.product_a.l10n_fr_regional_rate_id in invoice.invoice_line_ids.tax_ids)
        # This product doesn't have any rate, this should remove the 2 taxes
        invoice.invoice_line_ids.product_id = self.product
        self.assertFalse(self.product_a.l10n_fr_rate_id in invoice.invoice_line_ids.tax_ids)
        self.assertFalse(self.product_a.l10n_fr_regional_rate_id in invoice.invoice_line_ids.tax_ids)
        # This should now have the 2 taxes of product_b
        invoice.invoice_line_ids.product_id = self.product_b
        self.assertTrue(self.product_b.l10n_fr_rate_id in invoice.invoice_line_ids.tax_ids)
        self.assertTrue(self.product_b.l10n_fr_regional_rate_id in invoice.invoice_line_ids.tax_ids)

    def test_octroi_de_mer_generate_xml(self):
        invoice = self._create_invoice(
            partner_id=self.french_partner.id,
            post=True,
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100,
                }),
            ],
        )
        xml_bytes = self.env['account.edi.xml.ubl_21_fr']._export_invoice(invoice)[0]
        xml_file_path = file_path('l10n_fr_octroi_de_mer/tests/test_files/test_octroi_de_mer_ubl.xml')
        expected_tree = etree.parse(xml_file_path)
        self.assertXmlTreeEqual(etree.fromstring(xml_bytes), expected_tree.getroot())
