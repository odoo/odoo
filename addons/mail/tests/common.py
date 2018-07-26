# -*- coding: utf-8 -*-

from openerp.tests import common


class TestMail(common.SavepointCase):

    @classmethod
    def _init_mock_build_email(cls):
        cls._mails_args = []
        cls._mails = []

    def format_and_process(self, template, to='groups@example.com, other@gmail.com', subject='Frogs',
                           extra='', email_from='Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>',
                           cc='', msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>',
                           model=None, target_model='mail.channel', target_field='name'):
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

        def send_email(self, cr, uid, message, *args, **kwargs):
            return message['Message-Id']

        def mail_group_message_get_recipient_values(self, cr, uid, ids, notif_message=None, recipient_ids=None, context=None):
            return self.pool['mail.thread'].message_get_recipient_values(cr, uid, ids, notif_message=notif_message, recipient_ids=recipient_ids, context=context)

        cls.env['ir.mail_server']._patch_method('build_email', build_email)
        cls.env['ir.mail_server']._patch_method('send_email', send_email)
        cls.env['mail.channel']._patch_method('message_get_recipient_values', mail_group_message_get_recipient_values)

        # User groups
        user_group_employee = cls.env.ref('base.group_user')
        user_group_portal = cls.env.ref('base.group_portal')
        user_group_public = cls.env.ref('base.group_public')

        # User Data: employee, noone
        Users = cls.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True})
        cls.user_employee = Users.create({
            'name': 'Ernest Employee',
            'login': 'ernest',
            'alias_name': 'ernest',
            'email': 'e.e@example.com',
            'signature': '--\nErnest',
            'notify_email': 'always',
            'groups_id': [(6, 0, [user_group_employee.id])]})
        cls.user_public = Users.create({
            'name': 'Bert Tartignole',
            'login': 'bert',
            'alias_name': 'bert',
            'email': 'b.t@example.com',
            'signature': 'SignBert',
            'notify_email': 'always',
            'groups_id': [(6, 0, [user_group_public.id])]})
        cls.user_portal = Users.create({
            'name': 'Chell Gladys',
            'login': 'chell',
            'alias_name': 'chell',
            'email': 'chell@gladys.portal',
            'signature': 'SignChell',
            'notify_email': 'always',
            'groups_id': [(6, 0, [user_group_portal.id])]})
        cls.user_admin = cls.env.user

        # Test Data for Partners
        cls.partner_1 = cls.env['res.partner'].create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com',
            'notify_email': 'always'})
        cls.partner_2 = cls.env['res.partner'].create({
            'name': 'Valid Poilvache',
            'email': 'valid.other@gmail.com',
            'notify_email': 'always'})

        # Create test groups without followers and messages by default
        TestMailGroup = cls.env['mail.channel'].with_context({
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'mail_channel_noautofollow': True,
        })
        # Pigs: base group for tests
        cls.group_pigs = TestMailGroup.create({
            'name': 'Pigs',
            'description': 'Fans of Pigs, unite !',
            'public': 'groups',
            'group_public_id': user_group_employee.id,
            'alias_name': 'pigs',
            'alias_contact': 'followers'}
        ).with_context({'mail_create_nosubscribe': False})
        # Jobs: public group
        cls.group_public = TestMailGroup.create({
            'name': 'Jobs',
            'description': 'NotFalse',
            'public': 'public',
            'alias_name': 'public',
            'alias_contact': 'everyone'}
        ).with_context({'mail_create_nosubscribe': False})

        # remove default followers
        cls.env['mail.followers'].search([
            ('res_model', '=', 'mail.channel'),
            ('res_id', 'in', (cls.group_pigs | cls.group_public).ids)]).unlink()

        cls._init_mock_build_email()

    @classmethod
    def tearDownClass(cls):
        # Remove mocks
        cls.env['ir.mail_server']._revert_method('build_email')
        cls.env['ir.mail_server']._revert_method('send_email')
        cls.env['mail.channel']._revert_method('message_get_recipient_values')
        super(TestMail, cls).tearDownClass()
