# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestL10nGccInvoice(AccountTestInvoicingCommon):

    def test_line_name_without_arabic(self):
        """ The line name can be read when the arabic language is not installed. """
        arabic = self.env['res.lang'].search([('code', '=', 'ar_001')])
        if arabic.code in (self.env.user.lang, self.env.ref('base.user_admin').lang):
            self.skipTest("The arabic language is used")
        arabic.active = False
        invoice = self.init_invoice('out_invoice', products=self.product_a)
        line = invoice.invoice_line_ids
        self.assertEqual(line.l10n_gcc_line_name, line.name)
