# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo import fields
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE
from odoo.tests import Form, tagged, users
from odoo.tools import mute_logger


@tagged('mail_track')
class TestTracking(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        record = cls.env['mail.test.ticket'].with_user(
            cls.user_employee
        ).with_context(cls._test_context).create({
            'name': 'Test',
        })
        cls.record = record.with_context(mail_notrack=False)

    def test_message_track_author(self):
        """ Check that the author of the log note matches the user at the time
        of writing. """
        with self.mock_mail_gateway():
            self.record._track_set_author(self.partner_admin)
            self.record.write({
                'customer_id': self.partner_employee.id,
            })
            self.flush_tracking()

        self.assertEqual(len(self.record.message_ids), 1)
        self.assertEqual(len(self.record.message_ids.tracking_value_ids), 1)

        self.assertEqual(self.record.message_ids.author_id, self.partner_admin)

    @users('employee')
    def test_message_track_default_message(self):
        """Check that the default tracking log message defined on the model is used
        and that setting a log message overrides it. See `_track_get_default_log_message`"""

        record = self.env['mail.test.track'].with_context(self._test_context).create({
            'name': 'Test',
            'track_enable_default_log': True,
        }).with_context(mail_notrack=False)
        self.flush_tracking()

        with self.mock_mail_gateway():
            record.user_id = self.user_admin
            self.flush_tracking()

        messages = record.message_ids
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages.body, '<p>There was a change on Test for fields "user_id"</p>',
                         'Default message should be used')

        with self.mock_mail_gateway():
            record._track_set_log_message('Hi')
            record.user_id = False
            self.flush_tracking()

        messages = record.message_ids - messages
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages.body, '<p>Hi</p>', '_track_set_log_message should take priority over default message')

    @users('employee')
    def test_message_track_filter_for_display(self):
        """Check that tracked fields filtered for display are not present
        in the front-end and email formatting methods. See `_track_filter_for_display`"""
        field_dname = 'Responsible'
        field_name = 'user_id'
        field_type = 'many2one'
        original_user = self.user_admin
        new_user = self.user_employee

        records = self.env['mail.test.track'].create([{
            'name': 'TestTrack Hide User Field',
            'user_id': original_user.id,
            'track_fields_tofilter': 'user_id',
        }, {
            'name': 'TestTrack Show All Fields',
            'user_id': original_user.id,
            'track_fields_tofilter': '',
        }])
        self.flush_tracking()

        records.write({'user_id': new_user.id})
        self.flush_tracking()

        for record in records:
            self.assertEqual(len(record.message_ids), 2, 'Should be a creation message and a tracking message')
            self.assertTracking(
                record.message_ids[0],
                [('user_id', 'many2one', original_user, new_user)]
            )
        # first record: tracking value should be hidden
        message_0 = records[0].message_ids[0]
        formatted = Store(message_0, for_current_user=True).get_result()["mail.message"][0]
        self.assertEqual(formatted['trackingValues'], [], 'Hidden values should not be formatted')
        mail_render = records[0]._notify_by_email_prepare_rendering_context(message_0, {})
        self.assertEqual(mail_render['tracking_values'], [])

        # second record: all values displayed
        message_1 = records[1].message_ids[0]
        formatted = Store(message_1, for_current_user=True).get_result()["mail.message"][0]
        self.assertEqual(len(formatted['trackingValues']), 1)
        self.assertDictEqual(
            formatted['trackingValues'][0],
            {
                'changedField': field_dname,
                'fieldName': field_name,
                'fieldType': field_type,
                'id': message_1.tracking_value_ids.id,
                'newValue': {
                    'currencyId': False,
                    'floatPrecision': None,
                    'value': new_user.display_name,
                },
                'oldValue': {
                    'currencyId': False,
                    'floatPrecision': None,
                    'value': original_user.display_name,
                },
            })
        mail_render = records[1]._notify_by_email_prepare_rendering_context(message_1, {})
        self.assertEqual(mail_render['tracking_values'], [(field_dname, original_user.display_name, new_user.display_name)])

    def test_message_track_message_type(self):
        """Check that the right message type is applied for track templates."""
        self.record.message_subscribe(
            partner_ids=[self.user_admin.partner_id.id],
            subtype_ids=[self.env.ref('mail.mt_comment').id]
        )
        mail_templates = self.env['mail.template'].create([{
            'name': f'Template {n}',
            'subject': f'Template {n}',
            'model_id': self.env.ref('test_mail.model_mail_test_ticket').id,
            'body_html': f'<p>Template {n}</p>',
        } for n in range(2)])

        def _track_subtype(self, init_values):
            return self.env.ref('mail.mt_note')
        self.patch(self.registry('mail.test.ticket'), '_track_subtype', _track_subtype)

        def _track_template(self, changes):
            if 'email_from' in changes:
                return {'email_from': (mail_templates[0], {})}
            elif 'container_id' in changes:
                return {'container_id': (mail_templates[1], {'message_type': 'notification'})}
            return {}
        self.patch(self.registry('mail.test.ticket'), '_track_template', _track_template)

        container = self.env['mail.test.container'].create({'name': 'Container'})

        # default is auto_comment
        with self.mock_mail_gateway():
            self.record.email_from = 'test@test.lan'
            self.flush_tracking()

        first_message = self.record.message_ids.filtered(lambda message: message.subject == 'Template 0')
        self.assertEqual(len(self.record.message_ids), 2, 'Should be one change message and one automated template')
        self.assertEqual(first_message.message_type, 'auto_comment')

        # auto_comment can be overriden by _track_template
        with self.mock_mail_gateway(mail_unlink_sent=False):
            self.record.container_id = container
            self.flush_tracking()

        second_message = self.record.message_ids.filtered(lambda message: message.subject == 'Template 1')
        self.assertEqual(len(self.record.message_ids), 4, 'Should have added one change message and one automated template')
        self.assertEqual(second_message.message_type, 'notification')

    def test_message_track_multiple(self):
        """ check that multiple updates generate a single tracking message """
        container = self.env['mail.test.container'].with_context(mail_create_nosubscribe=True).create({'name': 'Container'})
        self.record.name = 'Zboub'
        self.record.customer_id = self.user_admin.partner_id
        self.record.user_id = self.user_admin
        self.record.container_id = container
        self.flush_tracking()

        # should have a single message with all tracked fields
        self.assertEqual(len(self.record.message_ids), 1, 'should have 1 tracking message')
        self.assertEqual(self.record.message_ids.author_id, self.partner_employee)
        self.assertTracking(self.record.message_ids[0], [
            ('customer_id', 'many2one', False, self.user_admin.partner_id),
            ('user_id', 'many2one', False, self.user_admin),
            ('container_id', 'many2one', False, container),
        ])

    def test_message_track_no_subtype(self):
        """ Update some tracked fields not linked to some subtype -> message with onchange """
        customer = self.env['res.partner'].create({'name': 'Customer', 'email': 'cust@example.com'})
        with self.mock_mail_gateway():
            self.record.write({
                'name': 'Test2',
                'customer_id': customer.id,
            })
            self.flush_tracking()

        # one new message containing tracking; without subtype linked to tracking, a note is generated
        self.assertEqual(len(self.record.message_ids), 1)
        self.assertEqual(self.record.message_ids.author_id, self.partner_employee)
        self.assertEqual(self.record.message_ids.subtype_id, self.env.ref('mail.mt_note'))

        # no specific recipients except those following notes, no email
        self.assertEqual(self.record.message_ids.partner_ids, self.env['res.partner'])
        self.assertEqual(self.record.message_ids.notified_partner_ids, self.env['res.partner'])
        self.assertNotSentEmail()

        # verify tracked value
        self.assertTracking(
            self.record.message_ids,
            [('customer_id', 'many2one', False, customer)  # onchange tracked field
             ])

    @users('employee')
    def test_message_track_no_tracking(self):
        """ Update a set of non tracked fields -> no message, no tracking, or
        use dedicated context key """
        record = self.record.with_env(self.env)
        record.write({
            'name': 'Tracking or not',
            'count': 32,
        })
        self.flush_tracking()
        self.assertFalse(record.message_ids)

        # check context key allowing to skip tracking
        record.with_context(mail_notrack=True).write({'email_from': 'new.from@test.example.com'})
        self.flush_tracking()
        self.assertFalse(record.message_ids)

    def test_message_track_subtype(self):
        """ Update some tracked fields linked to some subtype -> message with onchange """
        self.record.message_subscribe(
            partner_ids=[self.user_admin.partner_id.id],
            subtype_ids=[self.env.ref('test_mail.st_mail_test_ticket_container_upd').id]
        )

        container = self.env['mail.test.container'].with_context(mail_create_nosubscribe=True).create({'name': 'Container'})
        self.record.write({
            'name': 'Test2',
            'email_from': 'noone@example.com',
            'container_id': container.id,
        })
        self.flush_tracking()
        # one new message containing tracking; subtype linked to tracking
        self.assertEqual(len(self.record.message_ids), 1)
        self.assertEqual(self.record.message_ids.author_id, self.partner_employee)
        self.assertEqual(self.record.message_ids.subtype_id, self.env.ref('test_mail.st_mail_test_ticket_container_upd'))

        # no specific recipients except those following container
        self.assertEqual(self.record.message_ids.partner_ids, self.env['res.partner'])
        self.assertEqual(self.record.message_ids.notified_partner_ids, self.user_admin.partner_id)

        # verify tracked value
        self.assertTracking(
            self.record.message_ids,
            [('container_id', 'many2one', False, container)  # onchange tracked field
             ])

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_track_template(self):
        """ Update some tracked fields linked to some template -> message with onchange """
        self.record.write({'mail_template': self.env.ref('test_mail.mail_test_ticket_tracking_tpl').id})
        self.assertEqual(self.record.message_ids, self.env['mail.message'])

        with self.mock_mail_gateway():
            self.record.write({
                'name': 'Test2',
                'customer_id': self.user_admin.partner_id.id,
            })
            self.flush_tracking()

        self.assertEqual(len(self.record.message_ids), 2, 'should have 2 new messages: one for tracking, one for template')

        # one new message containing the template linked to tracking
        self.assertEqual(self.record.message_ids[0].author_id, self.partner_employee)
        self.assertEqual(self.record.message_ids[0].subject, 'Test Template')
        self.assertEqual(self.record.message_ids[0].body, '<p>Hello Test2</p>')

        # one email send due to template
        self.assertSentEmail(self.record.env.user.partner_id, [self.partner_admin], body='<p>Hello Test2</p>')

        # one new message containing tracking; without subtype linked to tracking
        self.assertEqual(self.record.message_ids[1].subtype_id, self.env.ref('mail.mt_note'))
        self.assertTracking(
            self.record.message_ids[1],
            [('customer_id', 'many2one', False, self.user_admin.partner_id)  # onchange tracked field
             ])

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_track_template_at_create(self):
        """ Create a record with tracking template on create, template should be sent."""

        Model = self.env['mail.test.ticket'].with_user(self.user_employee).with_context(self._test_context)
        Model = Model.with_context(mail_notrack=False)
        with self.mock_mail_gateway():
            record = Model.create({
                'name': 'Test',
                'customer_id': self.user_admin.partner_id.id,
                'mail_template': self.env.ref('test_mail.mail_test_ticket_tracking_tpl').id,
            })
            self.flush_tracking()

        self.assertEqual(len(record.message_ids), 1, 'should have 1 new messages for template')
        # one new message containing the template linked to tracking
        self.assertEqual(record.message_ids[0].author_id, self.partner_employee)
        self.assertEqual(record.message_ids[0].subject, 'Test Template')
        self.assertEqual(record.message_ids[0].body, '<p>Hello Test</p>')
        # one email send due to template
        self.assertSentEmail(self.record.env.user.partner_id, [self.partner_admin], body='<p>Hello Test</p>')

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.addons.mail.models.mail_thread')
    def test_message_track_template_at_create_from_message(self):
        """Make sure records created through aliasing show the original message before the template"""
        # setup
        test_model = self.env['ir.model']._get('mail.test.ticket')
        original_sender = self.user_admin.partner_id
        custom_values = {'name': 'Test', 'customer_id': original_sender.id,
                         'mail_template': self.env.ref('test_mail.mail_test_ticket_tracking_tpl').id}
        self.env['mail.alias'].create({
            'alias_name': 'groups',
            'alias_model_id': test_model.id,
            'alias_contact': 'everyone',
            'alias_defaults': custom_values})
        record = self.format_and_process(MAIL_TEMPLATE, '"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>',
                                         'groups@test.mycompany.com', target_field='customer_id', subject=custom_values['customer_id'],
                                         target_model='mail.test.ticket')

        with self.mock_mail_gateway(mail_unlink_sent=False):
            self.flush_tracking()

        # Should be trigger message and response template
        self.assertEqual(len(record.message_ids), 2)
        messages = list(record.message_ids)
        messages.sort(key=lambda msg: msg.id)
        trigger = messages[0]
        template = messages[1]
        self.assertIn('Please call me as soon as possible this afternoon!', trigger.body)
        self.assertIn(f"Hello {custom_values['name']}", template.body)
        self.assertMailMail(
            original_sender,
            'sent',
            author=self.env.ref('base.partner_root'),
            email_values={
                'body_content': f"<p>Hello {custom_values['name']}</p>",
            }
        )

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_track_template_create_partner_multicompany(self):
        """ Test partner created due to usage of a mail.template, triggered by
        a tracking, in a multi company environment. """
        company1 = self.env['res.company'].create({'name': 'company1'})
        self.env.user.write({'company_ids': [(4, company1.id, False)]})
        self.assertNotEqual(self.env.company, company1)

        email_new_partner = "diamonds@rust.com"
        Partner = self.env['res.partner']
        self.assertFalse(Partner.search([('email', '=', email_new_partner)]))

        template = self.env['mail.template'].create({
            'model_id': self.env['ir.model']._get('mail.test.track').id,
            'name': 'AutoTemplate',
            'subject': 'autoresponse',
            'email_from': self.env.user.email_formatted,
            'email_to': "{{ object.email_from }}",
            'body_html': "<div>A nice body</div>",
        })

        def patched_message_track_post_template(*args, **kwargs):
            if args[0]._name == "mail.test.track":
                args[0].message_post_with_source(template)
            return True

        with patch('odoo.addons.mail.models.mail_thread.MailThread._message_track_post_template', patched_message_track_post_template):
            self.env['mail.test.track'].create({
                'email_from': email_new_partner,
                'company_id': company1.id,
                'user_id': self.env.user.id, # trigger track template
            })
            self.flush_tracking()

        new_partner = Partner.search([('email', '=', email_new_partner)])
        self.assertTrue(new_partner)
        self.assertEqual(new_partner.company_id, company1)

    def test_message_track_template_defaults(self):
        """ Check that default_* keys are not taken into account in
        _message_track_post_template """
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
            'model_id': self.env.ref('test_mail.model_mail_test_container').id,
            'auto_delete': True,
            'body_html': '''<div>WOOP WOOP</div>''',
        })

        def _track_subtype(self, init_values):
            if 'name' in init_values and init_values['name'] == magic_code:
                return 'mail.mt_name_changed'
            return False
        self.patch(self.registry('mail.test.container'), '_track_subtype', _track_subtype)

        def _track_template(self, changes):
            res = {}
            if 'name' in changes:
                res['name'] = (mail_template, {'composition_mode': 'mass_mail'})
            return res
        self.patch(self.registry('mail.test.container'), '_track_template', _track_template)

        cls = type(self.env['mail.test.container'])
        self.assertFalse(hasattr(getattr(cls, 'name'), 'track_visibility'))
        getattr(cls, 'name').track_visibility = 'always'

        @self.addCleanup
        def cleanup():
            del getattr(cls, 'name').track_visibility

        test_mail_record = self.env['mail.test.container'].create({
            'name': 'Zizizatestmailname',
            'description': 'Zizizatestmaildescription',
        })
        test_mail_record.with_context(default_parent_id=2147483647).write({'name': magic_code})


@tagged('mail_track')
class TestTrackingInternals(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.record = cls.env['mail.test.ticket'].with_user(cls.user_employee).create({
            'name': 'Test',
        })
        cls.test_partner = cls.env['res.partner'].create({
            'country_id': cls.env.ref('base.be').id,
            'email': 'test.partner@test.example.com',
            'name': 'Test Partner',
            'phone': '0456001122',
        })

    @users('employee')
    def test_mail_track_2many(self):
        """ Check result of tracking one2many and many2many fields. Current
        usage is to aggregate names into value_char fields. """
        # Create a record with an initially invalid selection value
        test_tags = self.env['mail.test.track.all.m2m'].create([
            {'name': 'Tag1',},
            {'name': 'Tag2',},
            {'name': 'Tag3',},
        ])
        test_record = self.env['mail.test.track.all'].create({
            'name': 'Test 2Many fields tracking',
        })
        self.flush_tracking()

        # no tracked field, no tracking at create
        last_message = test_record.message_ids[0]
        self.assertFalse(last_message.tracking_value_ids)

        # update m2m
        test_record.write({
            'many2many_field': [(4, test_tags[0].id), (4, test_tags[1].id)],
        })
        self.flush_tracking()
        last_message = test_record.message_ids[0]
        self.assertTracking(
            last_message,
            [('many2many_field', 'many2many', '', ', '.join(test_tags[:2].mapped('name')))]
        )

        # update m2m + o2m
        test_record.write({
            'many2many_field': [(3, test_tags[0].id), (4, test_tags[2].id)],
            'one2many_field': [
                (0, 0, {'name': 'Child1'}),
                (0, 0, {'name': 'Child2'}),
                (0, 0, {'name': 'Child3'}),
                (0, 0, {'name': False}),
            ],
        })
        child4_tracking = f'Unnamed Sub-model: pseudo tags for tracking ({test_record.one2many_field[3].id})'
        self.flush_tracking()
        last_message = test_record.message_ids[0]
        self.assertTracking(
            last_message,
            [
                ('many2many_field', 'many2many', ', '.join(test_tags[:2].mapped('name')), ', '.join((test_tags[1] + test_tags[2]).mapped('name'))),
                ('one2many_field', 'one2many', '', f'Child1, Child2, Child3, {child4_tracking}'),
            ]
        )

        # remove from o2m
        test_record.write({'one2many_field': [(3, test_record.one2many_field[0].id)]})
        self.flush_tracking()
        last_message = test_record.message_ids[0]
        self.assertTracking(
            last_message,
            [('one2many_field', 'one2many', f'Child1, Child2, Child3, {child4_tracking}', f'Child2, Child3, {child4_tracking}')]
        )

    @users('employee')
    def test_mail_track_all_no2many(self):
        test_record = self.env['mail.test.track.all'].create({
            'company_id': self.env.company.id,
        })
        self.flush_tracking()
        self.assertEqual(test_record.currency_id, self.env.ref('base.USD'))
        messages = test_record.message_ids
        today = fields.Date.today()
        today_dt = fields.Datetime.to_datetime(today)
        now = fields.Datetime.now()

        test_record.write({
            'boolean_field': True,
            'char_field': 'char_value',
            'date_field': today,
            'datetime_field': now,
            'float_field': 3.22,
            'float_field_with_digits': 3.00001,
            'html_field': '<p>Html Value</p>',
            'integer_field': 42,
            'many2one_field_id': self.test_partner.id,
            'monetary_field': 42.42,
            'selection_field': 'first',
            'text_field': 'text_value',
        })
        self.flush_tracking()
        new_message = test_record.message_ids - messages
        self.assertEqual(len(new_message), 1,
                         'Should have generated a tracking value')
        tracking_value_list = [
            ('boolean_field', 'boolean', 0, 1),
            ('char_field', 'char', False, 'char_value'),
            ('date_field', 'date', False, today_dt),
            ('datetime_field', 'datetime', False, now),
            ('float_field', 'float', 0, 3.22),
            ('float_field_with_digits', 'float', 0, 3.00001),
            ('integer_field', 'integer', 0, 42),
            ('many2one_field_id', 'many2one', self.env['res.partner'], self.test_partner),
            ('monetary_field', 'monetary', False, (42.42, self.env.ref('base.USD'))),
            ('selection_field', 'selection', '', 'FIRST'),
            ('text_field', 'text', False, 'text_value'),
        ]
        self.assertTracking(new_message, tracking_value_list, strict=True)
        # check formatting for all field types
        formatted_values_all = new_message.tracking_value_ids._tracking_value_format()
        for (field_name, field_type, _, _), formatted_vals in zip(tracking_value_list, formatted_values_all):
            currency = self.env.ref('base.USD').id if field_type == 'monetary' else False
            precision = None if field_name != 'float_field_with_digits' else (10, 8)
            with self.subTest(field_name=field_name):
                self.assertEqual(formatted_vals['oldValue']['currencyId'], currency)
                self.assertEqual(formatted_vals['newValue']['currencyId'], currency)
                self.assertEqual(formatted_vals['oldValue']['floatPrecision'], precision)
                self.assertEqual(formatted_vals['newValue']['floatPrecision'], precision)

    @users('employee')
    def test_mail_track_compute(self):
        """ Test tracking of computed fields """
        # no tracking at creation
        compute_record = self.env['mail.test.track.compute'].create({})
        self.flush_tracking()
        self.assertEqual(len(compute_record.message_ids), 1)
        self.assertEqual(len(compute_record.message_ids[0].tracking_value_ids), 0)

        # assign partner_id: one tracking message for the modified field and all
        # the stored and non-stored computed fields on the record
        partner_su = self.env['res.partner'].sudo().create({
            'name': 'Foo',
            'email': 'foo@example.com',
            'phone': '1234567890',
        })
        compute_record.partner_id = partner_su
        self.flush_tracking()
        self.assertEqual(len(compute_record.message_ids), 2)
        self.assertEqual(len(compute_record.message_ids[0].tracking_value_ids), 4)
        self.assertEqual(compute_record.message_ids.author_id, self.partner_employee)
        self.assertTracking(compute_record.message_ids[0], [
            ('partner_id', 'many2one', False, partner_su),
            ('partner_name', 'char', False, 'Foo'),
            ('partner_email', 'char', False, 'foo@example.com'),
            ('partner_phone', 'char', False, '1234567890'),
        ])

        # modify partner: one tracking message for the only recomputed field
        partner_su.write({'name': 'Fool'})
        self.flush_tracking()
        self.assertEqual(len(compute_record.message_ids), 3)
        self.assertEqual(len(compute_record.message_ids[0].tracking_value_ids), 1)
        self.assertTracking(compute_record.message_ids[0], [
            ('partner_name', 'char', 'Foo', 'Fool'),
        ])

        # modify partner: one tracking message for both stored computed fields;
        # the non-stored computed fields have no tracking
        partner_su.write({
            'name': 'Bar',
            'email': 'bar@example.com',
            'phone': '0987654321',
        })
        # force recomputation of 'partner_phone' to make sure it does not
        # generate tracking values
        self.assertEqual(compute_record.partner_phone, '0987654321')
        self.flush_tracking()
        self.assertEqual(len(compute_record.message_ids), 4)
        self.assertEqual(len(compute_record.message_ids[0].tracking_value_ids), 2)
        self.assertTracking(compute_record.message_ids[0], [
            ('partner_name', 'char', 'Fool', 'Bar'),
            ('partner_email', 'char', 'foo@example.com', 'bar@example.com'),
        ])

    @users('employee')
    def test_mail_track_monetary(self):
        """ Update a record with a tracked monetary field """
        monetary_record = self.env['mail.test.track.monetary'].with_user(self.user_employee).create({
            'company_id': self.user_employee.company_id.id,
        })
        self.flush_tracking()
        self.assertEqual(len(monetary_record.message_ids), 1)

        # Check if the tracking value have the correct currency and values
        monetary_record.write({
            'revenue': 100,
        })
        self.flush_tracking()
        self.assertEqual(len(monetary_record.message_ids), 2)
        self.assertTracking(monetary_record.message_ids[0], [
            ('revenue', 'monetary', 0, (100, self.env.company.currency_id)),
        ])

        # Check if the tracking value have the correct currency and values after changing the value and the company
        monetary_record.write({
            'revenue': 200,
            'company_id': self.company_2.id,
        })
        self.flush_tracking()
        self.assertEqual(len(monetary_record.message_ids), 3)
        self.assertTracking(monetary_record.message_ids[0], [
            ('revenue', 'monetary', 100, (200, self.company_2.currency_id)),
            ('company_currency', 'many2one', self.user_employee.company_id.currency_id, self.company_2.currency_id)
        ])

    @users('employee')
    def test_mail_track_selection_invalid(self):
        """ Check that initial invalid selection values are allowed when tracking """
        # Create a record with an initially invalid selection value
        invalid_value = 'I love writing tests!'
        record = self.env['mail.test.track.selection'].create({
            'name': 'Test Invalid Selection Values',
            'selection_type': 'first',
        })

        self.flush_tracking()
        self.env.cr.execute(
            """
            UPDATE mail_test_track_selection
               SET selection_type = %s
             WHERE id = %s
            """,
            [invalid_value, record.id]
        )
        record.invalidate_recordset()
        self.assertEqual(record.selection_type, invalid_value)

        # Write a valid selection value
        record.selection_type = "second"

        self.flush_tracking()
        self.assertTracking(record.message_ids, [
            ('selection_type', 'char', invalid_value, 'Second'),
        ])

    def test_track_groups(self):
        """ Test field groups and filtering when using standard helpers """
        # say that 'email_from' is accessible to erp_managers only
        field = self.record._fields['email_from']
        self.addCleanup(setattr, field, 'groups', field.groups)
        field.groups = 'base.group_erp_manager'

        self.record.sudo().write({'email_from': 'X'})
        self.flush_tracking()

        msg_emp = Store(self.record.message_ids, for_current_user=True).get_result()
        msg_admin = Store(
            self.record.with_user(self.user_admin).message_ids, for_current_user=True
        ).get_result()
        msg_sudo = Store(self.record.sudo().message_ids, for_current_user=True).get_result()

        tracking_values = self.env['mail.tracking.value'].search([('mail_message_id', '=', self.record.message_ids[0].id)])
        formatted_tracking_values = [{
            'changedField': 'Email From',
            'id': tracking_values[0]['id'],
            'fieldName': 'email_from',
            'fieldType': 'char',
            'newValue': {
                'currencyId': False,
                'floatPrecision': None,
                'value': 'X',
            },
            'oldValue': {
                'currencyId': False,
                'floatPrecision': None,
                'value': False,
            },
        }]
        self.assertEqual(
            msg_emp["mail.message"][0].get("trackingValues"),
            [],
            "should not have protected tracking values",
        )
        self.assertEqual(
            msg_admin["mail.message"][0].get("trackingValues"),
            formatted_tracking_values,
            "should have protected tracking values",
        )
        self.assertEqual(
            msg_sudo["mail.message"][0].get("trackingValues"),
            formatted_tracking_values,
            "should have protected tracking values",
        )

        values_emp = self.record._notify_by_email_prepare_rendering_context(self.record.message_ids[0], {})
        values_admin = self.record.with_user(self.user_admin)._notify_by_email_prepare_rendering_context(self.record.message_ids[0], {})
        values_sudo = self.record.sudo()._notify_by_email_prepare_rendering_context(self.record.message_ids[0], {})
        self.assertFalse(values_emp.get('tracking_values'), "should not have protected tracking values")
        self.assertTrue(values_admin.get('tracking_values'), "should have protected tracking values")
        self.assertTrue(values_sudo.get('tracking_values'), "should have protected tracking values")

        # test editing the record with user not in the group of the field
        self.env.invalidate_all()
        self.env.registry.clear_cache()
        record_form = Form(self.record.with_user(self.user_employee))
        record_form.name = 'TestDoNoCrash'
        # the employee user must be able to save the fields on which they can write
        # if we fetch all the tracked fields, ignoring the group of the current user
        # it will crash and it shouldn't
        record = record_form.save()
        self.assertEqual(record.name, 'TestDoNoCrash')

    @users('employee')
    def test_track_invalid(self):
        """ Test invalid use cases: unknown field, unsupported type, ... """
        test_record = self.env['mail.test.track.all'].create({
            'company_id': self.env.company.id,
        })
        self.flush_tracking()

        # raise on non existing field
        with self.assertRaises(ValueError):
            self.env['mail.tracking.value']._create_tracking_values(
                '', 'Test',
                'not_existing_field', {'string': 'Test', 'type': 'char'},
                test_record,
            )

        # raise on unsupported field type
        with self.assertRaises(NotImplementedError):
            self.env['mail.tracking.value']._create_tracking_values(
                '', '<p>Html</p>',
                'html_field', {'string': 'HTML', 'type': 'html'},
                test_record,
            )

    @users('employee')
    def test_track_multi_models(self):
        """ Some models track value coming from another model e.g. when having
        a sub model (lines) on which some value should be tracked on a parent
        model. Test there is no model mismatch. """
        main_track = self.env['mail.test.track.all'].create({
            'name': 'Multi Models Tracking',
            'char_field': 'char_value',
        })
        self.flush_tracking()
        self.assertEqual(len(main_track.message_ids), 1)
        self.assertFalse(main_track.message_ids.tracking_value_ids)

        sub_track = self.env['mail.test.track.groups'].create({
            'name': 'Groups',
            'secret': 'secret',
        })
        # some custom code generates tracking values on main_track
        main_track.message_post(
            body='Custom Log with Tracking',
            tracking_value_ids=[
                (0, 0, {
                    'field_id': self.env['ir.model.fields']._get(sub_track._name, 'secret').id,
                    'new_value_char': 'secret',
                    'old_value_char': False,
                }),
                (0, 0, {
                    'field_id': False,
                    'new_value_integer': self.env.uid,
                    'old_value_integer': False,
                }),
                (0, 0, {
                    'field_id': False,
                    'field_info': {
                        'desc': 'Old integer',
                        'name': 'Removed',
                        'sequence': 35,
                        'type': 'integer',
                    },
                    'new_value_integer': 35,
                    'old_value_integer': 30,
                }),
            ],
        )
        trackings = main_track.message_ids.sudo().tracking_value_ids
        self.assertEqual(len(trackings), 3)

        # check groups, as it depends on model
        for tracking, exp_groups in zip(trackings, ['base.group_user', 'base.group_system', 'base.group_system']):
            groups = 'base.group_system'
            if tracking.field_id:
                field = self.env[tracking.field_id.model]._fields[tracking.field_id.name]
                groups = field.groups
            self.assertEqual(groups, exp_groups)

        # check formatting, as it fetches info on model
        formatted = trackings._tracking_value_format()
        self.assertEqual(
            formatted,
            [
                {
                    'changedField': 'Secret',
                    'id': trackings[0].id,
                    'fieldName': 'secret',
                    'fieldType': 'char',
                    'newValue': {'currencyId': False, 'floatPrecision': None, 'value': 'secret'},
                    'oldValue': {'currencyId': False, 'floatPrecision': None, 'value': False}
                }, {
                    'changedField': 'Old integer',
                    'id': trackings[2].id,
                    'fieldName': 'Removed',
                    'fieldType': 'integer',
                    'newValue': {'currencyId': False, 'floatPrecision': None, 'value': 35},
                    'oldValue': {'currencyId': False, 'floatPrecision': None, 'value': 30}
                }, {
                    'changedField': 'Unknown',
                    'id': trackings[1].id,
                    'fieldName': 'unknown',
                    'fieldType': 'char',
                    'newValue': {'currencyId': False, 'floatPrecision': None, 'value': False},
                    'oldValue': {'currencyId': False, 'floatPrecision': None, 'value': False}
                }
            ]
        )


    @users('employee')
    def test_track_sequence(self):
        """ Update some tracked fields and check that the mail.tracking.value
        are ordered according to their tracking_sequence """
        record = self.record.with_env(self.env)
        self.assertEqual(len(record.message_ids), 1)
        # order: user_id -> 1, customer_id -> 2, container_id -> True -> 100, email_from -> True -> 100
        ordered_fnames = ['user_id', 'customer_id', 'container_id', 'email_from']

        # Update tracked fields, should generate tracking values correctly ordered
        record.write({
            'container_id': self.env['mail.test.container'].with_context(mail_create_nosubscribe=True).create({'name': 'Container'}).id,
            'customer_id': self.user_admin.partner_id.id,
            'email_from': 'new.from@test.example.com',
            'name': 'Zboub',
            'user_id': self.user_admin.id,
        })
        self.flush_tracking()
        self.assertEqual(len(record.message_ids), 2, 'should have 1 new tracking message')
        tracking_values = self.env['mail.tracking.value'].sudo().search(
            [('mail_message_id', '=', record.message_ids[0].id)]
        )
        self.assertEqual(
            tracking_values.field_id.mapped('name'),
            ordered_fnames,
            'Track: order, based on ID DESC, should follow tracking sequence (or name) on field'
        )

        # Manually create trackings, format should be the fallback to reorder them
        new_msg = record.message_post(
            body='Manual Hack of tracking',
            subtype_xmlid='mail.mt_note',
        )
        custom_order_fnames = ['container_id', 'customer_id', 'email_from', 'user_id']
        field_ids = [
            self.env['ir.model.fields']._get(record._name, fname).id
            for fname in custom_order_fnames
        ]
        self.env['mail.tracking.value'].sudo().create([
            {
                'field_id': field_id,
                'mail_message_id': new_msg.id,
                'old_value_char': 'unimportant',
                'new_value_char': 'unimportant',
            }
            for field_id in field_ids
        ])
        tracking_values = self.env['mail.tracking.value'].sudo().search(
            [('mail_message_id', '=', record.message_ids[0].id)]
        )
        self.assertEqual(
            tracking_values.field_id.mapped('name'),
            list(reversed(custom_order_fnames)),
            'Tracking model: order, based on ID DESC, following reverted insertion'
        )
        tracking_formatted = tracking_values._tracking_value_format()
        self.assertEqual(
            [t['fieldName'] for t in tracking_formatted],
            ordered_fnames,
            'Track: formatted order is correctly based on field sequence definition'
        )

    @users('employee')
    def test_unlinked_model(self):
        """ Fields from obsolete models with tracking values can be unlinked without error. """
        record = self.record.with_env(self.env)
        record.write({'email_from': 'new_value'})  # create a tracking value
        self.flush_tracking()
        self.assertTracking(
            record.message_ids[0],
            [('email_from', 'char', False, 'new_value')],
            strict=True,
        )

        fields_to_remove = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'mail.test.ticket'),
        ])

        # Simulate a registry without the model, which is what we have if we
        # update a module with the model code removed
        model = self.env.registry.models.pop('mail.test.ticket')
        try:
            fields_to_remove.with_context(_force_unlink=True).unlink()
        finally:
            # Restore model to prevent registry errors after test
            self.env.registry.models['mail.test.ticket'] = model

    @users('employee')
    def test_unlinked_field(self):
        """ Check that removing a field removes its tracking values. """
        record = self.record.with_env(self.env)
        record.write({'email_from': 'new_value'})  # create a tracking value

        record_other = self.env['mail.test.ticket'].create({})
        self.flush_tracking()
        record_other.write({'email_from': 'email.from.1@example.com'})
        self.flush_tracking()
        record_other.write({
            'customer_id': self.test_partner.id,
            'email_from': 'email.from.2@example.com',
            'user_id': self.env.user.id,
        })
        self.flush_tracking()

        self.assertTracking(
            record.message_ids[0],
            [('email_from', 'char', False, 'new_value')],
            strict=True,
        )
        self.assertTracking(
            record_other.message_ids[0],
            [('customer_id', 'integer', False, self.test_partner.id),
             ('email_from', 'char', 'email.from.1@example.com', 'email.from.2@example.com'),
             ('user_id', 'integer', False, self.env.user.id)],
            strict=True,
        )
        self.assertTracking(
            record_other.message_ids[1],
            [('email_from', 'char', False, 'email.from.1@example.com')],
            strict=True,
        )

        # check display / format
        trackings_all = (record + record_other).message_ids.sudo().tracking_value_ids
        trackings_all_sorted = [
            trackings_all.filtered(lambda t: t.field_id.name == 'user_id'),  # tracking=1
            trackings_all.filtered(lambda t: t.field_id.name == 'customer_id'),  # tracking=2
            trackings_all.filtered(lambda t: t.field_id.name == 'email_from')[0],  # tracking=True -> 100
            trackings_all.filtered(lambda t: t.field_id.name == 'email_from')[1],  # tracking=True -> 100
            trackings_all.filtered(lambda t: t.field_id.name == 'email_from')[2],  # tracking=True -> 100
        ]
        fields_info = [
            ('user_id', 'many2one', 'Responsible'),
            ('customer_id', 'many2one', 'Customer'),
            ('email_from', 'char', 'Email From'),
            ('email_from', 'char', 'Email From'),
            ('email_from', 'char', 'Email From'),
        ]
        values_info = [
            ('', self.env.user.name),
            ('', self.test_partner.name),
            (False, 'new_value'),
            ('email.from.1@example.com', 'email.from.2@example.com'),
            (False, 'email.from.1@example.com'),
        ]
        formatted = trackings_all._tracking_value_format()
        self.assertEqual(
            formatted,
            [
                {
                    'changedField': field_info[2],
                    'id': tracking.id,
                    'fieldName': field_info[0],
                    'fieldType': field_info[1],
                    'newValue': {
                        'currencyId': False,
                        'floatPrecision': None,
                        'value': values[1],
                    },
                    'oldValue': {
                        'currencyId': False,
                        'floatPrecision': None,
                        'value': values[0],
                    },
                }
                for tracking, field_info, values in zip(trackings_all_sorted, fields_info, values_info)
            ]
        )

        # remove fields
        fields_toremove = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'mail.test.ticket'),
            ('name', 'in', ('email_from', 'user_id', 'datetime'))  # also include a non tracked field
        ])
        fields_toremove.with_context(_force_unlink=True).unlink()
        self.assertEqual(len(trackings_all.exists()), 5)

        # check display / format, even if field is removed
        formatted = trackings_all._tracking_value_format()
        self.assertEqual(
            formatted,
            [
                {
                    'changedField': field_info[2],
                    'id': tracking.id,
                    'fieldName': field_info[0],
                    'fieldType': field_info[1],
                    'newValue': {
                        'currencyId': False,
                        'floatPrecision': None,
                        'value': values[1],
                    },
                    'oldValue': {
                        'currencyId': False,
                        'floatPrecision': None,
                        'value': values[0],
                    },
                }
                for tracking, field_info, values in zip(trackings_all_sorted, fields_info, values_info)
            ]
        )
