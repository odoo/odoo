# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountEdiUblCii(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.uom_units = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozens = cls.env.ref('uom.product_uom_dozen')

        cls.displace_prdct = cls.env['product.product'].create({
            'name': 'Displacement',
            'uom_id': cls.uom_units.id,
            'standard_price': 90.0,
        })

        cls.place_prdct = cls.env['product.product'].create({
            'name': 'Placement',
            'uom_id': cls.uom_units.id,
            'standard_price': 80.0,
        })

    def test_import_product(self):
        line_vals = [
           {'product_id': self.place_prdct.id, 'product_uom_id': self.uom_units.id},
           {'product_id': self.displace_prdct.id, 'product_uom_id': self.uom_units.id},
           {'product_id': self.displace_prdct.id, 'product_uom_id': self.uom_units.id},
           {'product_id': self.displace_prdct.id, 'product_uom_id': self.uom_dozens.id}
        ]
        invoice = self.env['account.move'].create({
            'partner_id': self.company_data_2['company'].partner_id.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [(0, 0, vals) for vals in line_vals],
        })
        invoice.action_post()

        facturx_attachment = invoice.edi_document_ids.attachment_id
        xml_tree = etree.fromstring(facturx_attachment.raw)

        # Testing the case where a product on the invoice has a UoM with a different category than the one in the DB
        wrong_uom_line = xml_tree.findall('./{*}SupplyChainTradeTransaction/{*}IncludedSupplyChainTradeLineItem')[1]
        wrong_uom_line.find('./{*}SpecifiedLineTradeDelivery/{*}BilledQuantity').attrib['unitCode'] = 'HUR'

        new_invoice = self.env.ref('account_edi_facturx.edi_facturx_1_0_05')._create_invoice_from_xml_tree(
            facturx_attachment.name,
            xml_tree,
            invoice.journal_id,
        )

        self.assertRecordValues(new_invoice.invoice_line_ids, line_vals)
