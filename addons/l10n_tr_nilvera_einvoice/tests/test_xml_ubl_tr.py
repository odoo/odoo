from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tools import file_open
from odoo.addons.l10n_tr_nilvera_einvoice.tests.test_xml_ubl_tr_common import TestUBLTRCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLTR(TestUBLTRCommon):

    def setUp(self):
        super().setUp()
        if self.env['ir.module.module'].search([('name', '=', 'l10n_tr_nilvera_einvoice_extended')]).state == 'installed':
            self.skipTest("This test won't work if l10n_tr_nilvera_einvoice_extended is installed since it adds new nodes to the XML reports.")

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
