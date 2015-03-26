# -*- coding: utf-8 -*-

from openerp.addons.mail.tests.common import TestMail


class TestTracking(TestMail):

    def test_message_track(self):
        """ Testing auto tracking of fields. Warning, it has not be cleaned and
        should probably be. """
        def _strip_string_spaces(body):
            return body.replace(' ', '').replace('\n', '')
        self.group_pigs.message_subscribe_users(user_ids=[self.user_employee.id])
        # Data: res.users.group, to test group_public_id automatic logging
        group_system_id = self.env['ir.model.data'].xmlid_to_res_id('base.group_system') or False

        # Data: custom subtypes
        Subtype = self.env['mail.message.subtype']
        Data = self.env['ir.model.data']
        mt_private = Subtype.create({'name': 'private', 'description': 'Private public'})
        Data.create({'name': 'mt_private', 'model': 'mail.message.subtype', 'module': 'mail', 'res_id': mt_private.id})
        mt_name_supername = Subtype.create({'name': 'name_supername', 'description': 'Supername name'})
        Data.create({'name': 'mt_name_supername', 'model': 'mail.message.subtype', 'module': 'mail', 'res_id': mt_name_supername.id})
        mt_group_public_set = Subtype.create({'name': 'group_public_set', 'description': 'Group set'})
        Data.create({'name': 'mt_group_public_set', 'model': 'mail.message.subtype', 'module': 'mail', 'res_id': mt_group_public_set.id})
        mt_group_public = Subtype.create({'name': 'group_public', 'description': 'Group changed'})
        Data.create({'name': 'mt_group_public', 'model': 'mail.message.subtype', 'module': 'mail', 'res_id': mt_group_public.id})

        def _track_subtype(self, cr, uid, ids, init_values, context=None):
            record = self.browse(cr, uid, ids[0], context=context)
            if 'public' in init_values and record.public == 'private':
                return 'mail.mt_private'
            elif 'name' in init_values and record.name == 'supername':
                return 'mail.mt_name_supername'
            elif 'group_public_id' in init_values and record.group_public_id:
                return 'mail.mt_group_public_set'
            elif 'group_public_id' in init_values and not record.group_public_id:
                return 'mail.mt_group_public'
            return False
        self.registry('mail.group')._patch_method('_track_subtype', _track_subtype)

        visibility = {'public': 'onchange', 'name': 'always', 'group_public_id': 'onchange'}
        cls = type(self.env['mail.group'])
        for key in visibility:
            self.assertFalse(hasattr(getattr(cls, key), 'track_visibility'))
            getattr(cls, key).track_visibility = visibility[key]

        @self.addCleanup
        def cleanup():
            for key in visibility:
                del getattr(cls, key).track_visibility

        # Test: change name -> always tracked, not related to a subtype
        self.group_pigs.sudo(self.user_employee).write({'public': 'public'})
        self.assertEqual(len(self.group_pigs.message_ids.ids), 1, 'tracked: a message should have been produced')
        # Test: first produced message: no subtype, name change tracked
        last_msg = self.group_pigs.message_ids[-1]
        self.assertFalse(last_msg.subtype_id.id, 'tracked: message should not have been linked to a subtype')
        self.assertIn(u"Selectedgroupofusers\u2192Everyone", _strip_string_spaces(last_msg.body), 'tracked: message body incorrect')
        self.assertIn('Pigs', _strip_string_spaces(last_msg.body), 'tracked: message body does not hold always tracked field')
        # Test: change name as supername, public as private -> 2 subtypes
        self.group_pigs.sudo(self.user_employee).write({'name': 'supername', 'public': 'private'})
        self.assertEqual(len(self.group_pigs.message_ids.ids), 2, 'tracked: two messages should have been produced')
        # Test: first produced message: mt_name_supername
        last_msg = self.group_pigs.message_ids[-2]
        self.assertEqual(last_msg.subtype_id.id, mt_private.id, 'tracked: message should be linked to mt_private subtype')
        self.assertIn('Private public', last_msg.body, 'tracked: message body does not hold the subtype description')
        self.assertIn(u'Pigs\u2192supername', _strip_string_spaces(last_msg.body), 'tracked: message body incorrect')

        # Test: change public as public, group_public_id -> 1 subtype, name always tracked
        self.group_pigs.sudo(self.user_employee).write({'public': 'public', 'group_public_id': group_system_id})
        self.assertEqual(len(self.group_pigs.message_ids), 3, 'tracked: one message should have been produced')
        # Test: first produced message: mt_group_public_set_id, with name always tracked, public tracked on change
        last_msg = self.group_pigs.message_ids[-3]
        self.assertEqual(last_msg.subtype_id, mt_group_public_set, 'tracked: message should be linked to mt_group_public_set_id')
        self.assertIn('Group set', last_msg.body, 'tracked: message body does not hold the subtype description')
        self.assertIn(u"Invitedpeopleonly\u2192Everyone", _strip_string_spaces(last_msg.body), 'tracked: message body does not hold changed tracked field')
        self.assertIn(u'HumanResources/Employee\u2192Administration/Settings', _strip_string_spaces(last_msg.body), 'tracked: message body does not hold always tracked field')

        # Test: change group_public_id to False -> 1 subtype, name always tracked
        self.group_pigs.sudo(self.user_employee).write({'group_public_id': False})
        self.assertEqual(len(self.group_pigs.message_ids), 4, 'tracked: one message should have been produced')
        # Test: first produced message: mt_group_public_set_id, with name always tracked, public tracked on change
        last_msg = self.group_pigs.message_ids[-4]
        self.assertEqual(last_msg.subtype_id, mt_group_public, 'tracked: message should be linked to mt_group_public_id')
        self.assertIn('Group changed', last_msg.body, 'tracked: message body does not hold the subtype description')
        self.assertIn(u'Administration/Settings\u2192', _strip_string_spaces(last_msg.body), 'tracked: message body does not hold always tracked field')
        # Test: change not tracked field, no tracking message
        self.group_pigs.sudo(self.user_employee).write({'description': 'Dummy'})
        self.assertEqual(len(self.group_pigs.message_ids), 4, 'tracked: No message should have been produced')
