from odoo.addons.sms_twilio.tests.common import MockSmsTwilio
from odoo.tests import tagged, users
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'twilio', 'twilio_manage')
class TestSmsTwilio(MockSmsTwilio, TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_admin = cls.env.ref("base.user_admin")
        cls._setup_sms_twilio(cls.user_admin.company_id)

    @users('admin')
    def test_manage_action_reload_numbers(self):
        wizard = self.env["sms.twilio.account.manage"].create({})
        action = wizard.action_reload_numbers()
        self.assertDictEqual(action, {
            'name': 'Manage Twilio SMS',
            'res_model': wizard._name,
            'res_id': wizard.id,
            'context': self.env.context,
            'type': 'ir.actions.act_window',
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'new',
        })

    @users('admin')
    def test_manage_action_send_test(self):
        wizard = self.env["sms.twilio.account.manage"].create({
            'test_number': '+32455001122',
        })
        for twilio_error, notif_params in zip(
            (False, "wrong_number_format"),
            ({}, {
                'message': 'Wrong Number Format: Wrong Number Format',
                'type': 'danger',
            }),
            strict=True,
        ):
            with self.subTest(twilio_error=twilio_error):
                with self.mock_sms_twilio_send(error_type=twilio_error):
                    notif = wizard.action_send_test()
                params = {
                    'title': "Twilio SMS",
                    'message': 'The SMS has been sent from +32455998877 (Belgium)',
                    'type': 'success',
                    'sticky': False,
                    **notif_params,
                }
                self.assertDictEqual(notif, {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': params,
                })

    @users('admin')
    def test_manage_action_send_test_from_number(self):
        for test_number, exp_from in [
            ('+32455001122', '+32455998877 (Belgium)'),
            ('+15056528788', '+15056998877 (United States)'),
            ('+917891273899', '+32455998877 (Belgium)'),  # no match, takes first one
        ]:
            with self.subTest(test_number=test_number):
                wizard = self.env["sms.twilio.account.manage"].create({
                    'test_number': test_number,
                })
                with self.mock_sms_twilio_send():
                    notif = wizard.action_send_test()
                message = notif["params"]["message"]
                self.assertEqual(message, f'The SMS has been sent from {exp_from}')

        # in case there is no twilio number
        self.env.company.write({"sms_twilio_number_ids": [(5, 0)]})
        wizard = self.env["sms.twilio.account.manage"].create({
            'test_number': test_number,
        })
        with self.mock_sms_twilio_send():
            notif = wizard.action_send_test()
        message = notif["params"]["message"]
        self.assertEqual(message, 'The SMS has been sent from False')
