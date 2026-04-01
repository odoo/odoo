# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import file_open

from lxml import etree
from datetime import datetime


@tagged('post_install', '-at_install')
class TestPurchaseOrderEDIGen(AccountTestInvoicingCommon):
    def test_purchase_order_download_edi(self):
        self.env.company.vat = 'BE0477472701'
        self.partner_a.vat = 'NL123456782B90'

        po = self.env['purchase.order'].create({
            'name': 'My PO',
            'partner_id': self.partner_a.id,
            'partner_ref': 'SO/1234',
            'order_line': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'name': 'Product A description',
                    'product_qty': 10.0,
                    'price_unit': 50.0,
                    'discount': 10.0,
                }),
                (0, 0, {
                    'product_id': self.product_a.id,
                    'name': 'Product A description',
                    'product_qty': 1.0,
                    'price_unit': 10.0,
                }),
            ],
        })

        po.button_confirm()

        file_content = self.env['purchase.edi.xml.ubl_bis3']._export_order(po)
        generated_xml = etree.fromstring(file_content)

        with file_open('purchase_edi_ubl_bis3/tests/data/test_po_edi.xml', 'r') as f:
            current_date = f'{datetime.today().date()}'
            xml_template = f.read().encode().replace(b'create_date_placeholder', current_date.encode())
            expected_xml = etree.fromstring(xml_template)
        self.assertXmlTreeEqual(generated_xml, expected_xml)
