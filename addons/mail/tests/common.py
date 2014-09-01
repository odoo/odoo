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


class TestMail(common.TransactionCase):

    def _init_mock_build_email(self):
        self._build_email_args_list = []
        self._build_email_kwargs_list = []

    def setUp(self):
        super(TestMail, self).setUp()
        cr, uid = self.cr, self.uid

        # Install mock SMTP gateway
        test = self

        def build_email(self, *args, **kwargs):
            test._build_email_args_list.append(args)
            test._build_email_kwargs_list.append(kwargs)
            return build_email.origin(self, *args, **kwargs)

        def send_email(self, cr, uid, message, *args, **kwargs):
            return message['Message-Id']

        self._init_mock_build_email()
        self.registry('ir.mail_server')._patch_method('build_email', build_email)
        self.registry('ir.mail_server')._patch_method('send_email', send_email)

        # Usefull models
        self.ir_model = self.registry('ir.model')
        self.ir_model_data = self.registry('ir.model.data')
        self.ir_attachment = self.registry('ir.attachment')
        self.mail_alias = self.registry('mail.alias')
        self.mail_thread = self.registry('mail.thread')
        self.mail_group = self.registry('mail.group')
        self.mail_mail = self.registry('mail.mail')
        self.mail_message = self.registry('mail.message')
        self.mail_notification = self.registry('mail.notification')
        self.mail_followers = self.registry('mail.followers')
        self.mail_message_subtype = self.registry('mail.message.subtype')
        self.res_users = self.registry('res.users')
        self.res_partner = self.registry('res.partner')

        # Find Employee group
        group_employee_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'group_user')
        self.group_employee_id = group_employee_ref and group_employee_ref[1] or False

        # Partner Data

        # User Data: employee, noone
        self.user_employee_id = self.res_users.create(cr, uid, {
            'name': 'Ernest Employee',
            'login': 'ernest',
            'alias_name': 'ernest',
            'email': 'e.e@example.com',
            'signature': '--\nErnest',
            'notify_email': 'always',
            'groups_id': [(6, 0, [self.group_employee_id])]
        }, {'no_reset_password': True})
        self.user_noone_id = self.res_users.create(cr, uid, {
            'name': 'Noemie NoOne',
            'login': 'noemie',
            'alias_name': 'noemie',
            'email': 'n.n@example.com',
            'signature': '--\nNoemie',
            'notify_email': 'always',
            'groups_id': [(6, 0, [])]
        }, {'no_reset_password': True})

        # Test users to use through the various tests
        self.res_users.write(cr, uid, [uid], {'name': 'Administrator'})
        self.user_raoul_id = self.res_users.create(cr, uid, {
            'name': 'Raoul Grosbedon',
            'signature': 'SignRaoul',
            'email': 'raoul@raoul.fr',
            'login': 'raoul',
            'alias_name': 'raoul',
            'groups_id': [(6, 0, [self.group_employee_id])]
        })
        self.user_bert_id = self.res_users.create(cr, uid, {
            'name': 'Bert Tartignole',
            'signature': 'SignBert',
            'email': 'bert@bert.fr',
            'login': 'bert',
            'alias_name': 'bert',
            'groups_id': [(6, 0, [])]
        })
        self.user_raoul = self.res_users.browse(cr, uid, self.user_raoul_id)
        self.user_bert = self.res_users.browse(cr, uid, self.user_bert_id)
        self.user_admin = self.res_users.browse(cr, uid, uid)
        self.partner_admin_id = self.user_admin.partner_id.id
        self.partner_raoul_id = self.user_raoul.partner_id.id
        self.partner_bert_id = self.user_bert.partner_id.id

        # Test 'pigs' group to use through the various tests
        self.group_pigs_id = self.mail_group.create(
            cr, uid,
            {'name': 'Pigs', 'description': 'Fans of Pigs, unite !', 'alias_name': 'group+pigs'},
            {'mail_create_nolog': True}
        )
        self.group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)
        # Test mail.group: public to provide access to everyone
        self.group_jobs_id = self.mail_group.create(cr, uid, {'name': 'Jobs', 'public': 'public'})
        # Test mail.group: private to restrict access
        self.group_priv_id = self.mail_group.create(cr, uid, {'name': 'Private', 'public': 'private'})

    def tearDown(self):
        # Remove mocks
        self.registry('ir.mail_server')._revert_method('build_email')
        self.registry('ir.mail_server')._revert_method('send_email')
        super(TestMail, self).tearDown()
