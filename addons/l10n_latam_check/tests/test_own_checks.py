# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.l10n_latam_check.tests.common import L10nLatamCheckTest
from odoo.tests.common import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestOwnChecks(L10nLatamCheckTest):

    def test_01_pay_with_multiple_checks(self):
        """ Create one check with each checkbook, first check should choose deferred check by default. On current
        check force a different number than next one"""
        vals_list = [{
            'ref': 'Deferred check',
            'partner_id': self.partner_a.id,
            'amount': '00000001',
            'payment_type': 'outbound',
            'journal_id': self.bank_journal.id,
            'payment_method_line_id': self.bank_journal._get_available_payment_method_lines('outbound').filtered(lambda x: x.code == 'check_printing').id,
        }, {
            'ref': 'Current check',
            'partner_id': self.partner_a.id,
            'amount': '00000001',
            'check_number': '120',
            'payment_type': 'outbound',
            'journal_id': self.bank_journal.id,
            'payment_method_line_id': self.bank_journal._get_available_payment_method_lines('outbound').filtered(lambda x: x.code == 'check_printing').id,
        }, {
            'ref': 'Electronic check',
            'partner_id': self.partner_a.id,
            'amount': '00000001',
            'payment_type': 'outbound',
            'journal_id': self.bank_journal.id,
            'payment_method_line_id': self.bank_journal._get_available_payment_method_lines('outbound').filtered(lambda x: x.code == 'check_printing').id,
        }]
        payments = self.env['account.payment'].create(vals_list)
        payments.action_post()
        self.assertEqual(len(payments), 3, 'Checks where not created properly')
        for i, check_number in zip(range(3), [50, 120, 200]):
            payment = payments[i]
            self.assertEqual(payment.state, 'posted', 'Check %s was not created properly' % payment.check_number)
            self.assertTrue(payment.is_move_sent, 'Check %s was not set sent' % payment.check_number)
            self.assertEqual(
                payment.l10n_latam_checkbook_id.next_number, check_number + 1,
                'Next sequence was not updated properly on checkbook %s' % payment.check_number)
