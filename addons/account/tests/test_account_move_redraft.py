from odoo.tests import tagged
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("-at_install", "post_install")
class TestAccountMoveRedraft(AccountTestInvoicingCommon):
    def test_add_new_lines_pdf(self):

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'line1',
                }),
            ],
        })

        template = self.env.ref(invoice._get_mail_template())

        invoice.action_post()
        self.env['account.move.send']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({
                'mail_template_id': template.id,
            }).action_send_and_print()

        pre_draft_checksum = invoice.invoice_pdf_report_id.checksum

        invoice.button_draft()
        invoice._compute_linked_attachment_id('invoice_pdf_report_id', 'invoice_pdf_report_file')

        invoice.write({'invoice_line_ids': [
            Command.create({
                'name': 'line2',
            }),
        ]})

        invoice.action_post()
        self.env['account.move.send']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({
                'mail_template_id': template.id,
            }).action_send_and_print()

        self.assertNotEqual(
            invoice.invoice_pdf_report_id.checksum,
            pre_draft_checksum
        )
