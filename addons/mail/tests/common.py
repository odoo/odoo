# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.tests import common


class TestMail(common.SavepointCase):

    @classmethod
    def _init_mock_build_email(cls):
        cls._build_email_args_list = []
        cls._build_email_kwargs_list = []

    def setUp(self):
        super(TestMail, self).setUp()
        self._build_email_args_list[:] = []
        self._build_email_kwargs_list[:] = []

    @classmethod
    def setUpClass(cls):
        super(TestMail, cls).setUpClass()
        cr, uid = cls.cr, cls.uid

        def build_email(self, *args, **kwargs):
            cls._build_email_args_list.append(args)
            cls._build_email_kwargs_list.append(kwargs)
            return build_email.origin(self, *args, **kwargs)

        def send_email(self, cr, uid, message, *args, **kwargs):
            return message['Message-Id']

        cls._init_mock_build_email()
        cls.registry('ir.mail_server')._patch_method('build_email', build_email)
        cls.registry('ir.mail_server')._patch_method('send_email', send_email)

        # Usefull models
        cls.ir_model = cls.registry('ir.model')
        cls.ir_model_data = cls.registry('ir.model.data')
        cls.ir_attachment = cls.registry('ir.attachment')
        cls.mail_alias = cls.registry('mail.alias')
        cls.mail_thread = cls.registry('mail.thread')
        cls.mail_group = cls.registry('mail.group')
        cls.mail_mail = cls.registry('mail.mail')
        cls.mail_message = cls.registry('mail.message')
        cls.mail_notification = cls.registry('mail.notification')
        cls.mail_followers = cls.registry('mail.followers')
        cls.mail_message_subtype = cls.registry('mail.message.subtype')
        cls.res_users = cls.registry('res.users')
        cls.res_partner = cls.registry('res.partner')

        # Find Employee group
        cls.group_employee_id = cls.env.ref('base.group_user').id or False

        # Partner Data

        # User Data: employee, noone
        cls.user_employee_id = cls.res_users.create(cr, uid, {
            'name': 'Ernest Employee',
            'login': 'ernest',
            'alias_name': 'ernest',
            'email': 'e.e@example.com',
            'signature': '--\nErnest',
            'notify_email': 'always',
            'groups_id': [(6, 0, [cls.group_employee_id])]
        }, {'no_reset_password': True})
        cls.user_noone_id = cls.res_users.create(cr, uid, {
            'name': 'Noemie NoOne',
            'login': 'noemie',
            'alias_name': 'noemie',
            'email': 'n.n@example.com',
            'signature': '--\nNoemie',
            'notify_email': 'always',
            'groups_id': [(6, 0, [])]
        }, {'no_reset_password': True})

        # Test users to use through the various tests
        cls.res_users.write(cr, uid, uid, {'name': 'Administrator'})
        cls.user_raoul_id = cls.res_users.create(cr, uid, {
            'name': 'Raoul Grosbedon',
            'signature': 'SignRaoul',
            'email': 'raoul@raoul.fr',
            'login': 'raoul',
            'alias_name': 'raoul',
            'groups_id': [(6, 0, [cls.group_employee_id])]
        }, {'no_reset_password': True})
        cls.user_bert_id = cls.res_users.create(cr, uid, {
            'name': 'Bert Tartignole',
            'signature': 'SignBert',
            'email': 'bert@bert.fr',
            'login': 'bert',
            'alias_name': 'bert',
            'groups_id': [(6, 0, [])]
        }, {'no_reset_password': True})
        cls.user_raoul = cls.res_users.browse(cr, uid, cls.user_raoul_id)
        cls.user_bert = cls.res_users.browse(cr, uid, cls.user_bert_id)
        cls.user_admin = cls.res_users.browse(cr, uid, uid)
        cls.partner_admin_id = cls.user_admin.partner_id.id
        cls.partner_raoul_id = cls.user_raoul.partner_id.id
        cls.partner_bert_id = cls.user_bert.partner_id.id

        # Test 'pigs' group to use through the various tests
        cls.group_pigs_id = cls.mail_group.create(
            cr, uid,
            {'name': 'Pigs', 'description': 'Fans of Pigs, unite !', 'alias_name': 'group+pigs'},
            {'mail_create_nolog': True}
        )
        cls.group_pigs = cls.mail_group.browse(cr, uid, cls.group_pigs_id)
        # Test mail.group: public to provide access to everyone
        cls.group_jobs_id = cls.mail_group.create(cr, uid, {'name': 'Jobs', 'public': 'public'})
        # Test mail.group: private to restrict access
        cls.group_priv_id = cls.mail_group.create(cr, uid, {'name': 'Private', 'public': 'private'})

    @classmethod
    def tearDownClass(cls):
        # Remove mocks
        cls.registry('ir.mail_server')._revert_method('build_email')
        cls.registry('ir.mail_server')._revert_method('send_email')
        super(TestMail, cls).tearDownClass()
