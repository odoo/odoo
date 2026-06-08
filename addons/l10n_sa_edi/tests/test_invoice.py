from odoo import Command
from odoo.tests import tagged
from odoo.addons.l10n_sa_edi.tests.common import TestSaEdiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nSaInvoice(TestSaEdiCommon):

    def test_invoice_section_lines_rendering(self):
        invoice = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_sa_simplified.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'tax_ids': self.tax_15.ids,
                    'price_unit': 100.0,
                }),
                Command.create({
                    'display_type': 'line_section',
                    'name': 'section line',
                }),
                 Command.create({
                    'product_id': self.product_b.id,
                    'tax_ids': self.tax_15.ids,
                    'price_unit': 200.0,
                })
            ]
        }])
        invoice.action_post()
        html = self.env['ir.actions.report']._render_qweb_html('account.report_invoice_with_payments', invoice.ids)[0]
        self.assertTrue(html)
