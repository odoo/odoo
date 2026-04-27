from freezegun import freeze_time
from unittest import mock

from odoo import Command
from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.iap.tools import iap_tools


@tagged('post_install', '-at_install')
class TestSnailmailAccountFollowup(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['account_followup.followup.line'].search([]).unlink()

        cls.partner_a.write({
            'name': 'Test Partner',
            'email': 'partner_a@mypartners.xyz',
            'street': '270 rte d\'Arlon',
            'city': 'Strassen',
            'zip': '8010',
            'country_id': cls.env.ref('base.lu').id,
        })

        cls.classPatch(cls.env.registry['ir.actions.report'], '_run_wkhtmltopdf', lambda *args, **kwargs: b"0")

    def _mock_generate_report_pdf(self, info_dict):
        function_path = 'odoo.addons.snailmail_account_followup.models.snailmail_letter.SnailmailLetter._generate_report_pdf'

        def _fill_info_dict(self, report):
            info_dict.update({
                'report': report,
                'options': self.env.context.get('followup_options'),
                'letter': self,
            })
            # Return a fake filename and pdf to avoid generating a PDF in a test
            with file_open('base/tests/minimal.pdf', 'rb') as file:
                pdf_bytes = file.read()
            return "filename.pdf", pdf_bytes

        return mock.patch(function_path, _fill_info_dict)

    def _mock_iap_jsonrpc_credit_error(self):
        def mock_credit_error_iap_jsonrpc(*args, **kwargs):
            return {
                'request_code': 200,
                'total_cost': 0,
                'credit_error': True,
                'request': {
                    'documents': [{'sent': False, 'cost': 0, 'error': 'CREDIT_ERROR', 'letter_id': 22}],
                    'options': {'color': True, 'cover': True, 'duplex': False, 'currency_name': 'EUR'}
                }
            }

        return mock.patch.object(iap_tools, 'iap_jsonrpc', side_effect=mock_credit_error_iap_jsonrpc)

    def test_cron_generate_report_pdf(self):
        self.env.company.snailmail_cover = True

        followup_line = self.env['account_followup.followup.line'].create({
            'company_id': self.company_data['company'].id,
            'name': 'First Reminder',
            'delay': 15,
            'send_email': False,
            'send_letter': True,
            'auto_execute': True,
        })

        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'invoice_date_due': '2016-01-01',
            'date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500,
            })]
        }).action_post()

        info_dict = {}
        with freeze_time('2022-01-10'), self._mock_generate_report_pdf(info_dict), self._mock_iap_jsonrpc_credit_error(), mock.patch.object(self.env.cr, 'commit', lambda *args, **kwargs: None):
            self.env.ref('account_followup.ir_cron_auto_post_draft_entry').method_direct_trigger()

        self.assertEqual(info_dict.get('report'), self.env.ref('account_followup.action_report_followup'))
        self.assertTrue(info_dict.get('letter').cover)

        options = info_dict['options']
        expected_options = {'followup_line': followup_line, 'partner_id': self.partner_a.id}
        self.assertEqual({key: options[key] for key in expected_options}, expected_options)

    def test_manual_generate_report_pdf(self):
        self.env.company.snailmail_cover = True

        followup_line = self.env['account_followup.followup.line'].create({
            'company_id': self.company_data['company'].id,
            'name': 'First Reminder',
            'delay': 15,
            'send_email': False,
            'send_letter': True,
            'auto_execute': True,
        })

        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'invoice_date_due': '2016-01-01',
            'date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500,
            })]
        }).action_post()

        wizard = self.env['account_followup.manual_reminder'].with_context(
            active_model='res.partner',
            active_ids=self.partner_a.ids,
        ).create({})
        wizard.write({
            'email': False,
            'sms': False,
            'print': False,
            'snailmail': True,
        })

        info_dict = {}
        with freeze_time('2022-01-10'), self._mock_generate_report_pdf(info_dict), self._mock_iap_jsonrpc_credit_error(), mock.patch.object(self.env.cr, 'commit', lambda *args, **kwargs: None):
            wizard.process_followup()

        self.assertEqual(info_dict.get('report'), self.env.ref('account_followup.action_report_followup'))
        self.assertTrue(info_dict.get('letter').cover)
        options = info_dict.get('options', {})
        expected_options = {
            'followup_line': followup_line,
            'sms': False,
            'email': False,
            'snailmail': True,
            'manual_followup': True,
            'partner_id': self.partner_a.id,
        }
        self.assertEqual({key: options[key] for key in expected_options}, expected_options)
