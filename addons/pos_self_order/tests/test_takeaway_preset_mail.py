import odoo.tests
from odoo.addons.mail.tests.common import MailCase
from odoo.addons.pos_self_order.tests.test_self_order_preset import TestSelfOrderPreset


@odoo.tests.tagged('post_install', '-at_install')
class TestTakeawayMail(MailCase, TestSelfOrderPreset):

    def test_preset_takeaway_email_tour(self):
        self.preset_takeaway.mail_template_id = self.env.ref('pos_self_order.takeout_email_template')
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()

        with self.mock_mail_gateway():
            self.start_tour(self_route, "test_preset_takeaway_email_tour")
        self.assertEqual("Public user", self.env["pos.order"].search([], limit=1, order="id desc").floating_order_name)

        # Message is posted and mail is sent on time
        self.assertEqual(len(self._new_mails), 1)
        self.assertEqual(self._new_mails.subject, "Your BarTest receipt")
