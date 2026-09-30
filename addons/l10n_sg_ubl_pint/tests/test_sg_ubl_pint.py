# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools import file_open
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSgUBLPint(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='sg'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env.ref('base.EUR').active = True

    def test_invoice_import(self):
        with file_open('l10n_sg_ubl_pint/tests/expected_xmls/invoice.xml', 'rb') as f:
            xml_content = f.read()

        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.encodebytes(xml_content),
            'mimetype': 'application/xml',
        })

        journal = self.company_data['default_journal_purchase']
        invoice = journal._create_document_from_attachment(attachment.ids)

        self.assertTrue(invoice)
        self.assertRecordValues(invoice, [{
            'move_type': 'in_invoice',
            'currency_id': self.env.ref('base.EUR').id,
            'amount_untaxed': 2000.0,
            'amount_tax': 180.0,
            'amount_total': 2180.0,
        }])
