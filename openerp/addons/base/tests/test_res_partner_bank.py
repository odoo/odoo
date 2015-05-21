# -*- coding: utf-8 -*-
##############################################################################
#
#     This file is part of account_bank_statement_import,
#     an Odoo module.
#
#     Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
#
#     account_bank_statement_import is free software:
#     you can redistribute it and/or modify it under the terms of the GNU
#     Affero General Public License as published by the Free Software
#     Foundation,either version 3 of the License, or (at your option) any
#     later version.
#
#     account_bank_statement_import is distributed
#     in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
#     even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#     PURPOSE.  See the GNU Affero General Public License for more details.
#
#     You should have received a copy of the GNU Affero General Public License
#     along with account_bank_statement_import_coda.
#     If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.tests.common import TransactionCase


class TestResPartnerBank(TransactionCase):
    """Tests acc_number
    """

    def test_sanitized_acc_number(self):
        partner_bank_model = self.env['res.partner.bank']
        acc_number = " BE-001 2518823 03 "
        vals = partner_bank_model.search([('acc_number', '=', acc_number)])
        self.assertEquals(0, len(vals))
        partner_bank = partner_bank_model.create({
            'acc_number': acc_number,
            'partner_id': self.ref('base.res_partner_2'),
            'state': 'bank',
        })
        vals = partner_bank_model.search([('acc_number', '=', acc_number)])
        self.assertEquals(1, len(vals))
        self.assertEquals(partner_bank, vals[0])
        vals = partner_bank_model.search([('acc_number', 'in', [acc_number])])
        self.assertEquals(1, len(vals))
        self.assertEquals(partner_bank, vals[0])

        self.assertEqual(partner_bank.acc_number, acc_number)

        # sanitaze the acc_number
        sanitized_acc_number = 'BE001251882303'
        vals = partner_bank_model.search(
            [('acc_number', '=', sanitized_acc_number)])
        self.assertEquals(1, len(vals))
        self.assertEquals(partner_bank, vals[0])
        vals = partner_bank_model.search(
            [('acc_number', 'in', [sanitized_acc_number])])
        self.assertEquals(1, len(vals))
        self.assertEquals(partner_bank, vals[0])
        self.assertEqual(partner_bank.sanitized_acc_number,
                         sanitized_acc_number)

        # search is case insensitive
        vals = partner_bank_model.search(
            [('acc_number', '=', sanitized_acc_number.lower())])
        self.assertEquals(1, len(vals))
        vals = partner_bank_model.search(
            [('acc_number', '=', acc_number.lower())])
        self.assertEquals(1, len(vals))
