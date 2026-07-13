from odoo.addons.l10n_ro_edi.tests.test_xml_ubl_ro import TestUBLROCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLROCPVCode(TestUBLROCommon):

    def test_export_invoice(self):
        self.product_a.cpv_code_id = self.env.ref('l10n_ro_cpv_code.030000001')
        self.product_b.cpv_code_id = self.env.ref('l10n_ro_cpv_code.031000002')
        invoice = self.create_move("out_invoice")
        attachment = self.get_attachment(invoice)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_invoice_cpv_code.xml')
