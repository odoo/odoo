from odoo.addons.sms_twilio.tests.common import MockSmsTwilio
from odoo.tests import tagged, users
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'twilio', 'twilio', 'twilio_manage')
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
            'sms_twilio_to_number': '+32455001122',
        })
        with self.mock_sms_twilio_send():
            notif = wizard.action_send_test()
        self.assertDictEqual(notif, {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Twilio SMS",
                # FIXME: check this
                'message': 'The SMS has been sent from False',
                'type': 'success',
                'sticky': False,
            }
        })
