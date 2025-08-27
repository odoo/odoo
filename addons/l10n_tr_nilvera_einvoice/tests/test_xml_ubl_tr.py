from freezegun import freeze_time

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import file_open


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLTR(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('tr')
    @freeze_time('2025-03-05')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].partner_id.write({
            'vat': '3297552117',
            'street': '3281. Cadde',
            'zip': '06810',
            'city': 'İç Anadolu Bölgesi',
            'state_id': cls.env.ref('base.state_tr_81').id,
            'country_id': cls.env.ref('base.tr').id,
            'email': 'info@company.trexample.com',
            'phone': '+90 501 234 56 78',
            'ref': 'Ulus',
            'bank_ids': [Command.create({'acc_number': 'TR0123456789'})],
        })

        cls.einvoice_partner = cls.env['res.partner'].create({
            'name': 'einvoice_partner',
            'vat': '1729171602',
            'street': 'Gökhane Sokak No:1',
            'zip': '06934',
            'city': 'Sincan/Ankara',
            'state_id': cls.env.ref('base.state_tr_06').id,
            'country_id': cls.env.ref('base.tr').id,
            'email': 'info@tr_partner.com',
            'phone': '+90 509 876 54 32',
            'bank_ids': [Command.create({'acc_number': 'TR9876543210'})],
            'invoice_edi_format': 'ubl_tr',
            'ref': 'Ulus',
            'l10n_tr_nilvera_customer_status': 'einvoice',
        })

        cls.earchive_partner = cls.env['res.partner'].create({
            'name': 'earchive_partner',
            'vat': '17291716060',
            'street': 'Gökhane Sokak No:1',
            'zip': '06934',
            'city': 'Sincan/Ankara',
            'state_id': cls.env.ref('base.state_tr_06').id,
            'country_id': cls.env.ref('base.tr').id,
            'email': 'info@tr_partner.com',
            'phone': '+90 509 876 54 32',
            'bank_ids': [Command.create({'acc_number': 'TR9876543210'})],
            'invoice_edi_format': 'ubl_tr',
            'l10n_tr_nilvera_customer_status': 'earchive',
        })

        cls.tax_20 = cls.env['account.chart.template'].ref('tr_s_wh_20_2_10')

        # The rate of 1 USD = 40 TRY is meant to simplify tests
        usd = cls.env.ref('base.USD')
        cls.env['res.currency.rate'].search([
            ('company_id', '=', cls.company_data['company'].id),
            ('currency_id', '=', usd.id),
        ]).unlink()
        cls.env['res.currency.rate'].create({
            'name': '2019-01-01',
            'rate': 0.025,
            'currency_id': usd.id,
            'company_id': cls.company_data['company'].id,
        })

    def _generate_invoice_xml(self, partner_id, **kwargs):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company_data['company'].id,
            'partner_id': partner_id.id,
            'name': 'EIN/998833/0',
            'invoice_date': '2025-03-03',
            'narration': '3 products',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 50.00,
                    'quantity': 3,
                    'discount': 12,
                    'tax_ids': [Command.set(self.tax_20.ids)],
                }),
            ],
            **kwargs,
        })
        invoice.action_post()
        generated_xml = self.env['account.edi.xml.ubl.tr']._export_invoice(invoice)[0]
        return generated_xml

    def test_xml_invoice_einvoice(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(self.einvoice_partner)

        with file_open('l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_einvoice.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_xml),
            self.get_xml_tree_from_string(expected_xml),
        )

    def test_xml_invoice_einvoice_multicurrency(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(partner_id=self.einvoice_partner, currency_id=self.env.ref('base.USD').id)

        with file_open('l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_einvoice_multicurrency.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_xml),
            self.get_xml_tree_from_string(expected_xml),
        )

    def test_xml_invoice_earchive(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(self.earchive_partner)

        with file_open('l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_earchive.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_xml),
            self.get_xml_tree_from_string(expected_xml),
        )

    def test_xml_invoice_earchive_multicurrency(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(self.earchive_partner, currency_id=self.env.ref('base.USD').id)

        with file_open('l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_earchive_multicurrency.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_xml),
            self.get_xml_tree_from_string(expected_xml),
        )
