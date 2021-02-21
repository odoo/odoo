# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError

from odoo.tests import tagged
from odoo.addons.test_mail.tests import common
from odoo.addons.test_mail.tests.common import mail_new_test_user
from odoo.tests import tagged
from odoo.tools.misc import mute_logger


@tagged('mail_followers')
class BaseFollowersTest(common.BaseFunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(BaseFollowersTest, cls).setUpClass()
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({'name': 'Test', 'email_from': 'ignasse@example.com'})
        cls._create_portal_user()
        cls._create_channel_listener()

        Subtype = cls.env['mail.message.subtype']
        cls.mt_mg_def = Subtype.create({'name': 'mt_mg_def', 'default': True, 'res_model': 'mail.test.simple'})
        cls.mt_cl_def = Subtype.create({'name': 'mt_cl_def', 'default': True, 'res_model': 'mail.test'})
        cls.mt_al_def = Subtype.create({'name': 'mt_al_def', 'default': True, 'res_model': False})
        cls.mt_mg_nodef = Subtype.create({'name': 'mt_mg_nodef', 'default': False, 'res_model': 'mail.test.simple'})
        cls.mt_al_nodef = Subtype.create({'name': 'mt_al_nodef', 'default': False, 'res_model': False})
        cls.mt_mg_def_int = cls.env['mail.message.subtype'].create({'name': 'mt_mg_def', 'default': True, 'res_model': 'mail.test.simple', 'internal': True})
        cls.default_group_subtypes = Subtype.search([('default', '=', True), '|', ('res_model', '=', 'mail.test.simple'), ('res_model', '=', False)])
        cls.default_group_subtypes_portal = Subtype.search([('internal', '=', False), ('default', '=', True), '|', ('res_model', '=', 'mail.test.simple'), ('res_model', '=', False)])

    def test_field_message_is_follower(self):
        test_record = self.test_record.with_user(self.user_employee)
        followed_before = test_record.search([('message_is_follower', '=', True)])
        self.assertFalse(test_record.message_is_follower)
        test_record.message_subscribe(partner_ids=[self.user_employee.partner_id.id])
        followed_after = test_record.search([('message_is_follower', '=', True)])
        self.assertTrue(test_record.message_is_follower)
        self.assertEqual(followed_before | test_record, followed_after)

    def test_field_followers(self):
        test_record = self.test_record.with_user(self.user_employee)
        test_record.message_subscribe(partner_ids=[self.user_employee.partner_id.id, self.user_admin.partner_id.id], channel_ids=[self.channel_listen.id])
        followers = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.test.simple'),
            ('res_id', '=', test_record.id)])
        self.assertEqual(followers, test_record.message_follower_ids)
        self.assertEqual(test_record.message_partner_ids, self.user_employee.partner_id | self.user_admin.partner_id)
        self.assertEqual(test_record.message_channel_ids, self.channel_listen)

    def test_followers_subtypes_default(self):
        test_record = self.test_record.with_user(self.user_employee)
        test_record.message_subscribe(partner_ids=[self.user_employee.partner_id.id])
        self.assertEqual(test_record.message_partner_ids, self.user_employee.partner_id)
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.test.simple'),
            ('res_id', '=', test_record.id),
            ('partner_id', '=', self.user_employee.partner_id.id)])
        self.assertEqual(follower, test_record.message_follower_ids)
        self.assertEqual(follower.subtype_ids, self.default_group_subtypes)

    def test_followers_subtypes_default_internal(self):
        test_record = self.test_record.with_user(self.user_employee)
        test_record.message_subscribe(partner_ids=[self.partner_portal.id])
        self.assertEqual(test_record.message_partner_ids, self.partner_portal)
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.test.simple'),
            ('res_id', '=', test_record.id),
            ('partner_id', '=', self.partner_portal.id)])
        self.assertEqual(follower.subtype_ids, self.default_group_subtypes_portal)

    def test_followers_subtypes_specified(self):
        test_record = self.test_record.with_user(self.user_employee)
        test_record.message_subscribe(partner_ids=[self.user_employee.partner_id.id], subtype_ids=[self.mt_mg_nodef.id])
        self.assertEqual(test_record.message_partner_ids, self.user_employee.partner_id)
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.test.simple'),
            ('res_id', '=', test_record.id),
            ('partner_id', '=', self.user_employee.partner_id.id)])
        self.assertEqual(follower, test_record.message_follower_ids)
        self.assertEqual(follower.subtype_ids, self.mt_mg_nodef)

    def test_followers_multiple_subscription_force(self):
        test_record = self.test_record.with_user(self.user_employee)

        test_record.message_subscribe(partner_ids=[self.user_admin.partner_id.id], subtype_ids=[self.mt_mg_nodef.id])
        self.assertEqual(test_record.message_partner_ids, self.user_admin.partner_id)
        self.assertEqual(test_record.message_channel_ids, self.env['mail.channel'])
        self.assertEqual(test_record.message_follower_ids.subtype_ids, self.mt_mg_nodef)

        test_record.message_subscribe(partner_ids=[self.user_admin.partner_id.id], subtype_ids=[self.mt_mg_nodef.id, self.mt_al_nodef.id])
        self.assertEqual(test_record.message_partner_ids, self.user_admin.partner_id)
        self.assertEqual(test_record.message_channel_ids, self.env['mail.channel'])
        self.assertEqual(test_record.message_follower_ids.subtype_ids, self.mt_mg_nodef | self.mt_al_nodef)

    def test_followers_multiple_subscription_noforce(self):
        """ Calling message_subscribe without subtypes on an existing subscription should not do anything (default < existing) """
        test_record = self.test_record.with_user(self.user_employee)

        test_record.message_subscribe(partner_ids=[self.user_admin.partner_id.id], subtype_ids=[self.mt_mg_nodef.id, self.mt_al_nodef.id])
        self.assertEqual(test_record.message_partner_ids, self.user_admin.partner_id)
        self.assertEqual(test_record.message_channel_ids, self.env['mail.channel'])
        self.assertEqual(test_record.message_follower_ids.subtype_ids, self.mt_mg_nodef | self.mt_al_nodef)

        # set new subtypes with force=False, meaning no rewriting of the subscription is done -> result should not change
        test_record.message_subscribe(partner_ids=[self.user_admin.partner_id.id])
        self.assertEqual(test_record.message_partner_ids, self.user_admin.partner_id)
        self.assertEqual(test_record.message_channel_ids, self.env['mail.channel'])
        self.assertEqual(test_record.message_follower_ids.subtype_ids, self.mt_mg_nodef | self.mt_al_nodef)

    def test_followers_multiple_subscription_update(self):
        """ Calling message_subscribe with subtypes on an existing subscription should replace them (new > existing) """
        test_record = self.test_record.with_user(self.user_employee)
        test_record.message_subscribe(partner_ids=[self.user_employee.partner_id.id], subtype_ids=[self.mt_mg_def.id, self.mt_cl_def.id])
        self.assertEqual(test_record.message_partner_ids, self.user_employee.partner_id)
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.test.simple'),
            ('res_id', '=', test_record.id),
            ('partner_id', '=', self.user_employee.partner_id.id)])
        self.assertEqual(follower, test_record.message_follower_ids)
        self.assertEqual(follower.subtype_ids, self.mt_mg_def | self.mt_cl_def)

        # remove one subtype `mt_mg_def` and set new subtype `mt_al_def`
        test_record.message_subscribe(partner_ids=[self.user_employee.partner_id.id], subtype_ids=[self.mt_cl_def.id, self.mt_al_def.id])
        self.assertEqual(follower.subtype_ids, self.mt_cl_def | self.mt_al_def)

    def test_followers_no_DID(self):
        """Test that a follower cannot suffer from dissociative identity disorder.
           It cannot be both a partner and a channel.
        """
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self.env['mail.followers'].create({
                'res_model': self.test_record._name,
                'res_id': self.test_record.id,
                'partner_id': self.user_employee.partner_id.id,
                'channel_id': self.channel_listen.id,
            })

    def test_followers_default_partner_context(self):
        """Test that a follower partner_id is not taken from context
           when channel id is also defined.
        """
        test_record = self.test_record.with_user(self.user_employee)
        test_record.with_context(default_partner_id=1).message_subscribe(
            partner_ids=[self.user_employee.partner_id.id, self.user_admin.partner_id.id],
            channel_ids=[self.channel_listen.id]
        )


@tagged('mail_followers')
class AdvancedFollowersTest(common.BaseFunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(AdvancedFollowersTest, cls).setUpClass()
        cls._create_portal_user()

        cls.test_track = cls.env['mail.test.track'].with_user(cls.user_employee).create({
            'name': 'Test',
        })

        Subtype = cls.env['mail.message.subtype']

        # clean demo data to avoid interferences
        Subtype.search([('res_model', 'in', ['mail.test', 'mail.test.track'])]).unlink()

        # mail.test.track subtypes (aka: task records)
        cls.sub_track_1 = Subtype.create({
            'name': 'Track (with child relation) 1', 'default': False,
            'res_model': 'mail.test.track'
        })
        cls.sub_track_2 = Subtype.create({
            'name': 'Track (with child relation) 2', 'default': False,
            'res_model': 'mail.test.track'
        })
        cls.sub_track_nodef = Subtype.create({
            'name': 'Generic Track subtype', 'default': False, 'internal': False,
            'res_model': 'mail.test.track'
        })
        cls.sub_track_def = Subtype.create({
            'name': 'Default track subtype', 'default': True, 'internal': False,
            'res_model': 'mail.test.track'
        })

        # mail.test subtypes (aka: project records)
        cls.umb_nodef = Subtype.create({
            'name': 'Umbrella NoDefault', 'default': False,
            'res_model': 'mail.test'
        })
        cls.umb_def = Subtype.create({
            'name': 'Umbrella Default', 'default': True,
            'res_model': 'mail.test'
        })
        cls.umb_def_int = Subtype.create({
            'name': 'Umbrella Default', 'default': True, 'internal': True,
            'res_model': 'mail.test'
        })
        # -> subtypes for auto subscription from umbrella to sub records
        cls.umb_autosub_def = Subtype.create({
            'name': 'Umbrella AutoSub (default)', 'default': True, 'res_model': 'mail.test',
            'parent_id': cls.sub_track_1.id, 'relation_field': 'umbrella_id'
        })
        cls.umb_autosub_nodef = Subtype.create({
            'name': 'Umbrella AutoSub 2', 'default': False, 'res_model': 'mail.test',
            'parent_id': cls.sub_track_2.id, 'relation_field': 'umbrella_id'
        })

        # generic subtypes
        cls.sub_comment = cls.env.ref('mail.mt_comment')
        cls.sub_generic_int_nodef = Subtype.create({
            'name': 'Generic internal subtype',
            'default': False,
            'internal': True,
        })
        cls.sub_generic_int_def = Subtype.create({
            'name': 'Generic internal subtype (default)',
            'default': True,
            'internal': True,
        })

    def test_auto_subscribe_create(self):
        """ Creator of records are automatically added as followers """
        self.assertEqual(self.test_track.message_partner_ids, self.user_employee.partner_id)

    def test_auto_subscribe_post(self):
        """ People posting a message are automatically added as followers """
        self.test_track.with_user(self.user_admin).message_post(body='Coucou hibou', message_type='comment')
        self.assertEqual(self.test_track.message_partner_ids, self.user_employee.partner_id | self.user_admin.partner_id)

    def test_auto_subscribe_post_email(self):
        """ People posting an email are automatically added as followers """
        self.test_track.with_user(self.user_admin).message_post(body='Coucou hibou', message_type='email')
        self.assertEqual(self.test_track.message_partner_ids, self.user_employee.partner_id | self.user_admin.partner_id)

    def test_auto_subscribe_not_on_notification(self):
        """ People posting an automatic notification are not subscribed """
        self.test_track.with_user(self.user_admin).message_post(body='Coucou hibou', message_type='notification')
        self.assertEqual(self.test_track.message_partner_ids, self.user_employee.partner_id)

    def test_auto_subscribe_responsible(self):
        """ Responsibles are tracked and added as followers """
        sub = self.env['mail.test.track'].with_user(self.user_employee).create({
            'name': 'Test',
            'user_id': self.user_admin.id,
        })
        self.assertEqual(sub.message_partner_ids, (self.user_employee.partner_id | self.user_admin.partner_id))

    def test_auto_subscribe_defaults(self):
        """ Test auto subscription based on an umbrella record. This mimics
        the behavior of addons like project and task where subscribing to
        some project's subtypes automatically subscribe the follower to its tasks.

        Functional rules applied here

         * subscribing to an umbrella subtype with parent_id / relation_field set
           automatically create subscription with matching subtypes
         * subscribing to a sub-record as creator applies default subtype values
         * portal user should not have access to internal subtypes
        """
        umbrella = self.env['mail.test'].with_context(self._test_context).create({
            'name': 'Project-Like',
        })

        umbrella.message_subscribe(partner_ids=self.partner_portal.ids)
        umbrella.message_subscribe(partner_ids=self.partner_admin.ids, subtype_ids=(self.sub_comment | self.umb_autosub_nodef | self.sub_generic_int_nodef).ids)
        self.assertEqual(umbrella.message_partner_ids, self.partner_portal | self.partner_admin)
        follower_por = umbrella.message_follower_ids.filtered(lambda f: f.partner_id == self.partner_portal)
        follower_adm = umbrella.message_follower_ids.filtered(lambda f: f.partner_id == self.partner_admin)
        self.assertEqual(
            follower_por.subtype_ids,
            self.sub_comment | self.umb_def | self.umb_autosub_def,
            'Subscribe: Default subtypes: comment (default generic) and two model-related defaults')
        self.assertEqual(
            follower_adm.subtype_ids,
            self.sub_comment | self.umb_autosub_nodef | self.sub_generic_int_nodef,
            'Subscribe: Asked subtypes when subscribing')

        sub1 = self.env['mail.test.track'].with_user(self.user_employee).create({
            'name': 'Task-Like Test',
            'umbrella_id': umbrella.id,
        })

        self.assertEqual(
            sub1.message_partner_ids, self.partner_portal | self.partner_admin | self.user_employee.partner_id,
            'Followers: creator (employee) + auto subscribe from parent (portal)')
        follower_por = sub1.message_follower_ids.filtered(lambda fol: fol.partner_id == self.partner_portal)
        follower_adm = sub1.message_follower_ids.filtered(lambda fol: fol.partner_id == self.partner_admin)
        follower_emp = sub1.message_follower_ids.filtered(lambda fol: fol.partner_id == self.user_employee.partner_id)
        self.assertEqual(
            follower_por.subtype_ids, self.sub_comment | self.sub_track_1,
            'AutoSubscribe: comment (generic checked), Track (with child relation) 1 as Umbrella AutoSub (default) was checked'
        )
        self.assertEqual(
            follower_adm.subtype_ids, self.sub_comment | self.sub_track_2 | self.sub_generic_int_nodef,
            'AutoSubscribe: comment (generic checked), Track (with child relation) 2) as Umbrella AutoSub 2 was checked, Generic internal subtype (generic checked)'
        )
        self.assertEqual(
            follower_emp.subtype_ids, self.sub_comment | self.sub_track_def | self.sub_generic_int_def,
            'AutoSubscribe: only default one as no subscription on parent'
        )

        # check portal generic subscribe
        sub1.message_unsubscribe(partner_ids=self.partner_portal.ids)
        sub1.message_subscribe(partner_ids=self.partner_portal.ids)
        follower_por = sub1.message_follower_ids.filtered(lambda fol: fol.partner_id == self.partner_portal)
        self.assertEqual(
            follower_por.subtype_ids, self.sub_comment | self.sub_track_def,
            'AutoSubscribe: only default one as no subscription on parent (no internal as portal)'
        )

        # check auto subscribe as creator + auto subscribe as parent follower takes both subtypes
        umbrella.message_subscribe(
            partner_ids=self.user_employee.partner_id.ids,
            subtype_ids=(self.sub_comment | self.sub_generic_int_nodef | self.umb_autosub_nodef).ids)
        sub2 = self.env['mail.test.track'].with_user(self.user_employee).create({
            'name': 'Task-Like Test',
            'umbrella_id': umbrella.id,
        })
        follower_emp = sub2.message_follower_ids.filtered(lambda fol: fol.partner_id == self.user_employee.partner_id)
        defaults = self.sub_comment | self.sub_track_def | self.sub_generic_int_def
        parents = self.sub_generic_int_nodef | self.sub_track_2
        self.assertEqual(
            follower_emp.subtype_ids, defaults + parents,
            'AutoSubscribe: at create auto subscribe as creator + from parent take both subtypes'
        )


class AdvancedResponsibleNotifiedTest(common.BaseFunctionalTest):
    def setUp(self):
        super(AdvancedResponsibleNotifiedTest, self).setUp()

        # patch registry to simulate a ready environment so that _message_auto_subscribe_notify
        # will be executed with the associated notification
        old = self.env.registry.ready
        self.env.registry.ready = True
        self.addCleanup(setattr, self.env.registry, 'ready', old)

    def test_auto_subscribe_notify_email(self):
        """ Responsible is notified when assigned """
        partner = self.env['res.partner'].create({"name": "demo1", "email": "demo1@test.com"})
        notified_user = self.env['res.users'].create({
            'login': 'demo1',
            'partner_id': partner.id,
            'notification_type': 'email',
        })

        # TODO master: add a 'state' selection field on 'mail.test.track' with a 'done' value to have a complete test
        # check that 'default_state' context does not collide with mail.mail default values
        sub = self.env['mail.test.track'].with_user(self.user_employee).with_context({
            'default_state': 'done',
            'mail_notify_force_send': False
        }).create({
            'name': 'Test',
            'user_id': notified_user.id,
        })

        self.assertEqual(sub.message_partner_ids, (self.user_employee.partner_id | notified_user.partner_id))
        # fetch created "You have been assigned to 'Test'" mail.message
        mail_message = self.env['mail.message'].search([
            ('model', '=', 'mail.test.track'),
            ('res_id', '=', sub.id),
            ('partner_ids', 'in', partner.id),
        ])
        self.assertEqual(1, len(mail_message))

        # verify that a mail.mail is attached to it with the correct state ('outgoing')
        mail_notification = mail_message.notification_ids
        self.assertEqual(1, len(mail_notification))
        self.assertTrue(bool(mail_notification.mail_id))
        self.assertEqual('outgoing', mail_notification.mail_id.state)


@tagged('post_install', '-at_install')
class DuplicateNotificationTest(common.BaseFunctionalTest):
    def test_no_duplicate_notification(self):
        """
        Check that we only create one mail.notification per partner

        Post install because we need the registery to be ready to send notification
        """
        #Simulate case of 2 users that got their partner merged
        common_partner = self.env['res.partner'].create({"name": "demo1", "email": "demo1@test.com"})
        user_1 = self.env['res.users'].create({'login': 'demo1', 'partner_id': common_partner.id, 'notification_type': 'email'})
        user_2 = self.env['res.users'].create({'login': 'demo2', 'partner_id': common_partner.id, 'notification_type': 'inbox'})

        #Trigger auto subscribe notification
        test = self.env['mail.test.track'].create({"name": "Test Track", "user_id": user_2.id})
        mail_message = self.env['mail.message'].search([
             ('res_id', '=', test.id),
             ('model', '=', 'mail.test.track'),
             ('message_type', '=', 'user_notification')
        ])
        notif = self.env['mail.notification'].search([
            ('mail_message_id', '=', mail_message.id),
            ('res_partner_id', '=', common_partner.id)
        ])
        self.assertEqual(len(notif), 1)
        self.assertEqual(notif.notification_type, 'email')

        subtype = self.env.ref('mail.mt_comment')
        res = self.env['mail.followers']._get_recipient_data(test, 'comment',  subtype.id, pids=common_partner.ids)
        partner_notif = [r for r in res if r[0] == common_partner.id]
        self.assertEqual(len(partner_notif), 1)
        self.assertEqual(partner_notif[0][5], 'email')

@tagged('post_install', '-at_install')
class UnlinkedNotificationTest(common.BaseFunctionalTest):
    def test_unlinked_notification(self):
        """
        Check that we unlink the created user_notification after unlinked the related document

        Post install because we need the registery to be ready to send notification
        """
        common_partner = self.env['res.partner'].create({"name": "demo1", "email": "demo1@test.com"})
        user_1 = self.env['res.users'].create({'login': 'demo1', 'partner_id': common_partner.id, 'notification_type': 'inbox'})

        test = self.env['mail.test.track'].create({"name": "Test Track", "user_id": user_1.id})
        test_id = test.id
        mail_message = self.env['mail.message'].search([
             ('res_id', '=', test_id),
             ('model', '=', 'mail.test.track'),
             ('message_type', '=', 'user_notification')
        ])
        self.assertEqual(len(mail_message), 1)
        test.unlink()
        mail_message = self.env['mail.message'].search([
             ('res_id', '=', test_id),
             ('model', '=', 'mail.test.track'),
             ('message_type', '=', 'user_notification')
        ])
        self.assertEqual(len(mail_message), 0)
