# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

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

        # creating partners is required notably witn template usage
        cls.user_employee.write({'groups_id': [(4, cls.env.ref('base.group_partner_manager').id)]})

        cls.customer = cls.env['res.partner'].with_context(cls._test_context).create({
            'country_id': cls.env.ref('base.be').id,
            'email': 'customer.test@example.com',
            'name': 'Test Customer',
            'mobile': '0456123456',
        })

        cls.test_attachments_vals = cls._generate_attachments_data(
            cls, 3, res_model='mail.compose.message', res_id=0
        )

    def setUp(self):
        super(BaseMailPerformance, self).setUp()
        # patch registry to simulate a ready environment
        self.patch(self.env.registry, 'ready', True)
        self.flush_tracking()


@tagged('mail_performance', 'post_install', '-at_install')
class TestBaseMailPerformance(BaseMailPerformance):

    def setUp(self):
        super(TestBaseMailPerformance, self).setUp()

        self.res_partner_3 = self.env['res.partner'].create({
            'name': 'Gemini Furniture',
            'email': 'gemini.furniture39@example.com',
        })
        self.res_partner_4 = self.env['res.partner'].create({
            'name': 'Ready Mat',
            'email': 'ready.mat28@example.com',
        })
        self.res_partner_10 = self.env['res.partner'].create({
            'name': 'The Jackson Group',
            'email': 'jackson.group82@example.com',
        })
        self.res_partner_12 = self.env['res.partner'].create({
            'name': 'Azure Interior',
            'email': 'azure.Interior24@example.com',
        })
        self.env['mail.performance.thread'].create([
            {
                'name': 'Object 0',
                'value': 0,
                'partner_id': self.res_partner_3.id,
            }, {
                'name': 'Object 1',
                'value': 10,
                'partner_id': self.res_partner_3.id,
            }, {
                'name': 'Object 2',
                'value': 20,
                'partner_id': self.res_partner_4.id,
            }, {
                'name': 'Object 3',
                'value': 30,
                'partner_id': self.res_partner_10.id,
            }, {
                'name': 'Object 4',
                'value': 40,
                'partner_id': self.res_partner_12.id,
            }
        ])

    @users('__system__', 'demo')
    @warmup
    def test_read_mail(self):
        """ Read records inheriting from 'mail.thread'. """
        records = self.env['mail.performance.thread'].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(__system__=2, demo=2):
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

    @users('__system__', 'demo')
    @warmup
    def test_write_mail(self):
        """ Write records inheriting from 'mail.thread' (no recomputation). """
        records = self.env['mail.performance.thread'].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(__system__=2, demo=2):
            records.write({'name': 'X'})

    @users('__system__', 'demo')
    @warmup
    def test_write_mail_with_recomputation(self):
        """ Write records inheriting from 'mail.thread' (with recomputation). """
        records = self.env['mail.performance.thread'].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(__system__=2, demo=2):
            records.write({'value': 42})

    @users('__system__', 'demo')
    @warmup
    def test_write_mail_with_tracking(self):
        """ Write records inheriting from 'mail.thread' (with field tracking). """
        record = self.env['mail.performance.thread'].create({
            'name': 'Test',
            'track': 'Y',
            'value': 40,
            'partner_id': self.res_partner_12.id,
        })

        with self.assertQueryCount(__system__=3, demo=3):
            record.track = 'X'

    @users('__system__', 'demo')
    @warmup
    def test_create_mail(self):
        """ Create records inheriting from 'mail.thread' (without field tracking). """
        model = self.env['mail.performance.thread']

        with self.assertQueryCount(__system__=2, demo=2):
            model.with_context(tracking_disable=True).create({'name': 'X'})

    @users('__system__', 'demo')
    @warmup
    def test_create_mail_with_tracking(self):
        """ Create records inheriting from 'mail.thread' (with field tracking). """
        with self.assertQueryCount(__system__=8, demo=8):
            self.env['mail.performance.thread'].create({'name': 'X'})

    @users('__system__', 'employee')
    @warmup
    def test_create_mail_simple(self):
        with self.assertQueryCount(__system__=7, employee=7):
            self.env['mail.test.simple'].create({'name': 'Test'})

    @users('__system__', 'employee')
    @warmup
    def test_create_mail_simple_multi(self):
        with self.assertQueryCount(__system__=7, employee=7):
            self.env['mail.test.simple'].create([{'name': 'Test'}] * 5)

    @users('__system__', 'employee')
    @warmup
    def test_write_mail_simple(self):
        rec = self.env['mail.test.simple'].create({'name': 'Test'})
        with self.assertQueryCount(__system__=1, employee=1):
            rec.write({
                'name': 'Test2',
                'email_from': 'test@test.com',
            })


@tagged('mail_performance', 'post_install', '-at_install')
class TestMailAPIPerformance(BaseMailPerformance):

    def setUp(self):
        super(TestMailAPIPerformance, self).setUp()
        self.user_test = self.env['res.users'].with_context(self._test_context).create({
            'name': 'Paulette Testouille',
            'login': 'paul',
            'email': 'user.test.paulette@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })

        # automatically follow activities, for backward compatibility concerning query count
        self.env.ref('mail.mt_activities').write({'default': True})

    def _create_test_records(self):
        self.test_record_full = self.env['mail.test.ticket'].with_context(self._test_context).create({
            'name': 'TestRecord',
            'customer_id': self.customer.id,
            'user_id': self.user_test.id,
            'email_from': 'nopartner.test@example.com',
        })
        self.test_template_full = self.env['mail.template'].create({
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

    @users('__system__', 'employee')
    @warmup
    def test_adv_activity(self):
        model = self.env['mail.test.activity']

        with self.assertQueryCount(__system__=7, employee=7):
            model.create({'name': 'Test'})

    @users('__system__', 'employee')
    @warmup
    @mute_logger('odoo.models.unlink')
    def test_adv_activity_full(self):
        record = self.env['mail.test.activity'].create({'name': 'Test'})
        MailActivity = self.env['mail.activity'].with_context({
            'default_res_model': 'mail.test.activity',
        })

        with self.assertQueryCount(__system__=6, employee=6):
            activity = MailActivity.create({
                'summary': 'Test Activity',
                'res_id': record.id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            })
            # read activity_type to normalize cache between enterprise and community
            # voip module read activity_type during create leading to one less query in enterprise on action_feedback
            _category = activity.activity_type_id.category

        with self.assertQueryCount(__system__=14, employee=15):  # com+tm 14/15
            activity.action_feedback(feedback='Zizisse Done !')

    @users('__system__', 'employee')
    @warmup
    @mute_logger('odoo.models.unlink')
    def test_adv_activity_mixin(self):
        record = self.env['mail.test.activity'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=7, employee=7):
            activity = record.action_start('Test Start')
            # read activity_type to normalize cache between enterprise and community
            # voip module read activity_type during create leading to one less query in enterprise on action_close
            _category = activity.activity_type_id.category

        record.write({'name': 'Dupe write'})

        with self.assertQueryCount(__system__=15, employee=17):
            record.action_close('Dupe feedback')

        self.assertEqual(record.activity_ids, self.env['mail.activity'])

    @users('__system__', 'employee')
    @warmup
    @mute_logger('odoo.models.unlink')
    def test_adv_activity_mixin_w_attachments(self):
        record = self.env['mail.test.activity'].create({'name': 'Test'})

        attachments = self.env['ir.attachment'].create([
            dict(values,
                 res_model='mail.activity',
                 res_id=0)
            for values in self.test_attachments_vals
        ])

        with self.assertQueryCount(__system__=7, employee=7):
            activity = record.action_start('Test Start')
            #read activity_type to normalize cache between enterprise and community
            #voip module read activity_type during create leading to one less query in enterprise on action_close
            _category = activity.activity_type_id.category

        record.write({'name': 'Dupe write'})

        with self.assertQueryCount(__system__=18, employee=21):  # com+tm 17/20
            record.action_close('Dupe feedback', attachment_ids=attachments.ids)

        # notifications
        message = record.message_ids[0]
        self.assertEqual(
            set(message.attachment_ids.mapped('name')),
            set(['AttFileName_00.txt', 'AttFileName_01.txt', 'AttFileName_02.txt'])
        )

    @users('__system__', 'employee')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_mail_composer(self):
        self._create_test_records()
        test_record = self.env['mail.test.ticket'].browse(self.test_record_full.id)
        customer_id = self.customer.id
        with self.assertQueryCount(__system__=2, employee=2):
            composer = self.env['mail.compose.message'].with_context({
                'default_composition_mode': 'comment',
                'default_model': test_record._name,
                'default_res_id': test_record.id,
            }).create({
                'body': '<p>Test Body</p>',
                'partner_ids': [(4, customer_id)],
            })

        with self.assertQueryCount(__system__=26, employee=32):
            composer._action_send_mail()

    @users('__system__', 'employee')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_mail_composer_attachments(self):
        self._create_test_records()
        test_record = self.env['mail.test.ticket'].browse(self.test_record_full.id)
        customer = self.env['res.partner'].browse(self.customer.ids)
        attachments = self.env['ir.attachment'].with_user(self.env.user).create(self.test_attachments_vals)
        with self.assertQueryCount(__system__=3, employee=3):
            composer = self.env['mail.compose.message'].with_context({
                'default_composition_mode': 'comment',
                'default_model': test_record._name,
                'default_res_id': test_record.id,
            }).create({
                'attachment_ids': attachments.ids,
                'body': '<p>Test Body</p>',
                'partner_ids': [(4, customer.id)],
            })

        with self.assertQueryCount(__system__=29, employee=37):
            composer._action_send_mail()

    @users('__system__', 'employee')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_mail_composer_form_attachments(self):
        self._create_test_records()
        test_record = self.env['mail.test.ticket'].browse(self.test_record_full.id)
        customer = self.env['res.partner'].browse(self.customer.ids)
        attachments = self.env['ir.attachment'].with_user(self.env.user).create(self.test_attachments_vals)
        with self.assertQueryCount(__system__=18, employee=18):  # tm+com 16/16
            composer_form = Form(
                self.env['mail.compose.message'].with_context({
                    'default_composition_mode': 'comment',
                    'default_model': test_record._name,
                    'default_res_id': test_record.id,
                })
            )
            composer_form.body = '<p>Test Body</p>'
            composer_form.partner_ids.add(customer)
            for attachment in attachments:
                composer_form.attachment_ids.add(attachment)
            composer = composer_form.save()

        with self.assertQueryCount(__system__=39, employee=47):  # tm+com 38/46
            composer._action_send_mail()

        # notifications
        message = test_record.message_ids[0]
        self.assertEqual(message.attachment_ids, attachments)
        self.assertEqual(message.notified_partner_ids, customer + self.user_test.partner_id)

    @users('__system__', 'employee')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_mail_composer_nodelete(self):
        self._create_test_records()
        test_record = self.env['mail.test.ticket'].browse(self.test_record_full.id)
        customer_id = self.customer.id
        with self.assertQueryCount(__system__=2, employee=2):
            composer = self.env['mail.compose.message'].with_context({
                'default_composition_mode': 'comment',
                'default_model': test_record._name,
                'default_res_id': test_record.id,
                'mail_auto_delete': False,
            }).create({
                'body': '<p>Test Body</p>',
                'partner_ids': [(4, customer_id)],
            })

        with self.assertQueryCount(__system__=26, employee=32):
            composer._action_send_mail()

    @users('__system__', 'employee')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_mail_composer_w_template(self):
        self._create_test_records()
        self.test_template_full.write({'attachment_ids': [(5, 0)]})

        test_record = self.env['mail.test.ticket'].browse(self.test_record_full.id)
        test_template = self.env['mail.template'].browse(self.test_template_full.id)

        with self.assertQueryCount(__system__=23, employee=24):  # tm 13/14 / com 22/23
            composer = self.env['mail.compose.message'].with_context({
                'default_composition_mode': 'comment',
                'default_model': test_record._name,
                'default_res_id': test_record.id,
                'default_template_id': test_template.id,
            }).create({})
            composer._onchange_template_id_wrapper()

        with self.assertQueryCount(__system__=25, employee=31):
            composer._action_send_mail()

        # notifications
        message = test_record.message_ids[0]
        self.assertFalse(message.attachment_ids)

        # remove created partner to ensure tests are the same each run
        self.env['res.partner'].sudo().search([('email', '=', 'nopartner.test@example.com')]).unlink()

    @users('__system__', 'employee')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_mail_composer_w_template_attachments(self):
        self._create_test_records()

        test_record = self.env['mail.test.ticket'].browse(self.test_record_full.id)
        test_template = self.env['mail.template'].browse(self.test_template_full.id)
        with self.assertQueryCount(__system__=24, employee=25):  # tm 14/15 / com 23/24
            composer = self.env['mail.compose.message'].with_context({
                'default_composition_mode': 'comment',
                'default_model': test_record._name,
                'default_res_id': test_record.id,
                'default_template_id': test_template.id,
            }).create({})
            composer._onchange_template_id_wrapper()

        with self.assertQueryCount(__system__=33, employee=44):
            composer._action_send_mail()

        # notifications
        message = test_record.message_ids[0]
        self.assertEqual(
            set(message.attachment_ids.mapped('name')),
            set(['AttFileName_00.txt', 'AttFileName_01.txt', 'AttFileName_02.txt'])
        )

        # remove created partner to ensure tests are the same each run
        self.env['res.partner'].sudo().search([('email', '=', 'nopartner.test@example.com')]).unlink()

    @users('__system__', 'employee')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_mail_composer_w_template_form(self):
        self._create_test_records()
        self.test_template_full.write({'attachment_ids': [(5, 0)]})

        test_record = self.env['mail.test.ticket'].browse(self.test_record_full.id)
        test_template = self.env['mail.template'].browse(self.test_template_full.id)
        customer = self.env['res.partner'].browse(self.customer.ids)
        with self.assertQueryCount(__system__=40, employee=42):  # tm 28/30 / com 37/39
            composer_form = Form(
                self.env['mail.compose.message'].with_context({
                    'default_composition_mode': 'comment',
                    'default_model': test_record._name,
                    'default_res_id': test_record.id,
                    'default_template_id': test_template.id,
                })
            )
            composer = composer_form.save()

        with self.assertQueryCount(__system__=35, employee=41):
            composer._action_send_mail()

        # notifications
        new_partner = self.env['res.partner'].sudo().search([('email', '=', 'nopartner.test@example.com')])
        message = test_record.message_ids[0]
        self.assertFalse(message.attachment_ids)
        self.assertEqual(message.notified_partner_ids, customer + self.user_test.partner_id + new_partner)

        # remove created partner to ensure tests are the same each run
        new_partner.unlink()

    @users('__system__', 'employee')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_mail_composer_w_template_form_attachments(self):
        self._create_test_records()

        test_record = self.env['mail.test.ticket'].browse(self.test_record_full.id)
        test_template = self.env['mail.template'].browse(self.test_template_full.id)
        customer = self.env['res.partner'].browse(self.customer.ids)
        with self.assertQueryCount(__system__=41, employee=43):  # tm 29/31 / com 38/40
            composer_form = Form(
                self.env['mail.compose.message'].with_context({
                    'default_composition_mode': 'comment',
                    'default_model': test_record._name,
                    'default_res_id': test_record.id,
                    'default_template_id': test_template.id,
                })
            )
            composer = composer_form.save()

        with self.assertQueryCount(__system__=47, employee=64):
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
    @users('__system__', 'employee')
    @warmup
    def test_message_assignation_email(self):
        self.user_test.write({'notification_type': 'email'})
        record = self.env['mail.test.track'].create({'name': 'Test'})
        with self.assertQueryCount(__system__=27, employee=28):
            record.write({
                'user_id': self.user_test.id,
            })

    @users('__system__', 'employee')
    @warmup
    def test_message_assignation_inbox(self):
        record = self.env['mail.test.track'].create({'name': 'Test'})
        with self.assertQueryCount(__system__=19, employee=21):
            record.write({
                'user_id': self.user_test.id,
            })

    @users('__system__', 'employee')
    @warmup
    def test_message_log(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=1, employee=1):
            record._message_log(
                body='<p>Test _message_log</p>',
                message_type='comment')

    @users('__system__', 'employee')
    @warmup
    def test_message_log_with_post(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=4, employee=7):
            record.message_post(
                body='<p>Test message_post as log</p>',
                subtype_xmlid='mail.mt_note',
                message_type='comment')

    @users('__system__', 'employee')
    @warmup
    def test_message_post_no_notification(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=4, employee=7):
            record.message_post(
                body='<p>Test Post Performances basic</p>',
                partner_ids=[],
                message_type='comment',
                subtype_xmlid='mail.mt_comment')

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'employee')
    @warmup
    def test_message_post_one_email_notification(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=24, employee=28):
            record.message_post(
                body='<p>Test Post Performances with an email ping</p>',
                partner_ids=self.customer.ids,
                message_type='comment',
                subtype_xmlid='mail.mt_comment')

    @users('__system__', 'employee')
    @warmup
    def test_message_post_one_inbox_notification(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=14, employee=18):
            record.message_post(
                body='<p>Test Post Performances with an inbox ping</p>',
                partner_ids=self.user_test.partner_id.ids,
                message_type='comment',
                subtype_xmlid='mail.mt_comment')

    @mute_logger('odoo.models.unlink')
    @users('__system__', 'employee')
    @warmup
    def test_message_subscribe_default(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=6, employee=6):
            record.message_subscribe(partner_ids=self.user_test.partner_id.ids)

        with self.assertQueryCount(__system__=3, employee=3):
            record.message_subscribe(partner_ids=self.user_test.partner_id.ids)

    @mute_logger('odoo.models.unlink')
    @users('__system__', 'employee')
    @warmup
    def test_message_subscribe_subtypes(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})
        subtype_ids = (self.env.ref('test_mail.st_mail_test_simple_external') | self.env.ref('mail.mt_comment')).ids

        with self.assertQueryCount(__system__=5, employee=5):
            record.message_subscribe(partner_ids=self.user_test.partner_id.ids, subtype_ids=subtype_ids)

        with self.assertQueryCount(__system__=2, employee=2):
            record.message_subscribe(partner_ids=self.user_test.partner_id.ids, subtype_ids=subtype_ids)

    @mute_logger('odoo.models.unlink')
    @users('__system__', 'employee')
    @warmup
    def test_message_track(self):
        record = self.env['mail.performance.tracking'].create({'name': 'Zizizatestname'})
        with self.assertQueryCount(__system__=3, employee=3):
            record.write({'name': 'Zizizanewtestname'})

        with self.assertQueryCount(__system__=3, employee=3):
            record.write({'field_%s' % (i): 'Tracked Char Fields %s' % (i) for i in range(3)})

        with self.assertQueryCount(__system__=4, employee=4):
            record.write({'field_%s' % (i): 'Field Without Cache %s' % (i) for i in range(3)})
            record.flush_recordset()
            record.write({'field_%s' % (i): 'Field With Cache %s' % (i) for i in range(3)})

    @users('__system__', 'employee')
    @warmup
    def test_notification_reply_to_batch(self):
        test_records_sudo = self.env['mail.test.container'].sudo().create([
            {'alias_name': 'alias.test.%s.%d' % (self.env.user.name, index),
             'customer_id': self.customer.id,
             'name': 'Test_%d' % index,
            } for index in range(10)
        ])

        with self.assertQueryCount(__system__=1, employee=1):
            test_records = self.env['mail.test.container'].browse(test_records_sudo.ids)
            reply_to = test_records._notify_get_reply_to(
                default=self.env.user.email_formatted
            )

        for record in test_records:
            self.assertEqual(
                reply_to[record.id],
                formataddr(
                    ("%s %s" % (self.env.user.company_id.name, record.name),
                     "%s@%s" % (record.alias_name, self.alias_domain)
                    )
                )
            )


@tagged('mail_performance', 'post_install', '-at_install')
class TestMailComplexPerformance(BaseMailPerformance):

    def setUp(self):
        super(TestMailComplexPerformance, self).setUp()
        self.user_portal = self.env['res.users'].with_context(self._test_context).create({
            'name': 'Olivia Portal',
            'login': 'port',
            'email': 'p.p@example.com',
            'signature': '--\nOlivia',
            'notification_type': 'email',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        })

        self.container = self.env['mail.test.container'].with_context(mail_create_nosubscribe=True).create({
            'name': 'Test Container',
            'customer_id': self.customer.id,
            'alias_name': 'test-alias',
        })
        Partners = self.env['res.partner'].with_context(self._test_context)
        self.partners = self.env['res.partner']
        for x in range(0, 10):
            self.partners |= Partners.create({'name': 'Test %s' % x, 'email': 'test%s@example.com' % x})
        self.container.message_subscribe(self.partners.ids, subtype_ids=[
            self.env.ref('mail.mt_comment').id,
            self.env.ref('test_mail.st_mail_test_container_child_full').id
        ])

        # `test_complex_mail_mail_send`
        self.env.flush_all()

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'employee')
    @warmup
    def test_complex_mail_mail_send(self):
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
        with self.assertQueryCount(__system__=9, employee=9):
            self.env['mail.mail'].sudo().browse(mail.ids).send()

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'employee')
    @warmup
    def test_complex_mail_mail_send_batch_complete(self):
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
        mails[-2].write({'email_cc': False, 'email_to': 'strange@example¢¡.com'})
        mails[-1].write({'email_cc': False, 'email_to': 'void', 'recipient_ids': [(5, 0)]})
        with self.assertQueryCount(__system__=44, employee=44):
            self.env['mail.mail'].sudo().browse(mails.ids).send()

        for mail in mails[:-2]:
            self.assertEqual(mail.state, 'sent')
            self.assertTrue(mail.to_delete, 'Mail: sent mails are to be unlinked')
        self.assertEqual(mails[-2].state, 'exception')
        self.assertFalse(mails[-2].to_delete, 'Mail: invalid recipient, not to unlink')
        self.assertEqual(mails[-1].state, 'exception')
        self.assertFalse(mails[-2].to_delete, 'Mail: ninvalid recipient, not to unlink')

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'employee')
    @warmup
    def test_complex_message_post(self):
        self.container.message_subscribe(self.user_portal.partner_id.ids)
        record = self.container.with_user(self.env.user)

        # about 20 (19?) queries per additional customer group
        with self.assertQueryCount(__system__=35, employee=36):
            record.message_post(
                body='<p>Test Post Performances</p>',
                message_type='comment',
                subtype_xmlid='mail.mt_comment')

        self.assertEqual(record.message_ids[0].body, '<p>Test Post Performances</p>')
        self.assertEqual(record.message_ids[0].notified_partner_ids, self.partners | self.user_portal.partner_id)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'employee')
    @warmup
    def test_complex_message_post_template(self):
        self.container.message_subscribe(self.user_portal.partner_id.ids)
        record = self.container.with_user(self.env.user)
        template_id = self.env.ref('test_mail.mail_test_container_tpl').id

        # about 20 (19 ?) queries per additional customer group
        with self.assertQueryCount(__system__=42, employee=43):
            record.message_post_with_template(template_id, message_type='comment', composition_mode='comment')

        self.assertEqual(record.message_ids[0].body, '<p>Adding stuff on %s</p>' % record.name)
        self.assertEqual(record.message_ids[0].notified_partner_ids, self.partners | self.user_portal.partner_id | self.customer)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'employee')
    @warmup
    def test_complex_message_subscribe(self):
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
        with self.assertQueryCount(__system__=4, employee=4):
            rec.message_subscribe(
                partner_ids=pids[:4],
                subtype_ids=subtype_ids
            )

        self.assertEqual(rec1.message_partner_ids, self.env.user.partner_id | self.user_portal.partner_id | self.partners[:4])

        # subscribe existing and new followers with force=False, meaning only some new followers will be added
        with self.assertQueryCount(__system__=5, employee=5):
            rec.message_subscribe(
                partner_ids=pids[:6],
                subtype_ids=None
            )

        self.assertEqual(rec1.message_partner_ids, self.env.user.partner_id | self.user_portal.partner_id | self.partners[:6])

        # subscribe existing and new followers with force=True, meaning all will have the same subtypes
        with self.assertQueryCount(__system__=4, employee=4):
            rec.message_subscribe(
                partner_ids=pids,
                subtype_ids=subtype_ids
            )

        self.assertEqual(rec1.message_partner_ids, self.env.user.partner_id | self.user_portal.partner_id | self.partners)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'employee')
    @warmup
    def test_complex_tracking_assignation(self):
        """ Assignation performance test on already-created record """
        rec = self.env['mail.test.ticket'].create({
            'name': 'Test',
            'container_id': self.container.id,
            'customer_id': self.customer.id,
            'user_id': self.env.uid,
        })
        rec1 = rec.with_context(active_test=False)      # to see inactive records
        self.assertEqual(rec1.message_partner_ids, self.partners | self.env.user.partner_id)
        with self.assertQueryCount(__system__=24, employee=25):
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
    @users('__system__', 'employee')
    @warmup
    def test_complex_tracking_subscription_create(self):
        """ Creation performance test involving auto subscription, assignation, tracking with subtype and template send. """
        container_id = self.container.id
        customer_id = self.customer.id
        user_id = self.user_portal.id

        with self.assertQueryCount(__system__=56, employee=57):  # tm 56/57
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
    @users('__system__', 'employee')
    @warmup
    def test_complex_tracking_subscription_subtype(self):
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
        with self.assertQueryCount(__system__=36, employee=36):
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
    @users('__system__', 'employee')
    @warmup
    def test_complex_tracking_subscription_write(self):
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

        with self.assertQueryCount(__system__=36, employee=36):
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
    @users('__system__', 'employee')
    @warmup
    def test_complex_tracking_template(self):
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

        with self.assertQueryCount(__system__=19, employee=20):
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

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('employee')
    @warmup
    def test_message_format(self):
        """Test performance of `_message_format` and of `message_format` with
        multiple messages with multiple attachments, different authors, various
        notifications, and different tracking values.
        Those messages might not make sense functionally but they are crafted to
        cover as much of the code as possible in regard to number of queries.
        """
        name_field = self.env['ir.model.fields']._get(self.container._name, 'name')
        customer_id_field = self.env['ir.model.fields']._get(self.container._name, 'customer_id')

        messages = self.env['mail.message'].sudo().create([{
            'subject': 'Test 0',
            'body': '<p>Test 0</p>',
            'author_id': self.partners[0].id,
            'email_from': self.partners[0].email,
            'model': 'mail.test.container',
            'res_id': self.container.id,
            'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment'),
            'attachment_ids': [
                (0, 0, {
                    'name': 'test file 0 - %d' % j,
                    'datas': 'data',
                }) for j in range(2)
            ],
            'notification_ids': [
                (0, 0, {
                    'res_partner_id': self.partners[3].id,
                    'notification_type': 'inbox',
                }),
                (0, 0, {
                    'res_partner_id': self.partners[4].id,
                    'notification_type': 'email',
                    'notification_status': 'exception',
                }),
                (0, 0, {
                    'res_partner_id': self.partners[6].id,
                    'notification_type': 'email',
                    'notification_status': 'exception',
                }),
            ],
            'tracking_value_ids': [
                (0, 0, {
                    'field': name_field.id,
                    'field_desc': 'Name',
                    'old_value_char': 'old 0',
                    'new_value_char': 'new 0',
                }),
                (0, 0, {
                    'field': customer_id_field.id,
                    'field_desc': 'Customer',
                    'old_value_integer': self.partners[7].id,
                    'new_value_integer': self.partners[8].id,
                }),
            ]
        }, {
            'subject': 'Test 1',
            'body': '<p>Test 1</p>',
            'author_id': self.partners[1].id,
            'email_from': self.partners[1].email,
            'model': 'mail.test.container',
            'res_id': self.container.id,
            'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
            'attachment_ids': [
                (0, 0, {
                    'name': 'test file 1 - %d' % j,
                    'datas': 'data',
                }) for j in range(2)
            ],
            'notification_ids': [
                (0, 0, {
                    'res_partner_id': self.partners[5].id,
                    'notification_type': 'inbox',
                }),
                (0, 0, {
                    'res_partner_id': self.partners[6].id,
                    'notification_type': 'email',
                    'notification_status': 'exception',
                }),
            ],
            'tracking_value_ids': [
                (0, 0, {
                    'field': name_field.id,
                    'field_desc': 'Name',
                    'old_value_char': 'old 1',
                    'new_value_char': 'new 1',
                }),
                (0, 0, {
                    'field': customer_id_field.id,
                    'field_desc': 'Customer',
                    'old_value_integer': self.partners[7].id,
                    'new_value_integer': self.partners[8].id,
                }),
            ]
        }])

        with self.assertQueryCount(employee=6):
            res = messages.message_format()
            self.assertEqual(len(res), 2)
            for message in res:
                self.assertEqual(len(message['attachment_ids']), 2)

        self.env.flush_all()
        self.env.invalidate_all()

        with self.assertQueryCount(employee=19):
            res = messages.message_format()
            self.assertEqual(len(res), 2)
            for message in res:
                self.assertEqual(len(message['attachment_ids']), 2)

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

        with self.assertQueryCount(employee=5):
            res = messages.message_format()
            self.assertEqual(len(res), 6)

        self.env.flush_all()
        self.env.invalidate_all()

        with self.assertQueryCount(employee=14):
            res = messages.message_format()
            self.assertEqual(len(res), 6)


@tagged('mail_performance', 'post_install', '-at_install')
class TestMailHeavyPerformancePost(BaseMailPerformance):

    def setUp(self):
        super(TestMailHeavyPerformancePost, self).setUp()

        # record
        self.record_container = self.env['mail.test.container'].with_context(mail_create_nosubscribe=True).create({
            'name': 'Test record',
            'customer_id': self.customer.id,
            'alias_name': 'test-alias',
        })
        # followers
        self.user_follower_email = self.env['res.users'].with_context(self._test_context).create({
            'name': 'user_follower_email',
            'login': 'user_follower_email',
            'email': 'user_follower_email@example.com',
            'notification_type': 'email',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        self.user_follower_inbox = self.env['res.users'].with_context(self._test_context).create({
            'name': 'user_follower_inbox',
            'login': 'user_follower_inbox',
            'email': 'user_follower_inbox@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        self.partner_follower = self.env['res.partner'].with_context(self._test_context).create({
            'name': 'partner_follower',
            'email': 'partner_follower@example.com',
        })
        self.record_container.message_subscribe([
            self.partner_follower.id,
            self.user_follower_inbox.partner_id.id,
            self.user_follower_email.partner_id.id
        ])

        # partner_ids
        self.user_inbox = self.env['res.users'].with_context(self._test_context).create({
            'name': 'user_inbox',
            'login': 'user_inbox',
            'email': 'user_inbox@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        self.user_email = self.env['res.users'].with_context(self._test_context).create({
            'name': 'user_email',
            'login': 'user_email',
            'email': 'user_email@example.com',
            'notification_type': 'email',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        self.partner = self.env['res.partner'].with_context(self._test_context).create({
            'name': 'partner',
            'email': 'partner@example.com',
        })

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('employee')
    @warmup
    def test_complete_message_post(self):
        # aims to cover as much features of message_post as possible
        recipients = self.user_inbox.partner_id + self.user_email.partner_id + self.partner
        record_container = self.record_container.with_user(self.env.user)
        attachments_vals = [  # not linear on number of attachments_vals
            ('attach tuple 1', "attachement tupple content 1"),
            ('attach tuple 2', "attachement tupple content 2", {'cid': 'cid1'}),
            ('attach tuple 3', "attachement tupple content 3", {'cid': 'cid2'}),
        ]
        attachments = self.env['ir.attachment'].with_user(self.env.user).create(self.test_attachments_vals)
        with self.assertQueryCount(employee=49):
            self.cr.sql_log = self.warm and self.cr.sql_log_count
            record_container.with_context({}).message_post(
                body='<p>Test body <img src="cid:cid1"> <img src="cid:cid2"></p>',
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
            self.cr.sql_log = False
        new_message = record_container.message_ids[0]
        self.assertEqual(attachments.mapped('res_model'), [record_container._name for i in range(3)])
        self.assertEqual(attachments.mapped('res_id'), [record_container.id for i in range(3)])
        self.assertTrue(new_message.body.startswith('<p>Test body <img src="/web/image/'))
        self.assertEqual(new_message.notified_partner_ids, recipients)
