# -*- coding: utf-8 -*-

from odoo import api
from odoo.addons.mail.tests.common import TestMail


class TestTracking(TestMail):

    def test_message_track(self):
        """ Testing auto tracking of fields. Warning, it has not be cleaned and
        should probably be. """
        test_channel = self.env['mail.channel'].create({
            'name': 'Test',
            'channel_partner_ids': [(4, self.user_employee.partner_id.id)]
        })

        Subtype = self.env['mail.message.subtype']
        Data = self.env['ir.model.data']
        note_subtype = self.env.ref('mail.mt_note')

        group_system = self.env.ref('base.group_system')
        group_user = self.env.ref('base.group_user')

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
        test_channel.sudo(self.user_employee).write({'name': 'my_name'})
        self.assertEqual(len(test_channel.message_ids), 1)
        last_msg = test_channel.message_ids[-1]
        self.assertEqual(last_msg.subtype_id, note_subtype)
        self.assertEqual(len(last_msg.tracking_value_ids), 1)
        self.assertEqual(last_msg.tracking_value_ids.field, 'name')
        self.assertEqual(last_msg.tracking_value_ids.field_desc, 'Name')
        self.assertEqual(last_msg.tracking_value_ids.old_value_char, 'Test')
        self.assertEqual(last_msg.tracking_value_ids.new_value_char, 'my_name')

        # Test: change name as supername, public as private -> 1 subtype, private
        test_channel.sudo(self.user_employee).write({'name': 'supername', 'public': 'private'})
        test_channel.invalidate_cache()
        self.assertEqual(len(test_channel.message_ids.ids), 2)
        last_msg = test_channel.message_ids[0]
        self.assertEqual(last_msg.subtype_id, mt_private)
        self.assertEqual(len(last_msg.tracking_value_ids), 2)
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('field')), set(['name', 'public']))
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('field_desc')), set(['Name', 'Privacy']))
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('old_value_char')), set(['my_name', 'Selected group of users']))
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('new_value_char')), set(['supername', 'Invited people only']))

        # Test: change public as public, group_public_id -> 1 subtype, group public set
        test_channel.sudo(self.user_employee).write({'public': 'public', 'group_public_id': group_system.id})
        test_channel.invalidate_cache()
        self.assertEqual(len(test_channel.message_ids), 3)
        last_msg = test_channel.message_ids[0]
        self.assertEqual(last_msg.subtype_id, mt_group_public_set)
        self.assertEqual(len(last_msg.tracking_value_ids), 3)
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('field')), set(['group_public_id', 'public', 'name']))
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('field_desc')), set(['Authorized Group', 'Privacy', 'Name']))
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('old_value_char')), set([group_user.name_get()[0][1], 'Invited people only', 'supername']))
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('new_value_char')), set([group_system.name_get()[0][1], 'Everyone', 'supername']))
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('old_value_integer')), set([0, group_user.id]))
        self.assertEqual(set(last_msg.tracking_value_ids.mapped('new_value_integer')), set([0, group_system.id]))

    def test_track_template(self):
        # Test: Check that default_* keys are not taken into account in _message_track_post_template
        magic_code = 'Up-Up-Down-Down-Left-Right-Left-Right-Square-Triangle'

        mt_name_changed = self.env['mail.message.subtype'].create({
            'name': 'MAGIC CODE WOOP WOOP',
            'description': 'SPECIAL CONTENT UNLOCKED'
        })
        self.env['ir.model.data'].create({
            'name': 'mt_name_changed',
            'model': 'mail.message.subtype',
            'module': 'mail',
            'res_id': mt_name_changed.id
        })
        mail_template = self.env['mail.template'].create({
            'name': 'SPECIAL CONTENT UNLOCKED',
            'subject': 'SPECIAL CONTENT UNLOCKED',
            'model_id': self.env.ref('mail.model_mail_test').id,
            'auto_delete': True,
            'body_html': '''<div>WOOP WOOP</div>''',
        })

        @api.multi
        def _track_subtype(self, init_values):
            if 'name' in init_values and init_values['name'] == magic_code:
                return 'mail.mt_name_changed'
            return False
        self.registry('mail.test')._patch_method('_track_subtype', _track_subtype)

        def _track_template(self, tracking):
            res = {}
            record = self[0]
            changes, tracking_value_ids = tracking[record.id]
            if 'name' in changes:
                res['name'] = (mail_template, {'composition_mode': 'mass_mail'})
            return res
        self.registry('mail.test')._patch_method('_track_template', _track_template)

        cls = type(self.env['mail.test'])
        self.assertFalse(hasattr(getattr(cls, 'name'), 'track_visibility'))
        getattr(cls, 'name').track_visibility = 'always'

        @self.addCleanup
        def cleanup():
            del getattr(cls, 'name').track_visibility

        test_mail_record = self.env['mail.test'].create({
            'name': 'Zizizatestmailname',
            'description': 'Zizizatestmaildescription',
        })
        test_mail_record.with_context(default_parent_id=2147483647).write({'name': magic_code})
