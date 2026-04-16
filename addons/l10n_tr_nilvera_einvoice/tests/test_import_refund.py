from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.l10n_tr_nilvera_einvoice.tests.test_xml_ubl_tr_common import TestUBLTRCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestImportRefund(TestUBLTRCommon):
    def test_import_iade_creates_refund(self):
        with file_open('l10n_tr_nilvera_einvoice/tests/test_files/refund/refund_iade.xml', 'rb') as xml_file:
            invoice = self._create_invoice_from_xml(xml_file.read())
        self.assertEqual(invoice.move_type, 'in_refund')

    def test_import_tevkifatiade_creates_refund(self):
        with file_open('l10n_tr_nilvera_einvoice/tests/test_files/refund/refund_tevkifatiade.xml', 'rb') as xml_file:
            invoice = self._create_invoice_from_xml(xml_file.read())
        self.assertEqual(invoice.move_type, 'in_refund')
