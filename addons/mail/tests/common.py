# -*- coding: utf-8 -*-

import socket

from openerp.tests import common


class TestMail(common.TransactionCase):

    def _init_mock_build_email(self):
        self._mails_args = []
        self._mails = []

    def format_and_process(self, template, to='groups@example.com, other@gmail.com', subject='Frogs',
                           extra='', email_from='Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>',
                           cc='', msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>',
                           model=None, target_model='mail.group', target_field='name'):
        self.assertFalse(self.env[target_model].search([(target_field, '=', subject)]))
        mail = template.format(to=to, subject=subject, cc=cc, extra=extra, email_from=email_from, msg_id=msg_id)
        self.env['mail.thread'].message_process(model, mail)
        return self.env[target_model].search([(target_field, '=', subject)])

    def setUp(self):
        super(TestMail, self).setUp()
        Test = self

        def build_email(self, *args, **kwargs):
            Test._mails_args.append(args)
            Test._mails.append(kwargs)
            return build_email.origin(self, *args, **kwargs)

        def send_email(self, cr, uid, message, *args, **kwargs):
            return message['Message-Id']

        self.env['ir.mail_server']._patch_method('build_email', build_email)
        self.env['ir.mail_server']._patch_method('send_email', send_email)

        # User groups
        user_group_employee = self.env.ref('base.group_user')
        user_group_portal = self.env.ref('base.group_portal')
        user_group_public = self.env.ref('base.group_public')

        # User Data: employee, noone
        Users = self.env['res.users'].with_context({'no_reset_password': True})
        self.user_employee = Users.create({
            'name': 'Ernest Employee',
            'login': 'ernest',
            'alias_name': 'ernest',
            'email': 'e.e@example.com',
            'signature': '--\nErnest',
            'notify_email': 'always',
            'groups_id': [(6, 0, [user_group_employee.id])]})
        self.user_employee_2 = Users.create({
            'name': 'Raoul Grosbedon',
            'login': 'raoul',
            'alias_name': 'raoul',
            'email': 'r.g@example.com',
            'signature': 'SignRaoul',
            'notify_email': 'always',
            'groups_id': [(6, 0, [user_group_employee.id])]})
        self.user_noone = Users.create({
            'name': 'Noemie NoOne',
            'login': 'noemie',
            'alias_name': 'noemie',
            'email': 'n.n@example.com',
            'signature': '--\nNoemie',
            'notify_email': 'always',
            'groups_id': [(6, 0, [])]})
        self.user_public = Users.create({
            'name': 'Bert Tartignole',
            'login': 'bert',
            'alias_name': 'bert',
            'email': 'b.t@example.com',
            'signature': 'SignBert',
            'notify_email': 'always',
            'groups_id': [(6, 0, [user_group_public.id])]})
        self.user_portal = Users.create({
            'name': 'Chell Gladys',
            'login': 'chell',
            'alias_name': 'chell',
            'email': 'chell@gladys.portal',
            'signature': 'SignChell',
            'notify_email': 'always',
            'groups_id': [(6, 0, [user_group_portal.id])]})
        self.user_admin = self.env.user
        # Update admin
        # Set an email address for the user running the tests, used as Sender for outgoing mails
        self._company_name = 'TestCompany'
        self._admin_name = 'Administrator'
        self._admin_email = 'test@localhost'
        self.user_admin.write({
            'email': self._admin_email,
            'name': self._admin_name,
            'signature': 'SignAdmin',
            'notify_email': 'always',
        })
        self.user_admin.company_id.write({
            'name': self._company_name,
        })

        # Test Data for Partners
        self.partner_1 = self.env['res.partner'].create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com',
            'notify_email': 'always'})
        self.partner_2 = self.env['res.partner'].create({
            'name': 'Valid Poilvache',
            'email': 'valid.other@gmail.com',
            'notify_email': 'always'})

        # Create test groups without followers and messages by default
        TestMailGroup = self.env['mail.group'].with_context({
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True
        })
        # Pigs: base group for tests
        self.group_pigs = TestMailGroup.create({
            'name': 'Pigs',
            'description': 'Fans of Pigs, unite !',
            'public': 'groups',
            'group_public_id': user_group_employee.id,
            'alias_name': 'pigs',
            'alias_contact': 'followers'}
        ).with_context({'mail_create_nosubscribe': False})
        # Jobs: public group
        self.group_public = TestMailGroup.create({
            'name': 'Jobs',
            'description': 'NotFalse',
            'public': 'public',
            'alias_name': 'public',
            'alias_contact': 'everyone'}
        ).with_context({'mail_create_nosubscribe': False})
        # Private: private group
        self.group_private = TestMailGroup.create({
            'name': 'Private',
            'public': 'private'}
        ).with_context({'mail_create_nosubscribe': False})
        # Portal: group-based group using portal group
        self.group_portal = TestMailGroup.create({
            'name': 'PigsPortal',
            'public': 'groups',
            'group_public_id': user_group_portal.id}
        ).with_context({'mail_create_nosubscribe': False})

        # groups@.. will cause the creation of new mail groups
        self.mail_group_model = self.env['ir.model'].search([('model', '=', 'mail.group')], limit=1)
        self.alias = self.env['mail.alias'].create({
            'alias_name': 'groups',
            'alias_user_id': False,
            'alias_model_id': self.mail_group_model.id,
            'alias_contact': 'everyone'})

        # Set a first message on public group to test update and hierarchy
        self.fake_email = self.env['mail.message'].create({
            'model': 'mail.group',
            'res_id': self.group_public.id,
            'subject': 'Public Discussion',
            'message_type': 'email',
            'author_id': self.partner_1.id,
            'message_id': '<123456-openerp-%s-mail.group@%s>' % (self.group_public.id, socket.gethostname()),
        })

        self._init_mock_build_email()

    def tearDown(self):
        # Remove mocks
        self.env['ir.mail_server']._revert_method('build_email')
        self.env['ir.mail_server']._revert_method('send_email')
        super(TestMail, self).tearDown()
