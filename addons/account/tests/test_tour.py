# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(AccountTestInvoicingCommon, odoo.tests.HttpCase):

    def test_01_account_tour(self):
        account_with_taxes = self.env['account.account'].search([('tax_ids', '!=', False), ('company_id', '=', self.env.company.id)])
        account_with_taxes.write({
            'tax_ids': [Command.clear()],
        })
        self.start_tour("/web", 'account_tour', login="admin")
