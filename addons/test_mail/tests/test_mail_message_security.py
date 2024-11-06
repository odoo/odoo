import base64
from markupsafe import Markup
from unittest.mock import patch

from odoo.addons.mail.tests.common import mail_new_test_user, MailCommon
from odoo.addons.test_mail.models.test_mail_models import MailTestSimple
from odoo.exceptions import AccessError
from odoo.tools import mute_logger
from odoo.tests import tagged


@tagged('mail_message', 'security', 'post_install', '-at_install')
class TestMessageAccess(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMessageAccess, cls).setUpClass()

        cls.user_employee_1 = mail_new_test_user(cls.env, login='tao', groups='base.group_user', name='Tao Lee')
        cls.user_public = mail_new_test_user(cls.env, login='bert', groups='base.group_public', name='Bert Tartignole')
        cls.user_portal = mail_new_test_user(cls.env, login='chell', groups='base.group_portal', name='Chell Gladys')

        cls.group_restricted_channel = cls.env['discuss.channel'].channel_create(name='Channel for Groups', group_id=cls.env.ref('base.group_user').id)
        cls.public_channel = cls.env['discuss.channel'].channel_create(name='Public Channel', group_id=None)
        cls.private_group = cls.env['discuss.channel'].create_group(partners_to=cls.user_employee_1.partner_id.ids, name="Group")
        cls.message = cls.env['mail.message'].create({
            'body': 'My Body',
            'model': 'discuss.channel',
            'res_id': cls.private_group.id,
        })

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_message_access_search(self):
        # Data: various author_ids, partner_ids, documents
        msg1 = self.env['mail.message'].create({
            'subject': '_ZTest', 'body': 'A', 'subtype_id': self.ref('mail.mt_comment')})
        msg2 = self.env['mail.message'].create({
            'subject': '_ZTest', 'body': 'A+B', 'subtype_id': self.ref('mail.mt_comment'),
            'partner_ids': [(6, 0, [self.user_public.partner_id.id])]})
        msg3 = self.env['mail.message'].create({
            'subject': '_ZTest', 'body': 'A Pigs', 'subtype_id': False,
            'model': 'discuss.channel', 'res_id': self.group_restricted_channel.id})
        msg4 = self.env['mail.message'].create({
            'subject': '_ZTest', 'body': 'A+P Pigs', 'subtype_id': self.ref('mail.mt_comment'),
            'model': 'discuss.channel', 'res_id': self.group_restricted_channel.id,
            'partner_ids': [(6, 0, [self.user_public.partner_id.id])]})
        msg5 = self.env['mail.message'].create({
            'subject': '_ZTest', 'body': 'A+E Pigs', 'subtype_id': self.ref('mail.mt_comment'),
            'model': 'discuss.channel', 'res_id': self.group_restricted_channel.id,
            'partner_ids': [(6, 0, [self.user_employee.partner_id.id])]})
        msg6 = self.env['mail.message'].create({
            'subject': '_ZTest', 'body': 'A Birds', 'subtype_id': self.ref('mail.mt_comment'),
            'model': 'discuss.channel', 'res_id': self.private_group.id})
        msg7 = self.env['mail.message'].with_user(self.user_employee).create({
            'subject': '_ZTest', 'body': 'B', 'subtype_id': self.ref('mail.mt_comment')})
        msg8 = self.env['mail.message'].with_user(self.user_employee).create({
            'subject': '_ZTest', 'body': 'B+E', 'subtype_id': self.ref('mail.mt_comment'),
            'partner_ids': [(6, 0, [self.user_employee.partner_id.id])]})

        # Test: Public: 2 messages (recipient)
        messages = self.env['mail.message'].with_user(self.user_public).search([('subject', 'like', '_ZTest')])
        self.assertEqual(messages, msg2 | msg4)

        # Test: Employee: 3 messages on Channel Employee can read (employee can read group with default values)
        messages = self.env['mail.message'].with_user(self.user_employee).search([('subject', 'like', '_ZTest'), ('body', 'ilike', 'A')])
        self.assertEqual(messages, msg3 | msg4 | msg5)

        # Test: Employee: 3 messages on Channel Employee can read (employee can read group with default values), 0 on Birds (private group) + 2 messages as author
        messages = self.env['mail.message'].with_user(self.user_employee).search([('subject', 'like', '_ZTest')])
        self.assertEqual(messages, msg3 | msg4 | msg5 | msg7 | msg8)

        # Test: Admin: all messages
        messages = self.env['mail.message'].search([('subject', 'like', '_ZTest')])
        self.assertEqual(messages, msg1 | msg2 | msg3 | msg4 | msg5 | msg6 | msg7 | msg8)

        # Test: Portal: 0 (no access to groups, not recipient)
        messages = self.env['mail.message'].with_user(self.user_portal).search([('subject', 'like', '_ZTest')])
        self.assertFalse(messages)

        # Test: Portal: 2 messages (public channel)
        self.group_restricted_channel.write({'group_public_id': False})
        messages = self.env['mail.message'].with_user(self.user_portal).search([('subject', 'like', '_ZTest')])
        self.assertEqual(messages, msg4 | msg5)

    # --------------------------------------------------
    # READ
    # --------------------------------------------------

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_mail_message_access_read_crash(self):
        with self.assertRaises(AccessError):
            self.message.with_user(self.user_employee).read()

    @mute_logger('odoo.models')
    def test_mail_message_access_read_crash_portal(self):
        with self.assertRaises(AccessError):
            self.message.with_user(self.user_portal).read(['body', 'message_type', 'subtype_id'])

    def test_mail_message_access_read_ok_portal(self):
        self.message.write({'subtype_id': self.ref('mail.mt_comment'), 'res_id': self.public_channel.id})
        self.message.with_user(self.user_portal).read(['body', 'message_type', 'subtype_id'])

    def test_mail_message_access_read_notification(self):
        attachment = self.env['ir.attachment'].create({
            'datas': base64.b64encode(b'My attachment'),
            'name': 'doc.txt',
            'res_model': self.message._name,
            'res_id': self.message.id})
        # attach the attachment to the message
        self.message.write({'attachment_ids': [(4, attachment.id)]})
        self.message.write({'partner_ids': [(4, self.user_employee.partner_id.id)]})
        self.message.with_user(self.user_employee).read()
        # Test: Employee has access to attachment, ok because they can read message
        attachment.with_user(self.user_employee).read(['name', 'datas'])

    def test_mail_message_access_read_author(self):
        self.message.write({'author_id': self.user_employee.partner_id.id})
        self.message.with_user(self.user_employee).read()

    def test_mail_message_access_read_doc(self):
        self.message.write({'model': 'discuss.channel', 'res_id': self.public_channel.id})
        # Test: Employee reads the message, ok because linked to a doc they are allowed to read
        self.message.with_user(self.user_employee).read()

    # --------------------------------------------------
    # CREATE
    # --------------------------------------------------

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_mail_message_access_create_crash_public(self):
        # Public creates a message on Channel for groups -> ko, no enter rights
        with self.assertRaises(AccessError):
            self.env['mail.message'].with_user(self.user_public).create({'model': 'discuss.channel', 'res_id': self.group_restricted_channel.id, 'body': 'Test'})

        # Public create a message on Public Channel -> ko, no creation rights
        with self.assertRaises(AccessError):
            self.env['mail.message'].with_user(self.user_public).create({'model': 'discuss.channel', 'res_id': self.public_channel.id, 'body': 'Test'})

    @mute_logger('odoo.models')
    def test_mail_message_access_create_crash(self):
        # Do: Employee create a private message -> ko, no creation rights
        with self.assertRaises(AccessError):
            self.env['mail.message'].with_user(self.user_employee).create({'model': 'discuss.channel', 'res_id': self.private_group.id, 'body': 'Test'})

    @mute_logger('odoo.models')
    def test_mail_message_access_create_doc(self):
        Message = self.env['mail.message'].with_user(self.user_employee)
        # Do: Employee creates a message on Public Channel -> ok, write access to the related document
        Message.create({'model': 'discuss.channel', 'res_id': self.public_channel.id, 'body': 'Test'})
        # Do: Employee creates a message on Group -> ko, no write access to the related document
        with self.assertRaises(AccessError):
            Message.create({'model': 'discuss.channel', 'res_id': self.private_group.id, 'body': 'Test'})

    def test_mail_message_access_create_private(self):
        self.env['mail.message'].with_user(self.user_employee).create({'body': 'Test'})

    def test_mail_message_access_create_reply(self):
        # TDE FIXME: should it really work ? not sure - catchall makes crash (aka, post will crash also)
        self.message.write({'partner_ids': [(4, self.user_employee.partner_id.id)]})
        self.env['mail.message'].with_user(self.user_employee).create({'model': 'discuss.channel', 'res_id': self.private_group.id, 'body': 'Test', 'parent_id': self.message.id})

    def test_mail_message_access_create_wo_parent_access(self):
        """ Purpose is to test posting a message on a record whose first message / parent
        is not accessible by current user. """
        test_record = self.env['mail.test.simple'].with_context(self._test_context).create({'name': 'Test', 'email_from': 'ignasse@example.com'})
        partner_1 = self.env['res.partner'].create({
            'name': 'Jitendra Prajapati (jpr-odoo)',
            'email': 'jpr@odoo.com',
        })
        test_record.message_subscribe((partner_1 | self.user_admin.partner_id).ids)

        message = test_record.message_post(
            body=Markup('<p>This is First Message</p>'), subject='Subject',
            message_type='comment', subtype_xmlid='mail.mt_note')
        # portal user have no rights to read the message
        with self.assertRaises(AccessError):
            message.with_user(self.user_portal).read(['subject, body'])

        with patch.object(MailTestSimple, 'check_access_rights', return_value=True):
            with self.assertRaises(AccessError):
                message.with_user(self.user_portal).read(['subject, body'])

            # parent message is accessible to references notification mail values
            # for _notify method and portal user have no rights to send the message for this model
            new_msg = test_record.with_user(self.user_portal).message_post(
                body='<p>This is Second Message</p>',
                subject='Subject',
                parent_id=message.id,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                mail_auto_delete=False)

        new_mail = self.env['mail.mail'].sudo().search([
            ('mail_message_id', '=', new_msg.id),
            ('references', '=', f'{message.message_id} {new_msg.message_id}'),
        ])

        self.assertTrue(new_mail)
        self.assertEqual(new_msg.parent_id, message)
