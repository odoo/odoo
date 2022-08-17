# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.account.models.account_payment_method import AccountPaymentMethod
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.payment.tests.common import PaymentCommon


class AccountPaymentCommon(PaymentCommon, AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, *kw):
        # chart_template_ref is dropped on purpose because not needed for account_payment tests.
        super().setUpClass()

        Method_get_payment_method_information = AccountPaymentMethod._get_payment_method_information

        def _get_payment_method_information(self):
            res = Method_get_payment_method_information(self)
            res['none'] = {'mode': 'multi', 'domain': [('type', '=', 'bank')]}
            return res

        with patch.object(AccountPaymentMethod, '_get_payment_method_information', _get_payment_method_information):
            cls.env['account.payment.method'].create({
                'name': 'Dummy method',
                'code': 'none',
                'payment_type': 'inbound'
            })

        cls.dummy_provider.journal_id = cls.company_data['default_journal_bank'].id,

        cls.account = cls.company.account_journal_payment_credit_account_id
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'currency_id': cls.currency_euro.id,
            'partner_id': cls.partner.id,
            'line_ids': [
                (0, 0, {
                    'account_id': cls.account.id,
                    'debit': 100.0,
                    'credit': 0.0,
                    'amount_currency': 200.0,
                }),
                (0, 0, {
                    'account_id': cls.account.id,
                    'debit': 0.0,
                    'credit': 100.0,
                    'amount_currency': -200.0,
                }),
            ],
        })

    def setUp(self):
        super().setUp()
        # Disable _reconcile_after_done patcher
        self.reconcile_after_done_patcher.stop()

    #=== Utils ===#

    @classmethod
    def _prepare_provider(cls, provider_code='none', company=None, update_values=None):
        """ Override of `payment` to prepare and return the first provider matching the given
        provider and company.

        If no provider is found in the given company, we duplicate the one from the base company.
        All other providers belonging to the same company are disabled to avoid any interferences.

        :param str provider_code: The code of the provider to prepare.
        :param recordset company: The company of the provider to prepare, as a `res.company` record.
        :param dict update_values: The values used to update the provider.
        :return: The provider to prepare, if found.
        :rtype: recordset of `payment.provider`
        """
        provider = super()._prepare_provider(provider_code, company, update_values)
        if not provider.journal_id:
            provider.journal_id = cls.env['account.journal'].search(
                [('company_id', '=', provider.company_id.id), ('type', '=', 'bank')],
                limit=1,
            )
        return provider
