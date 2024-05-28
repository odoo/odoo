# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import os

from unittest.mock import patch

from odoo.fields import Command
from odoo.tests import Form, tagged
from odoo.tools.misc import file_open

from odoo.addons.sale.tests.common import SaleCommon

directory = os.path.dirname(__file__)


@tagged('post_install', '-at_install')
class TestPDFQuoteBuilder(SaleCommon):

    @classmethod
    def setUpClass(cls):
        print("hello")
        super().setUpClass()

        # cls.skipTest('One day, I will work')

        table = cls.env['product.product'].create({'name': 'Table'})
        cls.sale_template = cls.env['sale.order.template'].create({
            'name': "Order template with header and footer",
            'sale_order_template_line_ids': [
                Command.create({'product_id': cls.product.id}),
                Command.create({'display_type': 'line_section', 'name': "Test Section"}),
                Command.create({'product_id': table.id}),
                Command.create({'display_type': 'line_note', 'name': "Test Note"}),
            ]
        })

        with file_open(os.path.join(directory, 'test_pdf', 'header_footer.pdf'), 'rb') as f:
            header_footer = base64.b64encode(f.read())
            cls.env.company.write({
                'sale_header': header_footer, 'sale_footer': header_footer
            })
            cls.sale_template.write({
                'sale_header': header_footer, 'sale_footer': header_footer
            })
        with file_open(os.path.join(directory, 'test_pdf', 'product_document.pdf'), 'rb') as f:
            product_document = base64.b64encode(f.read())
            attachment = cls.env['ir.attachment'].create({'name': "Doc", 'datas': product_document})
            cls.env['product.document'].create({
                'name': "product doc",
                'ir_attachment_id': attachment.id,
                'attached_on': 'inside',
                'res_model': 'product.product',
                'res_id': cls.product.id,
            })

    # WKHTMLTOPDF doesn't agree to work with us
    def _test_send_quotation_mail_with_sale_order_template(self):
        # Empty company header and footer to verify the template ones are used
        self.env.company.sale_header = self.env.company.sale_footer = False

        sale_order = self.env['sale.order'].create({
            'name': 'Sale Order',
            'partner_id': self.partner.id,
            'sale_order_template_id': self.sale_template.id,
        })
        sale_order._onchange_sale_order_template_id()

        self.assertEqual(len(sale_order.order_line), 4)
        self.assertTrue(sale_order.sale_order_template_id.sale_header)
        self.assertTrue(sale_order.sale_order_template_id.sale_footer)

        action_data = sale_order.action_quotation_send()
        action_data['context']['force_report_rendering'] = True

        with patch(
            'odoo.addons.sale_pdf_quote_builder.models.ir_actions_report.IrActionsReport'
            '._add_pages_to_writer'
        ) as add_pages_to_writer_mock:
        #     Path 1: full mail send flow
        #     with Form(self.env[action_data['res_model']].with_context(action_data['context'])) as wizard_form:
        #         wizard = wizard_form.save()

        #     wizard.action_send_mail()
        #
        #     Path 2: report rendering
            self.env['ir.actions.report'].sudo().with_context(
                force_report_rendering=True
            )._render_qweb_pdf('sale.report_saleorder', res_ids=[sale_order.id])
        #
        #     Path 3: limited stream rendering
        #     self.env['ir.actions.report'].sudo()._render_qweb_pdf_prepare_streams('sale.report_saleorder', data={'report_type': 'pdf'}, res_ids=[sale_order.id])

            message = (
                "The method '_add_pages_to_writer' should have been called 4 times: for the header,"
                " the product document, the quotation and the footer."
            )
            self.assertEqual(add_pages_to_writer_mock.call_count, 4, msg=message)
