# -*- coding: utf-8 -*-

from odoo.tools import formataddr
from odoo.addons.test_mail.tests import common


class TestTracking(common.BaseFunctionalTest, common.MockEmails):

    def assertTracking(self, message, data):
        tracking_values = message.sudo().tracking_value_ids
        for field_name, value_type, old_value, new_value in data:
            tracking = tracking_values.filtered(lambda track: track.field == field_name)
            self.assertEqual(len(tracking), 1)
            if value_type in ('char', 'integer'):
                self.assertEqual(tracking.old_value_char, old_value)
                self.assertEqual(tracking.new_value_char, new_value)
            elif value_type in ('many2one'):
                self.assertEqual(tracking.old_value_integer, old_value and old_value.id or False)
                self.assertEqual(tracking.new_value_integer, new_value and new_value.id or False)
                self.assertEqual(tracking.old_value_char, old_value and old_value.name_get()[0][1] or '')
                self.assertEqual(tracking.new_value_char, new_value and new_value.name_get()[0][1] or '')
            else:
                self.assertEqual(1, 0)

    def setUp(self):
        super(TestTracking, self).setUp()

        record = self.env['mail.test.full'].sudo(self.user_employee).with_context(common.BaseFunctionalTest._test_context).create({
            'name': 'Test',
        })
        self.record = record.with_context(mail_notrack=False)

    def test_message_track_no_tracking(self):
        """ Update a set of non tracked fields -> no message, no tracking """
        self.record.write({
            'name': 'Tracking or not',
            'count': 32,
        })
        self.assertEqual(self.record.message_ids, self.env['mail.message'])

    def test_message_track_no_subtype(self):
        """ Update some tracked fields not linked to some subtype -> message with onchange """
        customer = self.env['res.partner'].create({'name': 'Customer', 'email': 'cust@example.com'})
        self.record.write({
            'name': 'Test2',
            'customer_id': customer.id,
        })

        # one new message containing tracking; without subtype linked to tracking, a note is generated
        self.assertEqual(len(self.record.message_ids), 1)
        self.assertEqual(self.record.message_ids.subtype_id, self.env.ref('mail.mt_note'))

        # no specific recipients except those following notes, no email
        self.assertEqual(self.record.message_ids.partner_ids, self.env['res.partner'])
        self.assertEqual(self.record.message_ids.needaction_partner_ids, self.env['res.partner'])
        self.assertEqual(self._mails, [])

        # verify tracked value
        self.assertTracking(
            self.record.message_ids,
            [('customer_id', 'many2one', False, customer)  # onchange tracked field
             ])

    def test_message_track_subtype(self):
        """ Update some tracked fields linked to some subtype -> message with onchange """
        self.record.message_subscribe(
            partner_ids=[self.user_admin.partner_id.id],
            subtype_ids=[self.env.ref('test_mail.st_mail_test_full_umbrella_upd').id]
        )

        umbrella = self.env['mail.test'].with_context(mail_create_nosubscribe=True).create({'name': 'Umbrella'})
        self.record.write({
            'name': 'Test2',
            'email_from': 'noone@example.com',
            'umbrella_id': umbrella.id,
        })
        # one new message containing tracking; subtype linked to tracking
        self.assertEqual(len(self.record.message_ids), 1)
        self.assertEqual(self.record.message_ids.subtype_id, self.env.ref('test_mail.st_mail_test_full_umbrella_upd'))

        # no specific recipients except those following umbrella
        self.assertEqual(self.record.message_ids.partner_ids, self.env['res.partner'])
        self.assertEqual(self.record.message_ids.needaction_partner_ids, self.user_admin.partner_id)

        # verify tracked value
        self.assertTracking(
            self.record.message_ids,
            [('umbrella_id', 'many2one', False, umbrella)  # onchange tracked field
             ])

    def test_message_track_template(self):
        """ Update some tracked fields linked to some template -> message with onchange """
        self.record.write({'mail_template': self.env.ref('test_mail.mail_test_full_tracking_tpl').id})
        self.assertEqual(self.record.message_ids, self.env['mail.message'])

        self.record.write({
            'name': 'Test2',
            'customer_id': self.user_admin.partner_id.id,
        })

        self.assertEqual(len(self.record.message_ids), 2, 'should have 2 new messages: one for tracking, one for template')

        # one new message containing the template linked to tracking
        self.assertEqual(self.record.message_ids[0].subject, 'Test Template')
        self.assertEqual(self.record.message_ids[0].body, '<p>Hello Test2</p>')

        # one email send due to template
        self.assertEqual(len(self._mails), 1)
        self.assertEqual(set(self._mails[0]['email_to']), set([formataddr((self.user_admin.name, self.user_admin.email))]))
        self.assertHtmlEqual(self._mails[0]['body'], '<p>Hello Test2</p>')

        # one new message containing tracking; without subtype linked to tracking
        self.assertEqual(self.record.message_ids[1].subtype_id, self.env.ref('mail.mt_note'))
        self.assertTracking(
            self.record.message_ids[1],
            [('customer_id', 'many2one', False, self.user_admin.partner_id)  # onchange tracked field
             ])

    def test_message_track_sequence(self):
        """ Update some tracked fields and check that the mail.tracking.value are ordered according to their track_sequence"""
        self.record.write({
            'name': 'Zboub',
            'customer_id': self.user_admin.partner_id.id,
            'user_id': self.user_admin.id,
            'umbrella_id': self.env['mail.test'].with_context(mail_create_nosubscribe=True).create({'name': 'Umbrella'}).id
        })
        self.assertEqual(len(self.record.message_ids), 1, 'should have 1 tracking message')

        tracking_values = self.env['mail.tracking.value'].search([('mail_message_id', '=', self.record.message_ids.id)])
        self.assertEqual(tracking_values[0].track_sequence, 1)
        self.assertEqual(tracking_values[1].track_sequence, 2)
        self.assertEqual(tracking_values[2].track_sequence, 100)

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
            'model_id': self.env.ref('test_mail.model_mail_test').id,
            'auto_delete': True,
            'body_html': '''<div>WOOP WOOP</div>''',
        })

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
