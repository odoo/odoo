# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import TransactionCase, tagged
from odoo.tools import file_open


@tagged('post_install', '-at_install')
class TestShippingReportPdf(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        picking_type = cls.env['stock.picking.type'].search([('code', '=', 'outgoing')], limit=1)
        cls.picking = cls.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'partner_id': cls.env['res.partner'].create({'name': 'Shipping Report Customer'}).id,
        })
        cls.report_labels = cls.env.ref('stock_delivery.action_report_shipping_labels')
        cls.report_docs = cls.env.ref('stock_delivery.action_report_shipping_docs')
        cls.env['printer.printer'].create({
            'name': 'Test Printer',
            'type': 'zpl',
            'report_ids': [Command.set((cls.report_labels | cls.report_docs).ids)],
        })
        with file_open('base/tests/files/file.pdf', 'rb') as pdf_file:
            cls.pdf_content = pdf_file.read()

    def test_render_shipping_pdf(self):
        """Shipping reports must return the attached PDF bytes unchanged."""
        for report, prefix in (
            (self.report_labels, 'LabelShipping'),
            (self.report_docs, 'ShippingDoc'),
        ):
            with self.subTest(report=report.report_name):
                self.env['ir.attachment'].create({
                    'name': f'{prefix}-test.pdf',
                    'type': 'binary',
                    'raw': self.pdf_content,
                    'mimetype': 'application/pdf',
                    'res_model': 'stock.picking',
                    'res_id': self.picking.id,
                })
                content, report_type = self.env['ir.actions.report']._render_qweb_pdf(
                    report.report_name, res_ids=self.picking.ids,
                )
                self.assertEqual(report_type, 'pdf')
                self.assertIsInstance(content, bytes)
                self.assertEqual(content, self.pdf_content)
