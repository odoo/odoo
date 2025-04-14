from itertools import product

from odoo import Command
from odoo.tests import tagged
from odoo.addons.l10n_jo_edi.tests.jo_edi_common import JoEdiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestJoEdiInvoiceCodes(JoEdiCommon):
    def _get_next_invoice_details(self):
        scope_types = ["local", "export", "development"]
        payment_methods = ["cash", "receivable"]
        company_types = ["income", "sales", "special"]

        for t_idx, p_idx, c_idx in product(range(3), range(2), range(3)):
            yield (
                scope_types[t_idx],
                payment_methods[p_idx],
                company_types[c_idx],
                f"{t_idx}{p_idx + 1}{c_idx + 1}"
            )

    def _get_xml_invoice_type(self, invoice):
        generated_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(invoice)[0]
        xml_tree = self.get_xml_tree_from_string(generated_file)
        return xml_tree.find(".//{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}InvoiceTypeCode").get('name')

    def test_jo_invoice_codes(self):
        invoice_vals = {
            'name': 'EIN/998833/0',
            'invoice_line_ids': [Command.create({})]
        }
        invoice = self._l10n_jo_create_invoice(invoice_vals)

        for scope_type, payment_method, company_type, expected_code in self._get_next_invoice_details():
            with self.subTest(subtest_name=f"Invoice ({scope_type} - {payment_method} - {company_type}) should have code {expected_code}"):
                invoice.l10n_jo_edi_invoice_type = scope_type
                invoice.l10n_jo_edi_payment_method = payment_method
                self.company.l10n_jo_edi_taxpayer_type = company_type
                self.assertEqual(self._get_xml_invoice_type(invoice), expected_code)
