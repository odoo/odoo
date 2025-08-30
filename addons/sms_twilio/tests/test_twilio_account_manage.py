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
                'message': 'sms_number_format: None',
                'type': 'danger',
            }),
            strict=True,
        ):
            with self.subTest(twilio_error=twilio_error):
                with self.mock_sms_twilio_send(mock_error_type=twilio_error):
                    notif = wizard.action_send_test()
                params = {
                    'title': "Twilio SMS",
                    # FIXME: check this
                    'message': 'The SMS has been sent from False',
                    'type': 'success',
                    'sticky': False,
                    **notif_params,
                }
                self.assertDictEqual(notif, {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': params,
                })
