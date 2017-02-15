# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import TestMail
from odoo.addons.mail.tests.test_mail_gateway import MAIL_TEMPLATE_PLAINTEXT
from odoo.tools import mute_logger


class TestMailFeatures(TestMail):
    # TDE TODO: tests on the redirection controller

    def test_alias_setup(self):
        alias = self.env['mail.alias'].with_context(alias_model_name='mail.channel').create({'alias_name': 'b4r+_#_R3wl$$'})
        self.assertEqual(alias.alias_name, 'b4r+_-_r3wl-', 'Disallowed chars should be replaced by hyphens')

    def test_10_cache_invalidation(self):
        """ Test that creating a mail-thread record does not invalidate the whole cache. """
        # make a new record in cache
        record = self.env['res.partner'].new({'name': 'Brave New Partner'})
        self.assertTrue(record.name)

        # creating a mail-thread record should not invalidate the whole cache
        self.env['res.partner'].create({'name': 'Actual Partner'})
        self.assertTrue(record.name)


    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_needaction(self):
        na_emp1_base = self.group_pigs.sudo(self.user_employee).message_needaction_counter
        na_emp2_base = self.group_pigs.sudo().message_needaction_counter

        self.group_pigs.message_post(body='Test', message_type='comment', subtype='mail.mt_comment', partner_ids=[self.user_employee.partner_id.id])

        na_emp1_new = self.group_pigs.sudo(self.user_employee).message_needaction_counter
        na_emp2_new = self.group_pigs.sudo().message_needaction_counter
        self.assertEqual(na_emp1_new, na_emp1_base + 1)
        self.assertEqual(na_emp2_new, na_emp2_base)


class TestMessagePost(TestMail):

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_no_subscribe_author(self):
        original = self.group_pigs.message_follower_ids
        self.group_pigs.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment')
        self.assertEqual(self.group_pigs.message_follower_ids.mapped('partner_id'), original.mapped('partner_id'))
        self.assertEqual(self.group_pigs.message_follower_ids.mapped('channel_id'), original.mapped('channel_id'))

    # TODO : the author of a message post on mail.channel should not be added as follower

    # @mute_logger('odoo.addons.mail.models.mail_mail')
    # def test_post_subscribe_author(self):
    #     original = self.group_pigs.message_follower_ids
    #     self.group_pigs.sudo(self.user_employee).message_post(
    #         body='Test Body', message_type='comment', subtype='mt_comment')
    #     self.assertEqual(self.group_pigs.message_follower_ids.mapped('partner_id'), original.mapped('partner_id') | self.user_employee.partner_id)
    #     self.assertEqual(self.group_pigs.message_follower_ids.mapped('channel_id'), original.mapped('channel_id'))

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_no_subscribe_recipients(self):
        original = self.group_pigs.message_follower_ids
        self.group_pigs.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment', partner_ids=[(4, self.partner_1.id), (4, self.partner_2.id)])
        self.assertEqual(self.group_pigs.message_follower_ids.mapped('partner_id'), original.mapped('partner_id'))
        self.assertEqual(self.group_pigs.message_follower_ids.mapped('channel_id'), original.mapped('channel_id'))

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_subscribe_recipients(self):
        original = self.group_pigs.message_follower_ids
        self.group_pigs.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True, 'mail_post_autofollow': True}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment', partner_ids=[(4, self.partner_1.id), (4, self.partner_2.id)])
        self.assertEqual(self.group_pigs.message_follower_ids.mapped('partner_id'), original.mapped('partner_id') | self.partner_1 | self.partner_2)
        self.assertEqual(self.group_pigs.message_follower_ids.mapped('channel_id'), original.mapped('channel_id'))

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_subscribe_recipients_partial(self):
        original = self.group_pigs.message_follower_ids
        self.group_pigs.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True, 'mail_post_autofollow': True, 'mail_post_autofollow_partner_ids': [self.partner_2.id]}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment', partner_ids=[(4, self.partner_1.id), (4, self.partner_2.id)])
        self.assertEqual(self.group_pigs.message_follower_ids.mapped('partner_id'), original.mapped('partner_id') | self.partner_2)
        self.assertEqual(self.group_pigs.message_follower_ids.mapped('channel_id'), original.mapped('channel_id'))

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_notifications(self):
        _body, _body_alt = '<p>Test Body</p>', 'Test Body'
        _subject = 'Test Subject'
        _attachments = [
            ('List1', 'My first attachment'),
            ('List2', 'My second attachment')
        ]
        _attach_1 = self.env['ir.attachment'].sudo(self.user_employee).create({
            'name': 'Attach1', 'datas_fname': 'Attach1',
            'datas': 'bWlncmF0aW9uIHRlc3Q=',
            'res_model': 'mail.compose.message', 'res_id': 0})
        _attach_2 = self.env['ir.attachment'].sudo(self.user_employee).create({
            'name': 'Attach2', 'datas_fname': 'Attach2',
            'datas': 'bWlncmF0aW9uIHRlc3Q=',
            'res_model': 'mail.compose.message', 'res_id': 0})
        # partner_2 does not want to receive notification email
        self.partner_2.write({'notify_email': 'none'})
        self.user_admin.write({'notify_email': 'always'})
        # subscribe second employee to the group to test notifications
        self.group_pigs.message_subscribe_users(user_ids=[self.env.user.id])

        # use aliases
        _domain = 'schlouby.fr'
        _catchall = 'test_catchall'
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', _domain)
        self.env['ir.config_parameter'].set_param('mail.catchall.alias', _catchall)

        msg = self.group_pigs.sudo(self.user_employee).message_post(
            body=_body, subject=_subject, partner_ids=[self.partner_1.id, self.partner_2.id],
            attachment_ids=[_attach_1.id, _attach_2.id], attachments=_attachments,
            message_type='comment', subtype='mt_comment')

        # message content
        self.assertEqual(msg.subject, _subject)
        self.assertEqual(msg.body, _body)
        self.assertEqual(msg.partner_ids, self.partner_1 | self.partner_2)
        self.assertEqual(msg.needaction_partner_ids, self.env.user.partner_id | self.partner_1 | self.partner_2)
        self.assertEqual(msg.channel_ids, self.env['mail.channel'])

        # attachments
        self.assertEqual(set(msg.attachment_ids.mapped('res_model')), set(['mail.channel']),
                         'message_post: all atttachments should be linked to the mail.channel model')
        self.assertEqual(set(msg.attachment_ids.mapped('res_id')), set([self.group_pigs.id]),
                         'message_post: all atttachments should be linked to the pigs group')
        self.assertEqual(set([x.decode('base64') for x in msg.attachment_ids.mapped('datas')]),
                         set(['migration test', _attachments[0][1], _attachments[1][1]]))
        self.assertTrue(set([_attach_1.id, _attach_2.id]).issubset(msg.attachment_ids.ids),
                        'message_post: mail.message attachments duplicated')
        # notifications
        self.assertFalse(self.env['mail.mail'].search([('mail_message_id', '=', msg.message_id)]),
                         'message_post: mail.mail notifications should have been auto-deleted')

        # notification emails: followers + recipients - notify_email=none (partner_2) - author (user_employee)
        self.assertEqual(set(m['email_from'] for m in self._mails),
                         set(['%s <%s>' % (self.user_employee.name, self.user_employee.email)]),
                         'message_post: notification email wrong email_from: should use sender email')
        self.assertEqual(set(m['email_to'][0] for m in self._mails),
                         set(['%s <%s>' % (self.partner_1.name, self.partner_1.email),
                              '%s <%s>' % (self.env.user.name, self.env.user.email)]))
        self.assertFalse(any(len(m['email_to']) != 1 for m in self._mails),
                         'message_post: notification email should be sent to one partner at a time')
        self.assertEqual(set(m['reply_to'] for m in self._mails),
                         set(['%s %s <%s@%s>' % (self.env.user.company_id.name, self.group_pigs.name, self.group_pigs.alias_name, _domain)]),
                         'message_post: notification email should use group aliases and data for reply to')
        self.assertTrue(all(_subject in m['subject'] for m in self._mails))
        self.assertTrue(all(_body in m['body'] for m in self._mails))
        self.assertTrue(all(_body_alt in m['body'] for m in self._mails))
        self.assertFalse(any(m['references'] for m in self._mails))

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_answer(self):
        _body = '<p>Test Body</p>'
        _subject = 'Test Subject'

        # use aliases
        _domain = 'schlouby.fr'
        _catchall = 'test_catchall'
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', _domain)
        self.env['ir.config_parameter'].set_param('mail.catchall.alias', _catchall)

        parent_msg = self.group_pigs.sudo(self.user_employee).message_post(
            body=_body, subject=_subject,
            message_type='comment', subtype='mt_comment')

        self.assertEqual(parent_msg.partner_ids, self.env['res.partner'])

        msg = self.group_pigs.sudo(self.user_employee).message_post(
            body=_body, subject=_subject, partner_ids=[self.partner_1.id],
            message_type='comment', subtype='mt_comment', parent_id=parent_msg.id)

        self.assertEqual(msg.parent_id.id, parent_msg.id)
        self.assertEqual(msg.partner_ids, self.partner_1)
        # self.assertEqual(parent_msg.partner_ids, self.partner_1)  # TDE FIXME: to check
        self.assertTrue(all('openerp-%d-mail.channel' % self.group_pigs.id in m['references'] for m in self._mails))
        new_msg = self.group_pigs.sudo(self.user_employee).message_post(
            body=_body, subject=_subject,
            message_type='comment', subtype='mt_comment', parent_id=msg.id)

        self.assertEqual(new_msg.parent_id.id, parent_msg.id, 'message_post: flatten error')
        self.assertFalse(new_msg.partner_ids)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_internal(self):
        self.group_pigs.message_subscribe_users([self.user_admin.id])
        msg = self.group_pigs.sudo(self.user_employee).message_post(
            body='My Body', subject='My Subject',
            message_type='comment', subtype='mt_note')
        self.assertEqual(msg.partner_ids, self.env['res.partner'])
        self.assertEqual(msg.needaction_partner_ids, self.env['res.partner'])
        self.assertEqual(self.group_pigs.message_ids, msg)

        self.format_and_process(
            MAIL_TEMPLATE_PLAINTEXT,
            email_from=self.user_admin.email,
            msg_id='<1198923581.41972151344608186800.JavaMail.diff1@agrolait.com>',
            to='not_my_businesss@example.com',
            extra='In-Reply-To:\r\n\t%s\n' % msg.message_id)
        reply = self.group_pigs.message_ids - msg
        self.assertTrue(reply)
        self.assertEqual(reply.subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(reply.needaction_partner_ids, self.env['res.partner'])

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_compose(self):
        composer = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_model': 'mail.channel',
            'default_res_id': self.group_pigs.id,
        }).sudo(self.user_employee).create({
            'body': '<p>Test Body</p>',
            'partner_ids': [(4, self.partner_1.id), (4, self.partner_2.id)]
        })
        self.assertEqual(composer.composition_mode,  'comment')
        self.assertEqual(composer.model, 'mail.channel')
        self.assertEqual(composer.subject, 'Re: %s' % self.group_pigs.name)
        self.assertEqual(composer.record_name, self.group_pigs.name)

        composer.send_mail()
        message = self.group_pigs.message_ids[0]

        composer = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_res_id': self.group_pigs.id,
            'default_parent_id': message.id
        }).sudo(self.user_employee).create({})

        self.assertEqual(composer.model, 'mail.channel')
        self.assertEqual(composer.res_id, self.group_pigs.id)
        self.assertEqual(composer.parent_id, message)
        self.assertEqual(composer.subject, 'Re: %s' % self.group_pigs.name)

        # TODO: test attachments ?

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_compose_mass_mail(self):
        composer = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'mass_mail',
            'default_model': 'mail.channel',
            'default_res_id': False,
            'active_ids': [self.group_pigs.id, self.group_public.id]
        }).sudo(self.user_employee).create({
            'subject': 'Testing ${object.name}',
            'body': '<p>${object.description}</p>',
            'partner_ids': [(4, self.partner_1.id), (4, self.partner_2.id)]
        })
        composer.with_context({
            'default_res_id': -1,
            'active_ids': [self.group_pigs.id, self.group_public.id]
        }).send_mail()

        # check mail_mail
        mails = self.env['mail.mail'].search([('subject', 'ilike', 'Testing')])
        for mail in mails:
            self.assertEqual(mail.recipient_ids, self.partner_1 | self.partner_2,
                             'compose wizard: mail_mail mass mailing: mail.mail in mass mail incorrect recipients')

        # check message on group_pigs
        message1 = self.group_pigs.message_ids[0]
        self.assertEqual(message1.subject, 'Testing %s' % self.group_pigs.name)
        self.assertEqual(message1.body, '<p>%s</p>' % self.group_pigs.description)

        # check message on group_public
        message1 = self.group_public.message_ids[0]
        self.assertEqual(message1.subject, 'Testing %s' % self.group_public.name)
        self.assertEqual(message1.body, '<p>%s</p>' % self.group_public.description)

        # # Test: Pigs and Bird did receive their message
        # # check logged messages
        # message1 = group_pigs.message_ids[0]
        # message2 = group_bird.message_ids[0]
        # # Test: Pigs and Bird did receive their message
        # messages = self.MailMessage.search([], limit=2)
        # mail = self.MailMail.search([('mail_message_id', '=', message2.id)], limit=1)
        # self.assertTrue(mail, 'message_send: mail.mail message should have in processing mail queue')
        # #check mass mail state...
        # mails = self.MailMail.search([('state', '=', 'exception')])
        # self.assertNotIn(mail.id, mails.ids, 'compose wizard: Mail sending Failed!!')
        # self.assertIn(message1.id, messages.ids, 'compose wizard: Pigs did not receive its mass mailing message')
        # self.assertIn(message2.id, messages.ids, 'compose wizard: Bird did not receive its mass mailing message')

        # check followers ?
        # Test: mail.channel followers: author not added as follower in mass mail mode
        # self.assertEqual(set(group_pigs.message_follower_ids.ids), set([self.partner_admin_id, p_b.id, p_c.id, p_d.id]),
        #                 'compose wizard: mail_post_autofollow and mail_create_nosubscribe context keys not correctly taken into account')
        # self.assertEqual(set(group_bird.message_follower_ids.ids), set([self.partner_admin_id]),
        #                 'compose wizard: mail_post_autofollow and mail_create_nosubscribe context keys not correctly taken into account')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_compose_mass_mail_active_domain(self):
        self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'mass_mail',
            'default_model': 'mail.channel',
            'default_use_active_domain': True,
            'active_ids': [self.group_pigs.id],
            'active_domain': [('name', 'in', ['%s' % self.group_pigs.name, '%s' % self.group_public.name])],
        }).sudo(self.user_employee).create({
            'subject': 'From Composer Test',
            'body': '${object.description}',
        }).send_mail()

        self.assertEqual(self.group_pigs.message_ids[0].subject, 'From Composer Test')
        self.assertEqual(self.group_public.message_ids[0].subject, 'From Composer Test')


    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_compose_mass_mail_no_active_domain(self):
        self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'mass_mail',
            'default_model': 'mail.channel',
            'default_use_active_domain': False,
            'active_ids': [self.group_pigs.id],
            'active_domain': [('name', 'in', ['%s' % self.group_pigs.name, '%s' % self.group_public.name])],
        }).sudo(self.user_employee).create({
            'subject': 'From Composer Test',
            'body': '${object.description}',
        }).send_mail()

        self.assertEqual(self.group_pigs.message_ids[0].subject, 'From Composer Test')
        self.assertFalse(self.group_public.message_ids.ids)
