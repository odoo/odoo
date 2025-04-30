# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.mail.tests.common import MailCase
from odoo.tests import Form, users
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestTracking(AccountTestInvoicingCommon, MailCase):

    @classmethod
    def default_env_context(cls):
        # OVERRIDE
        return {}

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
        # Isolate the tracked value for the invoice line because changing the account has recomputed the taxes.
        tracking_value = account_move.message_ids.sudo().tracking_value_ids\
            .filtered(lambda t: t.field_id.name == 'account_id' and t.old_value_integer == old_value.id)
        self.assertTracking(tracking_value.mail_message_id, [
            ('account_id', 'many2one', old_value, new_value),
        ])

        self.assertEqual(len(tracking_value), 1)
        self.assertTrue(tracking_value.field_id)
        field = self.env[tracking_value.field_id.model]._fields[tracking_value.field_id.name]
        self.assertFalse(field.groups, "There is no group on account.move.line.account_id")

    @users('admin')
    def test_invite_follower_account_moves(self):
        """ Test that the mail_followers_edit wizard works on both single and multiple account.move records """
        user_admin = self.env.ref('base.user_admin')
        user_admin.write({
                'country_id': self.env.ref('base.be').id,
                'email': 'test.admin@test.example.com',
                "name": "Mitchell Admin",
                'notification_type': 'inbox',
                'phone': '0455135790',
            })
        partner_admin = self.env.ref('base.partner_admin')
        multiple_account_moves = [
            {
                'description': 'Single account.move',
                'account_moves': [{'name': 'Test Single', 'partner_id': self.partner_a.id}],
                'expected_partners': self.partner_a | user_admin.partner_id,
            },
            {
                'description': 'Multiple account.moves',
                'account_moves': [
                    {'name': 'Move 1', 'partner_id': self.partner_a.id},
                    {'name': 'Move 2', 'partner_id': self.partner_b.id},
                ],
                'expected_partners': self.partner_a | user_admin.partner_id,
            },
        ]
        for move in multiple_account_moves:
            with self.subTest(move['description']):
                account_moves = self.env['account.move'].with_context(self._test_context).create(move['account_moves'])
                mail_invite = self.env['mail.followers.edit'].with_context({
                    'default_res_model': 'account.move',
                    'default_res_ids': account_moves.ids,
                }).with_user(user_admin).create({
                    'partner_ids': [(4, self.partner_a.id), (4, user_admin.partner_id.id)],
                    'notify': True,
                })
                with self.mock_mail_app(), self.mock_mail_gateway():
                    mail_invite.edit_followers()

                for account_move in account_moves:
                    self.assertEqual(account_move.message_partner_ids, move['expected_partners'])

                self.assertEqual(len(self._new_msgs), 1)
                self.assertEqual(len(self._mails), 1)
                self.assertNotSentEmail([partner_admin])
                self.assertNotified(
                    self._new_msgs[0],
                    [{'partner': partner_admin, 'type': 'inbox', 'is_read': False}]
                )
