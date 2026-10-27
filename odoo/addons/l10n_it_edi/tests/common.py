# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import tools
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdi(AccountTestInvoicingCommon):

    class RepartitionLine:
        def __init__(self, factor_percent, repartition_type, tag_ids):
            self.factor_percent = factor_percent
            self.repartition_type = repartition_type
            self.tag_ids = tag_ids

    @classmethod
    def get_tag_ids(cls, tag_codes):
        """ Helper function to define tag ids for taxes """
        return cls.env['account.account.tag'].search([
            ('applicability', '=', 'taxes'),
            ('country_id.code', '=', 'IT'),
            ('name', 'in', tag_codes)]).ids

    @classmethod
    def repartition_lines(cls, *lines):
        """ Helper function to define repartition lines in taxes """
        return ([(5, 0, 0)] + [(0, 0, {
            **line.__dict__,
            'tag_ids': cls.get_tag_ids(line.tag_ids)
        }) for line in lines])

    @classmethod
    def setUpClass(cls, chart_template_ref='it'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Company data ------
        cls.company = cls.company_data_2['company']
        cls.company.write({
            'vat': 'IT01234560157',
            'phone': '0266766700',
            'mobile': '+393288088988',
            'email': 'test@test.it',
            'street': "1234 Test Street",
            'zip': "12345",
            'city': "Prova",
            'country_id': cls.env.ref('base.it').id,
            'l10n_it_codice_fiscale': '01234560157',
            'l10n_it_tax_system': "RF01",
        })
        cls.company.partner_id.write({
            'l10n_it_pa_index': "0803HR0"
        })

        cls.test_bank = cls.env['res.partner.bank'].create({
            'partner_id': cls.company.partner_id.id,
            'acc_number': 'IT1212341234123412341234123',
            'bank_name': 'BIG BANK',
            'bank_bic': 'BIGGBANQ',
        })

        # Partners
        cls.italian_partner_a = cls.env['res.partner'].create({
            'name': 'Alessi',
            'vat': 'IT00465840031',
            'l10n_it_codice_fiscale': '93026890017',
            'country_id': cls.env.ref('base.it').id,
            'street': 'Via Privata Alessi 6',
            'zip': '28887',
            'city': 'Milan',
            'company_id': False,
            'is_company': True,
        })

        cls.italian_partner_b = cls.env['res.partner'].create({
            'name': 'pa partner',
            'vat': 'IT06655971007',
            'l10n_it_codice_fiscale': '06655971007',
            'l10n_it_pa_index': '123456',
            'country_id': cls.env.ref('base.it').id,
            'street': 'Via Test PA',
            'zip': '32121',
            'city': 'PA Town',
            'is_company': True
        })

        cls.italian_partner_no_address_codice = cls.env['res.partner'].create({
            'name': 'Alessi',
            'l10n_it_codice_fiscale': '00465840031',
            'is_company': True,
        })

        cls.italian_partner_no_address_VAT = cls.env['res.partner'].create({
            'name': 'Alessi',
            'vat': 'IT00465840031',
            'is_company': True,
        })

        cls.american_partner = cls.env['res.partner'].create({
            'name': 'Alessi',
            'vat': '00465840031',
            'country_id': cls.env.ref('base.us').id,
            'is_company': True,
        })

        # We create this because we are unable to post without a proxy user existing
        cls.proxy_user = cls.env['account_edi_proxy_client.user'].create({
            'proxy_type': 'l10n_it_edi',
            'id_client': 'l10n_it_edi_test',
            'company_id': cls.company.id,
            'edi_identification': 'l10n_it_edi_test',
            'private_key': 'l10n_it_edi_test',
        })

        cls.default_tax = cls.env['account.tax'].with_company(cls.company).create({
            'name': "22% default",
            'amount': 22.0,
            'amount_type': 'percent',
        })

        cls.module = 'l10n_it_edi'

    def _assert_export_invoice(self, invoice, filename):
        path = f'{self.module}/tests/export_xmls/{filename}'
        with tools.file_open(path, mode='rb') as fd:
            expected_tree = etree.fromstring(fd.read())
        xml = invoice._l10n_it_edi_render_xml()
        invoice_etree = etree.fromstring(xml)
        try:
            self.assertXmlTreeEqual(invoice_etree, expected_tree)
        except AssertionError as ae:
            ae.args = (ae.args[0] + f"\nFile used for comparison: {filename}", )
            raise

    def _assert_import_invoice(self, filename, expected_values_list, xml_to_apply=None):
        """ Tests an invoice imported from an XML vendor bill file on the filesystem
            against expected values. XPATHs can be applied with the `xml_to_apply`
            argument to the XML content before it's imported.
        """
        path = f'{self.module}/tests/import_xmls/{filename}'
        with tools.file_open(path, mode='rb') as fd:
            import_content = fd.read()

        if xml_to_apply:
            tree = self.with_applied_xpath(
                etree.fromstring(import_content),
                xml_to_apply
            )
            import_content = etree.tostring(tree)

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'raw': import_content,
        })
        purchase_journal = self.company_data_2['default_journal_purchase'].with_context(default_move_type='in_invoice')
        invoices = purchase_journal._create_document_from_attachment(attachment.ids)

        expected_invoice_values_list = []
        expected_invoice_line_ids_values_list = []
        for expected_values in expected_values_list:
            invoice_values = dict(expected_values)
            if 'invoice_line_ids' in invoice_values:
                expected_invoice_line_ids_values_list += invoice_values.pop('invoice_line_ids')
            expected_invoice_values_list.append(invoice_values)
        try:
            self.assertRecordValues(invoices, expected_invoice_values_list)
            if expected_invoice_line_ids_values_list:
                self.assertRecordValues(invoices.invoice_line_ids, expected_invoice_line_ids_values_list)
        except AssertionError as ae:
            ae.args = (ae.args[0] + f"\nFile used for comparison: {filename}", )
            raise

        return invoices
