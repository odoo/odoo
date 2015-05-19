# -*- coding: utf-8 -*-

from openerp.addons.mail.tests.common import TestMail
from openerp.tools import mute_logger


class TestMailFeatures(TestMail):

    def test_alias_setup(self):
        Users = self.env['res.users'].with_context({'no_reset_password': True})

        user_valentin = Users.create({
            'name': 'Valentin Cognito', 'email': 'valentin.cognito@gmail.com',
            'login': 'valentin.cognito', 'alias_name': 'valentin.cognito'})
        self.assertEqual(user_valentin.alias_name, user_valentin.login, "Login should be used as alias")

        user_pagan = Users.create({
            'name': 'Pagan Le Marchant', 'email': 'plmarchant@gmail.com',
            'login': 'plmarchant@gmail.com', 'alias_name': 'plmarchant@gmail.com'})
        self.assertEqual(user_pagan.alias_name, 'plmarchant', "If login is an email, the alias should keep only the local part")

        user_barty = Users.create({
            'name': 'Bartholomew Ironside', 'email': 'barty@gmail.com',
            'login': 'b4r+_#_R3wl$$', 'alias_name': 'b4r+_#_R3wl$$'})
        self.assertEqual(user_barty.alias_name, 'b4r+_-_r3wl-', 'Disallowed chars should be replaced by hyphens')

    def test_mail_notification_url_no_partner(self):
        mail = self.env['mail.mail'].create({'state': 'exception'})
        url = mail._get_partner_access_link()
        self.assertEqual(url, None)

    def test_mail_notification_url_partner(self):
        mail = self.env['mail.mail'].create({'state': 'exception'})
        url = mail._get_partner_access_link(self.partner_1)
        self.assertEqual(url, None)

    def test_mail_notification_url_user_signin(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        mail = self.env['mail.mail'].create({'state': 'exception'})
        url = mail._get_partner_access_link(self.user_employee.partner_id)
        self.assertIn(base_url, url)
        self.assertIn('db=%s' % self.env.cr.dbname, url,
                      'notification email: link should contain database name')
        self.assertIn('action=mail.action_mail_redirect', url,
                      'notification email: link should contain the redirect action')
        self.assertIn('login=%s' % self.user_employee.login, url,
                      'notification email: link should contain the user login')

    def test_mail_notification_url_user_document(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        mail = self.env['mail.mail'].create({'state': 'exception', 'model': 'mail.group', 'res_id': self.group_pigs.id})
        url = mail._get_partner_access_link(self.user_employee.partner_id)
        self.assertIn(base_url, url)
        self.assertIn('db=%s' % self.env.cr.dbname, url,
                      'notification email: link should contain database name')
        self.assertIn('action=mail.action_mail_redirect', url,
                      'notification email: link should contain the redirect action')
        self.assertIn('login=%s' % self.user_employee.login, url,
                      'notification email: link should contain the user login')
        self.assertIn('model=mail.group', url,
                      'notification email: link should contain the model when having not notification email on a record')
        self.assertIn('res_id=%s' % self.group_pigs.id, url,
                      'notification email: link should contain the res_id when having not notification email on a record')

    def test_inbox_redirection_basic(self):
        """ Inbox redirection: no params, Inbox """
        inbox_act_id = self.ref('mail.action_mail_inbox_feeds')
        action = self.env['mail.thread'].with_context({'params': {}}).sudo(self.user_employee).message_redirect_action()
        self.assertEqual(
            action.get('type'), 'ir.actions.client',
            'URL redirection: action without parameters should redirect to client action Inbox'
        )
        self.assertEqual(
            action.get('id'), inbox_act_id,
            'URL redirection: action without parameters should redirect to client action Inbox'
        )

    def test_inbox_redirection_document(self):
        """ Inbox redirection: document + read access: Doc """
        action = self.env['mail.thread'].with_context({
            'params': {'model': 'mail.group', 'res_id': self.group_pigs.id}
        }).sudo(self.user_employee).message_redirect_action()
        self.assertEqual(
            action.get('type'), 'ir.actions.act_window',
            'URL redirection: action with message_id for read-accredited user should redirect to Pigs'
        )
        self.assertEqual(
            action.get('res_id'), self.group_pigs.id,
            'URL redirection: action with message_id for read-accredited user should redirect to Pigs'
        )

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_inbox_redirection_message_document(self):
        """ Inbox redirection: message + read access: Doc """
        message = self.group_pigs.message_post(body='My body', partner_ids=[self.user_employee.partner_id.id], message_type='comment', subtype='mail.mt_comment')
        action = self.env['mail.thread'].with_context({
            'params': {'message_id': message.id}
        }).sudo(self.user_employee).message_redirect_action()
        self.assertEqual(
            action.get('type'), 'ir.actions.act_window',
            'URL redirection: action with message_id for read-accredited user should redirect to Pigs'
        )
        self.assertEqual(
            action.get('res_id'), self.group_pigs.id,
            'URL redirection: action with message_id for read-accredited user should redirect to Pigs'
        )

    @mute_logger('openerp.addons.mail.models.mail_mail', 'openerp.models')
    def test_inbox_redirection_message_inbox(self):
        """ Inbox redirection: message without read access: Inbox """
        message = self.group_pigs.message_post(body='My body', partner_ids=[self.user_employee.partner_id.id], message_type='comment', subtype='mail.mt_comment')
        inbox_act_id = self.ref('mail.action_mail_inbox_feeds')
        action = self.env['mail.thread'].with_context({
            'params': {'message_id': message.id}
        }).sudo(self.user_public).message_redirect_action()
        self.assertEqual(
            action.get('type'), 'ir.actions.client',
            'URL redirection: action without parameters should redirect to client action Inbox'
        )
        self.assertEqual(
            action.get('id'), inbox_act_id,
            'URL redirection: action without parameters should redirect to client action Inbox'
        )

    @mute_logger('openerp.models')
    def test_inbox_redirection_document_inbox(self):
        """ Inbox redirection: document without read access: Inbox """
        inbox_act_id = self.ref('mail.action_mail_inbox_feeds')
        action = self.env['mail.thread'].with_context({
            'params': {'model': 'mail.group', 'res_id': self.group_pigs.id}
        }).sudo(self.user_public).message_redirect_action()
        self.assertEqual(
            action.get('type'), 'ir.actions.client',
            'URL redirection: action without parameters should redirect to client action Inbox'
        )
        self.assertEqual(
            action.get('id'), inbox_act_id,
            'URL redirection: action without parameters should redirect to client action Inbox'
        )

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_needaction(self):
        na_emp1_base = self.env['mail.message'].sudo(self.user_employee)._needaction_count(domain=[])
        na_emp2_base = self.env['mail.message'].sudo(self.user_employee_2)._needaction_count(domain=[])

        self.group_pigs.message_post(body='Test', message_type='comment', subtype='mail.mt_comment', partner_ids=[self.user_employee.partner_id.id])

        na_emp1_new = self.env['mail.message'].sudo(self.user_employee)._needaction_count(domain=[])
        na_emp2_new = self.env['mail.message'].sudo(self.user_employee_2)._needaction_count(domain=[])
        self.assertEqual(na_emp1_new, na_emp1_base + 1)
        self.assertEqual(na_emp2_new, na_emp2_base)

        no_notify = self.env['mail.notification'].search_count([
            ('partner_id', '=', self.user_employee.partner_id.id),
            ('is_read', '=', False)])
        self.assertEqual(no_notify, na_emp1_new)


class TestMessagePost(TestMail):

    def setUp(self):
        super(TestMessagePost, self).setUp()
        self._attach_1 = self.env['ir.attachment'].sudo(self.user_employee).create({
            'name': 'Attach1', 'datas_fname': 'Attach1',
            'datas': 'bWlncmF0aW9uIHRlc3Q=',
            'res_model': 'mail.compose.message', 'res_id': 0})
        self._attach_2 = self.env['ir.attachment'].sudo(self.user_employee).create({
            'name': 'Attach2', 'datas_fname': 'Attach2',
            'datas': 'bWlncmF0aW9uIHRlc3Q=',
            'res_model': 'mail.compose.message', 'res_id': 0})
        self._attach_3 = self.env['ir.attachment'].sudo(self.user_employee).create({
            'name': 'Attach3', 'datas_fname': 'Attach3',
            'datas': 'bWlncmF0aW9uIHRlc3Q=',
            'res_model': 'mail.compose.message', 'res_id': 0})
        self.group_pigs.message_subscribe_users(user_ids=self.user_employee.id)

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_post_no_subscribe_author(self):
        original_followers = self.group_pigs.message_follower_ids
        self.group_pigs.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment')
        self.assertEqual(self.group_pigs.message_follower_ids, original_followers)

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_post_subscribe_author(self):
        original_followers = self.group_pigs.message_follower_ids
        self.group_pigs.sudo(self.user_employee).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment')
        self.assertEqual(self.group_pigs.message_follower_ids, original_followers | self.user_employee.partner_id)

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_post_no_subscribe_recipients(self):
        original_followers = self.group_pigs.message_follower_ids
        self.group_pigs.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment', partner_ids=[(4, self.partner_1.id), (4, self.partner_2.id)])
        self.assertEqual(self.group_pigs.message_follower_ids, original_followers)

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_post_subscribe_recipients(self):
        original_followers = self.group_pigs.message_follower_ids
        self.group_pigs.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True, 'mail_post_autofollow': True}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment', partner_ids=[(4, self.partner_1.id), (4, self.partner_2.id)])
        self.assertEqual(self.group_pigs.message_follower_ids, original_followers | self.partner_1 | self.partner_2)

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_post_subscribe_recipients_partial(self):
        original_followers = self.group_pigs.message_follower_ids
        self.group_pigs.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True, 'mail_post_autofollow': True, 'mail_post_autofollow_partner_ids': [self.partner_2.id]}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment', partner_ids=[(4, self.partner_1.id), (4, self.partner_2.id)])
        self.assertEqual(self.group_pigs.message_follower_ids, original_followers | self.partner_2)

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_post_notifications(self):
        _body, _body_alt = '<p>Test Body</p>', 'Test Body'
        _subject = 'Test Subject'
        _attachments = [
            ('List1', 'My first attachment'),
            ('List2', 'My second attachment')
        ]
        # partner_2 does not want to receive notification email
        self.partner_2.write({'notify_email': 'none'})
        # subscribe second employee to the group to test notifications
        self.group_pigs.message_subscribe_users(user_ids=self.user_employee_2.id)

        # use aliases
        _domain = 'schlouby.fr'
        _catchall = 'test_catchall'
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', _domain)
        self.env['ir.config_parameter'].set_param('mail.catchall.alias', _catchall)

        msg = self.group_pigs.sudo(self.user_employee).message_post(
            body=_body, subject=_subject, partner_ids=[self.partner_1.id, self.partner_2.id],
            attachment_ids=[self._attach_1.id, self._attach_2.id], attachments=_attachments,
            message_type='comment', subtype='mt_comment')

        # message content
        self.assertEqual(msg.subject, _subject)
        self.assertEqual(msg.body, _body)
        self.assertEqual(msg.partner_ids, self.partner_1 | self.partner_2)
        self.assertEqual(msg.notified_partner_ids, self.partner_1 | self.partner_2 | self.user_employee_2.partner_id)
        # attachments
        self.assertEqual(set(msg.attachment_ids.mapped('res_model')), set(['mail.group']),
                         'message_post: all atttachments should be linked to the mail.group model')
        self.assertEqual(set(msg.attachment_ids.mapped('res_id')), set([self.group_pigs.id]),
                         'message_post: all atttachments should be linked to the pigs group')
        self.assertEqual(set([x.decode('base64') for x in msg.attachment_ids.mapped('datas')]),
                         set(['migration test', _attachments[0][1], _attachments[1][1]]))
        self.assertTrue(set([self._attach_1.id, self._attach_2.id]).issubset(msg.attachment_ids.ids),
                        'message_post: mail.message attachments duplicated')
        # notifications
        self.assertFalse(self.env['mail.mail'].search([('mail_message_id', '=', msg.message_id)]),
                         'message_post: mail.mail notifications should have been auto-deleted')

        # notification emails: followers + recipients - notify_email=none (partner_2) - author (user_employee)
        self.assertEqual(set(m['email_from'] for m in self._mails),
                         set(['%s <%s@%s>' % (self.user_employee.name, self.user_employee.alias_name, _domain)]),
                         'message_post: notification email wrong email_from: should use alias of sender')
        self.assertEqual(set(m['email_to'][0] for m in self._mails),
                         set(['%s <%s>' % (self.partner_1.name, self.partner_1.email),
                              '%s <%s>' % (self.user_employee_2.name, self.user_employee_2.email)]))
        self.assertFalse(any(len(m['email_to']) != 1 for m in self._mails),
                         'message_post: notification email should be sent to one partner at a time')
        self.assertEqual(set(m['reply_to'] for m in self._mails),
                         set(['%s %s <%s@%s>' % (self._company_name, self.group_pigs.name, self.group_pigs.alias_name, _domain)]),
                         'message_post: notification email should use group aliases and data for reply to')
        self.assertTrue(all(_subject in m['subject'] for m in self._mails))
        self.assertTrue(all(_body in m['body'] for m in self._mails))
        self.assertTrue(all(_body_alt in m['body'] for m in self._mails))
        self.assertFalse(any(m['references'] for m in self._mails))

    @mute_logger('openerp.addons.mail.models.mail_mail')
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

        self.assertEqual(parent_msg.notified_partner_ids, self.env['res.partner'])

        msg = self.group_pigs.sudo(self.user_employee).message_post(
            body=_body, subject=_subject, partner_ids=[self.partner_1.id],
            message_type='comment', subtype='mt_comment', parent_id=parent_msg.id)

        self.assertEqual(msg.parent_id.id, parent_msg.id)
        self.assertEqual(msg.notified_partner_ids, self.partner_1)
        self.assertEqual(parent_msg.notified_partner_ids, self.partner_1)
        self.assertTrue(all('openerp-%d-mail.group' % self.group_pigs.id in m['references'] for m in self._mails))
        new_msg = self.group_pigs.sudo(self.user_employee).message_post(
            body=_body, subject=_subject,
            message_type='comment', subtype='mt_comment', parent_id=msg.id)

        self.assertEqual(new_msg.parent_id.id, parent_msg.id, 'message_post: flatten error')
        self.assertFalse(new_msg.notified_partner_ids)

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_message_compose(self):
        composer = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_model': 'mail.group',
            'default_res_id': self.group_pigs.id,
        }).sudo(self.user_employee).create({
            'body': '<p>Test Body</p>',
            'partner_ids': [(4, self.partner_1.id), (4, self.partner_2.id)]
        })
        self.assertEqual(composer.composition_mode,  'comment')
        self.assertEqual(composer.model, 'mail.group')
        self.assertEqual(composer.subject, 'Re: %s' % self.group_pigs.name)
        self.assertEqual(composer.record_name, self.group_pigs.name)

        composer.send_mail()
        message = self.group_pigs.message_ids[0]

        composer = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_res_id': self.group_pigs.id,
            'default_parent_id': message.id
        }).sudo(self.user_employee).create({})

        self.assertEqual(composer.model, 'mail.group')
        self.assertEqual(composer.res_id, self.group_pigs.id)
        self.assertEqual(composer.parent_id, message)
        self.assertEqual(composer.subject, 'Re: %s' % self.group_pigs.name)

        # TODO: test attachments ?

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_message_compose_mass_mail(self):
        composer = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'mass_mail',
            'default_model': 'mail.group',
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
        # Test: mail.group followers: author not added as follower in mass mail mode
        # self.assertEqual(set(group_pigs.message_follower_ids.ids), set([self.partner_admin_id, p_b.id, p_c.id, p_d.id]),
        #                 'compose wizard: mail_post_autofollow and mail_create_nosubscribe context keys not correctly taken into account')
        # self.assertEqual(set(group_bird.message_follower_ids.ids), set([self.partner_admin_id]),
        #                 'compose wizard: mail_post_autofollow and mail_create_nosubscribe context keys not correctly taken into account')

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_message_compose_mass_mail_active_domain(self):
        composer = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'mass_mail',
            'default_model': 'mail.group',
            'active_ids': [self.group_pigs.id],
            'active_domain': [('name', 'in', ['%s' % self.group_pigs.name, '%s' % self.group_public.name])],
        }).sudo(self.user_employee).create({
            'subject': 'From Composer Test',
            'body': '${object.description}',
        }).send_mail()

        self.assertEqual(self.group_pigs.message_ids[0].subject, 'From Composer Test')
        self.assertEqual(self.group_public.message_ids[0].subject, 'From Composer Test')
