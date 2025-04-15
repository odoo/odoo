# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import Form
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestTracking(AccountTestInvoicingCommon, MailCommon):

    def test_aml_change_tracking(self):
        """ tests that the field_groups is correctly set """
        account_move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 200.0})]
        })
        account_move.action_post()
        account_move.button_draft()
        old_value = account_move.invoice_line_ids.account_id

        with Form(account_move) as account_move_form:
            with account_move_form.invoice_line_ids.edit(0) as line_form:
                line_form.account_id = self.company_data['default_account_assets']
        new_value = account_move.invoice_line_ids.account_id

        self.flush_tracking()
        self.assertTracking(account_move.message_ids, [
            ('account_id', 'many2one', old_value, new_value),
        ])

        tracking_value = account_move.message_ids.sudo().tracking_value_ids
        tracking_value._compute_field_groups()

        self.assertEqual(tracking_value.field_groups, False, "There is no group on account.move.line.account_id")
