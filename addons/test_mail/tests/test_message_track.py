# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from unittest.mock import patch
from markupsafe import Markup

from odoo import fields
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE
from odoo.tests import Form, tagged, users
from odoo.tools import mute_logger
from odoo.tools.mail import formataddr


class TestTrackingCommon(MailCommon):
    """ Test main API and methods of tracking, to be called in py code. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dt_ref = datetime(2025, 9, 30, 9, 28, 15)
        cls.tracking_parent_for_properties = cls.env['mail.test.track.all.properties.parent'].with_user(cls.user_admin).create({
            'definition_properties': [
                {'name': 'property_char', 'string': 'Property Char', 'type': 'char', 'default': 'char value'},
                {'name': 'property_m2o', 'string': 'Property M2O', 'type': 'many2one', 'comodel': 'mail.test.ticket'},
            ],
            'name': 'PropDefinition',
        })
        cls.test_tracking_records = cls.env['mail.test.track.all'].with_user(cls.user_employee).create([
            {
                'datetime_field': cls.dt_ref,
                'name': f'Test Tracking {idx}',
                'properties_parent_id': cls.tracking_parent_for_properties.id,
            } for idx in range(5)
        ])

        # ticket-like record, for advanced tests with templates, subtypes, ...
        cls.test_ticket_record = cls.env['mail.test.ticket'].with_user(cls.user_employee).create({'name': 'Test'})


@tagged('mail_track')
class TestTrackingAPI(TestTrackingCommon):
    """ Test main API and methods of tracking, to be called in py code. """

    @users('employee')
    def test_tracking_create(self):
        records = self.test_tracking_records.with_env(self.env)
        for record in records:
            record_su = record.sudo()  # to check for tracking values directly
            self.assertEqual(len(record_su.message_ids), 1, 'Should have creation message only')
            # no tracking at create
            self.assertMessageFields(record_su.message_ids, {'tracking_values': []})

    @users('employee')
    def test_tracking_default_subtype(self):
        """ Update some tracked fields not linked to some subtype -> message with onchange """
        customer = self.env['res.partner'].create({'name': 'Customer', 'email': 'cust@example.com'})
        test_record = self.test_ticket_record.with_env(self.env)
        test_record.message_subscribe(
            partner_ids=self.user_admin.partner_id.ids,
            subtype_ids=self.env.ref('test_mail.st_mail_test_ticket_container_upd').ids,
        )
        self.assertEqual(len(test_record.message_ids), 1)

        with self.mock_mail_gateway(), self.mock_mail_app():
            test_record.write({
                'name': 'Test2',
                'customer_id': customer.id,
            })
            self.flush_tracking()

        # one new message containing tracking; without subtype linked to tracking, a note is generated
        self.assertEqual(len(test_record.message_ids), 2)
        track_msg = self._new_msgs
        self.assertMessageFields(
            track_msg, {
                'author_id': self.partner_employee,
                'notified_partner_ids': self.env['res.partner'],
                'partner_ids': self.env['res.partner'],  # no sepcific recipients except those following notes
                'subtype_id': self.env.ref('mail.mt_note'),
                'tracking_values': [('customer_id', 'many2one', False, customer)],  # onchange tracked field
            }
        )
        # no specific recipients except those following notes, no email
        self.assertNotSentEmail()

        # change container_id field, linked to a subtype through _track_subtype override
        container = self.env['mail.test.container'].create({'name': 'Container'})
        with self.mock_mail_gateway(), self.mock_mail_app():
            test_record.write({
                'name': 'Test2',
                'email_from': 'noone@example.com',
                'container_id': container.id,
            })
            self.flush_tracking()
        # one new message containing tracking; subtype linked to tracking
        self.assertEqual(len(test_record.message_ids), 3)
        track_msg = self._new_msgs
        self.assertMessageFields(
            track_msg, {
                'author_id': self.partner_employee,
                'notified_partner_ids': self.partner_admin,
                'partner_ids': self.env['res.partner'],  # no sepcific recipients except those following subtype
                'subtype_id': self.env.ref('test_mail.st_mail_test_ticket_container_upd'),
                'tracking_values': [
                    ('email_from', 'char', False, 'noone@example.com'),
                    ('container_id', 'many2one', False, container),
                ],
            }
        )

    @users('employee')
    def test_tracking_get_fields(self):
        """ Just be sure `_track_get_fields` can be accessed as classic user, check
        returned result """
        records = self.test_tracking_records.with_env(self.env)[0]
        fieldnames = records._track_get_fields()
        self.assertEqual(fieldnames, {
            'selection_field', 'text_field', 'many2one_field_id', 'char_field', 'float_field', 'properties',
            'boolean_field', 'date_field', 'integer_field', 'many2many_field', 'datetime_field', 'one2many_field',
            'float_field_with_digits', 'monetary_field', 'properties_parent_id'
        })

    @users('employee')
    def test_tracking_tweak_author(self):
        record = self.test_tracking_records.with_env(self.env)[0]
        with self.mock_mail_gateway(), self.mock_mail_app():
            record._track_set_author(self.partner_admin)
            record.write({
                'many2one_field_id': self.partner_employee.id,
            })
            self.flush_tracking()
        self.assertEqual(len(record.message_ids), 2)
        self.assertEqual(len(self._new_msgs), 1)
        track_msg = self._new_msgs
        self.assertMessageFields(
            track_msg, {
                'author_id': self.partner_admin,
                'tracking_values': [('many2one_field_id', 'many2one', False, self.partner_employee)],
            }
        )

    @users('employee')
    def test_tracking_tweak_default_message(self):
        """Check that the default tracking log message defined on the model is used
        and that setting a log message overrides it. See `_track_get_default_log_message`"""
        record = self.env['mail.test.track'].create({
            'name': 'Test',
            'track_enable_default_log': True,
        })
        self.flush_tracking()
        self.assertEqual(len(record.message_ids), 1)

        with self.mock_mail_gateway(), self.mock_mail_app():
            record.user_id = self.user_admin
            self.flush_tracking()
        self.assertEqual(len(record.message_ids), 2)
        track_msg = self._new_msgs.filtered(lambda m: m.message_type != "user_notification")
        self.assertMessageFields(
            track_msg, {
                'author_id': self.partner_employee,
                # default message (`_track_get_default_log_message`) should be used
                'body': '<p>There was a change on Test for fields "user_id"</p>',
                'tracking_values': [('user_id', 'many2one', False, self.user_admin)],
            }
        )

        with self.mock_mail_gateway(), self.mock_mail_app():
            record._track_set_log_message('<p>Forced Log</p>')
            record.user_id = False
            self.flush_tracking()
        self.assertEqual(len(record.message_ids), 3)
        track_msg = self._new_msgs
        self.assertMessageFields(
            track_msg, {
                'author_id': self.partner_employee,
                # _track_set_log_message should take priority over default message
                # and escapes content by default
                'body': '<p>&lt;p&gt;Forced Log&lt;/p&gt;</p>',
                'tracking_values': [('user_id', 'many2one', self.user_admin, False)],
            }
        )

        with self.mock_mail_gateway(), self.mock_mail_app():
            record._track_set_log_message(Markup('<p>Forced Log</p>'))
            record.user_id = self.user_admin.id
            self.flush_tracking()
        self.assertEqual(len(record.message_ids), 4)
        _assign_msg, track_msg = self._new_msgs  # tracking and user_notification for admin
        self.assertMessageFields(
            track_msg, {
                'author_id': self.partner_employee,
                # Markup content is valid html
                'body': '<p>Forced Log</p>',
                'tracking_values': [('user_id', 'many2one', False, self.user_admin)],
            }
        )

    @users('employee')
    def test_tracking_tweak_filter_for_display(self):
        """Check that tracked fields filtered for display are not present in the front-end and
        email formatting methods. See `_track_filter_for_display`"""
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
            self.assertMessageFields(
                record.message_ids[0], {
                    'tracking_values': [('user_id', 'many2one', original_user, new_user)],
                }
            )
        # first record: tracking value should be hidden
        message_0 = records[0].message_ids[0]
        formatted = Store().add(message_0, "_store_message_fields").get_result()["mail.message"][0]
        self.assertEqual(formatted['trackingValues'], [], 'Hidden values should not be formatted')
        mail_render = records[0]._notify_by_email_prepare_rendering_context(message_0, {})
        self.assertEqual(mail_render['tracking_values'], [])

        # second record: all values displayed
        message_1 = records[1].message_ids[0]
        formatted = Store().add(message_1, "_store_message_fields").get_result()["mail.message"][0]
        self.assertEqual(len(formatted['trackingValues']), 1)
        self.assertDictEqual(
            formatted['trackingValues'][0],
            {
                'id': message_1.sudo().tracking_value_ids.id,
                'fieldInfo': {
                    'changedField': 'Responsible',
                    'currencyId': False,
                    'floatPrecision': None,
                    'fieldType': 'many2one',
                    'isPropertyField': False,
                },
                'newValue': new_user.display_name,
                'oldValue': original_user.display_name,
            })
        mail_render = records[1]._notify_by_email_prepare_rendering_context(message_1, {})
        self.assertEqual(mail_render['tracking_values'], [('Responsible', original_user.display_name, new_user.display_name)])

    @users('employee')
    def test_tracking_update(self):
        test_record = self.test_tracking_records[0].with_env(self.env)
        original_messages = test_record.message_ids
        test_record.write({'name': 'Tracking or not'})
        self.flush_tracking()
        self.assertEqual(test_record.message_ids, original_messages)

        # check context key allowing to skip tracking
        test_record.with_context(mail_notrack=True).write({'char_field': 'new.from@test.example.com'})
        self.flush_tracking()
        self.assertEqual(test_record.message_ids, original_messages)

        with self.mock_mail_app():
            test_record.name = 'Zboub'
            test_record.float_field_with_digits = 15.285
            test_record.many2one_field_id = self.partner_admin
            test_record.selection_field = 'first'
            self.flush_tracking()
        # should have a single message with all tracked fields
        self.assertEqual(len(self._new_msgs), 1)
        self.assertMessageFields(
            self._new_msgs, {
                'author_id': self.partner_employee,
                'subtype_id': self.env.ref('mail.mt_note'),  # by default, trackings are notes
                'tracking_values': [
                    ('many2one_field_id', 'many2one', False, self.partner_admin),
                    ('float_field_with_digits', 'float', False, 15.285),
                    ('selection_field', 'selection', '', 'FIRST'),
                ],
            }
        )


@tagged('mail_track')
class TestTrackingTemplate(TestTrackingCommon):
    """ Test template-based message generation based on tracking """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # for multi-enabled tests
        cls.test_ticket_records = cls.test_ticket_record + cls.env['mail.test.ticket'].with_user(cls.user_employee).create([
            {'name': 'Test 2', 'mail_template': False},
            {'name': 'Test 3', 'mail_template': cls.env.ref('test_mail.mail_test_ticket_tracking_tpl').id},
        ])

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_track_template(self):
        """ Update some tracked fields linked to some template -> message with onchange on
        each updated record. """
        test_records = self.test_ticket_records.with_env(self.env)
        test_records.write({'mail_template': self.env.ref('test_mail.mail_test_ticket_tracking_tpl').id})
        self.flush_tracking()
        for test_record in test_records:
            self.assertEqual(len(test_record.message_ids), 1, 'Creation message')

        with self.mock_mail_gateway(), self.mock_mail_app():
            test_records.write({
                'name': 'Test2',
                'customer_id': self.user_admin.partner_id.id,
            })
            self.flush_tracking()
        for test_record in test_records:
            self.assertEqual(len(test_record.message_ids), 3, 'should have 2 new messages: one for tracking, one for template')
            tpl_msg, track_msg, _create_msg = test_record.message_ids
            self.assertMessageFields(
                tpl_msg, {
                    'author_id': self.partner_employee,
                    'body': f'<p>Hello {test_record.name}</p>',
                    'notified_partner_ids': self.partner_admin,
                    'subject': f'Test Template on {test_record.name}',
                    'subtype_id': self.env['mail.message.subtype'],  # tde: to check ?
                    'tracking_values': [],  # no tracking sent with template
                }
            )
            self.assertMessageFields(
                track_msg, {
                    'author_id': self.partner_employee,
                    'body': '',
                    'notified_partner_ids': self.env['res.partner'],
                    'subject': False,
                    'subtype_id': self.env.ref('mail.mt_note'),
                    'tracking_values': [
                        ('customer_id', 'many2one', False, self.user_admin.partner_id),
                    ],
                }
            )
            # one email sent due to template
            self.assertMailMail(
                [self.partner_admin],
                'sent',
                author=self.partner_employee,
                email_values={
                    'email_from': self.partner_employee.email_formatted,
                    'reply_to': formataddr((self.partner_employee.name, f'{self.alias_catchall}@{self.alias_domain}')),
                },
                fields_values={
                    'body': '<p>Hello Test2</p>',
                }
            )

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_track_template_at_create(self):
        """ Create records in batch with tracking template on create, template should be sent
        on all records. """
        with self.mock_mail_gateway():
            test_tickets = self.env['mail.test.ticket'].with_user(self.user_employee).create([
                {
                    'name': f'Create Test {idx}',
                    'customer_id': self.user_admin.partner_id.id,
                    'mail_template': self.env.ref('test_mail.mail_test_ticket_tracking_tpl').id,
                } for idx in range(2)
            ])
            self.flush_tracking()

        for test_ticket in test_tickets:
            self.assertEqual(len(test_ticket.message_ids), 2, 'should have 1 creation message and 1 template message')
            # one new message containing the template linked to tracking
            tpl_msg = test_ticket.message_ids[0]
            self.assertMessageFields(
                tpl_msg, {
                    'author_id': self.partner_employee,
                    'body': f'<p>Hello {test_ticket.name}</p>',
                    'subject': f'Test Template on {test_ticket.name}',
                }
            )
            # one email send due to template
            self.assertMailMail(
                [self.partner_admin],
                'sent',
                author=self.partner_employee,
                content=f'<p>Hello {test_ticket.name}</p>',  # used to distinguish outgoing mails
                email_values={
                    'email_from': self.partner_employee.email_formatted,
                    'reply_to': formataddr((self.partner_employee.name, f'{self.alias_catchall}@{self.alias_domain}')),
                    'subject': f'Test Template on {test_ticket.name}',
                },
                fields_values={
                    'body': f'<p>Hello {test_ticket.name}</p>',
                    'subject': f'Test Template on {test_ticket.name}',
                }
            )

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.addons.mail.models.mail_thread')
    def test_message_track_template_at_create_from_mailgateway(self):
        """Make sure records created through aliasing show the original message before the template"""
        # setup
        original_sender = self.user_admin.partner_id
        custom_values = {
            'customer_id': original_sender.id,
            'name': 'Test',
            'mail_template': self.env.ref('test_mail.mail_test_ticket_tracking_tpl').id,
        }
        self.env['mail.alias'].create({
            'alias_name': 'groups',
            'alias_model_id': self.env['ir.model']._get_id('mail.test.ticket'),
            'alias_contact': 'everyone',
            'alias_defaults': custom_values})
        record = self.format_and_process(
            MAIL_TEMPLATE, '"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>', 'groups@test.mycompany.com',
            target_field='customer_id', subject=custom_values['customer_id'],
            target_model='mail.test.ticket',
        )

        with self.mock_mail_gateway(mail_unlink_sent=False):
            self.flush_tracking()

        # Should be trigger message and response template
        self.assertEqual(len(record.message_ids), 2)
        trigger, template = sorted(record.message_ids, key=lambda msg: msg.id)
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

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_track_template_create_partner_multicompany(self):
        """ Test partner created due to usage of a mail.template, triggered by
        a tracking, in a multi company environment. """
        self.env.user.write({'company_ids': [(4, self.company_2.id, False)]})
        self.assertNotEqual(self.env.company, self.company_2)
        self.assertEqual(self.env.company, self.company_admin)

        email_new_partner = '"Raoulette Mobylette" <diamonds@rust.example.com>'
        email_new_partner_normalized = 'diamonds@rust.example.com'
        self.assertFalse(self.env['res.partner'].search([('email_normalized', '=', email_new_partner_normalized)]))

        template = self.env['mail.template'].create({
            'model_id': self.env['ir.model']._get_id('mail.test.track'),
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
                'company_id': self.company_2.id,
                'user_id': self.env.user.id,  # trigger track template
            })
            self.flush_tracking()

        new_partner = self.env['res.partner'].search([('email_normalized', '=', email_new_partner_normalized)])
        self.assertEqual(new_partner.company_id, self.company_2)
        self.assertEqual(new_partner.email, email_new_partner_normalized)
        self.assertEqual(new_partner.name, email_new_partner_normalized,
                        "TDE fixme: should be 'Raoulette Mobylette'")

    @users('employee')
    def test_message_track_template_message_type_subtype(self):
        """ Check that the right message_type / subtype_id are applied when tempalates
        are posting based on tracking. """
        test_record = self.test_ticket_record.with_env(self.env)
        test_record.message_subscribe(
            partner_ids=[self.user_admin.partner_id.id],
            subtype_ids=[self.env.ref('mail.mt_comment').id]
        )
        mail_templates = self.env['mail.template'].create([{
            'name': f'Template {n}',
            'subject': f'Template {n}',
            'model_id': self.env['ir.model']._get_id(self.test_ticket_record._name),
            'body_html': f'<p>Template {n}</p>',
            'use_default_to': True,
        } for n in range(2)])

        def _track_subtype(self, init_values):
            if 'container_id' in init_values and self.container_id:
                return self.env.ref('test_mail.st_mail_test_ticket_container_upd')
            return self.env.ref('mail.mt_note')
        self.patch(self.registry['mail.test.ticket'], '_track_subtype', _track_subtype)

        def _track_template(self, changes):
            if 'email_from' in changes:
                return {'email_from': (mail_templates[0], {})}
            elif 'container_id' in changes:
                return {'container_id': (
                    mail_templates[1], {
                        'message_type': 'notification',
                        'subtype_id': self.env.ref('mail.mt_comment').id,
                    }
                )}
            return {}
        self.patch(self.registry['mail.test.ticket'], '_track_template', _track_template)

        container = self.env['mail.test.container'].create({'name': 'Container'})

        # default is auto_comment
        with self.mock_mail_gateway():
            test_record.email_from = 'test@test.lan'
            self.flush_tracking()

        self.assertEqual(len(test_record.message_ids), 3, 'Should be one creation message, one change message and one automated template')
        first_message = test_record.message_ids.filtered(lambda message: message.subject == 'Template 0')
        self.assertMessageFields(
            first_message, {
                'message_type': 'auto_comment',  # default
                'subtype_id': self.env.ref('mail.mt_note'),  # default
            }
        )

        # auto_comment can be overriden by _track_template
        with self.mock_mail_gateway(mail_unlink_sent=False), self.mock_mail_app():
            test_record.container_id = container
            self.flush_tracking()
        self.assertEqual(len(test_record.message_ids), 5, 'Should have added one change message and one automated template')
        track_msg, tpl_msg = self._new_msgs
        self.assertMessageFields(
            tpl_msg, {
                'message_type': 'notification',  # defined in _track_template override
                'subject': 'Template 1',
                'subtype_id': self.env.ref('mail.mt_comment'),  # defined in _track_template override
            }
        )
        self.assertMessageFields(
            track_msg, {
                'message_type': 'notification',
                'subject': False,
                'subtype_id': self.env.ref('test_mail.st_mail_test_ticket_container_upd'),
                'tracking_values': [
                    ('container_id', 'many2one', False, container),
                ],
            }
        )


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

        cls.properties_linked_records = cls.env['mail.test.ticket'].create([{'name': f'Record {i}'} for i in range(3)])
        cls.properties_parent_1, cls.properties_parent_2 = cls.env['mail.test.track.all.properties.parent'].create([{
            'definition_properties': [
                {'name': 'property_char', 'string': 'Property Char', 'type': 'char', 'default': 'char value'},
                {'name': 'separator', 'type': 'separator'},
                {'name': 'property_int', 'string': 'Property Int', 'type': 'integer', 'default': 1337},
                {'name': 'property_m2o', 'string': 'Property M2O', 'type': 'many2one',
                 'default': (cls.properties_linked_records[0].id, cls.properties_linked_records[0].display_name), 'comodel': 'mail.test.ticket'},
            ],
            'name': 'Properties Parent 1',
        }, {
            'definition_properties': [
                {'name': 'property_m2m', 'string': 'Property M2M', 'type': 'many2many',
                 'default': [(rec.id, rec.display_name) for rec in cls.properties_linked_records], 'comodel': 'mail.test.ticket'},
                {'name': 'property_separator', 'string': 'Separator', 'type': 'separator'},
                {'name': 'property_tags', 'string': 'Property Tags', 'type': 'tags',
                 'default': ['aa', 'bb'], 'tags': [('aa', 'AA', 7), ('bb', 'BB', 2), ('cc', 'CC', 3)]},
                {'name': 'property_datetime', 'string': 'Property Datetime', 'type': 'datetime', 'default': '2024-01-02 12:59:01'},
                {'name': 'property_date', 'string': 'Property Date', 'type': 'date', 'default': '2024-01-03'},
            ],
            'name': 'Properties Parent 2',
        }])
        cls.properties_record_1, cls.properties_record_2 = cls.env['mail.test.track.all'].create([{
            'properties_parent_id': cls.properties_parent_1.id,
        }, {
            'properties_parent_id': cls.properties_parent_2.id,

        }])

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
        self.assertMessageFields(
            last_message, {
                'message_type': 'notification',
                'tracking_values': [],
            }
        )

        # update m2m
        test_record.write({
            'many2many_field': [(4, test_tags[0].id), (4, test_tags[1].id)],
        })
        self.flush_tracking()
        last_message = test_record.message_ids[0]
        self.assertMessageFields(
            last_message, {
                'tracking_values': [('many2many_field', 'many2many', '', ', '.join(test_tags[:2].mapped('name')))],
            }
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
        self.assertMessageFields(
            last_message, {
                'tracking_values': [
                    ('many2many_field', 'many2many', ', '.join(test_tags[:2].mapped('name')), ', '.join((test_tags[1] + test_tags[2]).mapped('name'))),
                    ('one2many_field', 'one2many', '', f'Child1, Child2, Child3, {child4_tracking}'),
                ],
            }
        )

        # remove from o2m
        test_record.write({'one2many_field': [(3, test_record.one2many_field[0].id)]})
        self.flush_tracking()
        last_message = test_record.message_ids[0]
        self.assertMessageFields(
            last_message, {
                'tracking_values': [
                    ('one2many_field', 'one2many', f'Child1, Child2, Child3, {child4_tracking}', f'Child2, Child3, {child4_tracking}')
                ],
            }
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
        self.assertMessageFields(
            new_message, {
                'tracking_values': tracking_value_list,
            }
        )
        # check formatting for all field types
        formatted_values_all = new_message.sudo().tracking_value_ids._tracking_value_format()
        for (field_name, field_type, _, _), formatted_vals in zip(tracking_value_list, formatted_values_all):
            currency = self.env.ref('base.USD').id if field_type == 'monetary' else False
            precision = None if field_name != 'float_field_with_digits' else (10, 8)
            with self.subTest(field_name=field_name):
                self.assertEqual(formatted_vals['fieldInfo']['currencyId'], currency)
                self.assertEqual(formatted_vals['fieldInfo']['floatPrecision'], precision)

        # check if the tracking value have the correct currency and values after
        # changing the value and the company at the same time
        self.assertEqual(self.company_2.currency_id, self.env.ref('base.CAD'))
        test_record.write({
            'monetary_field': 200.25,
            'company_id': self.company_2.id,
        })
        self.flush_tracking()
        self.assertEqual(len(test_record.message_ids), 3)
        self.assertMessageFields(
            test_record.message_ids[0], {
                'tracking_values': [
                    ('monetary_field', 'monetary', 42.42, (200.25, self.company_2.currency_id)),
                ],
            }
        )

    @users('employee')
    def test_mail_track_compute(self):
        """ Test tracking of computed fields """
        # no tracking at creation
        compute_record = self.env['mail.test.track.compute'].create({})
        self.flush_tracking()
        self.assertEqual(len(compute_record.message_ids), 1)
        self.assertMessageFields(
            compute_record.message_ids, {
                'author_id': self.partner_employee,
                'tracking_values': [],
            }
        )

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
        self.assertMessageFields(
            compute_record.message_ids[0], {
                'author_id': self.partner_employee,
                'tracking_values': [
                    ('partner_id', 'many2one', False, partner_su),
                    ('partner_name', 'char', False, 'Foo'),
                    ('partner_email', 'char', False, 'foo@example.com'),
                    ('partner_phone', 'char', False, '1234567890'),
                ],
            }
        )

        # modify partner: one tracking message for the only recomputed field
        partner_su.write({'name': 'Fool'})
        self.flush_tracking()
        self.assertEqual(len(compute_record.message_ids), 3)
        self.assertMessageFields(
            compute_record.message_ids[0], {
                'author_id': self.partner_employee,
                'tracking_values': [
                    ('partner_name', 'char', 'Foo', 'Fool'),
                ],
            }
        )

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
        self.assertMessageFields(
            compute_record.message_ids[0], {
                'author_id': self.partner_employee,
                'tracking_values': [
                    ('partner_name', 'char', 'Fool', 'Bar'),
                    ('partner_email', 'char', 'foo@example.com', 'bar@example.com'),
                ],
            }
        )

    @users('employee')
    def test_mail_track_properties(self):
        """Test that the old properties values are logged when the parent changes."""
        properties_record_2 = self.properties_record_2.with_env(self.env)

        # change the parent, it will change the properties values
        with self.mock_mail_gateway(), self.mock_mail_app():
            properties_record_2.properties_parent_id = self.properties_parent_1
            self.flush_tracking()
        self.assertMessageFields(
            self._new_msgs, {
                'author_id': self.partner_employee,
                'tracking_values': [
                    ('properties_parent_id', 'many2one', self.properties_parent_2, self.properties_parent_1),
                    ('properties', ('properties', 'Properties: Property Date', 'date'), datetime(2024, 1, 3, 0, 0, 0), False),
                    ('properties', ('properties', 'Properties: Property Datetime', 'datetime'), datetime(2024, 1, 2, 12, 59, 1), False),
                    ('properties', ('properties', 'Properties: Property Tags', 'tags'), 'AA, BB', ''),
                    ('properties', ('properties', 'Properties: Property M2M', 'many2many'), 'Record 0, Record 1, Record 2', ''),
                ],
            }
        )

        formatted_values = [t._tracking_value_format()[0] for t in self._new_msgs.sudo().tracking_value_ids]
        self.assertEqual(len(formatted_values), 5)
        self.assertFalse(formatted_values[0]['fieldInfo']['isPropertyField'])
        self.assertTrue(all(not f['newValue'] for f in formatted_values[1:]))
        self.assertTrue(all(f['fieldInfo']['isPropertyField'] for f in formatted_values[1:]))
        self.assertEqual(formatted_values[0]['fieldInfo']['changedField'], 'Properties Parent')
        self.assertEqual(formatted_values[1]['fieldInfo']['changedField'], 'Properties: Property Date')
        self.assertEqual(formatted_values[1]['oldValue'], '2024-01-03')
        self.assertEqual(formatted_values[2]['fieldInfo']['changedField'], 'Properties: Property Datetime')
        self.assertEqual(formatted_values[2]['oldValue'], '2024-01-02 12:59:01Z')
        self.assertEqual(formatted_values[3]['fieldInfo']['changedField'], 'Properties: Property Tags')
        self.assertEqual(formatted_values[3]['oldValue'], 'AA, BB')
        self.assertEqual(formatted_values[4]['fieldInfo']['changedField'], 'Properties: Property M2M')
        self.assertEqual(formatted_values[4]['oldValue'], 'Record 0, Record 1, Record 2')

        properties_record_1 = self.properties_record_1.with_env(self.env)
        with self.mock_mail_gateway(), self.mock_mail_app():
            properties_record_1.properties_parent_id = self.properties_parent_2
            self.flush_tracking()
        self.assertMessageFields(
            self._new_msgs, {
                'author_id': self.partner_employee,
                'tracking_values': [
                    ('properties_parent_id', 'many2one', self.properties_parent_1, self.properties_parent_2),
                    ('properties', ('properties', 'Properties: Property M2O', 'many2one'), self.properties_linked_records[0], False),
                    ('properties', ('properties', 'Properties: Property Int', 'integer'), 1337, False),
                    ('properties', ('properties', 'Properties: Property Char', 'char'), 'char value', False),
                ],
            }
        )

        formatted_values = [t._tracking_value_format()[0] for t in self._new_msgs.sudo().tracking_value_ids]
        self.assertEqual(len(formatted_values), 4)
        self.assertFalse(formatted_values[0]['fieldInfo']['isPropertyField'])
        self.assertTrue(all(not f['newValue'] for f in formatted_values[1:]))
        self.assertTrue(all(f['fieldInfo']['isPropertyField'] for f in formatted_values[1:]))
        self.assertEqual(formatted_values[0]['fieldInfo']['changedField'], 'Properties Parent')
        self.assertEqual(formatted_values[1]['fieldInfo']['changedField'], 'Properties: Property M2O')
        self.assertEqual(formatted_values[1]['oldValue'], 'Record 0')
        self.assertEqual(formatted_values[2]['fieldInfo']['changedField'], 'Properties: Property Int')
        self.assertEqual(formatted_values[2]['oldValue'], 1337)
        self.assertEqual(formatted_values[3]['fieldInfo']['changedField'], 'Properties: Property Char')
        self.assertEqual(formatted_values[3]['oldValue'], 'char value')

        # changing the parent and then changing again
        # to the original one to not create tracking values
        with self.mock_mail_gateway(), self.mock_mail_app():
            properties_record_1.properties_parent_id = self.properties_parent_1
            properties_record_1.properties_parent_id = self.properties_parent_2
            self.flush_tracking()
        self.assertFalse(self._new_mails)
        self.assertFalse(self._new_msgs)

        # do not create tracking if the value was false
        with self.mock_mail_gateway(), self.mock_mail_app():
            properties_record_1.properties = {
                'property_m2m': False,
                'property_tags': ['aa'],
                'property_datetime': False,
                'property_date': False,
            }
            self.flush_tracking()

        with self.mock_mail_gateway(), self.mock_mail_app():
            properties_record_1.properties_parent_id = self.properties_parent_1
            self.flush_tracking()
        self.assertEqual(len(self._new_msgs), 1)
        # Only the parent and the tags property should have been tracked
        self.assertMessageFields(
            self._new_msgs, {
                'author_id': self.partner_employee,
                'tracking_values': [
                    ('properties_parent_id', 'many2one', self.properties_parent_2, self.properties_parent_1),
                    ('properties', ('properties', 'Properties: Property Tags', 'tags'), 'AA', ''),
                ],
            }
        )
        self.assertEqual(properties_record_1._mail_track_get_field_sequence("properties"), 100,
            "Properties field should have the same sequence as their parent")

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
        with self.mock_mail_gateway(), self.mock_mail_app():
            record.selection_type = "second"
            self.flush_tracking()
        self.assertMessageFields(
            self._new_msgs, {'tracking_values': [
                ('selection_type', 'selection', invalid_value, 'Second'),
            ]}
        )

    def test_track_groups(self):
        """ Test field groups and filtering when using standard helpers """
        # say that 'email_from' is accessible to erp_managers only
        field = self.record._fields['email_from']
        self.addCleanup(setattr, field, 'groups', field.groups)
        field.groups = 'base.group_erp_manager'

        self.record.sudo().write({'email_from': 'X'})
        self.flush_tracking()

        msg_emp = Store().add(self.record.message_ids, "_store_message_fields").get_result()
        record_w_admin = self.record.with_user(self.user_admin)
        msg_admin = Store().add(record_w_admin.message_ids, "_store_message_fields").get_result()
        msg_sudo = Store().add(self.record.sudo().message_ids, "_store_message_fields").get_result()

        tracking_values = self.env['mail.tracking.value'].search([('mail_message_id', '=', self.record.message_ids[0].id)])
        formatted_tracking_values = [{
            'id': tracking_values[0]['id'],
            'fieldInfo': {
                'changedField': 'Email From',
                'currencyId': False,
                'fieldType': 'char',
                'floatPrecision': None,
                'isPropertyField': False,
            },
            'newValue': 'X',
            'oldValue': False,
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
        values_admin = record_w_admin._notify_by_email_prepare_rendering_context(self.record.message_ids[0], {})
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
        self.assertMessageFields(main_track.message_ids.sudo(), {'tracking_values': []})

        sub_track = self.env['mail.test.track.groups'].create({
            'name': 'Groups',
            'secret': 'secret',
        })
        # some custom code generates tracking values on main_track
        new_message = main_track.message_post(
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
        self.assertMessageFields(new_message, {'tracking_values': [
            ('secret', 'char', False, 'secret'),
            ('', 'integer', 0, self.env.uid),
            (('', {'name': 'Removed'}), 'integer', 30, 35),
        ]})
        trackings = new_message.sudo().tracking_value_ids

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
                    'id': trackings[0].id,
                    'fieldInfo': {
                        'changedField': 'Secret',
                        'currencyId': False,
                        'fieldType': 'char',
                        'floatPrecision': None,
                        'isPropertyField': False,
                    },
                    'newValue': 'secret',
                    'oldValue': False,
                },
                {
                    'id': trackings[2].id,
                    'fieldInfo': {
                        'changedField': 'Old integer',
                        'currencyId': False,
                        'fieldType': 'integer',
                        'floatPrecision': None,
                        'isPropertyField': False,
                    },
                    'newValue': 35,
                    'oldValue': 30,
                },
                {
                    'id': trackings[1].id,
                    'fieldInfo': {
                        'changedField': 'Unknown',
                        'currencyId': False,
                        'fieldType': 'char',
                        'floatPrecision': None,
                        'isPropertyField': False,
                    },
                    'newValue': False,
                    'oldValue': False,
                },
            ],
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
            [tracking_values.browse(t['id']).field_id.name for t in tracking_formatted],
            ordered_fnames,
            'Track: formatted order is correctly based on field sequence definition'
        )

    @users('employee')
    def test_unlinked_model(self):
        """ Fields from obsolete models with tracking values can be unlinked without error. """
        record = self.record.with_env(self.env)
        record.write({'email_from': 'new_value'})  # create a tracking value
        self.flush_tracking()
        self.assertMessageFields(
            record.message_ids[0], {'tracking_values': [('email_from', 'char', False, 'new_value')]},
        )

        fields_to_remove = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'mail.test.ticket'),
        ])

        # Simulate a registry without the model, which is what we have if we
        # update a module with the model code removed
        model = self.env.registry.models.pop('mail.test.ticket')
        try:
            fields_to_remove.with_context(force_delete=True).unlink()
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

        self.assertMessageFields(
            record.message_ids[0], {'tracking_values': [('email_from', 'char', False, 'new_value')]}
        )
        self.assertMessageFields(
            record_other.message_ids[0], {'tracking_values': [
                ('customer_id', 'many2one', False, self.test_partner),
                ('email_from', 'char', 'email.from.1@example.com', 'email.from.2@example.com'),
                ('user_id', 'many2one', False, self.env.user)
            ]}
        )
        self.assertMessageFields(
            record_other.message_ids[1], {'tracking_values': [('email_from', 'char', False, 'email.from.1@example.com')]}
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
                    'id': tracking.id,
                    'fieldInfo': {
                        'changedField': field_info[2],
                        'fieldType': field_info[1],
                        'floatPrecision': None,
                        'currencyId': False,
                        'isPropertyField': False,
                    },
                    'newValue': values[1],
                    'oldValue': values[0],
                }
                for tracking, field_info, values in zip(trackings_all_sorted, fields_info, values_info)
            ]
        )

        # remove fields
        fields_toremove = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'mail.test.ticket'),
            ('name', 'in', ('email_from', 'user_id', 'datetime'))  # also include a non tracked field
        ])
        fields_toremove.with_context(force_delete=True).unlink()
        self.assertEqual(len(trackings_all.exists()), 5)

        # check display / format, even if field is removed
        formatted = trackings_all._tracking_value_format()
        self.assertEqual(
            formatted,
            [
                {
                    'id': tracking.id,
                    'fieldInfo': {
                        'changedField': field_info[2],
                        'fieldType': field_info[1],
                        'isPropertyField': False,
                        'currencyId': False,
                        'floatPrecision': None,
                    },
                    'newValue': values[1],
                    'oldValue': values[0],
                }
                for tracking, field_info, values in zip(trackings_all_sorted, fields_info, values_info)
            ]
        )
