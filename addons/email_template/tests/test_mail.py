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

import base64
from openerp.addons.mail.tests.common import TestMail
from openerp.tools import mute_logger


class test_message_compose(TestMail):

    def setUp(self):
        super(test_message_compose, self).setUp()

        # create a 'pigs' and 'bird' groups that will be used through the various tests
        self.group_bird_id = self.mail_group.create(self.cr, self.uid,
            {'name': 'Bird', 'description': 'I am angry !'})

    def test_00_message_compose_wizard(self):
        """ Tests designed for the mail.compose.message wizard updated by email_template. """
        cr, uid = self.cr, self.uid
        mail_compose = self.registry('mail.compose.message')
        self.res_users.write(cr, uid, [uid], {'signature': 'Admin', 'email': 'a@a.a'})
        user_admin = self.res_users.browse(cr, uid, uid)
        p_a_id = user_admin.partner_id.id
        group_pigs = self.mail_group.browse(cr, uid, self.group_pigs_id)
        group_bird = self.mail_group.browse(cr, uid, self.group_bird_id)

        # Mail data
        _subject1 = 'Pigs'
        _subject2 = 'Bird'
        _body_html1 = 'Fans of Pigs, unite !'
        _body_html2 = 'I am angry !'
        _attachments = [
            {'name': 'First', 'datas_fname': 'first.txt', 'datas': base64.b64encode('My first attachment'), 'res_model': 'res.partner', 'res_id': self.partner_admin_id},
            {'name': 'Second', 'datas_fname': 'second.txt', 'datas': base64.b64encode('My second attachment'), 'res_model': 'res.partner', 'res_id': self.partner_admin_id},
            ]
        _attachments_test = [('first.txt', 'My first attachment'), ('second.txt', 'My second attachment')]

        # Create template on mail.group, with attachments
        group_model_id = self.registry('ir.model').search(cr, uid, [('model', '=', 'mail.group')])[0]
        email_template = self.registry('email.template')
        email_template_id = email_template.create(cr, uid, {
            'model_id': group_model_id,
            'name': 'Pigs Template',
            'subject': '${object.name}',
            'body_html': '${object.description}',
            'user_signature': False,
            'attachment_ids': [(0, 0, _attachments[0]), (0, 0, _attachments[1])],
            'email_to': 'b@b.b, c@c.c',
            'email_cc': 'd@d.d'
            })

        # ----------------------------------------
        # CASE1: comment and save as template
        # ----------------------------------------

        # 1. Comment on pigs
        compose_id = mail_compose.create(cr, uid,
            {'subject': 'Forget me subject', 'body': '<p>Dummy body</p>'},
            {'default_composition_mode': 'comment',
                'default_model': 'mail.group',
                'default_res_id': self.group_pigs_id,
                'active_ids': [self.group_pigs_id, self.group_bird_id]})
        compose = mail_compose.browse(cr, uid, compose_id)

        # 2. Save current composition form as a template
        mail_compose.save_as_template(cr, uid, [compose_id], context={'default_model': 'mail.group'})
        # Test: email_template subject, body_html, model
        last_template_id = email_template.search(cr, uid, [('model', '=', 'mail.group'), ('subject', '=', 'Forget me subject')], limit=1)[0]
        self.assertTrue(last_template_id, 'email_template not found for model mail.group, subject Forget me subject')
        last_template = email_template.browse(cr, uid, last_template_id)
        self.assertEqual(last_template.body_html, '<p>Dummy body</p>', 'email_template incorrect body_html')

        # ----------------------------------------
        # CASE2: comment with template, save as template
        # ----------------------------------------

        # 1. Comment on pigs
        context = {
            'default_composition_mode': 'comment',
            'default_model': 'mail.group',
            'default_res_id': self.group_pigs_id,
            'default_use_template': False,
            'default_template_id': email_template_id,
            'active_ids': [self.group_pigs_id, self.group_bird_id]
        }
        compose_id = mail_compose.create(cr, uid, {'subject': 'Forget me subject', 'body': 'Dummy body'}, context)
        compose = mail_compose.browse(cr, uid, compose_id, context)
        onchange_res = compose.onchange_template_id(email_template_id, 'comment', 'mail.group', self.group_pigs_id)['value']
        onchange_res['partner_ids'] = [(4, partner_id) for partner_id in onchange_res.pop('partner_ids', [])]
        onchange_res['attachment_ids'] = [(4, attachment_id) for attachment_id in onchange_res.pop('attachment_ids', [])]
        compose.write(onchange_res)
        compose.refresh()

        message_pids = [partner.id for partner in compose.partner_ids]
        partner_ids = self.res_partner.search(cr, uid, [('email', 'in', ['b@b.b', 'c@c.c', 'd@d.d'])])
        # Test: mail.compose.message: subject, body, partner_ids
        self.assertEqual(compose.subject, _subject1, 'mail.compose.message subject incorrect')
        self.assertIn(_body_html1, compose.body, 'mail.compose.message body incorrect')
        self.assertEqual(set(message_pids), set(partner_ids), 'mail.compose.message partner_ids incorrect')
        # Test: mail.compose.message: attachments (owner has not been modified)
        for attach in compose.attachment_ids:
            self.assertEqual(attach.res_model, 'res.partner', 'mail.compose.message attachment res_model through templat was overriden')
            self.assertEqual(attach.res_id, self.partner_admin_id, 'mail.compose.message attachment res_id incorrect')
            self.assertIn((attach.datas_fname, base64.b64decode(attach.datas)), _attachments_test,
                'mail.message attachment name / data incorrect')
        # Test: mail.message: attachments
        mail_compose.send_mail(cr, uid, [compose_id])
        group_pigs.refresh()
        message_pigs = group_pigs.message_ids[0]
        for attach in message_pigs.attachment_ids:
            self.assertEqual(attach.res_model, 'mail.group', 'mail.compose.message attachment res_model through templat was overriden')
            self.assertEqual(attach.res_id, self.group_pigs_id, 'mail.compose.message attachment res_id incorrect')
            self.assertIn((attach.datas_fname, base64.b64decode(attach.datas)), _attachments_test,
                'mail.message attachment name / data incorrect')

        # ----------------------------------------
        # CASE3: mass_mail with template
        # ----------------------------------------

        # 1. Mass_mail on pigs and bird, with a default_partner_ids set to check he is correctly added
        context = {
            'default_composition_mode': 'mass_mail',
            'default_notify': True,
            'default_model': 'mail.group',
            'default_res_id': self.group_pigs_id,
            'default_template_id': email_template_id,
            'default_partner_ids': [p_a_id],
            'active_ids': [self.group_pigs_id, self.group_bird_id]
        }
        compose_id = mail_compose.create(cr, uid, {'subject': 'Forget me subject', 'body': 'Dummy body'}, context)
        compose = mail_compose.browse(cr, uid, compose_id, context)
        onchange_res = compose.onchange_template_id(email_template_id, 'mass_mail', 'mail.group', self.group_pigs_id)['value']
        onchange_res['partner_ids'] = [(4, partner_id) for partner_id in onchange_res.pop('partner_ids', [])]
        onchange_res['attachment_ids'] = [(4, attachment_id) for attachment_id in onchange_res.pop('attachment_ids', [])]
        compose.write(onchange_res)
        compose.refresh()

        message_pids = [partner.id for partner in compose.partner_ids]
        partner_ids = [p_a_id]
        self.assertEqual(compose.subject, '${object.name}', 'mail.compose.message subject incorrect')
        self.assertEqual(compose.body, '<p>${object.description}</p>', 'mail.compose.message body incorrect')  # todo: check signature
        self.assertEqual(set(message_pids), set(partner_ids), 'mail.compose.message partner_ids incorrect')

        # 2. Post the comment, get created message
        mail_compose.send_mail(cr, uid, [compose_id],  {'default_res_id': -1, 'active_ids': [self.group_pigs_id, self.group_bird_id]})
        group_pigs.refresh()
        group_bird.refresh()
        message_pigs = group_pigs.message_ids[0]
        message_bird = group_bird.message_ids[0]
        # Test: subject, body
        self.assertEqual(message_pigs.subject, _subject1, 'mail.message subject on Pigs incorrect')
        self.assertEqual(message_bird.subject, _subject2, 'mail.message subject on Bird incorrect')
        self.assertIn(_body_html1, message_pigs.body, 'mail.message body on Pigs incorrect')
        self.assertIn(_body_html2, message_bird.body, 'mail.message body on Bird incorrect')
        # Test: partner_ids: p_a_id (default) + 3 newly created partners
        # message_pigs_pids = [partner.id for partner in message_pigs.notified_partner_ids]
        # message_bird_pids = [partner.id for partner in message_bird.notified_partner_ids]
        # partner_ids = self.res_partner.search(cr, uid, [('email', 'in', ['b@b.b', 'c@c.c', 'd@d.d'])])
        # partner_ids.append(p_a_id)
        # self.assertEqual(set(message_pigs_pids), set(partner_ids), 'mail.message on pigs incorrect number of notified_partner_ids')
        # self.assertEqual(set(message_bird_pids), set(partner_ids), 'mail.message on bird notified_partner_ids incorrect')

        # ----------------------------------------
        # CASE4: test newly introduced partner_to field
        # ----------------------------------------

        # get already-created partners back
        p_b_id = self.res_partner.search(cr, uid, [('email', '=', 'b@b.b')])[0]
        p_c_id = self.res_partner.search(cr, uid, [('email', '=', 'c@c.c')])[0]
        p_d_id = self.res_partner.search(cr, uid, [('email', '=', 'd@d.d')])[0]
        # modify template: use partner_to, use template and email address in email_to to test all features together
        user_model_id = self.registry('ir.model').search(cr, uid, [('model', '=', 'res.users')])[0]
        email_template.write(cr, uid, [email_template_id], {
            'model_id': user_model_id,
            'body_html': '${object.login}',
            'email_to': '${object.email}, c@c',
            'partner_to': '%i,%i' % (p_b_id, p_c_id),
            'email_cc': 'd@d',
            })
        # patner by email + partner by id (no double)
        send_to = [p_a_id, p_b_id, p_c_id, p_d_id]
        # Generate messsage with default email and partner on template
        mail_value = mail_compose.generate_email_for_composer(cr, uid, email_template_id, uid)
        self.assertEqual(set(mail_value['partner_ids']), set(send_to), 'mail.message partner_ids list created by template is incorrect')

    @mute_logger('openerp.models')
    def test_10_email_templating(self):
        """ Tests designed for the mail.compose.message wizard updated by email_template. """
        cr, uid, context = self.cr, self.uid, {}

        # create the email.template on mail.group model
        group_model_id = self.registry('ir.model').search(cr, uid, [('model', '=', 'mail.group')])[0]
        email_template = self.registry('email.template')
        email_template_id = email_template.create(cr, uid, {
            'model_id': group_model_id,
            'name': 'Pigs Template',
            'email_from': 'Raoul Grosbedon <raoul@example.com>',
            'subject': '${object.name}',
            'body_html': '${object.description}',
            'user_signature': True,
            'email_to': 'b@b.b, c@c.c',
            'email_cc': 'd@d.d',
            'partner_to': '${user.partner_id.id},%s,%s,-1' % (self.user_raoul.partner_id.id, self.user_bert.partner_id.id)
        })

        # not force send: email_recipients is not taken into account
        msg_id = email_template.send_mail(cr, uid, email_template_id, self.group_pigs_id, context=context)
        mail = self.mail_mail.browse(cr, uid, msg_id, context=context)
        self.assertEqual(mail.subject, 'Pigs', 'email_template: send_mail: wrong subject')
        self.assertEqual(mail.email_to, 'b@b.b, c@c.c', 'email_template: send_mail: wrong email_to')
        self.assertEqual(mail.email_cc, 'd@d.d', 'email_template: send_mail: wrong email_cc')
        self.assertEqual(
            set([partner.id for partner in mail.recipient_ids]),
            set((self.partner_admin_id, self.user_raoul.partner_id.id, self.user_bert.partner_id.id)),
            'email_template: send_mail: wrong management of partner_to')

        # force send: take email_recipients into account
        email_template.send_mail(cr, uid, email_template_id, self.group_pigs_id, force_send=True, context=context)
        sent_emails = self._build_email_kwargs_list
        email_to_lst = [
            ['b@b.b', 'c@c.c'], ['Administrator <admin@yourcompany.example.com>'],
            ['Raoul Grosbedon <raoul@raoul.fr>'], ['Bert Tartignole <bert@bert.fr>']]
        self.assertEqual(len(sent_emails), 4, 'email_template: send_mail: 3 valid email recipients + email_to -> should send 4 emails')
        for email in sent_emails:
            self.assertIn(email['email_to'], email_to_lst, 'email_template: send_mail: wrong email_recipients')
