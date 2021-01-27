# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError

from odoo.addons.test_mail.tests import common
from odoo.addons.test_mail.tests.common import mail_new_test_user
from odoo.tests import tagged
from odoo.tools.misc import mute_logger
from odoo.tests import tagged


@tagged('mail_followers')
class BaseFollowersTest(common.BaseFunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(BaseFollowersTest, cls).setUpClass()
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
        test_record = self.test_record.sudo(self.user_employee)
        followed_before = test_record.search([('message_is_follower', '=', True)])
        self.assertFalse(test_record.message_is_follower)
        test_record.message_subscribe(partner_ids=[self.user_employee.partner_id.id])
        followed_after = test_record.search([('message_is_follower', '=', True)])
        self.assertTrue(test_record.message_is_follower)
        self.assertEqual(followed_before | test_record, followed_after)

    def test_field_followers(self):
        test_record = self.test_record.sudo(self.user_employee)
        test_record.message_subscribe(partner_ids=[self.user_employee.partner_id.id, self.user_admin.partner_id.id], channel_ids=[self.channel_listen.id])
        followers = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.test.simple'),
            ('res_id', '=', test_record.id)])
        self.assertEqual(followers, test_record.message_follower_ids)
        self.assertEqual(test_record.message_partner_ids, self.user_employee.partner_id | self.user_admin.partner_id)
        self.assertEqual(test_record.message_channel_ids, self.channel_listen)

    def test_followers_subtypes_default(self):
        test_record = self.test_record.sudo(self.user_employee)
        test_record.message_subscribe(partner_ids=[self.user_employee.partner_id.id])
        self.assertEqual(test_record.message_partner_ids, self.user_employee.partner_id)
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.test.simple'),
            ('res_id', '=', test_record.id),
            ('partner_id', '=', self.user_employee.partner_id.id)])
        self.assertEqual(follower, test_record.message_follower_ids)
        self.assertEqual(follower.subtype_ids, self.default_group_subtypes)

    def test_followers_subtypes_default_internal(self):
        user_portal = mail_new_test_user(self.env, login='chell', groups='base.group_portal', name='Chell Gladys')

        test_record = self.test_record.sudo(self.user_employee)
        test_record.message_subscribe(partner_ids=[user_portal.partner_id.id])
        self.assertEqual(test_record.message_partner_ids, user_portal.partner_id)
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.test.simple'),
            ('res_id', '=', test_record.id),
            ('partner_id', '=', user_portal.partner_id.id)])
        self.assertEqual(follower.subtype_ids, self.default_group_subtypes_portal)

    def test_followers_subtypes_specified(self):
        test_record = self.test_record.sudo(self.user_employee)
        test_record.message_subscribe(partner_ids=[self.user_employee.partner_id.id], subtype_ids=[self.mt_mg_nodef.id])
        self.assertEqual(test_record.message_partner_ids, self.user_employee.partner_id)
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.test.simple'),
            ('res_id', '=', test_record.id),
            ('partner_id', '=', self.user_employee.partner_id.id)])
        self.assertEqual(follower, test_record.message_follower_ids)
        self.assertEqual(follower.subtype_ids, self.mt_mg_nodef)

    def test_followers_multiple_subscription_force(self):
        test_record = self.test_record.sudo(self.user_employee)

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
        test_record = self.test_record.sudo(self.user_employee)

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
        test_record = self.test_record.sudo(self.user_employee)
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
        test_record = self.test_record.sudo(self.user_employee)
        test_record.with_context(default_partner_id=1).message_subscribe(
            partner_ids=[self.user_employee.partner_id.id, self.user_admin.partner_id.id],
            channel_ids=[self.channel_listen.id]
        )


@tagged('mail_followers')
class AdvancedFollowersTest(common.BaseFunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(AdvancedFollowersTest, cls).setUpClass()

        cls.user_portal = mail_new_test_user(cls.env, login='chell', groups='base.group_portal', name='Chell Gladys')
        cls.partner_portal = cls.user_portal.partner_id

        cls.test_track = cls.env['mail.test.track'].sudo(cls.user_employee).create({
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
        self.test_track.sudo(self.user_admin).message_post(body='Coucou hibou', message_type='comment')
        self.assertEqual(self.test_track.message_partner_ids, self.user_employee.partner_id | self.user_admin.partner_id)

    def test_auto_subscribe_post_email(self):
        """ People posting an email are automatically added as followers """
        self.test_track.sudo(self.user_admin).message_post(body='Coucou hibou', message_type='email')
        self.assertEqual(self.test_track.message_partner_ids, self.user_employee.partner_id | self.user_admin.partner_id)

    def test_auto_subscribe_not_on_notification(self):
        """ People posting an automatic notification are not subscribed """
        self.test_track.sudo(self.user_admin).message_post(body='Coucou hibou', message_type='notification')
        self.assertEqual(self.test_track.message_partner_ids, self.user_employee.partner_id)

    def test_auto_subscribe_responsible(self):
        """ Responsibles are tracked and added as followers """
        sub = self.env['mail.test.track'].sudo(self.user_employee).create({
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
        umbrella = self.env['mail.test'].with_context(common.BaseFunctionalTest._test_context).create({
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

        sub1 = self.env['mail.test.track'].sudo(self.user_employee).create({
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
        sub2 = self.env['mail.test.track'].sudo(self.user_employee).create({
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
