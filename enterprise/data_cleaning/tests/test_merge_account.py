# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo.tests.common import tagged, users


@tagged('post_install', '-at_install')
class TestMerge(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if 'account.account' not in cls.env:
            cls.skipTest(cls, "`account` module not installed")

        cls.customer_invoice_journal = cls.env['account.journal'].search([('company_id', '=', cls.env.company.id), ('name', '=', 'Customer Invoices')])
        cls.account_sale_a = cls.env['account.account'].create({
            'code': '40001',
            'name': 'Account Sale A',
            'account_type': 'asset_receivable',
            'reconcile': True,
        })
        cls.account_sale_b = cls.env['account.account'].create({
            'code': '40002',
            'name': 'Account Sale B',
            'account_type': 'asset_receivable',
            'reconcile': True,
        })
        cls.partner_a = cls.env['res.partner'].create({'name': 'Partner A'})
        cls.partner_b = cls.env['res.partner'].create({'name': 'Partner B'})

    def _enable_merge(self, model_name):
        self.res_model_id = self.env['ir.model'].search([('model', '=', model_name)])
        self.res_model_id.action_merge_contextual_enable()
        self.model_id = self.env['data_merge.model'].create({
            'name': model_name,
            'res_model_id': self.res_model_id.id,
        })

    def test_merge_account(self):
        """
        Test that we cannot merge accounts.
        """
        self._enable_merge('account.account')

        data_merge_group = self.env['data_merge.group'].create({
            'model_id': self.model_id.id,
            'res_model_id': self.res_model_id.id,
            'record_ids': [
                (0, 0, {
                    'res_id': self.account_sale_a.id,
                    'is_master': True,
                }),
                (0, 0, {
                    'res_id': self.account_sale_b.id,
                }),
            ],
        })

        # use to replicate information sent from JS call `_onMergeClick`
        group_records = {str(data_merge_group.id): data_merge_group.record_ids.ids}
        with self.assertRaises(UserError, msg="You cannot merge accounts."):
            self.env['data_merge.group'].merge_multiple_records(group_records)

    @users('admin')
    def test_merge_partner_in_hashed_entries(self):
        """
        Test that we cannot merge partners used in hashed entries
        """
        self.env.user.write({'groups_id': [(4, self.env.ref('account.group_account_user').id)]})
        self._enable_merge('res.partner')
        move_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2023-07-21',
            'partner_id': self.partner_b.id,
            'invoice_line_ids': [Command.create({'name': 'test line', 'price_unit': 1000})],
        })
        move_1.action_post()

        self.customer_invoice_journal.restrict_mode_hash_table = True

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2023-07-22',
            'partner_id': self.partner_b.id,
            'invoice_line_ids': [Command.create({'name': 'test line', 'price_unit': 1000})],
        })
        move.action_post()

        # The integrity check should work
        integrity_check = move.company_id._check_hash_integrity()['results']
        integrity_check = next(filter(lambda j: move.sequence_prefix in j.get('journal_name'), integrity_check))
        self.assertRegex(integrity_check['msg_cover'], 'Entries are correctly hashed')

        data_merge_group = self.env['data_merge.group'].create({
            'model_id': self.model_id.id,
            'res_model_id': self.res_model_id.id,
            'record_ids': [
                (0, 0, {
                    'res_id': self.partner_a.id,
                    'is_master': True,
                }),
                (0, 0, {
                    'res_id': self.partner_b.id,
                }),
            ],
        })

        # use to replicate information sent from JS call `_onMergeClick`
        group_records = {str(data_merge_group.id): data_merge_group.record_ids.ids}
        with self.assertRaises(UserError, msg="Records that are used as fields in hashed entries cannot be merged."):
            self.env['data_merge.group'].merge_multiple_records(group_records)
