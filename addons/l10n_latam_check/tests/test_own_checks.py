# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.l10n_latam_check.tests.common import L10nLatamCheckTest
from odoo.tests import Form, tagged
from odoo import fields, Command


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestOwnChecks(L10nLatamCheckTest):

    def test_01_pay_with_manual_check(self):
        """ Create and post a manual check with deferred date """

        with Form(self.env['account.payment'].with_context(default_payment_type='outbound')) as payment_form:
            payment_form.partner_id = self.partner_a
            # payment_form.amount = 50
            payment_form.journal_id = self.bank_journal
            payment_form.payment_method_line_id = self.bank_journal._get_available_payment_method_lines(
                'outbound').filtered(lambda x: x.code == 'own_checks')

            payment_form.ref = 'Deferred check'
            payment_form.l10n_latam_new_check_ids = [
                Command.create(
                    {'name': '00000001', 'l10n_latam_check_payment_date': fields.Date.add(fields.Date.today(), months=1), 'amount': 25},
                    {'name': '00000002', 'l10n_latam_check_payment_date': fields.Date.add(fields.Date.today(), months=2), 'amount': 25},
                )]

        payment = payment_form.save()
        payment.action_post()
