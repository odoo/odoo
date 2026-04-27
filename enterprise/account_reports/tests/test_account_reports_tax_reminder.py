# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from unittest.mock import patch

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged
from odoo import fields


@tagged('post_install', '-at_install')
class TestAccountReportsTaxReminder(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env.ref('account.generic_tax_report')
        cls.pay_activity_id = cls.env.ref('account_reports.mail_activity_type_tax_report_to_pay').id
        cls.options = cls._generate_options(cls.report, '2024-08-01', '2024-08-31')
        action = cls.env['account.tax.report.handler'].with_context({'override_tax_closing_warning': True}).action_periodic_vat_entries(cls.options)
        cls.tax_return_move = cls.env['account.move'].browse(action['res_id'])

    def test_posting_adds_an_activity(self):
        """Posting the tax report move should be adding the proper tax to be sent activity"""
        act_type_tax_to_pay = self.env.ref('account_reports.mail_activity_type_tax_report_to_pay')
        act_type_report_to_send = self.env.ref('account_reports.mail_activity_type_tax_report_to_be_sent')
        all_report_activity_type = act_type_report_to_send + act_type_tax_to_pay

        self.tax_return_move.refresh_tax_entry()
        self.assertEqual(self.tax_return_move.state, 'draft')
        self.assertFalse(all_report_activity_type & self.tax_return_move.activity_ids.activity_type_id,
                         "There shouldn't be any of the closing activity on the closing move yet")

        self.init_invoice(
            'out_invoice',
            partner=self.partner_a,
            invoice_date=self.tax_return_move.date + relativedelta(days=-1),
            post=True,
            amounts=[200],
            taxes=self.tax_sale_a
        )
        self.tax_return_move.refresh_tax_entry()
        # Posting the tax entry should post a mail activity of this type
        with patch.object(self.env.registry[self.report._name], 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: {'file_name': 'dummy', 'file_content': b'', 'file_type': 'pdf'}):
            self.tax_return_move.action_post()

        self.assertEqual(self.tax_return_move.state, 'posted')
        self.assertEqual(self.tax_return_move._get_tax_to_pay_on_closing(), 30.0)
        self.assertRecordValues(self.tax_return_move.activity_ids, [{
            'activity_type_id': act_type_report_to_send.id,
            'summary': f'Send tax report: {self.tax_return_move.date.strftime("%B %Y")}',
            'date_deadline': fields.Date.context_today(self.env.user),
        }, {
            'activity_type_id': act_type_tax_to_pay.id,
            'summary': f'Pay tax: {self.tax_return_move.date.strftime("%B %Y")}',
            'date_deadline': fields.Date.context_today(self.env.user),
        }])

        # Posting tax return again should not create another activity
        before = len(self.tax_return_move.activity_ids)
        self.tax_return_move.button_draft()
        self.tax_return_move.refresh_tax_entry()
        with patch.object(self.env.registry[self.report._name], 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: {'file_name': 'dummy', 'file_content': b'', 'file_type': 'pdf'}):
            self.tax_return_move.action_post()
        after = len(self.tax_return_move.activity_ids)
        self.assertEqual(before, after, "resetting to draft and posting again shouldn't create a new activity")

        # 0.0 tax returns create a send tax report activity but shouldn't trigger the payment activity
        options = self._generate_options(self.report, '2024-09-01', '2024-09-30')
        action = self.env['account.tax.report.handler'].with_context({'override_tax_closing_warning': True}).action_periodic_vat_entries(options)
        next_tax_return_move = self.env['account.move'].browse(action['res_id'])
        next_tax_return_move.refresh_tax_entry()
        with patch.object(self.env.registry[self.report._name], 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: {'file_name': 'dummy', 'file_content': b'', 'file_type': 'pdf'}):
            next_tax_return_move.action_post()
        self.assertEqual(next_tax_return_move._get_tax_to_pay_on_closing(), 0.0)

        self.assertRecordValues(next_tax_return_move.activity_ids, [{
            'activity_type_id': act_type_report_to_send.id,
            'summary': f'Send tax report: {next_tax_return_move.date.strftime("%B %Y")}',
            'date_deadline': fields.Date.context_today(self.env.user),
        }])

        next_tax_return_move.activity_ids.action_done()
        self.assertFalse(all_report_activity_type & next_tax_return_move.activity_ids.activity_type_id,
                         "marking the sending as done shouldn't trigger any other similar activity")

    def test_posting_without_amount_and_no_pay_activity(self):
        """
        0.0 closing does not create a pay activity
        """
        with patch.object(self.env.registry[self.report._name], 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: {'file_name': 'dummy', 'file_content': b'', 'file_type': 'pdf'}):
            self.tax_return_move.action_post()
        self.assertEqual(self.tax_return_move._get_tax_to_pay_on_closing(), 0.0)
        self.assertFalse(self.env['mail.activity'].search([
            ('res_id', '=', self.tax_return_move.id),
            ('activity_type_id', '=', self.pay_activity_id),
        ]))

    def test_tax_closing_activity_reminder_duplication(self):
        """
        Test triggering multiple times the closing action don't recreate an activity for the closing move even if the moves are cancelled
        """
        # Cancel the main one to be able to create new ones for this closing
        self.tax_return_move.button_cancel()
        for i in range(0, 2):
            action = self.env['account.tax.report.handler'].with_context({'override_tax_closing_warning': True}).action_periodic_vat_entries(self.options)
            move = self.env['account.move'].browse(action['res_id'])
            move.button_cancel()
        activity = self.env.company._get_tax_closing_reminder_activity(self.report.id, fields.Date.from_string(self.options['date']['date_to']))
        self.assertEqual(len(activity), 1, "You cannot have duplicate tax closing reminder for the same report on the same period")

    def test_tax_closing_activity_reminder_post(self):
        """
        Test that when posting a closing move, the next one is created
        """
        activity = self.env.company._get_tax_closing_reminder_activity(self.report.id, fields.Date.from_string(self.options['date']['date_to']))
        self.assertTrue(activity, "There has been no activity created for the current period closing")
        with patch.object(self.env.registry[self.report._name], 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: {'file_name': 'dummy', 'file_content': b'', 'file_type': 'pdf'}):
            self.tax_return_move.action_post()

        _dummy, period_end = self.env.company._get_tax_closing_period_boundaries(fields.Date.from_string(self.options['date']['date_to']) + relativedelta(days=1), self.report)
        activity = self.env.company._get_tax_closing_reminder_activity(self.report.id, period_end)
        self.assertTrue(activity, "There has been no activity created for the next period closing")

    def test_tax_closing_activity_reminder_reset_on_periodicity_change(self):
        """
        Test that when changing the periodicity, the old activities got replaced by new ones
        """
        old_activity = self.env.company._get_tax_closing_reminder_activity(self.report.id, fields.Date.from_string(self.options['date']['date_to']))

        self.env.company.account_tax_periodicity = 'year'
        _dummy, period_end = self.env.company._get_tax_closing_period_boundaries(fields.Date.today(), self.report)
        new_activity = self.env.company._get_tax_closing_reminder_activity(self.report.id, period_end)

        self.assertNotEqual(old_activity.id, new_activity.id)
        self.assertEqual(fields.Date.from_string(new_activity.account_tax_closing_params['tax_closing_end_date']), period_end)
