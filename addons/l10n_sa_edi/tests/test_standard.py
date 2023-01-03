# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from .common import TestSaEdiCommon
import logging
from freezegun import freeze_time

_logger = logging.getLogger(__name__)

@tagged('post_install_l10n', '-at_install', 'post_install')
class TestEdiZatca(TestSaEdiCommon):

    # def testGetSandboxComplianceCSID(self):
    #     self.customer_invoice_journal.l10n_sa_regen_csr()
    #     self.customer_invoice_journal.l10n_sa_api_get_compliance_CSID(otp='123345')
    #     self.customer_invoice_journal.l10n_sa_run_compliance_checks()

    def testInvoiceStandard(self):

        with freeze_time(self.frozen_date):
            move = self._create_invoice()
            move.action_post()
            move._l10n_sa_generate_unsigned_xml()

            generated_files = move.l10n_sa_unsigned_xml_data
            self.assertTrue(generated_files)

            current_tree = self.get_xml_tree_from_string(generated_files)
            expected_tree = self.get_xml_tree_from_string(self.expected_invoice)
            for child in current_tree.getchildren():
                if 'UBLExtensions' in child.tag:
                    current_tree.remove(child)
            with open("/home/odoo/Desktop/current.xml", "w") as f:
                f.write(generated_files)
            self.assertXmlTreeEqual(current_tree, expected_tree)

    def testCreditNote(self):

        with freeze_time(self.frozen_date):
            move = self._create_credit()
            move.action_post()
            move._l10n_sa_generate_unsigned_xml()

            generated_files = move.l10n_sa_unsigned_xml_data
            self.assertTrue(generated_files)

            current_tree = self.get_xml_tree_from_string(generated_files)
            expected_tree = self.get_xml_tree_from_string(self.expected_invoice)
            for child in current_tree.getchildren():
                if 'UBLExtensions' in child.tag:
                    current_tree.remove(child)
            with open("/home/odoo/Desktop/current.xml", "w") as f:
                f.write(generated_files)
            self.assertXmlTreeEqual(current_tree, expected_tree)


    # def testRefundStandard(self):

    #     move = self._create_refund()
    #     move.action_post()
    #     move._l10n_sa_generate_unsigned_xml()

    #     generated_files = move.l10n_sa_unsigned_xml_signature
    #     self.assertTrue(generated_files)

    #     print(expected_xml_invoice_value)
    #     current_tree = self.get_xml_tree_from_string(generated_files)
    #     expected_tree = self.get_xml_tree_from_string(expected_xml_invoice_value)
    #     self.assertXmlTreeEqual(current_tree, expected_tree)
