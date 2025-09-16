# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from unittest.mock import patch
from urllib.parse import urlparse

from markupsafe import Markup

from odoo import Command
from odoo.addons.mail.models.mail_mail import _UNFOLLOW_REGEX
from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError
from odoo.tests import tagged, users
from odoo.tests.common import HttpCase
from odoo.tools import mute_logger


@tagged('mail_followers')
class BaseFollowersTest(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(BaseFollowersTest, cls).setUpClass()
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({'name': 'Test', 'email_from': 'ignasse@example.com'})
        cls._create_portal_user()

        Subtype = cls.env['mail.message.subtype']
        # global
        cls.mt_al_def = Subtype.create({'name': 'mt_al_def', 'default': True, 'res_model': False})
        cls.mt_al_nodef = Subtype.create({'name': 'mt_al_nodef', 'default': False, 'res_model': False})
        # mail.test.simple
        cls.mt_mg_def = Subtype.create({'name': 'mt_mg_def', 'default': True, 'res_model': 'mail.test.simple'})
        cls.mt_mg_nodef = Subtype.create({'name': 'mt_mg_nodef', 'default': False, 'res_model': 'mail.test.simple'})
        cls.mt_mg_def_int = Subtype.create({'name': 'mt_mg_def', 'default': True, 'res_model': 'mail.test.simple', 'internal': True})
        # mail.test.container
        cls.mt_cl_def = Subtype.create({'name': 'mt_cl_def', 'default': True, 'res_model': 'mail.test.container'})

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

    def test_field_message_partner_ids(self):
        test_record = self.test_record.with_user(self.user_employee)
        partner = self.user_employee.partner_id
        followed_before = self.env['mail.test.simple'].search([('message_partner_ids', 'in', partner.ids)])
        self.assertFalse(partner in test_record.message_partner_ids)
        self.assertNotIn(test_record, followed_before)
        test_record.message_subscribe(partner_ids=[partner.id])
        followed_after = self.env['mail.test.simple'].search([('message_partner_ids', 'in', partner.ids)])
        self.assertTrue(partner in test_record.message_partner_ids)
        self.assertEqual(followed_before + test_record, followed_after)
        with self.assertRaisesRegex(AccessError, 'Portal users can only filter threads'):
            self.env['mail.test.simple'].with_user(self.user_portal).search([('message_partner_ids', 'in', partner.ids)])

    def test_field_followers(self):
        test_record = self.test_record.with_user(self.user_employee)
        test_record.message_subscribe(partner_ids=[self.user_employee.partner_id.id, self.user_admin.partner_id.id])
        followers = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.test.simple'),
            ('res_id', '=', test_record.id)])
        self.assertEqual(followers, test_record.message_follower_ids)
        self.assertEqual(test_record.message_partner_ids, self.user_employee.partner_id | self.user_admin.partner_id)

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
        self.assertEqual(test_record.message_follower_ids.subtype_ids, self.mt_mg_nodef)

        test_record.message_subscribe(partner_ids=[self.user_admin.partner_id.id], subtype_ids=[self.mt_mg_nodef.id, self.mt_al_nodef.id])
        self.assertEqual(test_record.message_partner_ids, self.user_admin.partner_id)
        self.assertEqual(test_record.message_follower_ids.subtype_ids, self.mt_mg_nodef | self.mt_al_nodef)

    def test_followers_multiple_subscription_noforce(self):
        """ Calling message_subscribe without subtypes on an existing subscription should not do anything (default < existing) """
        test_record = self.test_record.with_user(self.user_employee)

        test_record.message_subscribe(partner_ids=[self.user_admin.partner_id.id], subtype_ids=[self.mt_mg_nodef.id, self.mt_al_nodef.id])
        self.assertEqual(test_record.message_partner_ids, self.user_admin.partner_id)
        self.assertEqual(test_record.message_follower_ids.subtype_ids, self.mt_mg_nodef | self.mt_al_nodef)

        # set new subtypes with force=False, meaning no rewriting of the subscription is done -> result should not change
        test_record.message_subscribe(partner_ids=[self.user_admin.partner_id.id])
        self.assertEqual(test_record.message_partner_ids, self.user_admin.partner_id)
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

    @users('employee')
    def test_followers_inactive(self):
        """ Test standard API does not subscribe inactive partners """
        customer = self.env['res.partner'].create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com',
            'country_id': self.env.ref('base.be').id,
            'phone': '0456001122',
            'active': False,
        })
        document = self.env['mail.test.simple'].browse(self.test_record.id)
        self.assertEqual(document.message_partner_ids, self.env['res.partner'])
        document.message_subscribe(partner_ids=(self.partner_portal | customer).ids)
        self.assertEqual(document.message_partner_ids, self.partner_portal)
        self.assertEqual(document.message_follower_ids.partner_id, self.partner_portal)

        # works through low-level API
        document._message_subscribe(partner_ids=(self.partner_portal | customer).ids)
        self.assertEqual(document.message_partner_ids, self.partner_portal, 'No active test: customer not visible')
        self.assertEqual(document.message_follower_ids.partner_id, self.partner_portal | customer)

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_followers_inverse_message_partner(self):
        test_record = self.test_record.with_env(self.env)
        partner0, partner1, partner2, partner3 = self.env['res.partner'].create(
            [{'email': f'partner.{n}@test.lan', 'name': f'partner{n}'} for n in range(4)]
        )
        self.assertFalse(test_record.message_follower_ids)
        self.assertFalse(test_record.message_partner_ids)

        # fillup with API
        test_record.message_subscribe(partner_ids=partner3.ids)
        self.assertEqual(test_record.message_follower_ids.partner_id, partner3)
        # set empty
        test_record.message_partner_ids = None
        self.assertFalse(test_record.message_follower_ids.partner_id)
        # set 1
        test_record.message_partner_ids = partner0
        self.assertEqual(test_record.message_follower_ids.partner_id, partner0)
        # set multiple when non-empty
        test_record.message_partner_ids = partner1 + partner2
        self.assertEqual(test_record.message_follower_ids.partner_id, partner1 + partner2)
        # remove 1
        test_record.message_partner_ids -= partner1
        self.assertEqual(test_record.message_follower_ids.partner_id, partner2)
        # add multiple with one already set
        test_record.message_partner_ids += partner1 + partner2
        self.assertEqual(test_record.message_follower_ids.partner_id, partner1 + partner2)
        # remove outside of existing
        test_record.message_partner_ids -= partner3
        self.assertEqual(test_record.message_follower_ids.partner_id, partner1 + partner2)
        # reset
        test_record.message_partner_ids = False
        self.assertFalse(test_record.message_follower_ids.partner_id)

        # test with inactive and commands
        partner0.write({'active': False})
        test_record.write({'message_partner_ids': [(4, partner0.id), (4, partner1.id)]})
        self.assertEqual(test_record.message_follower_ids.partner_id, partner1)

        # Test when the method inverse is called in batch
        other_record = test_record.create({
            'name': 'Other',
        })
        records = test_record + other_record

        records.message_partner_ids = (partner2 + partner3)
        self.assertEqual(records.message_partner_ids, partner2 + partner3)

        records.message_partner_ids -= partner2
        self.assertEqual(records.message_partner_ids, partner3)

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_followers_inverse_message_partner_access_rights(self):
        """ Make sure we're not bypassing security checks by setting a partner
        instead of a follower """
        test_record = self.test_record.with_user(self.user_portal)
        partner0 = self.env['res.partner'].create({
            'email': 'partner1@test.lan',
            'name': 'partner1',
        })
        _name = test_record.name  # check portal user can read

        # set empty
        with self.assertRaises(AccessError):
            test_record.message_partner_ids = None
        # set 1
        with self.assertRaises(AccessError):
            test_record.message_partner_ids = partner0
        # remove 1
        with self.assertRaises(AccessError):
            test_record.message_partner_ids -= partner0

    @users('employee')
    def test_followers_private_address(self):
        """ Test standard API does subscribe IDs the user can't read """
        other_company = self.env['res.company'].sudo().create({'name': 'Other Company'})
        private_address = self.env['res.partner'].create({
            'name': 'Private Address',
            'company_id': other_company.id,
        })
        self.env.user.write({'company_ids': [(3, other_company.id)]})
        document = self.env['mail.test.simple'].browse(self.test_record.id)
        document.message_subscribe(partner_ids=(self.partner_portal | private_address).ids)
        self.assertEqual(document.message_follower_ids.partner_id, self.partner_portal | private_address)

        # works through low-level API
        document._message_subscribe(partner_ids=(self.partner_portal | private_address).ids)
        self.assertEqual(document.message_follower_ids.partner_id, self.partner_portal | private_address)

    @users('employee')
    def test_create_multi_followers(self):
        documents = self.env['mail.test.simple'].create([{'name': 'ninja'}] * 5)
        for document in documents:
            self.assertEqual(document.message_follower_ids.partner_id, self.env.user.partner_id)
            self.assertEqual(document.message_follower_ids.subtype_ids, self.default_group_subtypes)

    @users('employee')
    def test_subscriptions_data_fetch(self):
        """ Test that _get_subscription_data gives correct values when modifying followers manually."""
        test_record = self.test_record
        test_record_copy = self.test_record.copy()
        test_records = test_record + test_record_copy
        test_record.message_subscribe([self.user_employee.partner_id.id])
        subscription_data = self.env['mail.followers']._get_subscription_data([(test_records._name, test_records.ids)], None)
        self.assertEqual(len(subscription_data), 1)
        self.assertEqual(subscription_data[0][1], test_record.id)
        self.env['mail.followers'].browse(subscription_data[0][0]).sudo().res_id = test_record_copy
        subscription_data = self.env['mail.followers']._get_subscription_data([(test_records._name, test_records.ids)], None)
        self.assertEqual(len(subscription_data), 1)
        self.assertEqual(subscription_data[0][1], test_record_copy.id)


@tagged('mail_followers')
class AdvancedFollowersTest(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(AdvancedFollowersTest, cls).setUpClass()
        cls._create_portal_user()

        cls.test_track = cls.env['mail.test.track'].with_user(cls.user_employee).create({
            'name': 'Test',
        })

        Subtype = cls.env['mail.message.subtype']

        # clean demo data to avoid interferences
        Subtype.search([('res_model', 'in', ['mail.test.container', 'mail.test.track'])]).unlink()

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
        cls.sub_track_parent_def = Subtype.create({
            'name': 'Parent track subtype', 'default': False, 'res_model': 'mail.test.track',
            'parent_id': cls.sub_track_def.id, 'relation_field': 'parent_id'
        })

        # mail.test.container subtypes (aka: project records)
        cls.umb_nodef = Subtype.create({
            'name': 'Container NoDefault', 'default': False,
            'res_model': 'mail.test.container'
        })
        cls.umb_def = Subtype.create({
            'name': 'Container Default', 'default': True,
            'res_model': 'mail.test.container'
        })
        cls.umb_def_int = Subtype.create({
            'name': 'Container Default', 'default': True, 'internal': True,
            'res_model': 'mail.test.container'
        })
        # -> subtypes for auto subscription from container to sub records
        cls.umb_autosub_def = Subtype.create({
            'name': 'Container AutoSub (default)', 'default': True, 'res_model': 'mail.test.container',
            'parent_id': cls.sub_track_1.id, 'relation_field': 'container_id'
        })
        cls.umb_autosub_nodef = Subtype.create({
            'name': 'Container AutoSub 2', 'default': False, 'res_model': 'mail.test.container',
            'parent_id': cls.sub_track_2.id, 'relation_field': 'container_id'
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
        for user, should_subscribe in [
            (self.user_root, False),
            (self.user_employee, True),
            (self.user_portal, False),
        ]:
            with self.subTest(user_name=user.name):
                # sudo, as done through mailgateway for example
                if user == self.user_portal:
                    new_rec = self.env['mail.test.track'].with_user(user).sudo().create({})
                else:
                    new_rec = self.env['mail.test.track'].with_user(user).create({})
                self.assertEqual(new_rec.message_partner_ids, user.partner_id if should_subscribe else self.env['res.partner'])

    @mute_logger('odoo.models.unlink')
    def test_auto_subscribe_inactive(self):
        """ Test inactive are not added as followers in automated subscription """
        self.test_track.user_id = False
        self.user_admin.active = False
        self.user_admin.flush_recordset()
        self.partner_admin.active = False
        self.partner_admin.flush_recordset()

        self.test_track.with_user(self.user_admin).message_post(body='Coucou hibou', message_type='comment')
        self.assertEqual(self.test_track.message_partner_ids, self.user_employee.partner_id)
        self.assertEqual(self.test_track.message_follower_ids.partner_id, self.user_employee.partner_id)

        self.test_track.write({'user_id': self.user_admin.id})
        self.assertEqual(self.test_track.message_partner_ids, self.user_employee.partner_id)
        self.assertEqual(self.test_track.message_follower_ids.partner_id, self.user_employee.partner_id)

        new_record = self.env['mail.test.track'].with_user(self.user_admin).create({
            'name': 'Test',
        })
        self.assertFalse(new_record.message_partner_ids,
                         'Filters out inactive partners')
        self.assertFalse(new_record.message_follower_ids.partner_id,
                         'Does not subscribe inactive partner')

    def test_auto_subscribe_post(self):
        """ People posting a discussion message are automatically added as
        followers """
        record = self.test_track.with_user(self.user_admin)
        for message_type, subtype, should_subscribe in [
            ('comment', self.env.ref('mail.mt_note'), False),
            ('comment', self.env.ref('mail.mt_comment'), True),
            ('email_outgoing', self.env.ref('mail.mt_note'), False),
            ('email_outgoing', self.env.ref('mail.mt_comment'), True),
            ('notification', self.env.ref('mail.mt_comment'), False),
        ]:
            with self.subTest(message_type=message_type, subtype_name=subtype.name):
                record.message_unsubscribe(partner_ids=self.user_admin.partner_id.ids)
                record.message_post(
                    body=f'Posting with {message_type} {subtype.name}',
                    message_type=message_type,
                    subtype_id=subtype.id,
                )
                if should_subscribe:
                    self.assertIn(self.user_admin.partner_id, record.message_partner_ids)
                else:
                    self.assertNotIn(self.user_admin.partner_id, record.message_partner_ids)

    def test_auto_subscribe_responsible(self):
        """ Responsibles are tracked and added as followers """
        sub = self.env['mail.test.track'].with_user(self.user_employee).create({
            'name': 'Test',
            'user_id': self.user_admin.id,
        })
        self.assertEqual(sub.message_partner_ids, (self.user_employee.partner_id | self.user_admin.partner_id))

    @mute_logger('odoo.models.unlink')
    def test_auto_subscribe_defaults(self):
        """ Test auto subscription based on an container record. This mimics
        the behavior of addons like project and task where subscribing to
        some project's subtypes automatically subscribe the follower to its tasks.

        Functional rules applied here

         * subscribing to an container subtype with parent_id / relation_field set
           automatically create subscription with matching subtypes
         * subscribing to a sub-record as creator applies default subtype values
         * portal user should not have access to internal subtypes

        Inactive partners should not be auto subscribed.
        """
        container = self.env['mail.test.container'].with_context(self._test_context).create({
            'name': 'Project-Like',
        })

        # have an inactive partner to check auto subscribe does not subscribe it
        user_root = self.env.ref('base.user_root')
        self.assertFalse(user_root.active)
        self.assertFalse(user_root.partner_id.active)

        container.message_subscribe(partner_ids=(self.partner_portal | user_root.partner_id).ids)
        container.message_subscribe(partner_ids=self.partner_admin.ids, subtype_ids=(self.sub_comment | self.umb_autosub_nodef | self.sub_generic_int_nodef).ids)
        self.assertEqual(container.message_partner_ids, self.partner_portal | self.partner_admin)
        follower_por = container.message_follower_ids.filtered(lambda f: f.partner_id == self.partner_portal)
        follower_adm = container.message_follower_ids.filtered(lambda f: f.partner_id == self.partner_admin)
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
            'container_id': container.id,
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
        container.message_subscribe(
            partner_ids=self.user_employee.partner_id.ids,
            subtype_ids=(self.sub_comment | self.sub_generic_int_nodef | self.umb_autosub_nodef).ids)
        sub2 = self.env['mail.test.track'].with_user(self.user_employee).create({
            'name': 'Task-Like Test',
            'container_id': container.id,
        })
        follower_emp = sub2.message_follower_ids.filtered(lambda fol: fol.partner_id == self.user_employee.partner_id)
        defaults = self.sub_comment | self.sub_track_def | self.sub_generic_int_def
        parents = self.sub_generic_int_nodef | self.sub_track_2
        self.assertEqual(
            follower_emp.subtype_ids, defaults + parents,
            'AutoSubscribe: at create auto subscribe as creator + from parent take both subtypes'
        )

        container.message_follower_ids = [Command.clear()]
        parent_track = self.env['mail.test.track'].with_user(self.user_employee).create({
            'name': 'Task-Like',
            'container_id': container.id,
        })

        child_track = self.env['mail.test.track'].with_user(self.user_admin).create({
            'name': 'Task-Like Test-sub-task',
            'parent_id': parent_track.id,
            'container_id': container.id,
        })
        self.assertIn(self.user_employee.partner_id, child_track.message_follower_ids.partner_id, 'The partner from the parent has not been added as follower.')


@tagged('mail_followers')
class AdvancedResponsibleNotifiedTest(MailCommon):

    def setUp(self):
        super(AdvancedResponsibleNotifiedTest, self).setUp()

        # patch registry to simulate a ready environment so that _message_auto_subscribe_notify
        # will be executed with the associated notification
        old = self.env.registry.ready
        self.env.registry.ready = True
        self.addCleanup(setattr, self.env.registry, 'ready', old)

    def test_auto_subscribe_notify_email(self):
        """ Responsible is notified when assigned """
        partner = self.env['res.partner'].create({"name": "demo1", "email": "demo1@test.mycompany.com"})
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
        self.assertTrue(bool(mail_notification.mail_mail_id))
        self.assertEqual(mail_notification.mail_mail_id.state, 'outgoing')


@tagged('mail_followers', 'post_install', '-at_install')
class RecipientsNotificationTest(MailCommon):
    """ Test advanced and complex recipients computation / notification, such
    as multiple users, batch computation, ... Post install because we need the
    registry to be ready to send notifications."""

    @classmethod
    def setUpClass(cls):
        super(RecipientsNotificationTest, cls).setUpClass()

        # portal user for testing share status / internal subtypes
        cls.user_portal = cls._create_portal_user()
        cls.partner_portal = cls.user_portal.partner_id

        # simple customer
        cls.customer = cls.env['res.partner'].create({
            'email': 'customer@test.customer.com',
            'name': 'Customer',
            'phone': '+32455778899',
        })

        # Simulate case of 2 users that got their partner merged
        cls.common_partner = cls.env['res.partner'].create({
            'email': 'common.partner@test.customer.com',
            'name': 'Common Partner',
            'phone': '+32455998877',
        })
        cls.user_1, cls.user_2 = cls.env['res.users'].with_context(no_reset_password=True).create([
            {'group_ids': [(4, cls.env.ref('base.group_portal').id)],
             'login': '_login_portal',
             'notification_type': 'email',
             'partner_id': cls.common_partner.id,
            },
            {'group_ids': [(4, cls.env.ref('base.group_user').id)],
             'login': '_login_internal',
             'notification_type': 'inbox',
             'partner_id': cls.common_partner.id,
            }
        ])
        cls.env.flush_all()

    def assertRecipientsData(self, recipients_data, records, partners, partner_to_users=None):
        """ Custom assert as recipients structure is custom and may change due
        to some implementation choice. """
        if records:
            self.assertEqual(set(recipients_data.keys()), set(records.ids))
            record_ids = records.ids
        else:
            records, record_ids = [False], [0]
        for record, record_id in zip(records, record_ids):
            record_data = recipients_data[record_id]
            self.assertEqual(set(record_data.keys()), set(partners.ids))
            for partner in partners:
                partner_data = record_data[partner.id]
                if partner_to_users and partner_to_users.get(partner.id):  #helps making test explicit
                    user = partner_to_users[partner.id]
                else:
                    user = next((user for user in partner.user_ids if not user.share), self.env['res.users'])
                    if not user:
                        user = next((user for user in partner.user_ids), self.env['res.users'])
                self.assertEqual(partner_data['active'], partner.active)
                self.assertEqual(partner_data['email_normalized'], partner.email_normalized)
                self.assertEqual(partner_data['lang'], partner.lang)
                self.assertEqual(partner_data['name'], partner.name)
                if user:
                    self.assertEqual(partner_data['groups'], set(user.all_group_ids.ids))
                    self.assertEqual(partner_data['notif'], user.notification_type)
                    self.assertEqual(partner_data['uid'], user.id)
                else:
                    self.assertEqual(partner_data['groups'], set())
                    self.assertEqual(partner_data['notif'], 'email')
                    self.assertFalse(partner_data['uid'])
                if record:
                    self.assertEqual(partner_data['is_follower'], partner in record.message_partner_ids)
                else:
                    self.assertFalse(partner_data['is_follower'])
                self.assertEqual(partner_data['share'], partner.partner_share)
                self.assertEqual(partner_data['ushare'], user.share)

    @users('employee')
    def test_notification_nodupe(self):
        """ Check that we only create one mail.notification per partner. """
        # Trigger auto subscribe notification
        test = self.env['mail.test.track'].create({"name": "Test Track", "user_id": self.user_2.id})
        mail_message = self.env['mail.message'].search([
            ('res_id', '=', test.id),
            ('model', '=', 'mail.test.track'),
            ('message_type', '=', 'user_notification')
        ])
        notif = self.env['mail.notification'].search([
            ('mail_message_id', '=', mail_message.id),
            ('res_partner_id', '=', self.common_partner.id)
        ])
        self.assertEqual(len(notif), 1)
        self.assertEqual(notif.notification_type, 'inbox', 'Multi users should take internal users if possible')

        recipients_data = self.env['mail.followers']._get_recipient_data(
            test, 'comment', self.env.ref('mail.mt_comment').id,
            pids=self.common_partner.ids)
        self.assertRecipientsData(recipients_data, test, self.common_partner + self.partner_employee,
                                  partner_to_users={self.common_partner.id: self.user_2})

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_notification_unlink(self):
        """ Check that we unlink the created user_notification after unlinked the
        related document. """
        test = self.env['mail.test.track'].create({"name": "Test Track", "user_id": self.user_1.id})
        mail_message = self.env['mail.message'].search([
            ('res_id', '=', test.id),
            ('model', '=', 'mail.test.track'),
            ('message_type', '=', 'user_notification')
        ])
        self.assertEqual(len(mail_message), 1)
        test.unlink()
        self.assertEqual(
            self.env['mail.message'].search_count([
                ('res_id', '=', test.id),
                ('model', '=', 'mail.test.track'),
                ('message_type', '=', 'user_notification')
            ]), 0
        )

    @users('employee')
    def test_notification_user_choice(self):
        """ Check fetching user information when notifying someone with multiple
        users (more complex use case). """
        company_other = self.env['res.company'].sudo().create({
            'currency_id': self.env.ref('base.CAD').id,
            'email': 'company_other@test.example.com',
            'name': 'Company Other',
        })
        shared_partner = self.env['res.partner'].sudo().create({
            'email': 'common.partner@test.customer.com',
            'name': 'Common Partner',
            'phone': '+32455998877',
        })
        cids = (company_other + self.company_admin).ids
        user_2_1, user_2_2, user_2_3 = self.env['res.users'].sudo().with_context(no_reset_password=True).create([
            {'company_ids': [(6, 0, cids)],
             'company_id': self.company_admin.id,
             'group_ids': [(4, self.env.ref('base.group_portal').id)],
             'login': '_login2_portal',
             'notification_type': 'email',
             'partner_id': shared_partner.id,
            },
            {'company_ids': [(6, 0, cids)],
             'company_id': self.company_admin.id,
             'group_ids': [(4, self.env.ref('base.group_user').id)],
             'login': '_login2_internal',
             'notification_type': 'inbox',
             'partner_id': shared_partner.id,
            },
            {'company_ids': [(6, 0, cids)],
             'company_id': company_other.id,
             'group_ids': [(4, self.env.ref('base.group_user').id), (4, self.env.ref('base.group_partner_manager').id)],
             'login': '_login2_manager',
             'notification_type': 'inbox',
             'partner_id': shared_partner.id,
            }
        ])
        (user_2_1 + user_2_2 + user_2_3).flush_recordset()

        # just ensure current share status
        self.assertFalse(shared_partner.partner_share)
        self.assertTrue(user_2_1.share)
        self.assertFalse(user_2_2.share or user_2_3.share)

        test = self.env['mail.test.track'].create({"name": "Test Track", "user_id": False})
        self.assertEqual(test.message_partner_ids, self.partner_employee)

        with self.assertSinglePostNotifications(
                [{'group': 'customer', 'partner': shared_partner,
                  'status': 'sent', 'type': 'inbox'}],
                message_info={'content': 'User Choice Notification'}):
            test.message_post(
                body=Markup('<p>User Choice Notification</p>'),
                message_type='comment',
                partner_ids=shared_partner.ids,
                subtype_xmlid='mail.mt_comment',
            )

        recipients_data = self.env['mail.followers']._get_recipient_data(
            test, 'comment', self.env.ref('mail.mt_comment').id,
            pids=shared_partner.ids)
        self.assertRecipientsData(recipients_data, test, self.partner_employee + shared_partner,
                                  partner_to_users={shared_partner.id: user_2_2})

    @users('employee')
    def test_recipients_fetch(self):
        test_records = self.env['mail.test.simple'].create([
            {'email_from': 'ignasse@example.com',
             'name': 'Test %s' % idx,
            } for idx in range(5)
        ])
        # make followers listen to notes to use it and check portal will never be notified of it (internal)
        test_records.message_follower_ids.sudo().write({'subtype_ids': [(4, self.env.ref('mail.mt_note').id)]})
        for test_record in test_records:
            self.assertEqual(test_record.message_partner_ids, self.env.user.partner_id)

        test_records[0].message_subscribe(self.partner_portal.ids)
        self.assertNotIn(
            self.env.ref('mail.mt_note'),
            test_records[0].message_follower_ids.filtered(lambda fol: fol.partner_id == self.partner_portal).subtype_ids,
            'Portal user should not follow notes by default')

        # just fetch followers
        recipients_data = self.env['mail.followers']._get_recipient_data(
            test_records[0], 'comment', self.env.ref('mail.mt_comment').id,
            pids=None
        )
        self.assertRecipientsData(recipients_data, test_records[0], self.env.user.partner_id + self.partner_portal)

        # followers + additional recipients
        recipients_data = self.env['mail.followers']._get_recipient_data(
            test_records[0], 'comment', self.env.ref('mail.mt_comment').id,
            pids=(self.customer + self.common_partner + self.partner_admin).ids
        )
        self.assertRecipientsData(recipients_data, test_records[0],
                                  self.env.user.partner_id + self.partner_portal + self.customer + self.common_partner + self.partner_admin)

        # ensure filtering on internal: should exclude Portal even if misconfiguration
        follower_portal = test_records[0].message_follower_ids.filtered(lambda fol: fol.partner_id == self.partner_portal).sudo()
        follower_portal.write({'subtype_ids': [(4, self.env.ref('mail.mt_note').id)]})
        follower_portal.flush_recordset()
        recipients_data = self.env['mail.followers']._get_recipient_data(
            test_records[0], 'comment', self.env.ref('mail.mt_note').id,
            pids=(self.common_partner + self.partner_admin).ids
        )
        self.assertRecipientsData(recipients_data, test_records[0], self.env.user.partner_id + self.common_partner + self.partner_admin)

        # ensure filtering on subtype: should exclude Portal as it does not follow comment anymore
        follower_portal.write({'subtype_ids': [(3, self.env.ref('mail.mt_comment').id)]})
        recipients_data = self.env['mail.followers']._get_recipient_data(
            test_records[0], 'comment', self.env.ref('mail.mt_comment').id,
            pids=(self.common_partner + self.partner_admin).ids
        )
        self.assertRecipientsData(recipients_data, test_records[0], self.env.user.partner_id + self.common_partner + self.partner_admin)

        # check without subtype
        recipients_data = self.env['mail.followers']._get_recipient_data(
            test_records[0], 'comment', False,
            pids=(self.common_partner + self.partner_admin).ids
        )
        self.assertRecipientsData(recipients_data, test_records[0], self.common_partner + self.partner_admin)

        # multi mode
        test_records[1].message_subscribe(self.partner_portal.ids)
        test_records[0:4].message_subscribe(self.common_partner.ids)
        recipients_data = self.env['mail.followers']._get_recipient_data(
            test_records, 'comment', self.env.ref('mail.mt_comment').id,
            pids=self.partner_admin.ids
        )
        # 0: portal is follower but does not follow comment + common partner (+ admin as pid)
        recipients_data_1 = dict((r, recipients_data[r]) for r in recipients_data if r in  test_records[0:1].ids)
        self.assertRecipientsData(recipients_data_1, test_records[0:1], self.env.user.partner_id + self.common_partner + self.partner_admin)
        # 1: portal is follower with comment + common partner (+ admin as pid)
        recipients_data_1 = dict((r, recipients_data[r]) for r in recipients_data if r in  test_records[1:2].ids)
        self.assertRecipientsData(recipients_data_1, test_records[1:2], self.env.user.partner_id + self.common_partner + self.partner_portal + self.partner_admin)
        # 2-3: common partner (+ admin as pid)
        recipients_data_2 = dict((r, recipients_data[r]) for r in recipients_data if r in  test_records[2:4].ids)
        self.assertRecipientsData(recipients_data_2, test_records[2:4], self.env.user.partner_id + self.common_partner + self.partner_admin)
        # 4+: env user partner (+ admin as pid)
        recipients_data_3 = dict((r, recipients_data[r]) for r in recipients_data if r in  test_records[4:].ids)
        self.assertRecipientsData(recipients_data_3, test_records[4:], self.env.user.partner_id + self.partner_admin)

        # multi mode, pids only
        recipients_data = self.env['mail.followers']._get_recipient_data(
            test_records, 'comment', False,
            pids=(self.env.user.partner_id + self.partner_admin).ids
        )
        self.assertRecipientsData(recipients_data, test_records, self.env.user.partner_id + self.partner_admin)

        # on mail.thread, False everywhere: pathologic case
        test_partners = self.partner_admin + self.partner_employee + self.common_partner
        recipients_data = self.env['mail.followers']._get_recipient_data(
            self.env['mail.thread'], False, False,
            pids=test_partners.ids
        )
        self.assertRecipientsData(recipients_data, False, test_partners)

    def test_subscribe_post_author(self):
        """ Test author is added in followers, unless it is archived / odoobot """
        # some automated action post on behalf of author
        test_record = self.env['mail.test.simple'].create({'name': 'Test'})
        self.partner_root.active = True  # edge case, people activating Odoobot partner (not user)
        (self.user_1 + self.user_2).active = False  # archived users should not be subscribed
        self.user_1.partner_id.active = False  # archived authors should not be subscribed
        self.assertFalse(test_record.message_partner_ids)
        for user, author, exp_followers in [
            # active user = real author
            (self.user_employee, self.user_2.partner_id, self.user_employee.partner_id),
            # inactive user -> check for author
            (self.user_2, self.user_employee.partner_id, self.user_employee.partner_id),
            (self.user_2, self.user_1.partner_id, self.env['res.partner']),  # no inactive !
            (self.user_2, self.user_root.partner_id, self.env['res.partner']),  # no odoobot !
        ]:
            with self.subTest(user=user.name, author=author.name):
                test_record.with_user(user).message_post(
                    author_id=author.id,
                    body='Youpie',
                    message_type='comment',
                    subtype_id=self.env.ref('mail.mt_comment').id,
                )
                self.assertEqual(test_record.message_partner_ids, exp_followers)
                if exp_followers:
                    test_record.message_unsubscribe(partner_ids=exp_followers.ids)

@tagged('mail_followers', 'post_install', '-at_install')
class UnfollowLinkTest(MailCommon, HttpCase):
    """ Test unfollow links, notably used in notification emails """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_portal = cls._create_portal_user()
        cls.partner_portal = cls.user_portal.partner_id
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({'name': 'Test'})
        cls.test_record_copy = cls.test_record.copy()
        cls.test_record_unfollow = cls.env['mail.test.simple.unfollow'].with_context(cls._test_context).create(
            {'name': 'unfollow'})
        cls.partner_without_user = cls.env['res.partner'].create({
            'name': 'Dave',
            'email': 'dave@odoo.com',
        })
        cls.user_employee.write({'notification_type': 'email'})

    def _message_unsubscribe_unreadable_record(self, user):
        def raise_access_error(*args, **kwargs):
            raise AccessError('Unreadable')

        with patch.object(self.test_record.__class__, 'check_access', side_effect=raise_access_error):
            self.test_record.with_user(user).message_unsubscribe(user.partner_id.ids)


    def _test_tampered_unfollow_url(self, record, unfollow_url, partner):
        """ Test that tampered urls doesn't work.

        Test that:
        - when the following parameters are altered, the browsing the URL returns
        a 403 and doesn't unsubscribe the partner.
        - when trying to use the same URL with another partner, it also returns a
        403 and doesn't unsubscribe the other partner.
        """
        for param, value in (
            ('token', '0000000000000000000000000000000000000000'),
            ('model', 'mail.test.gateway'),
            ('res_id', self.test_record_copy.id),
            ('partner_id', self.partner_admin.id),
        ):
            with self.subTest(f'Tampered {param}'):
                tampered_unfollow_url = self._url_update_query_parameters(unfollow_url, **{param: value})
                response = self.url_open(tampered_unfollow_url)
                self.assertEqual(response.status_code, 403)
                self.assertIn(partner, record.message_partner_ids)

    def _test_unfollow_url(self, record, unfollow_url, partner):
        """ Test that the unfollow url works.

        Test that: that browsing the unfollow URL unsubscribe the user from the record
        """
        with self.subTest('Legitimate unfollow'):
            # We test that the URL still work a second time if the user has been re-added
            for _ in range(2):
                try:
                    self.assertIn(partner, record.message_partner_ids)
                    response = self.url_open(unfollow_url)
                    self.assertEqual(response.status_code, 200)
                    self.assertNotIn(partner, record.message_partner_ids)
                    self.assertEqual(urlparse(response.url).path, '/mail/unfollow')
                    self.assertIn("You are no longer following the document", response.text)
                    self.assertIn('o_access_record_link', response.text)
                finally:
                    record._message_subscribe(partner_ids=partner.ids)

    def test_assert_initial_data(self):
        """ Test some initial value. """
        record_employee = self.test_record.with_user(self.user_employee)
        record_employee.check_access('read')
        record_portal = self.test_record.with_user(self.user_portal)
        with self.assertRaises(AccessError):
            record_portal.check_access('write')
        for template_ref in ('mail.mail_notification_layout', 'mail.mail_notification_light'):
            with self.subTest(f'Unfollow link in {template_ref}'):
                mail_template_arch = self.env.ref(template_ref).arch
                self.assertIn('/mail/unfollow', mail_template_arch)
                self.assertNotIn('/mail/unfollow', re.sub(_UNFOLLOW_REGEX, '', mail_template_arch))

    @users('employee')
    @mute_logger('odoo.models')
    def test_inbox_unfollow_information(self):
        """ Check follow-up information for displaying inbox messages used to
        implement "unfollow" in the inbox.

        Note that the actual mechanism to unfollow a record from a message is
        tested in the client part.
        """
        self.user_employee.write({'notification_type': 'inbox'})

        test_record = self.env['mail.test.simple'].browse(self.test_record.ids)
        _message = test_record.with_user(self.user_admin).message_post(
            body="test message",
            subtype_id=self.env.ref("mail.mt_comment").id,
            partner_ids=self.partner_employee.ids,
        )
        # The user doesn't follow the record
        self.authenticate(self.env.user.login, self.env.user.login)
        message_data = self.make_jsonrpc_request("/mail/inbox/messages")["data"]
        self.assertFalse(message_data["mail.thread"][0]["selfFollower"])
        self.assertFalse(message_data.get("mail.followers"), "Should not have void followers data")
        self.assertFalse(test_record.with_user(self.user_employee).message_is_follower)

        # The user follows the record
        test_record._message_subscribe(partner_ids=self.env.user.partner_id.ids)
        follower = test_record.message_follower_ids.filtered(
            lambda follower: follower.partner_id == self.env.user.partner_id
        )
        message_data = self.make_jsonrpc_request("/mail/inbox/messages")["data"]
        self.assertEqual(message_data["mail.followers"], [
            {
                "id": follower.id,
                "is_active": True,
                "partner_id": self.env.user.partner_id.id,
            },
        ])
        self.assertEqual(message_data["mail.thread"][0]["selfFollower"], follower.id, "Should have follower ID")

    @mute_logger('odoo.addons.base.models', 'odoo.addons.mail.controllers.mail', 'odoo.http', 'odoo.models')
    def test_notification_email_unfollow_link(self):
        """ Internal user must receive an unfollow URL, that cannot be tampered
        and redirects to the correct page.
        """
        for test_partners, test_record, exp_has_url in [
            (self.partner_employee, self.test_record, [True]),
            # customer should not receive an unfollow URL
            (self.partner_without_user, self.test_record, [False]),
            (self.partner_portal, self.test_record, [False]),
            # always unfollow link (model definition)
            (self.partner_without_user, self.test_record_unfollow, [True]),
            (self.partner_portal, self.test_record_unfollow, [True]),
            # multi partners
            (
                self.partner_without_user + self.partner_portal + self.partner_employee,
                self.test_record, [False, False, True],
            ),
            (
                self.partner_without_user + self.partner_portal + self.partner_employee,
                self.test_record_unfollow, [True, True, True],
            ),
        ]:
            with self.subTest(partners=test_partners.mapped('name')):
                # Test that the user receives an unfollow URL when following the record
                test_record._message_subscribe(partner_ids=test_partners.ids)
                unfollow_urls = self._message_post_and_get_unfollow_urls(test_record, test_partners)
                for test_partner, unfollow_url, has_url in zip(test_partners, unfollow_urls, exp_has_url):
                    self.assertEqual(bool(unfollow_url), has_url)

                    # Test unfollowing URL when user is not logged
                    if has_url:
                        self.authenticate(None, None)
                        self._test_unfollow_url(test_record, unfollow_url, test_partner)
                        self._test_tampered_unfollow_url(test_record, unfollow_url, test_partner)

                        if test_partner == self.partner_employee:
                            # Test unfollowing URL when user is logged
                            self.authenticate(self.user_employee.login, self.user_employee.login)
                            self._test_unfollow_url(test_record, unfollow_url, test_partner)

                # Test that the user doesn't receive the unfollow URL when not following the record
                test_record.message_unsubscribe(partner_ids=test_partners.ids)
                unfollow_urls = self._message_post_and_get_unfollow_urls(test_record, test_partners)
                for test_partner, unfollow_url in zip(test_partners, unfollow_urls):
                    self.assertFalse(unfollow_url)

    def test_unsubscribe_unreadable(self):
        """ Check internal can always unsubscribe form records while portal are
        limited to records they can access. Other records are considered as customer
        oriented and we don't want to lose emails. """
        for user, can_unsubscribe in [
            (self.user_employee, True),
            (self.user_portal, False),
        ]:
            self.test_record._message_subscribe(partner_ids=user.partner_id.ids)
            self.assertIn(user.partner_id, self.test_record.message_partner_ids)
            if can_unsubscribe:
                self._message_unsubscribe_unreadable_record(user)
                self.assertNotIn(user.partner_id, self.test_record.message_partner_ids)
            else:
                with self.assertRaises(AccessError):
                    self._message_unsubscribe_unreadable_record(user)
