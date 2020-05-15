# -*- coding: utf-8 -*-

from odoo import api
from odoo.tests import common


class BaseFunctionalTest(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(BaseFunctionalTest, cls).setUpClass()

        # User groups
        user_group_employee = cls.env.ref('base.group_user')
        user_group_portal = cls.env.ref('base.group_portal')
        user_group_public = cls.env.ref('base.group_public')

        # User Data: employee, noone
        Users = cls.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True})
        cls.user_employee = Users.create({
            'name': 'Ernest Employee',
            'login': 'ernest',
            'email': 'e.e@example.com',
            'signature': '--\nErnest',
            'notification_type': 'email',
            'groups_id': [(6, 0, [user_group_employee.id])]})
        cls.user_public = Users.create({
            'name': 'Bert Tartignole',
            'login': 'bert',
            'email': 'b.t@example.com',
            'signature': 'SignBert',
            'notification_type': 'email',
            'groups_id': [(6, 0, [user_group_public.id])]})
        cls.user_portal = Users.create({
            'name': 'Chell Gladys',
            'login': 'chell',
            'email': 'chell@gladys.portal',
            'signature': 'SignChell',
            'notification_type': 'email',
            'groups_id': [(6, 0, [user_group_portal.id])]})
        cls.user_admin = cls.env.user

        # Listener channel
        cls.channel_listen = cls.env['mail.channel'].with_context({
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True
        }).create({'name': 'Listener'})


class TestMail(BaseFunctionalTest):

    @classmethod
    def _init_mock_build_email(cls):
        cls._mails_args = []
        cls._mails = []

    def format_and_process(self, template, to='groups@example.com, other@gmail.com', subject='Frogs',
                           extra='', email_from='Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>',
                           cc='', msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>',
                           model=None, target_model='mail.test', target_field='name'):
        self.assertFalse(self.env[target_model].search([(target_field, '=', subject)]))
        mail = template.format(to=to, subject=subject, cc=cc, extra=extra, email_from=email_from, msg_id=msg_id)
        self.env['mail.thread'].with_context(mail_channel_noautofollow=True).message_process(model, mail)
        return self.env[target_model].search([(target_field, '=', subject)])

    def setUp(self):
        super(TestMail, self).setUp()
        self._mails_args[:] = []
        self._mails[:] = []

    @classmethod
    def setUpClass(cls):
        super(TestMail, cls).setUpClass()

        def build_email(self, *args, **kwargs):
            cls._mails_args.append(args)
            cls._mails.append(kwargs)
            return build_email.origin(self, *args, **kwargs)

        @api.model
        def send_email(self, message, *args, **kwargs):
            return message['Message-Id']

        cls.env['ir.mail_server']._patch_method('build_email', build_email)
        cls.env['ir.mail_server']._patch_method('send_email', send_email)

        # Test Data for Partners
        cls.partner_1 = cls.env['res.partner'].create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com'})
        cls.partner_2 = cls.env['res.partner'].create({
            'name': 'Valid Poilvache',
            'email': 'valid.other@gmail.com'})

        TestModel = cls.env['mail.test'].with_context({
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
        })
        cls.test_pigs = TestModel.create({
            'name': 'Pigs',
            'description': 'Fans of Pigs, unite !',
            'alias_name': 'pigs',
            'alias_contact': 'followers',
        })
        cls.test_public = TestModel.create({
            'name': 'Public',
            'description': 'NotFalse',
            'alias_name': 'public',
            'alias_contact': 'everyone'
        })

        cls.env['mail.followers'].search([
            ('res_model', '=', 'mail.test'),
            ('res_id', 'in', (cls.test_public | cls.test_pigs).ids)]).unlink()

        cls._init_mock_build_email()

    @classmethod
    def tearDownClass(cls):
        # Remove mocks
        cls.env['ir.mail_server']._revert_method('build_email')
        cls.env['ir.mail_server']._revert_method('send_email')
        super(TestMail, cls).tearDownClass()

    def gateway_reply_wrecord(self, template, record, use_in_reply_to=True):
        """ Simulate a reply through the mail gateway. Usage: giving a record,
        find an email sent to him and use its message-ID to simulate a reply.

        Some noise is added in References just to test some robustness. """
        email = self._find_sent_email_wrecord(record)

        if use_in_reply_to:
            extra = 'In-Reply-To:\r\n\t%s\n' % email['message_id']
        else:
            disturbing_other_msg_id = '<123456.654321@another.host.com>'
            extra = 'References:\r\n\t%s\n\r%s' % (email['message_id'], disturbing_other_msg_id)

        return self.format_and_process(
            template, email_from=email['email_to'][0], to=email['reply_to'],
            subject='Re: %s' % email['subject'],
            extra=extra,
            msg_id='<123456.%s.%d@test.example.com>' % (record._name, record.id),
            target_model=record._name,
            target_field=record._rec_name,
        )

    def _find_sent_email_wrecord(self, record):
        """ Helper to find in outgoing emails (see build_email) an email linked to
        a given record. It has been introduced with a fix for mass mailing and is
        not meant to be used widely, proper tools are available in later versions. """
        for mail in self._mails:
            if mail['object_id'] == '%d-%s' % (record.id, record._name):
                break
        else:
            raise AssertionError('Sent email not found for record %s' % record)
        return mail
