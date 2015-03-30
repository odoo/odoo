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


class TestAccountBankStatemetImport(TransactionCase):
    """Tests for import bank statement file import
    (account.bank.statement.import)
    """

    def setUp(self):
        super(TestAccountBankStatemetImport, self).setUp()
        self.statement_import_model = self.env[
            'account.bank.statement.import']
        self.account_journal_model = self.env['account.journal']
        self.res_users_model = self.env['res.users']

        self.journal_id = self.ref('account.bank_journal')
        self.base_user_root_id = self.ref('base.user_root')
        self.base_user_root = self.res_users_model.browse(
            self.base_user_root_id)

        # create a new user that belongs to the same company as
        # user_root
        self.other_partner_id = self.env['res.partner'].create(
            {"name": "My other partner",
             "is_company": False,
             "email": "test@tes.ttest",
             })
        self.company_id = self.base_user_root.company_id.id
        self.other_user_id_a = self.res_users_model.create(
            {"partner_id": self.other_partner_id.id,
             "company_id": self.company_id,
             "company_ids": [(4, self.company_id)],
             "login": "my_login a",
             "name": "my user",
             "groups_id": [(4, self.ref('account.group_account_manager'))]
             })

    def test_create_bank_account(self):
        """Checks that the bank_account created by the import belongs to the
        partner linked to the company of the provided journal
        """
        journal = self.account_journal_model.browse(self.journal_id)
        expected_id = journal.company_id.partner_id.id

        st_import = self.statement_import_model.sudo(self.other_user_id_a.id)
        bank = st_import._create_bank_account(
            '001251882303', company_id=self.company_id)

        self.assertEqual(bank.partner_id.id,
                         expected_id)
