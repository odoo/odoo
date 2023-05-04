# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE
from odoo.tests.common import tagged
from odoo.tests import Form


@tagged('mail_track')
class TestTracking(MailCommon):

    def setUp(self):
        super(TestTracking, self).setUp()

        record = self.env['mail.test.ticket'].with_user(self.user_employee).with_context(self._test_context).create({
            'name': 'Test',
        })
        self.flush_tracking()
        self.record = record.with_context(mail_notrack=False)

    def test_message_track_author(self):
        """ Checks that the author of the log note matches the user at the time of writing"""
        with self.mock_mail_gateway():
            self.record._track_set_author(self.partner_admin)
            self.record.write({
                'customer_id': self.partner_employee.id,
            })
            self.flush_tracking()

        self.assertEqual(len(self.record.message_ids), 1)
        self.assertEqual(len(self.record.message_ids.tracking_value_ids), 1)

        self.assertEqual(self.record.message_ids.author_id, self.partner_admin)

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

    def test_message_track_no_tracking(self):
        """ Update a set of non tracked fields -> no message, no tracking """
        self.record.write({
            'name': 'Tracking or not',
            'count': 32,
        })
        self.flush_tracking()
        self.assertEqual(self.record.message_ids, self.env['mail.message'])

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

    def test_message_track_template_at_create_from_message(self):
        """Make sure records created through aliasing show the original message before the template"""
        # setup
        test_model = self.env['ir.model']._get('mail.test.ticket')
        original_sender = self.user_admin.partner_id
        custom_values = {'name': 'Test', 'customer_id': original_sender.id,
                         'mail_template': self.env.ref('test_mail.mail_test_ticket_tracking_tpl').id}
        self.env['mail.alias'].create({
            'alias_name': 'groups',
            'alias_user_id': False,
            'alias_model_id': test_model.id,
            'alias_contact': 'everyone',
            'alias_defaults': custom_values})
        record = self.format_and_process(MAIL_TEMPLATE, '"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>',
                                         'groups@test.com', target_field='customer_id', subject=custom_values['customer_id'],
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

    def test_create_partner_from_tracking_multicompany(self):
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

    def test_track_invalid_selection(self):
        # Test: Check that initial invalid selection values are allowed when tracking
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

    def test_tracked_compute(self):
        # no tracking at creation
        record = self.env['mail.test.track.compute'].create({})
        self.flush_tracking()
        self.assertEqual(len(record.message_ids), 1)
        self.assertEqual(len(record.message_ids[0].tracking_value_ids), 0)

        # assign partner_id: one tracking message for the modified field and all
        # the stored and non-stored computed fields on the record
        partner = self.env['res.partner'].create({
            'name': 'Foo',
            'email': 'foo@example.com',
            'phone': '1234567890',
        })
        record.partner_id = partner
        self.flush_tracking()
        self.assertEqual(len(record.message_ids), 2)
        self.assertEqual(len(record.message_ids[0].tracking_value_ids), 4)
        self.assertEqual(record.message_ids.author_id, self.partner_root)
        self.assertTracking(record.message_ids[0], [
            ('partner_id', 'many2one', False, partner),
            ('partner_name', 'char', False, 'Foo'),
            ('partner_email', 'char', False, 'foo@example.com'),
            ('partner_phone', 'char', False, '1234567890'),
        ])

        # modify partner: one tracking message for the only recomputed field
        partner.write({'name': 'Fool'})
        self.flush_tracking()
        self.assertEqual(len(record.message_ids), 3)
        self.assertEqual(len(record.message_ids[0].tracking_value_ids), 1)
        self.assertTracking(record.message_ids[0], [
            ('partner_name', 'char', 'Foo', 'Fool'),
        ])

        # modify partner: one tracking message for both stored computed fields;
        # the non-stored computed fields have no tracking
        partner.write({
            'name': 'Bar',
            'email': 'bar@example.com',
            'phone': '0987654321',
        })
        # force recomputation of 'partner_phone' to make sure it does not
        # generate tracking values
        self.assertEqual(record.partner_phone, '0987654321')
        self.flush_tracking()
        self.assertEqual(len(record.message_ids), 4)
        self.assertEqual(len(record.message_ids[0].tracking_value_ids), 2)
        self.assertTracking(record.message_ids[0], [
            ('partner_name', 'char', 'Fool', 'Bar'),
            ('partner_email', 'char', 'foo@example.com', 'bar@example.com'),
        ])

@tagged('mail_track')
class TestTrackingMonetary(MailCommon):

    def setUp(self):
        super(TestTrackingMonetary, self).setUp()

        self._activate_multi_company()

        record = self.env['mail.test.track.monetary'].with_user(self.user_employee).with_context(self._test_context).create({
            'company_id': self.user_employee.company_id.id,
        })
        self.flush_tracking()
        self.record = record.with_context(mail_notrack=False)

    def test_message_track_monetary(self):
        """ Update a record with a tracked monetary field """

        # Check if the tracking value have the correct currency and values
        self.record.write({
            'revenue': 100,
        })
        self.flush_tracking()
        self.assertEqual(len(self.record.message_ids), 1)

        self.assertTracking(self.record.message_ids[0], [
            ('revenue', 'monetary', 0, 100),
        ])

        # Check if the tracking value have the correct currency and values after changing the value and the company
        self.record.write({
            'revenue': 200,
            'company_id': self.company_2.id,
        })
        self.flush_tracking()
        self.assertEqual(len(self.record.message_ids), 2)

        self.assertTracking(self.record.message_ids[0], [
            ('revenue', 'monetary', 100, 200),
            ('company_currency', 'many2one', self.user_employee.company_id.currency_id, self.company_2.currency_id)
        ])


@tagged('mail_track')
class TestTrackingInternals(MailCommon):

    def setUp(self):
        super(TestTrackingInternals, self).setUp()

        record = self.env['mail.test.ticket'].with_user(self.user_employee).with_context(self._test_context).create({
            'name': 'Test',
        })
        self.flush_tracking()
        self.record = record.with_context(mail_notrack=False)

    def test_track_groups(self):
        field = self.record._fields['email_from']
        self.addCleanup(setattr, field, 'groups', field.groups)
        field.groups = 'base.group_erp_manager'

        self.record.sudo().write({'email_from': 'X'})
        self.flush_tracking()

        msg_emp = self.record.message_ids.message_format()
        msg_sudo = self.record.sudo().message_ids.message_format()
        tracking_values = self.env['mail.tracking.value'].search([('mail_message_id', '=', self.record.message_ids.id)])
        formattedTrackingValues = [{
            'changedField': 'Email From',
            'id': tracking_values[0]['id'],
            'newValue': {
                'currencyId': False,
                'fieldType': 'char',
                'value': 'X',
            },
            'oldValue': {
                'currencyId': False,
                'fieldType': 'char',
                'value': False,
            },
        }]
        self.assertEqual(msg_emp[0].get('trackingValues'), [], "should not have protected tracking values")
        self.assertEqual(msg_sudo[0].get('trackingValues'), formattedTrackingValues, "should have protected tracking values")

        msg_emp = self.record._notify_by_email_prepare_rendering_context(self.record.message_ids, {})
        msg_sudo = self.record.sudo()._notify_by_email_prepare_rendering_context(self.record.message_ids, {})
        self.assertFalse(msg_emp.get('tracking_values'), "should not have protected tracking values")
        self.assertTrue(msg_sudo.get('tracking_values'), "should have protected tracking values")

        # test editing the record with user not in the group of the field
        self.env.invalidate_all()
        self.record.clear_caches()
        record_form = Form(self.record.with_user(self.user_employee))
        record_form.name = 'TestDoNoCrash'
        # the employee user must be able to save the fields on which they can write
        # if we fetch all the tracked fields, ignoring the group of the current user
        # it will crash and it shouldn't
        record = record_form.save()
        self.assertEqual(record.name, 'TestDoNoCrash')

    def test_track_sequence(self):
        """ Update some tracked fields and check that the mail.tracking.value are ordered according to their tracking_sequence"""
        self.record.write({
            'name': 'Zboub',
            'customer_id': self.user_admin.partner_id.id,
            'user_id': self.user_admin.id,
            'container_id': self.env['mail.test.container'].with_context(mail_create_nosubscribe=True).create({'name': 'Container'}).id
        })
        self.flush_tracking()
        self.assertEqual(len(self.record.message_ids), 1, 'should have 1 tracking message')

        tracking_values = self.env['mail.tracking.value'].search([('mail_message_id', '=', self.record.message_ids.id)])
        self.assertEqual(tracking_values[0].tracking_sequence, 1)
        self.assertEqual(tracking_values[1].tracking_sequence, 2)
        self.assertEqual(tracking_values[2].tracking_sequence, 100)

    def test_unlinked_field(self):
        record_sudo = self.record.sudo()
        record_sudo.write({'email_from': 'new_value'})  # create a tracking value
        self.flush_tracking()
        self.assertEqual(len(record_sudo.message_ids.tracking_value_ids), 1)
        ir_model_field = self.env['ir.model.fields'].search([
            ('model', '=', 'mail.test.ticket'),
            ('name', '=', 'email_from')])
        ir_model_field.with_context(_force_unlink=True).unlink()
        self.assertEqual(len(record_sudo.message_ids.tracking_value_ids), 0)
