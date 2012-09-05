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
        self.res_users.write(cr, uid, [uid], {'signature': 'Admin', 'email': 'a@a.a'})
        user_admin = self.res_users.browse(cr, uid, uid)
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)
        group_bird_id = self.mail_group.create(cr, uid, {'name': 'Bird', 'description': 'I am angry !'})
        group_bird = self.mail_group.browse(cr, uid, group_bird_id)

        # Create template on mail.group
        group_model_id = self.registry('ir.model').search(cr, uid, [('model', '=', 'mail.group')])[0]
        email_template = self.registry('email.template')
        email_template_id = email_template.create(cr, uid, {'model_id': group_model_id,
            'name': 'Pigs Template', 'subject': '${object.name}',
            'body_html': '${object.description}', 'user_signature': True,
            'email_to': 'b@b.b c@c.c', 'email_cc': 'd@d.d'})

        # Mail data
        _subject1 = 'Pigs'
        _subject2 = 'Bird'
        _body_text1 = 'Pigs rules'
        _body_text_html1 = 'Fans of Pigs, unite !\n<pre>Admin</pre>\n'
        _body_text2 = 'I am angry !'
        _body_text_html2 = 'I am angry !<pre>Admin</pre>'

        # CASE1: create in comment
        compose_id = mail_compose.create(cr, uid,
            {'subject': 'Forget me subject', 'body': 'Dummy body'},
            {'default_composition_mode': 'comment', 'default_model': 'mail.group',
                'default_res_id': self.group_pigs_id, 'default_use_template': True,
                'active_ids': [self.group_pigs_id, group_bird_id] })
        compose = mail_compose.browse(cr, uid, compose_id)

        # Perform 'onchange_template_id' with 'use_template' set
        values = mail_compose.onchange_template_id(cr, uid, [], compose.use_template, email_template_id, compose.composition_mode, compose.model, compose.res_id)
        compose.write(values.get('value', {}), {'default_composition_mode': 'comment', 'default_model': 'mail.group'})
        compose.refresh()
        message_pids = [partner.id for partner in compose.partner_ids]
        partner_ids = self.res_partner.search(cr, uid, [('email', 'in', ['b@b.b', 'c@c.c', 'd@d.d'])])
        partners = self.res_partner.browse(cr, uid, partner_ids)
        # Test: subject, body, partner_ids
        self.assertEqual(compose.subject, _subject1, 'mail.compose.message subject incorrect')
        self.assertEqual(compose.body, _body_text_html1, 'mail.compose.message body incorrect')
        self.assertEqual(set(message_pids), set(partner_ids), 'mail.compose.message partner_ids incorrect')

        # Perform 'onchange_use_template': use_template is not set anymore
        values = mail_compose.onchange_use_template(cr, uid, [], not compose.use_template, compose.template_id, compose.composition_mode, compose.model, compose.res_id)
        compose.write(values.get('value', {}), {'default_composition_mode': 'comment', 'default_model': 'mail.group'})
        compose.refresh()
        # Test: subject, body, partner_ids
        self.assertEqual(compose.subject, False, 'mail.compose.message subject incorrect')
        self.assertEqual(compose.body, '', 'mail.compose.message body incorrect')

        # CASE12 create in mass_mail composition
        compose_id = mail_compose.create(cr, uid,
            {'subject': 'Forget me subject', 'body': 'Dummy body'},
            {'default_composition_mode': 'mass_mail', 'default_model': 'mail.group',
                'default_res_id': -1, 'default_use_template': True,
                'active_ids': [self.group_pigs_id, group_bird_id] })
        compose = mail_compose.browse(cr, uid, compose_id)

        # Test 'onchange_template_id' with 'use_template' set
        values = mail_compose.onchange_template_id(cr, uid, [], compose.use_template, email_template_id, compose.composition_mode, compose.model, compose.res_id)
        print values
        # self.assertEqual()
        # compose.write(values['value'])
        values = mail_compose.onchange_use_template(cr, uid, [], not compose.use_template, compose.template_id, compose.composition_mode, compose.model, compose.res_id)
        print values

        compose.refresh()

        # Post the comment, get created message
        mail_compose.send_mail(cr, uid, [compose_id],  {'default_res_id': -1, 'active_ids': [self.group_pigs_id, group_bird_id]})
        group_pigs.refresh()
        group_bird.refresh()
        message_pigs = group_pigs.message_ids[0]
        message_bird = group_bird.message_ids[0]
        # Test: subject, body
        self.assertEqual(message_pigs.subject, _subject1, 'mail.message subject on Pigs incorrect')
        self.assertEqual(message_bird.subject, _subject2, 'mail.message subject on Bird incorrect')
        self.assertEqual(message_pigs.body, _body_text_html1, 'mail.message body on Pigs incorrect')
        self.assertEqual(message_bird.body, _body_text_html2, 'mail.message body on Bird incorrect')
        # Test: partner_ids
        print message_pigs.partner_ids
        print message_pigs.partner_ids
        self.assertEqual(len(message_pigs.partner_ids), 6, 'mail.message partner_ids incorrect')