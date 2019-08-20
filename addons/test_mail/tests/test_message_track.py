# -*- coding: utf-8 -*-
from unittest.mock import patch
from odoo.addons.test_mail.tests import common
from odoo.tools import formataddr


class TestTracking(common.BaseFunctionalTest, common.MockEmails):

    def setUp(self):
        super(TestTracking, self).setUp()

        record = self.env['mail.test.full'].with_user(self.user_employee).with_context(self._test_context).create({
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
        self.assertEqual(self.record.message_ids.notified_partner_ids, self.env['res.partner'])
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
        self.assertEqual(self.record.message_ids.notified_partner_ids, self.user_admin.partner_id)

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

    def test_message_track_template_at_create(self):
        """ Create a record with tracking template on create, template should be sent."""

        Model = self.env['mail.test.full'].with_user(self.user_employee).with_context(self._test_context)
        Model = Model.with_context(mail_notrack=False)
        record = Model.create({
            'name': 'Test',
            'customer_id': self.user_admin.partner_id.id,
            'mail_template': self.env.ref('test_mail.mail_test_full_tracking_tpl').id,
        })

        self.assertEqual(len(record.message_ids), 1, 'should have 1 new messages for template')
        # one new message containing the template linked to tracking
        self.assertEqual(record.message_ids[0].subject, 'Test Template')
        self.assertEqual(record.message_ids[0].body, '<p>Hello Test</p>')
        # one email send due to template
        self.assertEqual(len(self._mails), 1)

    def test_message_tracking_sequence(self):
        """ Update some tracked fields and check that the mail.tracking.value are ordered according to their tracking_sequence"""
        self.record.write({
            'name': 'Zboub',
            'customer_id': self.user_admin.partner_id.id,
            'user_id': self.user_admin.id,
            'umbrella_id': self.env['mail.test'].with_context(mail_create_nosubscribe=True).create({'name': 'Umbrella'}).id
        })
        self.assertEqual(len(self.record.message_ids), 1, 'should have 1 tracking message')

        tracking_values = self.env['mail.tracking.value'].search([('mail_message_id', '=', self.record.message_ids.id)])
        self.assertEqual(tracking_values[0].tracking_sequence, 1)
        self.assertEqual(tracking_values[1].tracking_sequence, 2)
        self.assertEqual(tracking_values[2].tracking_sequence, 100)

    def test_track_groups(self):
        # patch the group attribute
        field = self.record._fields['email_from']
        self.addCleanup(setattr, field, 'groups', field.groups)
        field.groups = 'base.group_erp_manager'

        self.record.sudo().write({'email_from': 'X'})

        msg_emp = self.record.message_ids.message_format()
        msg_sudo = self.record.sudo().message_ids.message_format()
        self.assertFalse(msg_emp[0].get('tracking_value_ids'), "should not have protected tracking values")
        self.assertTrue(msg_sudo[0].get('tracking_value_ids'), "should have protected tracking values")

    def test_notify_track_groups(self):
        # patch the group attribute
        field = self.record._fields['email_from']
        self.addCleanup(setattr, field, 'groups', field.groups)
        field.groups = 'base.group_erp_manager'

        self.record.sudo().write({'email_from': 'X'})

        msg_emp = self.record._notify_prepare_template_context(self.record.message_ids, {})
        msg_sudo = self.record.sudo()._notify_prepare_template_context(self.record.message_ids, {})
        self.assertFalse(msg_emp.get('tracking_values'), "should not have protected tracking values")
        self.assertTrue(msg_sudo.get('tracking_values'), "should have protected tracking values")

    def test_unlinked_field(self):
        record_sudo = self.record.sudo()
        record_sudo.write({'email_from': 'X'})  # create a tracking value
        self.assertEqual(len(record_sudo.message_ids.tracking_value_ids), 1)
        ir_model_field = self.env['ir.model.fields'].search([
            ('model', '=', 'mail.test.full'),
            ('name', '=', 'email_from')])
        ir_model_field.with_context(_force_unlink=True).unlink()
        self.assertEqual(len(record_sudo.message_ids.tracking_value_ids), 0)

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
            'email_to': "${object.email_from}",
            'body_html': "<div>A nice body</div>",
        })

        def patched_message_track_post_template(*args, **kwargs):
            if args[0]._name == "mail.test.track":
                args[0].message_post_with_template(template.id)
            return True

        with patch('odoo.addons.mail.models.mail_thread.MailThread._message_track_post_template', patched_message_track_post_template):
            self.env['mail.test.track'].create({
                'email_from': email_new_partner,
                'company_id': company1.id,
                'user_id': self.env.user.id, # trigger track template
            })

        new_partner = Partner.search([('email', '=', email_new_partner)])
        self.assertTrue(new_partner)
        self.assertEqual(new_partner.company_id, company1)
