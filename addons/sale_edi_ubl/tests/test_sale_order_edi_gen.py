# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import tagged
from odoo.tools import file_open

from lxml import etree
from datetime import datetime


@tagged('post_install', '-at_install')
class TestSaleOrderEDIGen(TestSaleCommon):
    def test_sale_order_download_edi(self):
        self.env.company.vat = 'BE0477472701'
        self.partner_a.vat = 'NL123456782B90'

        so = self.env['sale.order'].create({
            'name': 'My SO',
            'partner_id': self.partner_a.id,
            'client_order_ref': 'PO/1234',
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'name': 'Product A description',
                    'product_uom_qty': 10.0,
                    'price_unit': 50.0,
                    'discount': 10.0,
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'name': 'Product A description',
                    'product_uom_qty': 1.0,
                    'price_unit': 10.0,
                })
            ]
        })

        so.action_confirm()

        file_content = self.env['sale.edi.xml.ubl_bis3']._export_order(so)
        generated_xml = etree.fromstring(file_content)

        with file_open('sale_edi_ubl/tests/data/test_so_edi.xml', 'r') as f:
            current_date = f'{datetime.today().date()}'
            validity_date = f'{so.validity_date}'
            xml_template = f.read().encode().replace(b'create_date_placeholder', current_date.encode()).replace(b'validity_date_placeholder', validity_date.encode())
            expected_xml = etree.fromstring(xml_template)
        self.assertXmlTreeEqual(generated_xml, expected_xml)
