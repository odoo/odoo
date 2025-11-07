# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)

from odoo.tests import tagged

from odoo.addons.base.tests.common import SavepointCaseWithUserDemo


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestResPartnerBank(SavepointCaseWithUserDemo):
    """Tests account_number
    """

    def test_sanitized_account_number(self):
        partner_bank_model = self.env['res.partner.bank']
        account_number = " BE-001 2518823 03 "
        vals = partner_bank_model.search([('account_number', '=', account_number)])
        self.assertEqual(0, len(vals))
        partner_bank = partner_bank_model.create({
            'account_number': account_number,
            'partner_id': self.env['res.partner'].create({'name': 'Pepper Test'}).id,
        })
        vals = partner_bank_model.search([('account_number', '=', account_number)])
        self.assertEqual(1, len(vals))
        self.assertEqual(partner_bank, vals[0])
        vals = partner_bank_model.search([('account_number', 'in', [account_number])])
        self.assertEqual(1, len(vals))
        self.assertEqual(partner_bank, vals[0])

        self.assertEqual(partner_bank.account_number, account_number)

        # sanitaze the account_number
        sanitized_account_number = 'BE001251882303'
        self.assertEqual(partner_bank.sanitized_account_number, sanitized_account_number)
        vals = partner_bank_model.search(
            [('account_number', '=', sanitized_account_number)])
        self.assertEqual(1, len(vals))
        self.assertEqual(partner_bank, vals[0])
        vals = partner_bank_model.search(
            [('account_number', 'in', [sanitized_account_number])])
        self.assertEqual(1, len(vals))
        self.assertEqual(partner_bank, vals[0])
        self.assertEqual(partner_bank.sanitized_account_number,
                         sanitized_account_number)

        # search is case insensitive
        vals = partner_bank_model.search(
            [('account_number', '=', sanitized_account_number.lower())])
        self.assertEqual(1, len(vals))
        vals = partner_bank_model.search(
            [('account_number', '=', account_number.lower())])
        self.assertEqual(1, len(vals))

        # updating the sanitized value will also update the account_number
        partner_bank.write({'sanitized_account_number': 'BE001251882303WRONG'})
        self.assertEqual(partner_bank.account_number, partner_bank.sanitized_account_number)
