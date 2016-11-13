# -*- coding: utf-8 -*-

from odoo import api
from odoo.addons.mail.tests.common import TestMail


class TestTracking(TestMail):

    def test_message_track(self):
        """ Testing auto tracking of fields. Warning, it has not be cleaned and
        should probably be. """
        Subtype = self.env['mail.message.subtype']
        Data = self.env['ir.model.data']
        note_subtype = self.env.ref('mail.mt_note')

        group_system = self.env.ref('base.group_system')
        group_user = self.env.ref('base.group_user')
        self.group_pigs.write({'channel_partner_ids': [(4, self.user_employee.partner_id.id)]})

        # mt_private: public field (tracked as onchange) set to 'private' (selection)
        mt_private = Subtype.create({
            'name': 'private',
            'description': 'Public field set to private'
        })
        Data.create({
            'name': 'mt_private',
            'model': 'mail.message.subtype',
            'module': 'mail',
            'res_id': mt_private.id
        })

        # mt_name_supername: name field (tracked as always) set to 'supername' (char)
        mt_name_supername = Subtype.create({
            'name': 'name_supername',
            'description': 'Name field set to supername'
        })
        Data.create({
            'name': 'mt_name_supername',
            'model': 'mail.message.subtype',
            'module': 'mail',
            'res_id': mt_name_supername.id
        })

        # mt_group_public_set: group_public field (tracked as onchange) set to something (m2o)
        mt_group_public_set = Subtype.create({
            'name': 'group_public_set',
            'description': 'Group_public field set'
        })
        Data.create({
            'name': 'mt_group_public_set',
            'model': 'mail.message.subtype',
            'module': 'mail',
            'res_id': mt_group_public_set.id
        })

        # mt_group_public_set: group_public field (tracked as onchange) set to nothing (m2o)
        mt_group_public_unset = Subtype.create({
            'name': 'group_public_unset',
            'description': 'Group_public field unset'
        })
        Data.create({
            'name': 'mt_group_public_unset',
            'model': 'mail.message.subtype',
            'module': 'mail',
            'res_id': mt_group_public_unset.id
        })

        @api.multi
        def _track_subtype(self, init_values):
            if 'public' in init_values and self.public == 'private':
                return 'mail.mt_private'
            elif 'name' in init_values and self.name == 'supername':
                return 'mail.mt_name_supername'
            elif 'group_public_id' in init_values and self.group_public_id:
                return 'mail.mt_group_public_set'
            elif 'group_public_id' in init_values and not self.group_public_id:
                return 'mail.mt_group_public_unset'
            return False
        self.registry('mail.channel')._patch_method('_track_subtype', _track_subtype)

        visibility = {
            'public': 'onchange',
            'name': 'always',
            'group_public_id': 'onchange'
        }
        cls = type(self.env['mail.channel'])
        for key in visibility:
            self.assertFalse(hasattr(getattr(cls, key), 'track_visibility'))
            getattr(cls, key).track_visibility = visibility[key]

        @self.addCleanup
        def cleanup():
            for key in visibility:
                del getattr(cls, key).track_visibility

        # Test: change name -> always tracked, not related to a subtype
        self.group_pigs.sudo(self.user_employee).write({'name': 'my_name'})
        self.assertEqual(len(self.group_pigs.message_ids), 1)
        last_msg = self.group_pigs.message_ids[-1]
        self.assertEqual(last_msg.subtype_id, note_subtype)
        self.assertEqual(len(last_msg.tracking_value_ids), 1)
        self.assertEqual(last_msg.tracking_value_ids.field, 'name')
        self.assertEqual(last_msg.tracking_value_ids.field_desc, 'Name')
        self.assertEqual(last_msg.tracking_value_ids.old_value_char, 'Pigs')
        self.assertEqual(last_msg.tracking_value_ids.new_value_char, 'my_name')

        # Test: change name as supername, public as private -> 1 subtype, private
        self.group_pigs.sudo(self.user_employee).write({'name': 'supername', 'public': 'private'})
        self.group_pigs.invalidate_cache()
        self.assertEqual(len(self.group_pigs.message_ids.ids), 2)
        last_msg = self.group_pigs.message_ids[0]
        self.assertEqual(last_msg.subtype_id, mt_private)
        self.assertEqual(len(last_msg.tracking_value_ids), 2)
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('field')), set(['name', 'public']))
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('field_desc')), set(['Name', 'Privacy']))
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('old_value_char')), set(['my_name', 'Selected group of users']))
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('new_value_char')), set(['supername', 'Invited people only']))

        # Test: change public as public, group_public_id -> 1 subtype, group public set
        self.group_pigs.sudo(self.user_employee).write({'public': 'public', 'group_public_id': group_system.id})
        self.group_pigs.invalidate_cache()
        self.assertEqual(len(self.group_pigs.message_ids), 3)
        last_msg = self.group_pigs.message_ids[0]
        self.assertEqual(last_msg.subtype_id, mt_group_public_set)
        self.assertEqual(len(last_msg.tracking_value_ids), 3)
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('field')), set(['group_public_id', 'public', 'name']))
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('field_desc')), set(['Authorized Group', 'Privacy', 'Name']))
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('old_value_char')), set([group_user.name_get()[0][1], 'Invited people only', 'supername']))
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('new_value_char')), set([group_system.name_get()[0][1], 'Everyone', 'supername']))
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('old_value_integer')), set([0, group_user.id]))
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('new_value_integer')), set([0, group_system.id]))
