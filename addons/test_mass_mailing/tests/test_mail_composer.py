
from odoo.addons.test_mail.tests.test_mail_composer import TestMailComposer

from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import mute_logger


@tagged('mail_composer')
class TestMailComposerMassMailing(TestMailComposer):
    """Test internals of composer when sending mass mailing."""

    @classmethod
    def setUpClass(cls):
        super(TestMailComposerMassMailing, cls).setUpClass()
        # ensure employee can create partners, necessary for templates
        # as well as mailings
        cls.user_employee.write({
            'groups_id': [(4, cls.env.ref('base.group_partner_manager').id), (4, cls.env.ref('mass_mailing.group_mass_mailing_user').id)],
        })

    @users('employee')
    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_composer_mass_mailing_auto_delete_message(self):
        """Check that setting auto_delete_keep_log to False effectively removes the messages."""
        composer = self.env['mail.compose.message'].with_context(
            self._get_web_context(self.test_records, add_web=True),
        ).create({
            'body': '<p>Test Body</p>',
            'subject': 'Test Mailing Subject',
            'mass_mailing_name': 'Test Mailing',
            'partner_ids': [(4, self.partner_1.id), (4, self.partner_2.id)]
        })

        composer.auto_delete_keep_log = False
        with self.mock_mail_gateway(mail_unlink_sent=True), self.mock_mail_app():
            composer._action_send_mail()

        record_mails = self._new_mails.exists().filtered(lambda mail: mail.mail_message_id.model == self.test_records._name)
        record_messages = self._new_msgs.exists().filtered(lambda msg: msg.model == self.test_records._name)
        record_traces = self.env['mailing.trace'].search([('mail_mail_id', 'in', self._new_mails.ids)])

        self.assertEqual(len(self._new_mails), 2, 'Should have created 1 mail.mail per record')
        self.assertFalse(record_mails, 'Should have deleted emails')
        self.assertEqual(len(self._new_msgs), 3, 'Should have created 1 mail.message per target record + 1 to log the mailing')
        self.assertFalse(record_messages, 'Should have deleted mail.message records for target records')
        self.assertFalse(self._new_notifs, 'Should not have created any mail.notification')
        self.assertFalse(record_traces, 'Should have deleted mailing.trace records')

    @users('employee')
    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_composer_mass_mailing_no_template_auto_delete(self):
        """ Check that mails sent as part of archived mailings are not auto_deleted regardless of template
            (allows message-mailing link)
        """
        self.template.auto_delete = True
        composer = self.env['mail.compose.message'].with_context(
            self._get_web_context(self.test_records, add_web=True,
                                  default_template_id=self.template.id),
        ).create({
            'body': '<p>Test Body</p>',
            'subject': 'Test Mailing Subject',
            'mass_mailing_name': 'Test Mailing',
            'partner_ids': [(4, self.partner_1.id), (4, self.partner_2.id)]
        })
        with self.mock_mail_gateway(mail_unlink_sent=False), self.mock_mail_app():
            composer._action_send_mail()

        self.assertEqual(len(self._new_mails.exists().filtered(lambda mail: not mail.auto_delete)), 2,
                         'Mails should not be marked auto_delete when sent from archived mailing')
