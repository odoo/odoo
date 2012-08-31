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
import tools

class test_message_compose(common.TransactionCase):

    def _mock_smtp_gateway(self, *args, **kwargs):
        return True

    def _mock_build_email(self, *args, **kwargs):
        self._build_email_args = args
        self._build_email_kwargs = kwargs
        return self.build_email_real(*args, **kwargs)

    def setUp(self):
        super(test_message_compose, self).setUp()
        self.mail_group = self.registry('mail.group')
        self.mail_mail = self.registry('mail.mail')
        self.mail_message = self.registry('mail.message')
        self.res_users = self.registry('res.users')
        self.res_partner = self.registry('res.partner')

        # Install mock SMTP gateway
        self.build_email_real = self.registry('ir.mail_server').build_email
        self.registry('ir.mail_server').build_email = self._mock_build_email
        self.registry('ir.mail_server').send_email = self._mock_smtp_gateway
        
        # create a 'pigs' group that will be used through the various tests
        self.group_pigs_id = self.mail_group.create(self.cr, self.uid,
            {'name': 'Pigs', 'description': 'Fans of Pigs, unite !'})

    def test_00_message_compose_wizard(self):
        """ Tests designed for the mail.compose.message wizard updated by email_template. """
        cr, uid = self.cr, self.uid
        mail_compose = self.registry('mail.compose.message')
        self.res_users.write(cr, uid, [uid], {'signature': 'Admin', 'email': 'a@a'})
        user_admin = self.res_users.browse(cr, uid, uid)
        group_model_id = self.registry('ir.model').search(cr, uid, [('model', '=', 'mail.group')])[0]
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)

        # Create template on mail.group
        email_template = self.registry('email.template')
        email_template_id = email_template.create(cr, uid, {'model_id': group_model_id,
            'name': 'Pigs Template', 'subject': '${record.name}',
            'body_html': '${object.description}', 'user_signature': True,
            'email_to': 'b@b c@c', 'email_cc': 'd@d'})
        # import pdb
        # pdb.set_trace()

        # Mail data
        _subject = 'Pigs'
        _body_text = 'Pigs rules'

        # 3 - Create in mass_mail composition mode that should work with or without email_template installed
        compose_id = mail_compose.create(cr, uid,
            {'subject': _subject, 'body': _body_text},
            {'default_composition_mode': 'mass_mail', 'default_model': 'mail.group',
                'default_res_id': -1, 'default_use_template': True,
                'active_ids': [self.group_pigs_id], 'default_template_id': email_template_id})
        compose = mail_compose.browse(cr, uid, compose_id)
        # print compose.subject
        

        # Try the 'onchange_template_id'
        values = mail_compose.onchange_template_id(cr, uid, [], compose.use_template, compose.template_id, compose.composition_mode, compose.res_id)
        # print values
        values = mail_compose.onchange_use_template(cr, uid, [], not compose.use_template, compose.template_id, compose.composition_mode, compose.res_id)
        # print values

        compose.refresh()


        # # Post the comment, get created message
        # mail_compose.send_mail(cr, uid, [compose_id], {'default_res_id': -1, 'active_ids': [self.group_pigs_id]})
        # group_pigs.refresh()
        # msg = group_pigs.message_ids[0]

        # # Test: last message on Pigs = last created message
        # test_msg = self.mail_message.browse(cr, uid, self.mail_message.search(cr, uid, [], limit=1))[0]
        # self.assertEqual(msg.id, test_msg.id, 'Pigs did not receive its mass mailing message')
        # # Test: mail.message: subject, body
        # self.assertEqual(msg.subject, _subject, 'mail.message subject is incorrect')
        # self.assertEqual(msg.body, group_pigs.description, 'mail.message body is incorrect')