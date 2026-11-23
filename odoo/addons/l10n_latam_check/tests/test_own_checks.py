# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.l10n_latam_check.tests.common import L10nLatamCheckTest
from odoo.tests.common import Form, tagged
from odoo import fields


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestOwnChecks(L10nLatamCheckTest):

    def test_01_pay_with_manual_check(self):
        """ Create and post a manual check with deferred date """

        with Form(self.env['account.payment'].with_context(default_payment_type='outbound')) as payment_form:
            payment_form.partner_id = self.partner_a
            payment_form.amount = 50
            payment_form.journal_id = self.bank_journal
            payment_form.payment_method_line_id = self.bank_journal._get_available_payment_method_lines(
                'outbound').filtered(lambda x: x.code == 'check_printing')

            payment_form.ref = 'Deferred check'
            payment_form.l10n_latam_check_payment_date = fields.Date.add(fields.Date.today(), months=1)

            # Manual check (deferred/electronic) has l10n_latam_manual_checks = True and do not auto compute the check
            # number field
            self.assertEqual(payment_form.l10n_latam_manual_checks, True)
            self.assertEqual(payment_form.check_number, False)

            payment_form.l10n_latam_check_number = '00000001'

        payment = payment_form.save()
        payment.action_post()
