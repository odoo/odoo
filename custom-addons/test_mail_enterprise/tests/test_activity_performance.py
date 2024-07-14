# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields
from odoo.addons.test_mail.tests.test_performance import BaseMailPerformance
from odoo.tests.common import users, warmup
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('mail_performance', 'post_install', '-at_install')
class TestActivityPerformance(BaseMailPerformance):

    @classmethod
    def setUpClass(cls):
        super(TestActivityPerformance, cls).setUpClass()

        cls.customer = cls.env['res.partner'].with_context(cls._test_context).create({
            'country_id': cls.env.ref('base.be').id,
            'email': '"Super Customer" <customer.test@example.com>',
            'mobile': '0456123456',
            'name': 'Super Customer',
        })
        cls.test_record = cls.env['mail.test.sms.bl.activity'].with_context(cls._test_context).create({
            'name': 'Test Record',
            'customer_id': cls.customer.id,
            'email_from': cls.customer.email,
            'phone_nbr': '0456999999',
        })
        cls.test_records_voip, cls._test_partners = cls._create_records_for_batch(
            'mail.test.activity.bl.sms.voip',
            10
        )
        cls.test_record_voip = cls.env['mail.test.activity.bl.sms.voip'].with_context(cls._test_context).create({
            'name': 'Test Record',
            'customer_id': cls.customer.id,
            'email_from': cls.customer.email,
            'phone_nbr': '0456999999',
        })

        # documents records for activities
        cls.documents_test_folder = cls.env['documents.folder'].create({
            'name': 'Test Folder',
        })
        cls.documents_test_facet = cls.env['documents.facet'].create({
            'folder_id': cls.documents_test_folder.id,
            'name': 'Test Facet',
        })
        cls.documents_test_tags = cls.env['documents.tag'].create([
            {'facet_id': cls.documents_test_facet.id,
             'folder_id': cls.documents_test_folder.id,
             'name': 'Test Tag %d' % index,
            } for index in range(2)
        ])
        cls.phonecall_activity = cls.env.ref('mail.mail_activity_data_call')
        cls.phonecall_activity.write({
            'default_user_id': cls.user_admin.id,
        })
        cls.upload_activity = cls.env.ref('mail.mail_activity_data_upload_document')
        cls.upload_activity.write({
            'default_user_id': cls.user_admin.id,
            'folder_id': cls.documents_test_folder.id,
        })
        cls.generic_activity = cls.env['mail.activity.type'].create({
            'category': 'default',
            'delay_count': 5,
            'icon': 'fa-tasks',
            'name': 'Generic activity type',
            'sequence': 99,
        })

        cls.env['mail.activity.type'].search([
            ('category', '=', 'phonecall'),
            ('id', '!=', cls.phonecall_activity.id),
        ]).unlink()

    @users('employee')
    @warmup
    def test_activity_mixin_crud(self):
        """ Simply check CRUD operations on records having advanced mixing
        enabled. No computed fields are involved. """
        ActivityModel = self.env['mail.test.sms.bl.activity']

        with self.assertQueryCount(employee=9):
            record = ActivityModel.create({
                'name': 'Test',
            })
            self.env.flush_all()

        with self.assertQueryCount(employee=1):
            record.write({'name': 'New Name'})
            self.env.flush_all()

    @users('employee')
    @warmup
    def test_activity_mixin_schedule_call(self):
        """ Simply check CRUD operations on records having advanced mixing
        enabled. No computed fields are involved. """
        test_record = self.test_record.with_env(self.env)

        with self.assertQueryCount(employee=34):
            activity = test_record.activity_schedule(
                'mail.mail_activity_data_call',
                summary='Call Activity',
            )
            self.env.flush_all()

        # check business information (to benefits from this test)
        self.assertEqual(activity.user_id, self.user_admin)
        self.assertEqual(test_record.activity_ids, activity)

    @users('employee')
    @warmup
    def test_activity_mixin_schedule_call_batch_voip(self):
        """ Simply check CRUD operations on records having advanced mixin VOIP
        enabled. No computed fields are involved. """
        test_records = self.test_records_voip.with_env(self.env)

        with self.assertQueryCount(employee=178):
            activities = test_records.activity_schedule(
                'mail.mail_activity_data_call',
                summary='Call Activity',
            )
            self.env.flush_all()

        # check business information (to benefits from this test)
        self.assertEqual(len(activities), 10)
        self.assertEqual(activities.user_id, self.user_admin)
        self.assertEqual(test_records.activity_ids, activities)

    @users('employee')
    @warmup
    def test_activity_mixin_schedule_document(self):
        """ Simply check CRUD operations on records having advanced mixing
        enabled. No computed fields are involved. """
        test_record_voip = self.test_record_voip.with_env(self.env)

        with self.assertQueryCount(employee=41):
            activity = test_record_voip.activity_schedule(
                'mail.mail_activity_data_upload_document',
                summary='Upload Activity',
            )
            self.env.flush_all()

        # check business information (to benefits from this test)
        self.assertEqual(activity.user_id, self.user_admin)
        self.assertEqual(test_record_voip.activity_ids, activity)

    @users('employee')
    @warmup
    def test_create_call_activity(self):
        test_record_voip = self.test_record_voip.with_env(self.env)

        with self.assertQueryCount(employee=11):
            activity = test_record_voip.create_call_activity()
            self.env.flush_all()

        # check business information (to benefits from this test)
        self.assertEqual(activity.activity_type_id, self.phonecall_activity)

    @mute_logger('odoo.models.unlink')
    @users('employee')
    @warmup
    def test_generic_activities_misc_batch(self):
        """ Test generic activities performance when

          * creating;
          * updating responsible;
          * setting as done (feedback) with attachments;

        in order to see difference with other activities (generic type). """
        test_records = self.test_records_voip.with_env(self.env)

        with self.assertQueryCount(employee=168):
            activities = test_records.activity_schedule(
                activity_type_id=self.generic_activity.id,
                automated=False,
                user_id=self.user_admin.id,
            )
            self.env.flush_all()
        self.assertEqual(len(activities), 10)

        with self.assertQueryCount(employee=35):
            activities[:3].write({'user_id': self.user_root.id})
            activities[3:6].write({'user_id': self.env.uid})
            activities[6:].write({'user_id': self.user_admin.id})
            self.env.flush_all()

        attachments = self.env['ir.attachment'].create([
            dict(values,
                 res_model='mail.activity',
                 res_id=0)
            for values in self.test_attachments_vals
        ])
        self.env.flush_all()

        with self.assertQueryCount(employee=59):
            activities.action_feedback(
                feedback='Intense feedback',
                attachment_ids=attachments.ids,
            )
            self.env.flush_all()

    @mute_logger('odoo.models.unlink')
    @users('employee')
    @warmup
    def test_voip_activities_misc_batch(self):
        """ Test VOIP activities performance when

          * creating;
          * updating responsible;
          * setting as done (feedback) with attachments;

        in order to see difference with other activities (generic type). """
        test_records = self.test_records_voip.with_env(self.env)

        with self.assertQueryCount(employee=29):
            activities = test_records.create_call_activity()
            self.env.flush_all()

        # check business information (to benefits from this test)
        self.assertEqual(activities.activity_type_id, self.phonecall_activity)

        with self.assertQueryCount(employee=108):
            activities[:3].write({'user_id': self.user_root.id})
            activities[3:6].write({'user_id': self.env.uid})
            activities[6:].write({'user_id': self.user_admin.id})
            activities.write({'date_deadline': fields.Date.today() + timedelta(days=1)})
            self.env.flush_all()

        attachments = self.env['ir.attachment'].create([
            dict(values,
                 res_model='mail.activity',
                 res_id=0)
            for values in self.test_attachments_vals
        ])
        self.env.flush_all()

        with self.assertQueryCount(employee=59):
            activities.action_feedback(
                feedback='Intense feedback',
                attachment_ids=attachments.ids,
            )
            self.env.flush_all()
