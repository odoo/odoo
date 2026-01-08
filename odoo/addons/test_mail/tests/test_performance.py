# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from unittest.mock import patch

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import users, warmup, Form
from odoo.tests import tagged
from odoo.tools import mute_logger, formataddr


@tagged('mail_performance', 'post_install', '-at_install')
class BaseMailPerformance(MailCommon, TransactionCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super(BaseMailPerformance, cls).setUpClass()

        # creating partners is required notably with template usage
        cls.user_employee.write({'groups_id': [(4, cls.env.ref('base.group_partner_manager').id)]})
        cls.user_test = cls.user_test_inbox = cls.env['res.users'].with_context(cls._test_context).create({
            'name': 'Paulette Testouille',
            'login': 'paul',
            'email': 'user.test.paulette@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.user_test_email = cls.env['res.users'].with_context(cls._test_context).create({
            'name': 'Georgette Testouille',
            'login': 'george',
            'email': 'user.test.georgette@example.com',
            'notification_type': 'email',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
        })

        cls.customers = cls.env['res.partner'].with_context(cls._test_context).create([
            {
                'country_id': cls.env.ref('base.be').id,
                'email': 'customer.test@example.com',
                'name': 'Test Customer',
                'mobile': '0456123456',
            }, {
                'country_id': cls.env.ref('base.be').id,
                'email': 'customer.test.2@example.com',
                'name': 'Test Customer 2',
                'mobile': '0456654321',
            }
        ])
        cls.customer = cls.customers[0]

        cls.test_attachments_vals = cls._generate_attachments_data(3, 'mail.compose.message', 0)

    def setUp(self):
        super(BaseMailPerformance, self).setUp()
        # patch registry to simulate a ready environment
        self.patch(self.env.registry, 'ready', True)

    def _create_test_records(self):
        test_record_full = self.env['mail.test.ticket'].with_context(self._test_context).create({
            'name': 'TestRecord',
            'customer_id': self.customer.id,
            'user_id': self.user_test.id,
            'email_from': 'nopartner.test@example.com',
        })
        test_template_full = self.env['mail.template'].create({
            'name': 'TestTemplate',
            'model_id': self.env['ir.model']._get('mail.test.ticket').id,
            'subject': 'About {{ object.name }}',
            'body_html': '<p>Hello <t t-out="object.name"/></p>',
            'email_from': '{{ object.user_id.email_formatted }}',
            'partner_to': '{{ object.customer_id.id }}',
            'email_to': '{{ ("%s Customer <%s>" % (object.name, object.email_from)) }}',
            'attachment_ids': [
                (0, 0, dict(attachment, res_model='mail.template'))
                for attachment in self.test_attachments_vals
            ],
        })
        self.flush_tracking()
        return test_record_full, test_template_full

    def _create_test_records_for_batch(self):
        test_partners = self.env['res.partner'].create([{
            'phone': f'0485{idx}{idx}1122',
            'email': f'test.customer.{idx}@test.example.com',
            'name': f'Test Customer {idx}',
        } for idx in range(0, 10)])
        test_records = self.env['mail.test.ticket'].create([{
            'customer_id': test_partners[idx].id,
            'email_from': test_partners[idx].email_formatted,
            'name': f'Test Ticket {idx}',
            'user_id': self.user_test.id,
        } for idx in range(0, 10)])
        test_template_full = self.env['mail.template'].create({
            'name': 'TestTemplate',
            'model_id': self.env['ir.model']._get('mail.test.ticket').id,
            'subject': 'About {{ object.name }}',
            'body_html': '<p>Hello <t t-out="object.name"/></p>',
            'email_from': '{{ object.user_id.email_formatted }}',
            'partner_to': '{{ object.customer_id.id }}',
            'email_to': '{{ ("%s Customer <%s>" % (object.name, object.email_from)) }}',
            'attachment_ids': [
                (0, 0, dict(attachment, res_model='mail.template'))
                for attachment in self.test_attachments_vals
            ],
        })
        self.flush_tracking()
        return test_partners, test_records, test_template_full


@tagged('mail_performance', 'post_install', '-at_install')
class TestBaseMailPerformance(BaseMailPerformance):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.res_partner_3 = cls.env['res.partner'].create({
            'name': 'Gemini Furniture',
            'email': 'gemini.furniture39@example.com',
        })
        cls.res_partner_4 = cls.env['res.partner'].create({
            'name': 'Ready Mat',
            'email': 'ready.mat28@example.com',
        })
        cls.res_partner_10 = cls.env['res.partner'].create({
            'name': 'The Jackson Group',
            'email': 'jackson.group82@example.com',
        })
        cls.res_partner_12 = cls.env['res.partner'].create({
            'name': 'Azure Interior',
            'email': 'azure.Interior24@example.com',
        })
        cls.env['mail.performance.thread'].create([
            {
                'name': 'Object 0',
                'value': 0,
                'partner_id': cls.res_partner_3.id,
            }, {
                'name': 'Object 1',
                'value': 10,
                'partner_id': cls.res_partner_3.id,
            }, {
                'name': 'Object 2',
                'value': 20,
                'partner_id': cls.res_partner_4.id,
            }, {
                'name': 'Object 3',
                'value': 30,
                'partner_id': cls.res_partner_10.id,
            }, {
                'name': 'Object 4',
                'value': 40,
                'partner_id': cls.res_partner_12.id,
            }
        ])

    @users('admin', 'demo')
    @warmup
    def test_read_mail(self):
        """ Read records inheriting from 'mail.thread'. """
        records = self.env['mail.performance.thread'].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(admin=3, demo=3):
            # without cache
            for record in records:
                record.partner_id.country_id.name

        with self.assertQueryCount(0):
            # with cache
            for record in records:
                record.partner_id.country_id.name

        with self.assertQueryCount(0):
            # value_pc must have been prefetched, too
            for record in records:
                record.value_pc

    @users('admin', 'demo')
    @warmup
    def test_write_mail(self):
        """ Write records inheriting from 'mail.thread' (no recomputation). """
        records = self.env['mail.performance.thread'].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(admin=2, demo=2):
            records.write({'name': 'X'})

    @users('admin', 'demo')
    @warmup
    def test_write_mail_with_recomputation(self):
        """ Write records inheriting from 'mail.thread' (with recomputation). """
        records = self.env['mail.performance.thread'].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(admin=2, demo=2):
            records.write({'value': 42})

    @users('admin', 'demo')
    @warmup
    def test_write_mail_with_tracking(self):
        """ Write records inheriting from 'mail.thread' (with field tracking). """
        record = self.env['mail.performance.thread'].create({
            'name': 'Test',
            'track': 'Y',
            'value': 40,
            'partner_id': self.res_partner_12.id,
        })

        with self.assertQueryCount(admin=3, demo=3):
            record.track = 'X'

    @users('admin', 'demo')
    @warmup
    def test_create_mail(self):
        """ Create records inheriting from 'mail.thread' (without field tracking). """
        model = self.env['mail.performance.thread']

        with self.assertQueryCount(admin=2, demo=2):
            model.with_context(tracking_disable=True).create({'name': 'X'})

    @users('admin', 'demo')
    @warmup
    def test_create_mail_with_tracking(self):
        """ Create records inheriting from 'mail.thread' (with field tracking). """
        with self.assertQueryCount(admin=9, demo=9):
            self.env['mail.performance.thread'].create({'name': 'X'})

    @users('admin', 'employee')
    @warmup
    def test_create_mail_simple(self):
        with self.assertQueryCount(admin=8, employee=8):
            self.env['mail.test.simple'].create({'name': 'Test'})

    @users('admin', 'employee')
    @warmup
    def test_create_mail_simple_multi(self):
        with self.assertQueryCount(admin=8, employee=8):
            self.env['mail.test.simple'].create([{'name': 'Test'}] * 5)

    @users('admin', 'employee')
    @warmup
    def test_write_mail_simple(self):
        rec = self.env['mail.test.simple'].create({'name': 'Test'})
        with self.assertQueryCount(admin=1, employee=1):
            rec.write({
                'name': 'Test2',
                'email_from': 'test@test.mycompany.com',
            })


@tagged('mail_performance', 'post_install', '-at_install')
class TestBaseAPIPerformance(BaseMailPerformance):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # automatically follow activities, for backward compatibility concerning query count
        cls.env.ref('mail.mt_activities').write({'default': True})

    @users('admin', 'employee')
    @warmup
    def test_adv_activity(self):
        model = self.env['mail.test.activity']

        with self.assertQueryCount(admin=8, employee=8):
            model.create({'name': 'Test'})

    @users('admin', 'employee')
    @warmup
    @mute_logger('odoo.models.unlink')
    def test_activity_full(self):
        record = self.env['mail.test.activity'].create({'name': 'Test'})
        MailActivity = self.env['mail.activity'].with_context({
            'default_res_model': 'mail.test.activity',
        })

        with self.assertQueryCount(admin=6, employee=6):
            activity = MailActivity.create({
                'summary': 'Test Activity',
                'res_id': record.id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            })
            # read activity_type to normalize cache between enterprise and community
            # voip module read activity_type during create leading to one less query in enterprise on action_feedback
            _category = activity.activity_type_id.category

        with self.assertQueryCount(admin=12, employee=12):
            activity.action_feedback(feedback='Zizisse Done !')

    @warmup
    def test_activity_mixin_batched(self):
        records = self.env['mail.test.activity'].create([{'name': 'Test'}] * 10)
        MailActivity = self.env['mail.activity'].with_context({
            'default_res_model': 'mail.test.activity',
        })
        activity_type = self.env.ref('mail.mail_activity_data_todo')

        MailActivity.create([{
            'summary': 'Test Activity',
            'res_id': record.id,
            'activity_type_id': activity_type.id,
        } for record in records])

        self.env.invalidate_all()
        with self.assertQueryCount(2):
            records.mapped('activity_date_deadline')

    @users('admin', 'employee')
    @warmup
    @mute_logger('odoo.models.unlink')
    def test_activity_mixin(self):
        record = self.env['mail.test.activity'].create({'name': 'Test'})

        with self.assertQueryCount(admin=5, employee=5):
            activity = record.action_start('Test Start')
            # read activity_type to normalize cache between enterprise and community
            # voip module read activity_type during create leading to one less query in enterprise on action_close
            _category = activity.activity_type_id.category

        record.write({'name': 'Dupe write'})

        with self.assertQueryCount(admin=13, employee=13):
            record.action_close('Dupe feedback')

        self.assertEqual(record.activity_ids, self.env['mail.activity'])

    @users('admin', 'employee')
    @warmup
    @mute_logger('odoo.models.unlink')
    def test_activity_mixin_w_attachments(self):
        record = self.env['mail.test.activity'].create({'name': 'Test'})

        attachments = self.env['ir.attachment'].create([
            dict(values,
                 res_model='mail.activity',
                 res_id=0)
            for values in self.test_attachments_vals
        ])

        with self.assertQueryCount(admin=5, employee=5):
            activity = record.action_start('Test Start')
            #read activity_type to normalize cache between enterprise and community
            #voip module read activity_type during create leading to one less query in enterprise on action_close
            _category = activity.activity_type_id.category

        record.write({'name': 'Dupe write'})

        with self.assertQueryCount(admin=15, employee=15):  # com+tm 14/14
            record.action_close('Dupe feedback', attachment_ids=attachments.ids)

        # notifications
        message = record.message_ids[0]
        self.assertEqual(
            set(message.attachment_ids.mapped('name')),
            set(['AttFileName_00.txt', 'AttFileName_01.txt', 'AttFileName_02.txt'])
        )

    @users('admin', 'employee')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_mail_composer(self):
        test_record, _test_template = self._create_test_records()
        customer_id = self.customer.id
        with self.assertQueryCount(admin=7, employee=7):
            composer = self.env['mail.compose.message'].with_context({
                'default_composition_mode': 'comment',
                'default_model': test_record._name,
                'default_res_ids': test_record.ids,
            }).create({
                'body': '<p>Test Body</p>',
                'partner_ids': [(4, customer_id)],
            })

        with self.assertQueryCount(admin=42, employee=42):
            composer._action_send_mail()

    @users('admin', 'employee')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_mail_composer_attachments(self):
        test_record, _test_template = self._create_test_records()
        customer = self.env['res.partner'].browse(self.customer.ids)
        attachments = self.env['ir.attachment'].with_user(self.env.user).create(self.test_attachments_vals)
        with self.assertQueryCount(admin=8, employee=8):
            composer = self.env['mail.compose.message'].with_context({
                'default_composition_mode': 'comment',
                'default_model': test_record._name,
                'default_res_ids': test_record.ids,
            }).create({
                'attachment_ids': attachments.ids,
                'body': '<p>Test Body</p>',
                'partner_ids': [(4, customer.id)],
            })

        with self.assertQueryCount(admin=43, employee=43):
            composer._action_send_mail()

    @users('admin', 'employee')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_mail_composer_form_attachments(self):
        test_record, _test_template = self._create_test_records()
        customer = self.env['res.partner'].browse(self.customer.ids)
        attachments = self.env['ir.attachment'].with_user(self.env.user).create(self.test_attachments_vals)
        with self.assertQueryCount(admin=8, employee=8):
            composer_form = Form(
                self.env['mail.compose.message'].with_context({
                    'default_composition_mode': 'comment',
                    'default_model': test_record._name,
                    'default_res_ids': test_record.ids,
                })
            )
            composer_form.body = '<p>Test Body</p>'
            composer_form.partner_ids.add(customer)
            for attachment in attachments:
                composer_form.attachment_ids.add(attachment)
            composer = composer_form.save()

        with self.assertQueryCount(admin=57, employee=57):  # tm+com 56/56
            composer._action_send_mail()

        # notifications
        message = test_record.message_ids[0]
        self.assertEqual(message.attachment_ids, attachments)
        self.assertEqual(message.notified_partner_ids, customer + self.user_test.partner_id)

    @users('admin', 'employee')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_mail_composer_mass_w_template(self):
        _partners, test_records, test_template = self._create_test_records_for_batch()

        with self.assertQueryCount(admin=4, employee=4):
            composer = self.env['mail.compose.message'].with_context({
                'default_composition_mode': 'mass_mail',
                'default_model': test_records._name,
                'default_res_ids': test_records.ids,
                'default_template_id': test_template.id,
            }).create({})

        with self.assertQueryCount(admin=92, employee=95), self.mock_mail_gateway():
            composer._action_send_mail()

        self.assertEqual(len(self._new_mails), 10)

    @users('admin', 'employee')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_mail_composer_nodelete(self):
        test_record, _test_template = self._create_test_records()
        customer_id = self.customer.id
        with self.assertQueryCount(admin=7, employee=7):
            composer = self.env['mail.compose.message'].with_context({
                'default_composition_mode': 'comment',
                'default_model': test_record._name,
                'default_res_ids': test_record.ids,
                'mail_auto_delete': False,
            }).create({
                'body': '<p>Test Body</p>',
                'partner_ids': [(4, customer_id)],
            })

        with self.assertQueryCount(admin=42, employee=42):
            composer._action_send_mail()

    @users('admin', 'employee')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_mail_composer_w_template(self):
        test_record, test_template = self._create_test_records()
        test_template.write({'attachment_ids': [(5, 0)]})

        with self.assertQueryCount(admin=28, employee=28):  # tm 16/16
            composer = self.env['mail.compose.message'].with_context({
                'default_composition_mode': 'comment',
                'default_model': test_record._name,
                'default_res_ids': test_record.ids,
                'default_template_id': test_template.id,
            }).create({})

        with self.assertQueryCount(admin=43, employee=43):
            composer._action_send_mail()

        # notifications
        message = test_record.message_ids[0]
        self.assertFalse(message.attachment_ids)

        # remove created partner to ensure tests are the same each run
        self.env['res.partner'].sudo().search([('email', '=', 'nopartner.test@example.com')]).unlink()

    @users('admin', 'employee')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_mail_composer_w_template_attachments(self):
        test_record, test_template = self._create_test_records()

        with self.assertQueryCount(admin=29, employee=29):  # tm 17/17
            composer = self.env['mail.compose.message'].with_context({
                'default_composition_mode': 'comment',
                'default_model': test_record._name,
                'default_res_ids': test_record.ids,
                'default_template_id': test_template.id,
            }).create({})

        with self.assertQueryCount(admin=52, employee=52):
            composer._action_send_mail()

        # notifications
        message = test_record.message_ids[0]
        self.assertEqual(
            set(message.attachment_ids.mapped('name')),
            set(['AttFileName_00.txt', 'AttFileName_01.txt', 'AttFileName_02.txt'])
        )

        # remove created partner to ensure tests are the same each run
        self.env['res.partner'].sudo().search([('email', '=', 'nopartner.test@example.com')]).unlink()

    @users('admin', 'employee')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_mail_composer_w_template_form(self):
        test_record, test_template = self._create_test_records()
        test_template.write({'attachment_ids': [(5, 0)]})

        customer = self.env['res.partner'].browse(self.customer.ids)
        with self.assertQueryCount(admin=36, employee=36):  # tm 24/24
            composer_form = Form(
                self.env['mail.compose.message'].with_context({
                    'default_composition_mode': 'comment',
                    'default_model': test_record._name,
                    'default_res_ids': test_record.ids,
                    'default_template_id': test_template.id,
                })
            )
            composer = composer_form.save()

        with self.assertQueryCount(admin=53, employee=53):
            composer._action_send_mail()

        # notifications
        new_partner = self.env['res.partner'].sudo().search([('email', '=', 'nopartner.test@example.com')])
        message = test_record.message_ids[0]
        self.assertFalse(message.attachment_ids)
        self.assertEqual(message.notified_partner_ids, customer + self.user_test.partner_id + new_partner)

        # remove created partner to ensure tests are the same each run
        new_partner.unlink()

    @users('admin', 'employee')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_mail_composer_w_template_form_attachments(self):
        test_record, test_template = self._create_test_records()

        customer = self.env['res.partner'].browse(self.customer.ids)
        with self.assertQueryCount(admin=36, employee=36):  # tm 24/24
            composer_form = Form(
                self.env['mail.compose.message'].with_context({
                    'default_composition_mode': 'comment',
                    'default_model': test_record._name,
                    'default_res_ids': test_record.ids,
                    'default_template_id': test_template.id,
                })
            )
            composer = composer_form.save()

        with self.assertQueryCount(admin=72, employee=72):
            composer._action_send_mail()

        # notifications
        new_partner = self.env['res.partner'].sudo().search([('email', '=', 'nopartner.test@example.com')])
        message = test_record.message_ids[0]
        self.assertEqual(
            set(message.attachment_ids.mapped('name')),
            set(['AttFileName_00.txt', 'AttFileName_01.txt', 'AttFileName_02.txt'])
        )
        self.assertEqual(message.notified_partner_ids, customer + self.user_test.partner_id + new_partner)

        # remove created partner to ensure tests are the same each run
        new_partner.unlink()

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('admin', 'employee')
    @warmup
    def test_message_assignation_email(self):
        # Changing the `notification_type` of a user adds or removes him a group
        # which clear the caches.
        # The @warmup decorator would then becomes useless,
        # as the first thing done by this method would be to clear the cache, making the warmup pointless.
        # So, instead of changing the user notification type within this method,
        # use another user already pre-defined with the email notification type,
        # so the ormcache is preserved.
        record = self.env['mail.test.track'].create({'name': 'Test'})
        with self.assertQueryCount(admin=45, employee=44):
            record.write({
                'user_id': self.user_test_email.id,
            })

    @users('admin', 'employee')
    @warmup
    def test_message_assignation_inbox(self):
        record = self.env['mail.test.track'].create({'name': 'Test'})
        with self.assertQueryCount(admin=24, employee=23):
            record.write({
                'user_id': self.user_test_inbox.id,
            })

    @users('admin', 'employee')
    @warmup
    def test_message_log(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(admin=1, employee=1):
            record._message_log(
                body=Markup('<p>Test _message_log</p>'),
                message_type='comment')

    @users('admin', 'employee')
    @warmup
    def test_message_log_batch(self):
        records = self.env['mail.test.simple'].create([
            {'name': f'Test_{idx}'}
            for idx in range(10)
        ])

        with self.assertQueryCount(admin=1, employee=1):
            records._message_log_batch(
                bodies=dict(
                    (record.id, Markup('<p>Test _message_log</p>'))
                    for record in records
                ),
                message_type='comment')

    @users('admin', 'employee')
    @warmup
    def test_message_log_with_view(self):
        records = self.env['mail.test.simple'].create([
            {'name': f'Test_{idx}'}
            for idx in range(10)
        ])

        with self.assertQueryCount(admin=3, employee=2):
            records._message_log_with_view(
                'test_mail.mail_template_simple_test',
                render_values={'partner': self.customer.with_env(self.env)}
            )

    @users('admin', 'employee')
    @warmup
    def test_message_log_with_post(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(admin=7, employee=7):
            record.message_post(
                body=Markup('<p>Test message_post as log</p>'),
                subtype_xmlid='mail.mt_note',
                message_type='comment')

    @users('admin', 'employee')
    @warmup
    def test_message_post_no_notification(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(admin=7, employee=7):
            record.message_post(
                body=Markup('<p>Test Post Performances basic</p>'),
                partner_ids=[],
                message_type='comment',
                subtype_xmlid='mail.mt_comment')

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('admin', 'employee')
    @warmup
    def test_message_post_one_email_notification(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(admin=35, employee=35):  # com 32/32
            record.message_post(
                body=Markup('<p>Test Post Performances with an email ping</p>'),
                partner_ids=self.customer.ids,
                message_type='comment',
                subtype_xmlid='mail.mt_comment')

    @users('admin', 'employee')
    @warmup
    def test_message_post_one_inbox_notification(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(admin=21, employee=21):  # com 18/18
            record.message_post(
                body=Markup('<p>Test Post Performances with an inbox ping</p>'),
                partner_ids=self.user_test.partner_id.ids,
                message_type='comment',
                subtype_xmlid='mail.mt_comment')

    @mute_logger('odoo.models.unlink')
    @users('admin', 'employee')
    @warmup
    def test_message_subscribe_default(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(admin=6, employee=6):
            record.message_subscribe(partner_ids=self.user_test.partner_id.ids)

        with self.assertQueryCount(admin=3, employee=3):
            record.message_subscribe(partner_ids=self.user_test.partner_id.ids)

    @mute_logger('odoo.models.unlink')
    @users('admin', 'employee')
    @warmup
    def test_message_subscribe_subtypes(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})
        subtype_ids = (self.env.ref('test_mail.st_mail_test_simple_external') | self.env.ref('mail.mt_comment')).ids

        with self.assertQueryCount(admin=5, employee=5):
            record.message_subscribe(partner_ids=self.user_test.partner_id.ids, subtype_ids=subtype_ids)

        with self.assertQueryCount(admin=2, employee=2):
            record.message_subscribe(partner_ids=self.user_test.partner_id.ids, subtype_ids=subtype_ids)

    @mute_logger('odoo.models.unlink')
    @users('admin', 'employee')
    @warmup
    def test_message_track(self):
        record = self.env['mail.performance.tracking'].create({'name': 'Zizizatestname'})
        with self.assertQueryCount(admin=3, employee=3):
            record.write({'name': 'Zizizanewtestname'})

        with self.assertQueryCount(admin=3, employee=3):
            record.write({'field_%s' % (i): 'Tracked Char Fields %s' % (i) for i in range(3)})

        with self.assertQueryCount(admin=4, employee=4):
            record.write({'field_%s' % (i): 'Field Without Cache %s' % (i) for i in range(3)})
            record.flush_recordset()
            record.write({'field_%s' % (i): 'Field With Cache %s' % (i) for i in range(3)})

    @users('admin', 'employee')
    @warmup
    def test_notification_reply_to_batch(self):
        # overwrite company name to keep it short/simple
        # and not trigger the 68 character reply_to formatting
        self.env.user.company_id.name = "Forced"
        test_records_sudo = self.env['mail.test.container'].sudo().create([
            {'alias_name': 'a.%s.%d' % (self.env.user.name, index),
             'customer_id': self.customer.id,
             'name': 'T_%d' % index,
            } for index in range(10)
        ])

        with self.assertQueryCount(admin=1, employee=1):
            test_records = self.env['mail.test.container'].browse(test_records_sudo.ids)
            reply_to = test_records._notify_get_reply_to(
                default=self.env.user.email_formatted
            )

        for record in test_records:
            self.assertEqual(
                reply_to[record.id],
                formataddr((
                    f"{record.env.company.name} {record.name}",
                    f"{record.alias_name}@{self.alias_domain}"
                ))
            )


@tagged('mail_performance', 'post_install', '-at_install')
class TestMailAPIPerformance(BaseMailPerformance):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_portal = cls.env['res.users'].with_context(cls._test_context).create({
            'name': 'Olivia Portal',
            'login': 'port',
            'email': 'p.p@example.com',
            'signature': '--\nOlivia',
            'notification_type': 'email',
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id])],
        })

        cls.container = cls.env['mail.test.container'].with_context(mail_create_nosubscribe=True).create({
            'alias_name': 'test-alias',
            'customer_id': cls.customers[0].id,
            'name': 'Test Container',
        })
        cls.partners = cls.env['res.partner'].with_context(cls._test_context).create([
            {
                'name': f'Test {idx}',
                'email': f'test{idx}@example.com',
            }
            for idx in range(10)
        ])
        cls.container.message_subscribe(cls.partners.ids, subtype_ids=[
            cls.env.ref('mail.mt_comment').id,
            cls.env.ref('test_mail.st_mail_test_container_child_full').id
        ])

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('admin', 'employee')
    @warmup
    def test_mail_mail_send(self):
        message = self.env['mail.message'].sudo().create({
            'author_id': self.env.user.partner_id.id,
            'body': '<p>Test</p>',
            'email_from': self.env.user.partner_id.email,
            'message_type': 'comment',
            'model': 'mail.test.container',
            'res_id': self.container.id,
            'subject': 'Test',
        })
        attachments = self.env['ir.attachment'].create([
            dict(attachment, res_id=self.container.id, res_model='mail.test.container')
            for attachment in self.test_attachments_vals
        ])
        mail = self.env['mail.mail'].sudo().create({
            'attachment_ids': [(4, att.id) for att in attachments],
            'auto_delete': False,
            'body_html': '<p>Test</p>',
            'mail_message_id': message.id,
            'recipient_ids': [(4, pid) for pid in self.partners.ids],
        })
        with self.assertQueryCount(admin=8, employee=8):
            self.env['mail.mail'].sudo().browse(mail.ids).send()

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('admin', 'employee')
    @warmup
    def test_mail_mail_send_batch_complete(self):
        """ A more complete use case: 10 mails, attachments, servers, ... And
        2 failing emails. """
        message = self.env['mail.message'].sudo().create({
            'author_id': self.env.user.partner_id.id,
            'email_from': self.env.user.partner_id.email,
            'message_type': 'comment',
            'model': 'mail.test.container',
            'res_id': self.container.id,
            'subject': 'Test',
        })
        attachments = self.env['ir.attachment'].create([
            dict(attachment, res_id=self.container.id, res_model='mail.test.container')
            for attachment in self.test_attachments_vals
        ])
        mails = self.env['mail.mail'].sudo().create([{
            'attachment_ids': [(4, att.id) for att in attachments],
            'auto_delete': True,
            'body_html': '<p>Test %s</p>' % idx,
            'email_cc': 'cc.1@test.example.com, cc.2@test.example.com',
            'email_to': 'customer.1@example.com, customer.2@example.com',
            'mail_message_id': message.id,
            'mail_server_id': self.mail_servers.ids[idx % len(self.mail_servers.ids)],
            'recipient_ids': [(4, pid) for pid in self.partners.ids],
        } for idx in range(12)])
        mails[-2].write({'email_cc': False, 'email_to': 'strange@example¢¡.com', 'recipient_ids': [(5, 0)]})
        mails[-1].write({'email_cc': False, 'email_to': 'void', 'recipient_ids': [(5, 0)]})

        def _patched_unlink(records):
            nonlocal unlinked_mails
            unlinked_mails |= set(records.ids)
        unlinked_mails = set()

        with self.assertQueryCount(admin=31, employee=31), \
             patch.object(type(self.env['mail.mail']), 'unlink', _patched_unlink):
            self.env['mail.mail'].sudo().browse(mails.ids).send()

        for mail in mails[:-2]:
            self.assertEqual(mail.state, 'sent')
            self.assertIn(mail.id, unlinked_mails, 'Mail: sent mails are to be unlinked')
        self.assertEqual(mails[-2].state, 'exception')
        self.assertIn(mails[-2].id, unlinked_mails, 'Mail: mails with invalid recipient are also to be unlinked')
        self.assertEqual(mails[-1].state, 'exception')
        self.assertIn(mails[-1].id, unlinked_mails, 'Mail: mails with invalid recipient are also to be unlinked')

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('admin', 'employee')
    @warmup
    def test_message_post(self):
        self.container.message_subscribe(self.user_portal.partner_id.ids)
        record = self.container.with_user(self.env.user)

        # about 20 (19?) queries per additional customer
        with self.assertQueryCount(admin=61, employee=61):
            record.message_post(
                body=Markup('<p>Test Post Performances</p>'),
                message_type='comment',
                subtype_xmlid='mail.mt_comment')

        self.assertEqual(record.message_ids[0].body, '<p>Test Post Performances</p>')
        self.assertEqual(record.message_ids[0].notified_partner_ids, self.partners | self.user_portal.partner_id)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('admin', 'employee')
    @warmup
    def test_message_post_template(self):
        self.container.message_subscribe(self.user_portal.partner_id.ids)
        record = self.container.with_user(self.env.user)
        template = self.env.ref('test_mail.mail_test_container_tpl')

        # about 20 (19 ?) queries per additional custome
        with self.assertQueryCount(admin=75, employee=75):
            record.message_post_with_source(
                template,
                message_type='comment',
                subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment'),
            )

        self.assertEqual(record.message_ids[0].body, '<p>Adding stuff on %s</p>' % record.name)
        self.assertEqual(record.message_ids[0].notified_partner_ids, self.partners | self.user_portal.partner_id | self.customer)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('admin', 'employee')
    @warmup
    def test_message_post_view(self):
        _partners, test_records, test_template = self._create_test_records_for_batch()

        with self.assertQueryCount(admin=4, employee=4):
            _composer = self.env['mail.compose.message'].with_context({
                'default_composition_mode': 'mass_mail',
                'default_model': test_records._name,
                'default_res_ids': test_records.ids,
                'default_template_id': test_template.id,
            }).create({})

        with self.assertQueryCount(admin=142, employee=142):
            messages_as_sudo = test_records.message_post_with_source(
                'test_mail.mail_template_simple_test',
                render_values={'partner': self.user_test.partner_id},
                subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')
            )

        self.assertEqual(len(messages_as_sudo), 10)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('admin', 'employee')
    @warmup
    def test_message_subscribe(self):
        pids = self.partners.ids
        subtypes = self.env.ref('mail.mt_comment') | self.env.ref('test_mail.st_mail_test_ticket_container_upd')
        subtype_ids = subtypes.ids
        rec = self.env['mail.test.ticket'].create({
            'name': 'Test',
            'container_id': False,
            'customer_id': False,
            'user_id': self.user_portal.id,
        })
        rec1 = rec.with_context(active_test=False)      # to see inactive records

        self.assertEqual(rec1.message_partner_ids, self.env.user.partner_id | self.user_portal.partner_id)

        # subscribe new followers with forced given subtypes
        with self.assertQueryCount(admin=4, employee=4):
            rec.message_subscribe(
                partner_ids=pids[:4],
                subtype_ids=subtype_ids
            )

        self.assertEqual(rec1.message_partner_ids, self.env.user.partner_id | self.user_portal.partner_id | self.partners[:4])

        # subscribe existing and new followers with force=False, meaning only some new followers will be added
        with self.assertQueryCount(admin=5, employee=5):
            rec.message_subscribe(
                partner_ids=pids[:6],
                subtype_ids=None
            )

        self.assertEqual(rec1.message_partner_ids, self.env.user.partner_id | self.user_portal.partner_id | self.partners[:6])

        # subscribe existing and new followers with force=True, meaning all will have the same subtypes
        with self.assertQueryCount(admin=4, employee=4):
            rec.message_subscribe(
                partner_ids=pids,
                subtype_ids=subtype_ids
            )

        self.assertEqual(rec1.message_partner_ids, self.env.user.partner_id | self.user_portal.partner_id | self.partners)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('admin', 'employee')
    @warmup
    def test_tracking_assignation(self):
        """ Assignation performance test on already-created record """
        rec = self.env['mail.test.ticket'].create({
            'name': 'Test',
            'container_id': self.container.id,
            'customer_id': self.customer.id,
            'user_id': self.env.uid,
        })
        rec1 = rec.with_context(active_test=False)      # to see inactive records
        self.assertEqual(rec1.message_partner_ids, self.partners | self.env.user.partner_id)

        with self.assertQueryCount(admin=46, employee=46):
            rec.write({'user_id': self.user_portal.id})
        self.assertEqual(rec1.message_partner_ids, self.partners | self.env.user.partner_id | self.user_portal.partner_id)
        # write tracking message
        self.assertEqual(rec1.message_ids[0].subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(rec1.message_ids[0].notified_partner_ids, self.env['res.partner'])
        # creation message
        self.assertEqual(rec1.message_ids[1].subtype_id, self.env.ref('test_mail.st_mail_test_ticket_container_upd'))
        self.assertEqual(rec1.message_ids[1].notified_partner_ids, self.partners)
        self.assertEqual(len(rec1.message_ids), 2)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('admin', 'employee')
    @warmup
    def test_tracking_subscription_create(self):
        """ Creation performance test involving auto subscription, assignation, tracking with subtype and template send. """
        container_id = self.container.id
        customer_id = self.customer.id
        user_id = self.user_portal.id

        with self.assertQueryCount(admin=105, employee=105):
            rec = self.env['mail.test.ticket'].create({
                'name': 'Test',
                'container_id': container_id,
                'customer_id': customer_id,
                'user_id': user_id,
            })

        rec1 = rec.with_context(active_test=False)      # to see inactive records
        self.assertEqual(rec1.message_partner_ids, self.partners | self.env.user.partner_id | self.user_portal.partner_id)
        # creation message
        self.assertEqual(rec1.message_ids[0].subtype_id, self.env.ref('test_mail.st_mail_test_ticket_container_upd'))
        self.assertEqual(rec1.message_ids[0].notified_partner_ids, self.partners | self.user_portal.partner_id)
        self.assertEqual(len(rec1.message_ids), 1)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('admin', 'employee')
    @warmup
    def test_tracking_subscription_subtype(self):
        """ Write performance test involving auto subscription, tracking with subtype """
        rec = self.env['mail.test.ticket'].create({
            'name': 'Test',
            'container_id': False,
            'customer_id': False,
            'user_id': self.user_portal.id,
        })
        rec1 = rec.with_context(active_test=False)      # to see inactive records
        self.assertEqual(rec1.message_partner_ids, self.user_portal.partner_id | self.env.user.partner_id)
        self.assertEqual(len(rec1.message_ids), 1)

        with self.assertQueryCount(admin=64, employee=64):
            rec.write({
                'name': 'Test2',
                'container_id': self.container.id,
            })

        self.assertEqual(rec1.message_partner_ids, self.partners | self.env.user.partner_id | self.user_portal.partner_id)
        # write tracking message
        self.assertEqual(rec1.message_ids[0].subtype_id, self.env.ref('test_mail.st_mail_test_ticket_container_upd'))
        self.assertEqual(rec1.message_ids[0].notified_partner_ids, self.partners | self.user_portal.partner_id)
        # creation message
        self.assertEqual(rec1.message_ids[1].subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(rec1.message_ids[1].notified_partner_ids, self.env['res.partner'])
        self.assertEqual(len(rec1.message_ids), 2)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('admin', 'employee')
    @warmup
    def test_tracking_subscription_write(self):
        """ Write performance test involving auto subscription, tracking with subtype and template send """
        container_id = self.container.id
        customer_id = self.customer.id
        container2 = self.env['mail.test.container'].with_context(mail_create_nosubscribe=True).create({
            'name': 'Test Container 2',
            'customer_id': False,
            'alias_name': False,
        })

        rec = self.env['mail.test.ticket'].create({
            'name': 'Test',
            'container_id': container2.id,
            'customer_id': False,
            'user_id': self.user_portal.id,
        })
        rec1 = rec.with_context(active_test=False)      # to see inactive records
        self.assertEqual(rec1.message_partner_ids, self.user_portal.partner_id | self.env.user.partner_id)

        with self.assertQueryCount(admin=70, employee=70):
            rec.write({
                'name': 'Test2',
                'container_id': container_id,
                'customer_id': customer_id,
            })

        self.assertEqual(rec1.message_partner_ids, self.partners | self.env.user.partner_id | self.user_portal.partner_id)
        # write tracking message
        self.assertEqual(rec1.message_ids[0].subtype_id, self.env.ref('test_mail.st_mail_test_ticket_container_upd'))
        self.assertEqual(rec1.message_ids[0].notified_partner_ids, self.partners | self.user_portal.partner_id)
        # creation message
        self.assertEqual(rec1.message_ids[1].subtype_id, self.env.ref('test_mail.st_mail_test_ticket_container_upd'))
        self.assertEqual(rec1.message_ids[1].notified_partner_ids, self.user_portal.partner_id)
        self.assertEqual(len(rec1.message_ids), 2)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('admin', 'employee')
    @warmup
    def test_tracking_template(self):
        """ Write performance test involving assignation, tracking with template """
        customer_id = self.customer.id
        self.assertTrue(self.env.registry.ready, "We need to simulate that registery is ready")
        rec = self.env['mail.test.ticket'].create({
            'name': 'Test',
            'container_id': self.container.id,
            'customer_id': False,
            'user_id': self.user_portal.id,
            'mail_template': self.env.ref('test_mail.mail_test_ticket_tracking_tpl').id,
        })
        rec1 = rec.with_context(active_test=False)      # to see inactive records
        self.assertEqual(rec1.message_partner_ids, self.partners | self.env.user.partner_id | self.user_portal.partner_id)

        with self.assertQueryCount(admin=34, employee=34):
            rec.write({
                'name': 'Test2',
                'customer_id': customer_id,
                'user_id': self.env.uid,
            })

        # write template message (sent to customer, mass mailing kept for history)
        self.assertEqual(rec1.message_ids[0].subtype_id, self.env['mail.message.subtype'])
        self.assertEqual(rec1.message_ids[0].subject, 'Test Template')
        # write tracking message
        self.assertEqual(rec1.message_ids[1].subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(rec1.message_ids[1].notified_partner_ids, self.env['res.partner'])
        # creation message
        self.assertEqual(rec1.message_ids[2].subtype_id, self.env.ref('test_mail.st_mail_test_ticket_container_upd'))
        self.assertEqual(rec1.message_ids[2].notified_partner_ids, self.partners | self.user_portal.partner_id)
        self.assertEqual(len(rec1.message_ids), 3)


@tagged('mail_performance', 'post_install', '-at_install')
class TestMailFormattersPerformance(BaseMailPerformance):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.containers = cls.env['mail.test.container'].with_context(mail_create_nosubscribe=True).create([
            {
                'alias_name': 'test-alias',
                'customer_id': cls.customers[0].id,
                'name': 'Test Container',
            }, {
                'alias_name': 'test-alias-2',
                'customer_id': cls.customers[1].id,
                'name': 'Test Container 2',
            },
        ])
        cls.partners = cls.env['res.partner'].with_context(cls._test_context).create([
            {
                'name': f'Test {idx}',
                'email': f'test{idx}@example.com',
            }
            for idx in range(10)
        ])
        cls.containers.message_subscribe(cls.partners.ids, subtype_ids=[
            cls.env.ref('mail.mt_comment').id,
            cls.env.ref('test_mail.st_mail_test_container_child_full').id
        ])
        cls.container = cls.containers[0]

        name_field = cls.env['ir.model.fields']._get(cls.container._name, 'name')
        customer_id_field = cls.env['ir.model.fields']._get(cls.container._name, 'customer_id')
        comment_subtype_id = cls.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')

        cls.messages_all = cls.env['mail.message'].sudo().create([
            {
                'attachment_ids': [
                    (0, 0, {
                        'datas': 'data',
                        'name': f'Test file {att_idx}',
                        'res_id': record.id,
                        'res_model': record._name,
                    })
                    for att_idx in range(2)
                ],
                'author_id': cls.partners[msg_idx].id,
                'body': f'<p>Test {msg_idx}</p>',
                'email_from': cls.partners[msg_idx].email_formatted,
                'link_preview_ids': [
                    (0, 0, {
                        'source_url': 'https://www.odoo.com',
                    }), (0, 0, {
                        'source_url': 'https://www.example.com',
                    }),
                ],
                'message_type': 'comment',
                'model': record._name,
                'notification_ids': [
                    (0, 0, {
                        'is_read': False,
                        'notification_type': 'inbox',
                        'res_partner_id': cls.partners[(record_idx * 5) + (msg_idx * 2)].id,
                    }),
                    (0, 0, {
                        'is_read': True,
                        'notification_type': 'email',
                        'notification_status': 'sent',
                        'res_partner_id': cls.partners[(record_idx * 5) + (msg_idx * 2) + 1].id,
                    }),
                    (0, 0, {
                        'is_read': True,
                        'notification_type': 'email',
                        'notification_status': 'exception',
                        'res_partner_id': cls.partners[(record_idx * 5) + (msg_idx * 2) + 2].id,
                    }),
                ],
                'partner_ids': [
                    (4, cls.partners[(record_idx * 5) + msg_idx].id),
                    (4, cls.partners[(record_idx * 5) + msg_idx + 1].id),
                ],
                'reaction_ids': [
                    (0, 0, {
                        'content': '\U0001F4E7',
                        'partner_id': cls.partners[(record_idx * 5)].id
                    }), (0, 0, {
                        'content': '\U0001F4E8',
                        'partner_id': cls.partners[(record_idx * 5) + 1].id
                    }),
                ],
                'res_id': record.id,
                'starred_partner_ids': [
                    (4, cls.partners[(record_idx * 5) + msg_idx].id),
                    (4, cls.partners[(record_idx * 5) + (msg_idx * 2) + 1].id),
                ],
                'subject': f'Test Container {msg_idx}',
                'subtype_id': comment_subtype_id,
                'tracking_value_ids': [
                    (0, 0, {
                        'field_id': name_field.id,
                        'new_value_char': 'new 0',
                        'old_value_char': 'old 0',
                    }),
                    (0, 0, {
                        'field_id': customer_id_field.id,
                        'new_value_char': 'new 1',
                        'new_value_integer': cls.partners[(record_idx * 5)].id,
                        'old_value_char': 'old 1',
                        'old_value_integer': cls.partners[(record_idx * 5) + 1].id,
                    }),
                ]
            }
            for msg_idx in range(2)
            for record_idx, record in enumerate(cls.containers)
        ])

    def test_assert_initial_values(self):
        self.assertEqual(len(self.messages_all), 2*2)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('employee')
    @warmup
    def test_message_format_multi(self):
        """Test performance of `_message_format` and of `message_format` with
        multiple messages with multiple attachments, different authors, various
        notifications, and different tracking values.

        Those messages might not make sense functionally but they are crafted to
        cover as much of the code as possible in regard to number of queries.

        Setup :
          * 2 records (self.containers -> 2 mail.test.container record, with
            a different customer_id each)
          * 2 messages / record
          * 2 attachments / message
          * 3 notifications / message
          * 2 tracking values / message
        """
        messages_all = self.messages_all.with_env(self.env)

        with self.assertQueryCount(employee=27):
            res = messages_all.message_format()

        self.assertEqual(len(res), 2*2)
        for message in res:
            self.assertEqual(len(message['attachments']), 2)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('employee')
    @warmup
    def test_message_format_single(self):
        message = self.messages_all[0].with_env(self.env)

        with self.assertQueryCount(employee=24):
            res = message.message_format()

        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0]['attachments']), 2)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('employee')
    @warmup
    def test_message_format_group_thread_name_by_model(self):
        """Ensures the fetch of multiple thread names is grouped by model."""
        records = []
        for _i in range(5):
            records.append(self.env['mail.test.simple'].create({'name': 'Test'}))
        records.append(self.env['mail.test.track'].create({'name': 'Test'}))

        messages = self.env['mail.message'].create([{
            'model': record._name,
            'res_id': record.id
        } for record in records])

        with self.assertQueryCount(employee=7):
            res = messages.message_format()
            self.assertEqual(len(res), 6)

        self.env.flush_all()
        self.env.invalidate_all()

        with self.assertQueryCount(employee=15):
            res = messages.message_format()
            self.assertEqual(len(res), 6)


@tagged('mail_performance', 'post_install', '-at_install')
class TestPerformance(BaseMailPerformance):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # record
        cls.record_container = cls.env['mail.test.container'].with_context(mail_create_nosubscribe=True).create({
            'name': 'Test record',
            'customer_id': cls.customer.id,
            'alias_name': 'test-alias',
        })
        # followers
        cls.user_follower_email = cls.env['res.users'].with_context(cls._test_context).create({
            'name': 'user_follower_email',
            'login': 'user_follower_email',
            'email': 'user_follower_email@example.com',
            'notification_type': 'email',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.user_follower_inbox = cls.env['res.users'].with_context(cls._test_context).create({
            'name': 'user_follower_inbox',
            'login': 'user_follower_inbox',
            'email': 'user_follower_inbox@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.partner_follower = cls.env['res.partner'].with_context(cls._test_context).create({
            'name': 'partner_follower',
            'email': 'partner_follower@example.com',
        })
        cls.record_container.message_subscribe([
            cls.partner_follower.id,
            cls.user_follower_inbox.partner_id.id,
            cls.user_follower_email.partner_id.id
        ])

        # partner_ids
        cls.user_inbox = cls.env['res.users'].with_context(cls._test_context).create({
            'name': 'user_inbox',
            'login': 'user_inbox',
            'email': 'user_inbox@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.user_email = cls.env['res.users'].with_context(cls._test_context).create({
            'name': 'user_email',
            'login': 'user_email',
            'email': 'user_email@example.com',
            'notification_type': 'email',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.partner = cls.env['res.partner'].with_context(cls._test_context).create({
            'name': 'partner',
            'email': 'partner@example.com',
        })

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('employee')
    @warmup
    def test_message_post(self):
        # aims to cover as much features of message_post as possible
        recipients = self.user_inbox.partner_id + self.user_email.partner_id + self.partner
        record_container = self.record_container.with_user(self.env.user)
        attachments_vals = [  # not linear on number of attachments_vals
            ('attach tuple 1', "attachement tupple content 1"),
            ('attach tuple 2', "attachement tupple content 2", {'cid': 'cid1'}),
            ('attach tuple 3', "attachement tupple content 3", {'cid': 'cid2'}),
        ]
        attachments = self.env['ir.attachment'].with_user(self.env.user).create(self.test_attachments_vals)
        # enable_logging = self.cr._enable_logging() if self.warm else nullcontext()
        # with self.assertQueryCount(employee=63), enable_logging:
        with self.assertQueryCount(employee=69):
            record_container.with_context({}).message_post(
                body=Markup('<p>Test body <img src="cid:cid1"> <img src="cid:cid2"></p>'),
                subject='Test Subject',
                message_type='notification',
                subtype_xmlid=None,
                partner_ids=recipients.ids,
                parent_id=False,
                attachments=attachments_vals,
                attachment_ids=attachments.ids,
                email_add_signature=True,
                model_description=False,
                mail_auto_delete=True
            )
        new_message = record_container.message_ids[0]
        self.assertEqual(attachments.mapped('res_model'), [record_container._name for i in range(3)])
        self.assertEqual(attachments.mapped('res_id'), [record_container.id for i in range(3)])
        self.assertTrue(new_message.body.startswith('<p>Test body <img src="/web/image/'))
        self.assertEqual(new_message.notified_partner_ids, recipients)
