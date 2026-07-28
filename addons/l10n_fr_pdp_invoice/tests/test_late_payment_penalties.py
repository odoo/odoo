from datetime import date
from unittest.mock import patch

from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestLatePaymentPenalties(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data['company']
        cls.change_company_country(cls.company, cls.env.ref('base.fr'))
        cls.company_data_2 = cls.setup_other_company()
        cls.change_company_country(
            cls.company_data_2['company'],
            cls.env.ref('base.fr'),
        )
        cls.env['ir.config_parameter'].sudo().set_param(
            'account_peppol.edi.mode',
            'test',
        )
        cls.billing_user = new_test_user(
            cls.env,
            login='late_payment_billing_user',
            groups='account.group_account_invoice',
            company_id=cls.company.id,
            company_ids=[Command.set(cls.company.ids)],
        )

    def _create_invoice(
        self,
        *,
        company_data=None,
        invoice_date=None,
        move_type='out_invoice',
    ):
        company_data = company_data or self.company_data
        is_sale = move_type in self.env['account.move'].get_sale_types(
            include_receipts=True
        )
        return self.env['account.move'].create({
            'move_type': move_type,
            'journal_id': (
                company_data['default_journal_sale']
                if is_sale
                else company_data['default_journal_purchase']
            ).id,
            'partner_id': self.partner_a.id,
            'invoice_date': invoice_date or fields.Date.today(),
            'invoice_line_ids': [
                Command.create({
                    'name': 'Test line',
                    'account_id': (
                        company_data['default_account_revenue']
                        if is_sale
                        else company_data['default_account_expense']
                    ).id,
                    'quantity': 1,
                    'price_unit': 100,
                }),
            ],
        })

    def _set_manual_rate(self, company, rate):
        company.write({
            'l10n_fr_pdp_late_payment_penalties_rate': rate,
            'l10n_fr_pdp_late_payment_penalties_automatic': False,
        })

    def test_semester_start_boundaries(self):
        get_semester_start = self.company._l10n_fr_pdp_get_semester_start
        self.assertEqual(get_semester_start(date(2026, 1, 1)), date(2026, 1, 1))
        self.assertEqual(get_semester_start(date(2026, 6, 30)), date(2026, 1, 1))
        self.assertEqual(get_semester_start(date(2026, 7, 1)), date(2026, 7, 1))
        self.assertEqual(get_semester_start(date(2026, 12, 31)), date(2026, 7, 1))

    def test_manual_rate_can_be_set_from_accounting_settings(self):
        self.env['res.config.settings'].create({
            'company_id': self.company.id,
            'l10n_fr_pdp_late_payment_penalties_rate': 12.4,
        })

        self.assertEqual(
            self.company.l10n_fr_pdp_late_payment_penalties_rate,
            12.4,
        )
        self.assertFalse(
            self.company.l10n_fr_pdp_late_payment_penalties_automatic
        )

    def test_manual_rate_is_snapshotted_when_invoice_is_posted(self):
        self._set_manual_rate(self.company, 12.4)
        invoice = self._create_invoice(invoice_date=date(2026, 6, 30))
        invoice.action_post()

        self.company.l10n_fr_pdp_late_payment_penalties_rate = 15

        self.assertEqual(invoice.l10n_fr_pdp_late_payment_penalties_rate, 12.4)
        self.assertIn(
            "12.40%",
            invoice._l10n_fr_pdp_get_late_payment_penalty_note(),
        )

    def test_unchanged_settings_keep_automatic_rate_period(self):
        self.company._l10n_fr_pdp_set_automatic_late_payment_penalties_rate(
            12.4,
            date(2026, 7, 1),
        )

        self.company.write({
            'l10n_fr_pdp_late_payment_penalties_rate': 12.4,
            'l10n_fr_pdp_late_payment_penalties_automatic': True,
        })

        self.assertTrue(
            self.company.l10n_fr_pdp_late_payment_penalties_automatic
        )
        self.assertEqual(
            self.company.l10n_fr_pdp_late_payment_penalties_period,
            date(2026, 7, 1),
        )

    def test_iap_rate_is_requested_once_for_current_semester(self):
        self.company.l10n_fr_pdp_late_payment_penalties_automatic = True
        first_invoice = self._create_invoice(invoice_date=date(2026, 7, 1))
        second_invoice = self._create_invoice(invoice_date=date(2026, 7, 15))
        response = [{
            'period_start': '2026-07-01',
            'late_payment_penalty_rate': 12.4,
        }]

        with (
            patch('odoo.fields.Date.today', return_value=date(2026, 7, 15)),
            patch(
                'odoo.addons.l10n_fr_pdp_invoice.models.res_company.iap_tools.iap_jsonrpc',
                return_value=response,
            ) as mocked_iap,
        ):
            first_invoice.action_post()
            second_invoice.action_post()

        self.assertRecordValues(first_invoice | second_invoice, [
            {'l10n_fr_pdp_late_payment_penalties_rate': 12.4},
            {'l10n_fr_pdp_late_payment_penalties_rate': 12.4},
        ])
        self.assertEqual(
            self.company.l10n_fr_pdp_late_payment_penalties_period,
            date(2026, 7, 1),
        )
        mocked_iap.assert_called_once_with(
            'https://pdp.test.odoo.com/api/pdp/1/late_payment_penalty_rates',
            params={'period_starts': ['2026-07-01']},
        )

    def test_iap_rates_are_requested_in_batch(self):
        first_invoice = self._create_invoice(invoice_date=date(2026, 6, 30))
        second_invoice = self._create_invoice(invoice_date=date(2026, 7, 15))
        third_invoice = self._create_invoice(
            company_data=self.company_data_2,
            invoice_date=date(2026, 7, 15),
        )

        with (
            patch('odoo.fields.Date.today', return_value=date(2026, 7, 15)),
            patch(
                'odoo.addons.l10n_fr_pdp_invoice.models.res_company.iap_tools.iap_jsonrpc',
                return_value=[
                    {
                        'period_start': '2026-01-01',
                        'late_payment_penalty_rate': 12.15,
                    },
                    {
                        'period_start': '2026-07-01',
                        'late_payment_penalty_rate': 12.4,
                    },
                ],
            ) as mocked_iap,
        ):
            (first_invoice | second_invoice | third_invoice).action_post()

        self.assertEqual(first_invoice.l10n_fr_pdp_late_payment_penalties_rate, 12.15)
        self.assertEqual(second_invoice.l10n_fr_pdp_late_payment_penalties_rate, 12.4)
        self.assertEqual(third_invoice.l10n_fr_pdp_late_payment_penalties_rate, 12.4)
        mocked_iap.assert_called_once_with(
            'https://pdp.test.odoo.com/api/pdp/1/late_payment_penalty_rates',
            params={'period_starts': ['2026-01-01', '2026-07-01']},
        )

    def test_billing_user_can_update_company_rate_cache(self):
        first_invoice = self._create_invoice(invoice_date=date(2026, 7, 1))
        second_invoice = self._create_invoice(invoice_date=date(2026, 7, 15))
        response = [{
            'period_start': '2026-07-01',
            'late_payment_penalty_rate': 12.4,
        }]

        self.assertFalse(self.billing_user.has_group('base.group_system'))
        with (
            patch('odoo.fields.Date.today', return_value=date(2026, 7, 15)),
            patch(
                'odoo.addons.l10n_fr_pdp_invoice.models.res_company.iap_tools.iap_jsonrpc',
                return_value=response,
            ) as mocked_iap,
        ):
            first_invoice.with_user(self.billing_user).action_post()
            second_invoice.with_user(self.billing_user).action_post()

        self.assertEqual(
            self.company.l10n_fr_pdp_late_payment_penalties_rate,
            12.4,
        )
        self.assertEqual(
            self.company.l10n_fr_pdp_late_payment_penalties_period,
            date(2026, 7, 1),
        )
        mocked_iap.assert_called_once()

    def test_historical_rate_does_not_replace_company_current_rate(self):
        self.company._l10n_fr_pdp_set_automatic_late_payment_penalties_rate(
            12.4,
            date(2026, 7, 1),
        )
        invoice = self._create_invoice(invoice_date=date(2026, 6, 30))

        with (
            patch('odoo.fields.Date.today', return_value=date(2026, 7, 15)),
            patch(
                'odoo.addons.l10n_fr_pdp_invoice.models.res_company.iap_tools.iap_jsonrpc',
                return_value=[{
                    'period_start': '2026-01-01',
                    'late_payment_penalty_rate': 12.15,
                }],
            ),
        ):
            invoice.action_post()

        self.assertEqual(
            invoice.l10n_fr_pdp_late_payment_penalties_rate,
            12.15,
        )
        self.assertEqual(
            self.company.l10n_fr_pdp_late_payment_penalties_period,
            date(2026, 7, 1),
        )
        self.assertEqual(
            self.company.l10n_fr_pdp_late_payment_penalties_rate,
            12.4,
        )

    def test_iap_failure_keeps_rate_and_retries_on_next_invoice(self):
        self.company._l10n_fr_pdp_set_automatic_late_payment_penalties_rate(
            12.15,
            date(2026, 1, 1),
        )
        first_invoice = self._create_invoice(invoice_date=date(2026, 7, 15))

        with (
            patch('odoo.fields.Date.today', return_value=date(2026, 7, 15)),
            mute_logger(
                'odoo.addons.l10n_fr_pdp_invoice.models.res_company'
            ),
            patch(
                'odoo.addons.l10n_fr_pdp_invoice.models.res_company.iap_tools.iap_jsonrpc',
                side_effect=AccessError("IAP unavailable"),
            ),
        ):
            first_invoice.action_post()

        self.assertEqual(first_invoice.state, 'posted')
        self.assertEqual(
            first_invoice.l10n_fr_pdp_late_payment_penalties_rate,
            12.15,
        )
        self.assertEqual(
            self.company.l10n_fr_pdp_late_payment_penalties_period,
            date(2026, 1, 1),
        )
        warning = first_invoice.message_ids.filtered(
            lambda message: 'could not be updated' in (message.body or '')
        )
        self.assertTrue(warning)

        second_invoice = self._create_invoice(invoice_date=date(2026, 7, 16))
        with (
            patch('odoo.fields.Date.today', return_value=date(2026, 7, 16)),
            patch(
                'odoo.addons.l10n_fr_pdp_invoice.models.res_company.iap_tools.iap_jsonrpc',
                return_value=[{
                    'period_start': '2026-07-01',
                    'late_payment_penalty_rate': 12.4,
                }],
            ) as mocked_iap,
        ):
            second_invoice.action_post()

        mocked_iap.assert_called_once()
        self.assertEqual(
            second_invoice.l10n_fr_pdp_late_payment_penalties_rate,
            12.4,
        )

    def test_invalid_iap_response_keeps_fallback_rate(self):
        self.company._l10n_fr_pdp_set_automatic_late_payment_penalties_rate(
            12.15,
            date(2026, 1, 1),
        )
        invoice = self._create_invoice(invoice_date=date(2026, 7, 15))

        with (
            patch('odoo.fields.Date.today', return_value=date(2026, 7, 15)),
            mute_logger(
                'odoo.addons.l10n_fr_pdp_invoice.models.res_company'
            ),
            patch(
                'odoo.addons.l10n_fr_pdp_invoice.models.res_company.iap_tools.iap_jsonrpc',
                side_effect=ValueError("The response is not valid JSON."),
            ),
        ):
            invoice.action_post()

        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(
            invoice.l10n_fr_pdp_late_payment_penalties_rate,
            12.15,
        )

    def test_iap_is_not_called_before_supported_period(self):
        invoice = self._create_invoice(invoice_date=date(2025, 12, 31))

        with patch(
            'odoo.addons.l10n_fr_pdp_invoice.models.res_company.iap_tools.iap_jsonrpc',
        ) as mocked_iap:
            invoice.action_post()

        mocked_iap.assert_not_called()
        self.assertEqual(
            invoice.l10n_fr_pdp_late_payment_penalties_rate,
            10,
        )

    def test_manual_rate_is_used_before_supported_period(self):
        self._set_manual_rate(self.company, 12.4)
        invoice = self._create_invoice(invoice_date=date(2025, 12, 31))

        with patch(
            'odoo.addons.l10n_fr_pdp_invoice.models.res_company.iap_tools.iap_jsonrpc',
        ) as mocked_iap:
            invoice.action_post()

        mocked_iap.assert_not_called()
        self.assertEqual(
            invoice.l10n_fr_pdp_late_payment_penalties_rate,
            12.4,
        )

    def test_multicompany_uses_the_journal_company_rate(self):
        company_2 = self.company_data_2['company']
        self._set_manual_rate(self.company, 11)
        self._set_manual_rate(company_2, 13)

        invoice = self._create_invoice(
            company_data=self.company_data_2,
            invoice_date=date(2026, 7, 15),
        )
        invoice.action_post()

        self.assertEqual(invoice.company_id, company_2)
        self.assertEqual(
            invoice.l10n_fr_pdp_late_payment_penalties_rate,
            13,
        )

    def test_rate_is_not_applied_outside_e_invoicing_scope(self):
        self.change_company_country(self.company, self.env.ref('base.gf'))
        self._set_manual_rate(self.company, 12.4)
        invoice = self._create_invoice()
        invoice.action_post()

        self.assertFalse(
            self.company.l10n_fr_pdp_late_payment_penalties_applicable
        )
        self.assertEqual(
            invoice.l10n_fr_pdp_late_payment_penalties_rate,
            10,
        )

    def test_rate_is_applied_to_b2bi_invoice(self):
        self.partner_a.country_id = self.env.ref('base.be')
        self._set_manual_rate(self.company, 12.4)
        invoice = self._create_invoice(invoice_date=date(2026, 7, 15))
        invoice.action_post()

        self.assertEqual(
            invoice.l10n_fr_pdp_late_payment_penalties_rate,
            12.4,
        )

    def test_iap_is_not_called_for_vendor_bills_or_receipts(self):
        self.company.l10n_fr_pdp_late_payment_penalties_automatic = True
        moves = (
            self._create_invoice(move_type='in_invoice')
            | self._create_invoice(move_type='out_receipt')
        )

        with patch(
            'odoo.addons.l10n_fr_pdp_invoice.models.res_company.iap_tools.iap_jsonrpc',
        ) as mocked_iap:
            moves.action_post()

        mocked_iap.assert_not_called()
        self.assertRecordValues(moves, [
            {'l10n_fr_pdp_late_payment_penalties_rate': 10},
            {'l10n_fr_pdp_late_payment_penalties_rate': 10},
        ])

    def test_invoice_report_contains_late_payment_penalties(self):
        self._set_manual_rate(self.company, 12.4)
        invoice = self._create_invoice()
        invoice.action_post()

        report_html = self.env['ir.actions.report']._render_qweb_html(
            'account.report_invoice_with_payments',
            invoice.ids,
        )[0].decode()

        self.assertIn("flat-rate fee of €40", report_html)
        self.assertIn("annual rate of 12.40%", report_html)

    def test_draft_invoice_report_does_not_contain_late_payment_penalties(self):
        self._set_manual_rate(self.company, 12.4)
        invoice = self._create_invoice()

        report_html = self.env['ir.actions.report']._render_qweb_html(
            'account.report_invoice_with_payments',
            invoice.ids,
        )[0].decode()

        self.assertNotIn("flat-rate fee of €40", report_html)
        self.assertNotIn("annual rate of", report_html)

    def test_customer_credit_note_uses_late_payment_penalties_rate(self):
        self._set_manual_rate(self.company, 12.4)
        credit_note = self._create_invoice(
            move_type='out_refund',
            invoice_date=date(2026, 7, 15),
        )
        credit_note.action_post()

        self.assertEqual(
            credit_note.l10n_fr_pdp_late_payment_penalties_rate,
            12.4,
        )
