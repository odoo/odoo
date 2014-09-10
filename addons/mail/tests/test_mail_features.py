# -*- coding: utf-8 -*-

from openerp.addons.mail.tests.common import TestMail
<<<<<<< HEAD
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
        url = self.env['mail.mail']._get_partner_access_link(mail)
        self.assertEqual(url, None)

    def test_mail_notification_url_partner(self):
        mail = self.env['mail.mail'].create({'state': 'exception'})
        url = self.env['mail.mail']._get_partner_access_link(mail, self.partner_1)
        self.assertEqual(url, None)

    def test_mail_notification_url_user_signin(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        mail = self.env['mail.mail'].create({'state': 'exception'})
        url = self.env['mail.mail']._get_partner_access_link(mail, self.user_employee.partner_id)
        self.assertIn(base_url, url)
        self.assertIn('db=%s' % self.env.cr.dbname, url,
=======
from openerp.tools import mute_logger, email_split, html2plaintext
from openerp.tools.mail import html_sanitize

class test_mail(TestMail):

    def test_000_alias_setup(self):
        """ Test basic mail.alias setup works, before trying to use them for routing """
        cr, uid = self.cr, self.uid
        self.user_valentin_id = self.res_users.create(cr, uid,
            {'name': 'Valentin Cognito', 'email': 'valentin.cognito@gmail.com', 'login': 'valentin.cognito', 'alias_name': 'valentin.cognito'})
        self.user_valentin = self.res_users.browse(cr, uid, self.user_valentin_id)
        self.assertEquals(self.user_valentin.alias_name, self.user_valentin.login, "Login should be used as alias")

        self.user_pagan_id = self.res_users.create(cr, uid,
            {'name': 'Pagan Le Marchant', 'email': 'plmarchant@gmail.com', 'login': 'plmarchant@gmail.com', 'alias_name': 'plmarchant@gmail.com'})
        self.user_pagan = self.res_users.browse(cr, uid, self.user_pagan_id)
        self.assertEquals(self.user_pagan.alias_name, 'plmarchant', "If login is an email, the alias should keep only the local part")

        self.user_barty_id = self.res_users.create(cr, uid,
            {'name': 'Bartholomew Ironside', 'email': 'barty@gmail.com', 'login': 'b4r+_#_R3wl$$', 'alias_name': 'b4r+_#_R3wl$$'})
        self.user_barty = self.res_users.browse(cr, uid, self.user_barty_id)
        self.assertEquals(self.user_barty.alias_name, 'b4r+_-_r3wl-', 'Disallowed chars should be replaced by hyphens')

    def test_00_followers_function_field(self):
        """ Tests designed for the many2many function field 'follower_ids'.
            We will test to perform writes using the many2many commands 0, 3, 4,
            5 and 6. """
        cr, uid, user_admin, partner_bert_id, group_pigs = self.cr, self.uid, self.user_admin, self.partner_bert_id, self.group_pigs

        # Data: create 'disturbing' values in mail.followers: same res_id, other res_model; same res_model, other res_id
        group_dummy_id = self.mail_group.create(cr, uid,
            {'name': 'Dummy group'}, {'mail_create_nolog': True})
        self.mail_followers.create(cr, uid,
            {'res_model': 'mail.thread', 'res_id': self.group_pigs_id, 'partner_id': partner_bert_id})
        self.mail_followers.create(cr, uid,
            {'res_model': 'mail.group', 'res_id': group_dummy_id, 'partner_id': partner_bert_id})

        # Pigs just created: should be only Admin as follower
        follower_ids = set([follower.id for follower in group_pigs.message_follower_ids])
        self.assertEqual(follower_ids, set([user_admin.partner_id.id]), 'Admin should be the only Pigs fan')

        # Subscribe Bert through a '4' command
        print '------------------'
        group_pigs.write({'message_follower_ids': [(4, partner_bert_id)]})
        group_pigs.refresh()
        print '------------------'
        follower_ids = set([follower.id for follower in group_pigs.message_follower_ids])
        self.assertEqual(follower_ids, set([partner_bert_id, user_admin.partner_id.id]), 'Bert and Admin should be the only Pigs fans')

        # Unsubscribe Bert through a '3' command
        group_pigs.write({'message_follower_ids': [(3, partner_bert_id)]})
        group_pigs.refresh()
        follower_ids = set([follower.id for follower in group_pigs.message_follower_ids])
        self.assertEqual(follower_ids, set([user_admin.partner_id.id]), 'Admin should be the only Pigs fan')

        # Set followers through a '6' command
        group_pigs.write({'message_follower_ids': [(6, 0, [partner_bert_id])]})
        group_pigs.refresh()
        follower_ids = set([follower.id for follower in group_pigs.message_follower_ids])
        self.assertEqual(follower_ids, set([partner_bert_id]), 'Bert should be the only Pigs fan')

        # Add a follower created on the fly through a '0' command
        group_pigs.write({'message_follower_ids': [(0, 0, {'name': 'Patrick Fiori'})]})
        partner_patrick_id = self.res_partner.search(cr, uid, [('name', '=', 'Patrick Fiori')])[0]
        group_pigs.refresh()
        follower_ids = set([follower.id for follower in group_pigs.message_follower_ids])
        self.assertEqual(follower_ids, set([partner_bert_id, partner_patrick_id]), 'Bert and Patrick should be the only Pigs fans')

        # Finally, unlink through a '5' command
        group_pigs.write({'message_follower_ids': [(5, 0)]})
        group_pigs.refresh()
        follower_ids = set([follower.id for follower in group_pigs.message_follower_ids])
        self.assertFalse(follower_ids, 'Pigs group should not have fans anymore')

        # Test dummy data has not been altered
        fol_obj_ids = self.mail_followers.search(cr, uid, [('res_model', '=', 'mail.thread'), ('res_id', '=', self.group_pigs_id)])
        follower_ids = set([follower.partner_id.id for follower in self.mail_followers.browse(cr, uid, fol_obj_ids)])
        self.assertEqual(follower_ids, set([partner_bert_id]), 'Bert should be the follower of dummy mail.thread data')
        fol_obj_ids = self.mail_followers.search(cr, uid, [('res_model', '=', 'mail.group'), ('res_id', '=', group_dummy_id)])
        follower_ids = set([follower.partner_id.id for follower in self.mail_followers.browse(cr, uid, fol_obj_ids)])
        self.assertEqual(follower_ids, set([partner_bert_id, user_admin.partner_id.id]), 'Bert and Admin should be the followers of dummy mail.group data')

    def test_05_message_followers_and_subtypes(self):
        """ Tests designed for the subscriber API as well as message subtypes """
        cr, uid, user_admin, user_raoul, group_pigs = self.cr, self.uid, self.user_admin, self.user_raoul, self.group_pigs
        # Data: message subtypes
        self.mail_message_subtype.create(cr, uid, {'name': 'mt_mg_def', 'default': True, 'res_model': 'mail.group'})
        self.mail_message_subtype.create(cr, uid, {'name': 'mt_other_def', 'default': True, 'res_model': 'crm.lead'})
        self.mail_message_subtype.create(cr, uid, {'name': 'mt_all_def', 'default': True, 'res_model': False})
        mt_mg_nodef = self.mail_message_subtype.create(cr, uid, {'name': 'mt_mg_nodef', 'default': False, 'res_model': 'mail.group'})
        mt_all_nodef = self.mail_message_subtype.create(cr, uid, {'name': 'mt_all_nodef', 'default': False, 'res_model': False})
        default_group_subtypes = self.mail_message_subtype.search(cr, uid, [('default', '=', True), '|', ('res_model', '=', 'mail.group'), ('res_model', '=', False)])

        # ----------------------------------------
        # CASE1: test subscriptions with subtypes
        # ----------------------------------------

        # Do: subscribe Raoul, should have default subtypes
        group_pigs.message_subscribe_users([user_raoul.id])
        group_pigs.refresh()
        # Test: 2 followers (Admin and Raoul)
        follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
        self.assertEqual(set(follower_ids), set([user_raoul.partner_id.id, user_admin.partner_id.id]),
                        'message_subscribe: Admin and Raoul should be the only 2 Pigs fans')
        # Raoul follows default subtypes
        fol_ids = self.mail_followers.search(cr, uid, [
                        ('res_model', '=', 'mail.group'),
                        ('res_id', '=', self.group_pigs_id),
                        ('partner_id', '=', user_raoul.partner_id.id)
                    ])
        fol_obj = self.mail_followers.browse(cr, uid, fol_ids)[0]
        fol_subtype_ids = set([subtype.id for subtype in fol_obj.subtype_ids])
        self.assertEqual(set(fol_subtype_ids), set(default_group_subtypes),
                        'message_subscribe: Raoul subscription subtypes are incorrect, should be all default ones')

        # Do: subscribe Raoul with specified new subtypes
        group_pigs.message_subscribe_users([user_raoul.id], subtype_ids=[mt_mg_nodef])
        # Test: 2 followers (Admin and Raoul)
        follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
        self.assertEqual(set(follower_ids), set([user_raoul.partner_id.id, user_admin.partner_id.id]),
                        'message_subscribe: Admin and Raoul should be the only 2 Pigs fans')
        # Test: 2 lines in mail.followers (no duplicate for Raoul)
        fol_ids = self.mail_followers.search(cr, uid, [
                        ('res_model', '=', 'mail.group'),
                        ('res_id', '=', self.group_pigs_id),
                    ])
        self.assertEqual(len(fol_ids), 2,
                        'message_subscribe: subscribing an already-existing follower should not create new entries in mail.followers')
        # Test: Raoul follows only specified subtypes
        fol_ids = self.mail_followers.search(cr, uid, [
                        ('res_model', '=', 'mail.group'),
                        ('res_id', '=', self.group_pigs_id),
                        ('partner_id', '=', user_raoul.partner_id.id)
                    ])
        fol_obj = self.mail_followers.browse(cr, uid, fol_ids)[0]
        fol_subtype_ids = set([subtype.id for subtype in fol_obj.subtype_ids])
        self.assertEqual(set(fol_subtype_ids), set([mt_mg_nodef]),
                        'message_subscribe: Raoul subscription subtypes are incorrect, should be only specified')

        # Do: Subscribe Raoul without specified subtypes: should not erase existing subscription subtypes
        group_pigs.message_subscribe_users([user_raoul.id, user_raoul.id])
        group_pigs.message_subscribe_users([user_raoul.id])
        group_pigs.refresh()
        # Test: 2 followers (Admin and Raoul)
        follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
        self.assertEqual(set(follower_ids), set([user_raoul.partner_id.id, user_admin.partner_id.id]),
                        'message_subscribe: Admin and Raoul should be the only 2 Pigs fans')
        # Test: Raoul follows default subtypes
        fol_ids = self.mail_followers.search(cr, uid, [
                        ('res_model', '=', 'mail.group'),
                        ('res_id', '=', self.group_pigs_id),
                        ('partner_id', '=', user_raoul.partner_id.id)
                    ])
        fol_obj = self.mail_followers.browse(cr, uid, fol_ids)[0]
        fol_subtype_ids = set([subtype.id for subtype in fol_obj.subtype_ids])
        self.assertEqual(set(fol_subtype_ids), set([mt_mg_nodef]),
                        'message_subscribe: Raoul subscription subtypes are incorrect, should be only specified')

        # Do: Unsubscribe Raoul twice through message_unsubscribe_users
        group_pigs.message_unsubscribe_users([user_raoul.id, user_raoul.id])
        group_pigs.refresh()
        # Test: 1 follower (Admin)
        follower_ids = [follower.id for follower in group_pigs.message_follower_ids]
        self.assertEqual(follower_ids, [user_admin.partner_id.id], 'Admin must be the only Pigs fan')
        # Test: 1 lines in mail.followers (no duplicate for Raoul)
        fol_ids = self.mail_followers.search(cr, uid, [
                        ('res_model', '=', 'mail.group'),
                        ('res_id', '=', self.group_pigs_id)
                    ])
        self.assertEqual(len(fol_ids), 1,
                        'message_subscribe: group should have only 1 entry in mail.follower for 1 follower')

        # Do: subscribe Admin with subtype_ids
        group_pigs.message_subscribe_users([uid], [mt_mg_nodef, mt_all_nodef])
        fol_ids = self.mail_followers.search(cr, uid, [('res_model', '=', 'mail.group'), ('res_id', '=', self.group_pigs_id), ('partner_id', '=', user_admin.partner_id.id)])
        fol_obj = self.mail_followers.browse(cr, uid, fol_ids)[0]
        fol_subtype_ids = set([subtype.id for subtype in fol_obj.subtype_ids])
        self.assertEqual(set(fol_subtype_ids), set([mt_mg_nodef, mt_all_nodef]), 'subscription subtypes are incorrect')

        # ----------------------------------------
        # CASE2: test mail_thread fields
        # ----------------------------------------

        subtype_data = group_pigs._get_subscription_data(None, None)[group_pigs.id]['message_subtype_data']
        self.assertEqual(set(subtype_data.keys()), set(['Discussions', 'mt_mg_def', 'mt_all_def', 'mt_mg_nodef', 'mt_all_nodef']), 'mail.group available subtypes incorrect')
        self.assertFalse(subtype_data['Discussions']['followed'], 'Admin should not follow Discussions in pigs')
        self.assertTrue(subtype_data['mt_mg_nodef']['followed'], 'Admin should follow mt_mg_nodef in pigs')
        self.assertTrue(subtype_data['mt_all_nodef']['followed'], 'Admin should follow mt_all_nodef in pigs')

    def test_11_notification_url(self):
        """ Tests designed to test the URL added in notification emails. """
        cr, uid, group_pigs = self.cr, self.uid, self.group_pigs
        # Test URL formatting
        base_url = self.registry('ir.config_parameter').get_param(cr, uid, 'web.base.url')

        # Partner data
        partner_raoul = self.res_partner.browse(cr, uid, self.partner_raoul_id)
        partner_bert_id = self.res_partner.create(cr, uid, {'name': 'bert'})
        partner_bert = self.res_partner.browse(cr, uid, partner_bert_id)
        # Mail data
        mail_mail_id = self.mail_mail.create(cr, uid, {'state': 'exception'})
        mail = self.mail_mail.browse(cr, uid, mail_mail_id)

        # Test: link for nobody -> None
        url = mail_mail._get_partner_access_link(self.mail_mail, cr, uid, mail)
        self.assertEqual(url, None,
                         'notification email: mails not send to a specific partner should not have any URL')

        # Test: link for partner -> None
        url = mail_mail._get_partner_access_link(self.mail_mail, cr, uid, mail, partner=partner_bert)
        self.assertEqual(url, None,
                         'notification email: mails send to a not-user partner should not have any URL')

        # Test: link for user -> signin
        url = mail_mail._get_partner_access_link(self.mail_mail, cr, uid, mail, partner=partner_raoul)
        self.assertIn(base_url, url,
                      'notification email: link should contain web.base.url')
        self.assertIn('db=%s' % cr.dbname, url,
>>>>>>> [WIP] Migrate
                      'notification email: link should contain database name')
        self.assertIn('action=mail.action_mail_redirect', url,
                      'notification email: link should contain the redirect action')
        self.assertIn('login=%s' % self.user_employee.login, url,
                      'notification email: link should contain the user login')

    def test_mail_notification_url_user_document(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        mail = self.env['mail.mail'].create({'state': 'exception', 'model': 'mail.group', 'res_id': self.group_pigs.id})
        url = self.env['mail.mail']._get_partner_access_link(mail, self.user_employee.partner_id)
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

    @mute_logger('openerp.addons.mail.mail_mail')
    def test_inbox_redirection_message_document(self):
        """ Inbox redirection: message + read access: Doc """
        msg_id = self.group_pigs.message_post(body='My body', partner_ids=[self.user_employee.partner_id.id], type='comment', subtype='mail.mt_comment')
        action = self.env['mail.thread'].with_context({
            'params': {'message_id': msg_id}
        }).sudo(self.user_employee).message_redirect_action()
        self.assertEqual(
            action.get('type'), 'ir.actions.act_window',
            'URL redirection: action with message_id for read-accredited user should redirect to Pigs'
        )
        self.assertEqual(
            action.get('res_id'), self.group_pigs.id,
            'URL redirection: action with message_id for read-accredited user should redirect to Pigs'
        )

    @mute_logger('openerp.addons.mail.mail_mail', 'openerp.models')
    def test_inbox_redirection_message_inbox(self):
        """ Inbox redirection: message without read access: Inbox """
        msg_id = self.group_pigs.message_post(body='My body', partner_ids=[self.user_employee.partner_id.id], type='comment', subtype='mail.mt_comment')
        inbox_act_id = self.ref('mail.action_mail_inbox_feeds')
        action = self.env['mail.thread'].with_context({
            'params': {'message_id': msg_id}
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

    @mute_logger('openerp.addons.mail.mail_mail')
    def test_needaction(self):
        na_emp1_base = self.env['mail.message'].sudo(self.user_employee)._needaction_count(domain=[])
        na_emp2_base = self.env['mail.message'].sudo(self.user_employee_2)._needaction_count(domain=[])

        self.group_pigs.message_post(body='Test', type='comment', subtype='mail.mt_comment', partner_ids=[self.user_employee.partner_id.id])

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

    @mute_logger('openerp.addons.mail.mail_mail')
    def test_post_no_subscribe_author(self):
        original_followers = self.group_pigs.message_follower_ids
        self.group_pigs.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True}).message_post(
            body='Test Body', type='comment', subtype='mt_comment')
        self.assertEqual(self.group_pigs.message_follower_ids, original_followers)

    @mute_logger('openerp.addons.mail.mail_mail')
    def test_post_subscribe_author(self):
        original_followers = self.group_pigs.message_follower_ids
        self.group_pigs.sudo(self.user_employee).message_post(
            body='Test Body', type='comment', subtype='mt_comment')
        self.assertEqual(self.group_pigs.message_follower_ids, original_followers | self.user_employee.partner_id)

    @mute_logger('openerp.addons.mail.mail_mail')
    def test_post_no_subscribe_recipients(self):
        original_followers = self.group_pigs.message_follower_ids
        self.group_pigs.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True}).message_post(
            body='Test Body', type='comment', subtype='mt_comment', partner_ids=[(4, self.partner_1.id), (4, self.partner_2.id)])
        self.assertEqual(self.group_pigs.message_follower_ids, original_followers)

    @mute_logger('openerp.addons.mail.mail_mail')
    def test_post_subscribe_recipients(self):
        original_followers = self.group_pigs.message_follower_ids
        self.group_pigs.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True, 'mail_post_autofollow': True}).message_post(
            body='Test Body', type='comment', subtype='mt_comment', partner_ids=[(4, self.partner_1.id), (4, self.partner_2.id)])
        self.assertEqual(self.group_pigs.message_follower_ids, original_followers | self.partner_1 | self.partner_2)

    @mute_logger('openerp.addons.mail.mail_mail')
    def test_post_subscribe_recipients_partial(self):
        original_followers = self.group_pigs.message_follower_ids
        self.group_pigs.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True, 'mail_post_autofollow': True, 'mail_post_autofollow_partner_ids': [self.partner_2.id]}).message_post(
            body='Test Body', type='comment', subtype='mt_comment', partner_ids=[(4, self.partner_1.id), (4, self.partner_2.id)])
        self.assertEqual(self.group_pigs.message_follower_ids, original_followers | self.partner_2)

    @mute_logger('openerp.addons.mail.mail_mail')
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

        msg_id = self.group_pigs.sudo(self.user_employee).message_post(
            body=_body, subject=_subject, partner_ids=[self.partner_1.id, self.partner_2.id],
            attachment_ids=[self._attach_1.id, self._attach_2.id], attachments=_attachments,
            type='comment', subtype='mt_comment')
        msg = self.env['mail.message'].browse(msg_id)

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

    @mute_logger('openerp.addons.mail.mail_mail')
    def test_post_answer(self):
        _body = '<p>Test Body</p>'
        _subject = 'Test Subject'

        # use aliases
        _domain = 'schlouby.fr'
        _catchall = 'test_catchall'
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', _domain)
        self.env['ir.config_parameter'].set_param('mail.catchall.alias', _catchall)

        parent_msg_id = self.group_pigs.sudo(self.user_employee).message_post(
            body=_body, subject=_subject,
            type='comment', subtype='mt_comment')
        parent_msg = self.env['mail.message'].browse(parent_msg_id)

        self.assertEqual(parent_msg.notified_partner_ids, self.env['res.partner'])

        msg_id = self.group_pigs.sudo(self.user_employee).message_post(
            body=_body, subject=_subject, partner_ids=[self.partner_1.id],
            type='comment', subtype='mt_comment', parent_id=parent_msg_id)
        msg = self.env['mail.message'].browse(msg_id)

        self.assertEqual(msg.parent_id.id, parent_msg_id)
        self.assertEqual(msg.notified_partner_ids, self.partner_1)
        self.assertEqual(parent_msg.notified_partner_ids, self.partner_1)
        self.assertTrue(all('openerp-%d-mail.group' % self.group_pigs.id in m['references'] for m in self._mails))
        new_msg_id = self.group_pigs.sudo(self.user_employee).message_post(
            body=_body, subject=_subject,
            type='comment', subtype='mt_comment', parent_id=msg_id)
        new_msg = self.env['mail.message'].browse(new_msg_id)

        self.assertEqual(new_msg.parent_id.id, parent_msg_id, 'message_post: flatten error')
        self.assertFalse(new_msg.notified_partner_ids)

    @mute_logger('openerp.addons.mail.mail_mail')
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

    @mute_logger('openerp.addons.mail.mail_mail')
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

    @mute_logger('openerp.addons.mail.mail_mail')
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
