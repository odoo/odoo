# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.account_payment.tests.common import AccountPaymentCommon


@tagged('-at_install', 'post_install')
class TestPaymentProvider(AccountPaymentCommon):

    def test_duplicate_provider_child_company_no_journal_id(self):
        """
        When you duplicate a payment provider from a parent company and set it to a child company,
        if you don't set the journal (only possible if the provider is disabled), it should not raise an error when trying to reopen it.
        We want the journal to be set only if the company has a Bank journal defined in it.
        """
        child_company = self.env['res.company'].create({
            'name': 'Child Company',
            'parent_id': self.env.company.id,
        })
        with self.mocked_get_payment_method_information():
            provider_duplicated = self.dummy_provider.copy(default={
                'name': 'Duplicated Provider',
                'company_id': child_company.id,
                'state': 'test',
            })
            self.assertFalse(provider_duplicated.journal_id)

            bank_journal = self.env['account.journal'].create({
                'name': 'Bank Journal',
                'type': 'bank',
                'company_id': child_company.id,
            })
            provider_duplicated.invalidate_recordset(fnames=['journal_id'])
            self.assertEqual(provider_duplicated.journal_id, bank_journal)
