# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountantTours(AccountTestInvoicingHttpCommon):
    def test_account_merge_wizard_tour(self):
        companies = self.env['res.company'].create([
            {'name': 'tour_company_1'},
            {'name': 'tour_company_2'},
        ])

        self.env['account.account'].create([
            {
                'company_ids': [Command.set(companies[0].ids)],
                'code': "100001",
                'name': "Current Assets",
                'account_type': 'asset_current',
            },
            {
                'company_ids': [Command.set(companies[0].ids)],
                'code': "100002",
                'name': "Non-Current Assets",
                'account_type': 'asset_non_current',
            },
            {
                'company_ids': [Command.set(companies[1].ids)],
                'code': "200001",
                'name': "Current Assets",
                'account_type': 'asset_current',
            },
            {
                'company_ids': [Command.set(companies[1].ids)],
                'code': "200002",
                'name': "Non-Current Assets",
                'account_type': 'asset_non_current',
            },
        ])

        self.env.ref('base.user_admin').write({
            'company_id': companies[0].id,
            'company_ids': [Command.set(companies.ids)],
        })
        self.start_tour("/odoo", 'account_merge_wizard_tour', login="admin", cookies={"cids": f"{companies[0].id}-{companies[1].id}"})
