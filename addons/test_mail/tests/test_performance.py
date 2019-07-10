# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from email.utils import formataddr

from odoo.tests.common import TransactionCase, users, warmup
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('mail_performance')
class BaseMailPerformance(TransactionCase):

    def setUp(self):
        super(BaseMailPerformance, self).setUp()
        self._quick_create_ctx = {
            'no_reset_password': True,
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'mail_notrack': True,
        }
        self.user_employee = self.env['res.users'].with_context(self._quick_create_ctx).create({
            'name': 'Ernest Employee',
            'login': 'emp',
            'email': 'e.e@example.com',
            'signature': '--\nErnest',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })

        # patch registry to simulate a ready environment
        self.patch(self.env.registry, 'ready', True)


@tagged('mail_performance')
class TestMailPerformance(BaseMailPerformance):

    @users('__system__', 'demo')
    @warmup
    def test_read_mail(self):
        """ Read records inheriting from 'mail.thread'. """
        records = self.env['test_performance.mail'].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(__system__=3, demo=3):
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
        records = self.env['test_performance.mail'].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(__system__=3, demo=3):  # test_mail only: 3 - 3
            records.write({'name': 'X'})

    @users('__system__', 'demo')
    @warmup
    def test_write_mail_with_recomputation(self):
        """ Write records inheriting from 'mail.thread' (with recomputation). """
        records = self.env['test_performance.mail'].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(__system__=5, demo=5):  # test_mail only: 5 - 5
            records.write({'value': 42})

    @users('__system__', 'demo')
    @warmup
    def test_write_mail_with_tracking(self):
        """ Write records inheriting from 'mail.thread' (with field tracking). """
        record = self.env['test_performance.mail'].create({
            'name': 'Test',
            'track': 'Y',
            'value': 40,
            'partner_id': self.env.ref('base.res_partner_12').id,
        })

        with self.assertQueryCount(__system__=4, demo=4):  # test_mail only: 4 - 4
            record.track = 'X'

    @users('__system__', 'demo')
    @warmup
    def test_create_mail(self):
        """ Create records inheriting from 'mail.thread' (without field tracking). """
        model = self.env['test_performance.mail']

        with self.assertQueryCount(__system__=3, demo=3):  # test_mail only: 3 - 3
            model.with_context(tracking_disable=True).create({'name': 'X'})

    @users('__system__', 'demo')
    @warmup
    def test_create_mail_with_tracking(self):
        """ Create records inheriting from 'mail.thread' (with field tracking). """
        with self.assertQueryCount(__system__=8, demo=8):  # test_mail only: 8 - 8
            self.env['test_performance.mail'].create({'name': 'X'})

    @users('__system__', 'emp')
    @warmup
    def test_create_mail_simple(self):
        with self.assertQueryCount(__system__=6, emp=6):  # test_mail only: 6 - 6
            self.env['mail.test.simple'].create({'name': 'Test'})

    @users('__system__', 'emp')
    @warmup
    def test_write_mail_simple(self):
        rec = self.env['mail.test.simple'].create({'name': 'Test'})
        with self.assertQueryCount(__system__=1, emp=1):  # test_mail only: 1 - 1
            rec.write({
                'name': 'Test2',
                'email_from': 'test@test.com',
            })


@tagged('mail_performance')
class TestAdvMailPerformance(BaseMailPerformance):

    def setUp(self):
        super(TestAdvMailPerformance, self).setUp()
        self.customer = self.env['res.partner'].with_context(self._quick_create_ctx).create({
            'name': 'Test Customer',
            'email': 'test@example.com',
        })
        self.user_test = self.env['res.users'].with_context(self._quick_create_ctx).create({
            'name': 'Paulette Testouille',
            'login': 'paul',
            'email': 'p.p@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })

        # automatically follow activities, for backward compatibility concerning query count
        self.env.ref('mail.mt_activities').write({'default': True})

    @users('__system__', 'emp')
    @warmup
    def test_adv_activity(self):
        model = self.env['mail.test.activity']

        with self.assertQueryCount(__system__=7, emp=6):  # test_mail only: 7 - 6
            model.create({'name': 'Test'})

    @users('__system__', 'emp')
    @warmup
    @mute_logger('odoo.models.unlink')
    def test_adv_activity_full(self):
        record = self.env['mail.test.activity'].create({'name': 'Test'})
        MailActivity = self.env['mail.activity'].with_context({
            'default_res_model': 'mail.test.activity',
        })

        with self.assertQueryCount(__system__=10, emp=13):  # com runbot: 10 - 13 // test_mail only: 10 - 13
            activity = MailActivity.create({
                'summary': 'Test Activity',
                'res_id': record.id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            })
            #read activity_type to normalize cache between enterprise and community
            #voip module read activity_type during create leading to one less query in enterprise on action_feedback
            category = activity.activity_type_id.category

        with self.assertQueryCount(__system__=24, emp=31):  # com runbot: 24 - 31 // test_mail only: 24 - 31
            activity.action_feedback(feedback='Zizisse Done !')

    @users('__system__', 'emp')
    @warmup
    @mute_logger('odoo.models.unlink')
    def test_adv_activity_mixin(self):
        record = self.env['mail.test.activity'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=10, emp=14):  # com runbot: 10 - 14 // test_mail only: 10 - 14
            activity = record.action_start('Test Start')
            #read activity_type to normalize cache between enterprise and community
            #voip module read activity_type during create leading to one less query in enterprise on action_close
            category = activity.activity_type_id.category

        record.write({'name': 'Dupe write'})

        with self.assertQueryCount(__system__=26, emp=31):  # com runbot: 26 - 31 // test_mail only: 26 - 31
            record.action_close('Dupe feedback')

        self.assertEqual(record.activity_ids, self.env['mail.activity'])

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'emp')
    @warmup
    def test_message_assignation_email(self):
        self.user_test.write({'notification_type': 'email'})
        record = self.env['mail.test.track'].create({'name': 'Test'})
        with self.assertQueryCount(__system__=55, emp=58):  # com runbot: 55 - 58 // test_mail only: 55 - 58
            record.write({
                'user_id': self.user_test.id,
            })

    @users('__system__', 'emp')
    @warmup
    def test_message_assignation_inbox(self):
        record = self.env['mail.test.track'].create({'name': 'Test'})
        with self.assertQueryCount(__system__=33, emp=39):  # test_mail only: 33 - 39
            record.write({
                'user_id': self.user_test.id,
            })

    @users('__system__', 'emp')
    @warmup
    def test_message_log(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=1, emp=1):  # test_mail only: 1 - 1
            record._message_log(
                body='<p>Test _message_log</p>',
                message_type='comment')

    @users('__system__', 'emp')
    @warmup
    def test_message_log_with_post(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=6, emp=7):  # test_mail only: 6 - 7
            record.message_post(
                body='<p>Test message_post as log</p>',
                subtype='mail.mt_note',
                message_type='comment')

    @users('__system__', 'emp')
    @warmup
    def test_message_post_no_notification(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=6, emp=7):  # test_mail only: 6 - 7
            record.message_post(
                body='<p>Test Post Performances basic</p>',
                partner_ids=[],
                message_type='comment',
                subtype='mail.mt_comment')

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'emp')
    @warmup
    def test_message_post_one_email_notification(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=47, emp=51):  # com runbot: 47 - 51 // test_mail only: 47 - 51
            record.message_post(
                body='<p>Test Post Performances with an email ping</p>',
                partner_ids=self.customer.ids,
                message_type='comment',
                subtype='mail.mt_comment')

    @users('__system__', 'emp')
    @warmup
    def test_message_post_one_inbox_notification(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=30, emp=36):  # com runbot 30 - 36 // test_mail only: 30 - 36
            record.message_post(
                body='<p>Test Post Performances with an inbox ping</p>',
                partner_ids=self.user_test.partner_id.ids,
                message_type='comment',
                subtype='mail.mt_comment')

    @mute_logger('odoo.models.unlink')
    @users('__system__', 'emp')
    @warmup
    def test_message_subscribe_default(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=6, emp=6):  # test_mail only: 6 - 6
            record.message_subscribe(partner_ids=self.user_test.partner_id.ids)

        with self.assertQueryCount(__system__=3, emp=3):  # test_mail only: 3 - 3
            record.message_subscribe(partner_ids=self.user_test.partner_id.ids)

    @mute_logger('odoo.models.unlink')
    @users('__system__', 'emp')
    @warmup
    def test_message_subscribe_subtypes(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})
        subtype_ids = (self.env.ref('test_mail.st_mail_test_simple_external') | self.env.ref('mail.mt_comment')).ids

        with self.assertQueryCount(__system__=5, emp=5):  # test_mail only: 5 - 5
            record.message_subscribe(partner_ids=self.user_test.partner_id.ids, subtype_ids=subtype_ids)

        with self.assertQueryCount(__system__=2, emp=2):  # test_mail only: 2 - 2
            record.message_subscribe(partner_ids=self.user_test.partner_id.ids, subtype_ids=subtype_ids)


@tagged('mail_performance')
class TestHeavyMailPerformance(BaseMailPerformance):

    def setUp(self):
        super(TestHeavyMailPerformance, self).setUp()
        self.user_portal = self.env['res.users'].with_context(self._quick_create_ctx).create({
            'name': 'Olivia Portal',
            'login': 'port',
            'email': 'p.p@example.com',
            'signature': '--\nOlivia',
            'notification_type': 'email',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        })

        self.admin = self.env.user

        # setup mail gateway
        self.env['ir.config_parameter'].sudo().set_param('mail.catchall.domain', 'example.com')
        self.env['ir.config_parameter'].sudo().set_param('mail.catchall.alias', 'test-catchall')
        self.env['ir.config_parameter'].sudo().set_param('mail.bounce.alias', 'test-bounce')

        self.channel = self.env['mail.channel'].with_context(self._quick_create_ctx).create({
            'name': 'Listener',
        })

        # prepare recipients to test for more realistic workload
        self.customer = self.env['res.partner'].with_context(self._quick_create_ctx).create({
            'name': 'Test Customer',
            'email': 'test@example.com'
        })
        self.umbrella = self.env['mail.test'].with_context(mail_create_nosubscribe=True).create({
            'name': 'Test Umbrella',
            'customer_id': self.customer.id,
            'alias_name': 'test-alias',
        })
        Partners = self.env['res.partner'].with_context(self._quick_create_ctx)
        self.partners = self.env['res.partner']
        for x in range(0, 10):
            self.partners |= Partners.create({'name': 'Test %s' % x, 'email': 'test%s@example.com' % x})
        self.umbrella.message_subscribe(self.partners.ids, subtype_ids=[
            self.env.ref('mail.mt_comment').id,
            self.env.ref('test_mail.st_mail_test_child_full').id]
        )

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'emp')
    @warmup
    def test_complex_mail_mail_send(self):
        message = self.env['mail.message'].sudo().create({
            'subject': 'Test',
            'body': '<p>Test</p>',
            'author_id': self.env.user.partner_id.id,
            'email_from': self.env.user.partner_id.email,
            'model': 'mail.test',
            'res_id': self.umbrella.id,
        })
        mail = self.env['mail.mail'].sudo().create({
            'body_html': '<p>Test</p>',
            'mail_message_id': message.id,
            'recipient_ids': [(4, pid) for pid in self.partners.ids],
        })
        mail_ids = mail.ids
        with self.assertQueryCount(__system__=16, emp=21):  # test_mail only: 16 - 21
            self.env['mail.mail'].browse(mail_ids).send()

        self.assertEqual(mail.body_html, '<p>Test</p>')
        self.assertEqual(mail.reply_to, formataddr(('%s %s' % (self.env.company.name, self.umbrella.name), 'test-alias@example.com')))

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'emp')
    @warmup
    def test_complex_message_post(self):
        self.umbrella.message_subscribe(self.user_portal.partner_id.ids)
        record = self.umbrella.with_user(self.env.user)

        with self.assertQueryCount(__system__=78, emp=82):  # com runbot: 78 - 82 // test_mail only: 78 - 82
            record.message_post(
                body='<p>Test Post Performances</p>',
                message_type='comment',
                subtype='mail.mt_comment')

        self.assertEqual(record.message_ids[0].body, '<p>Test Post Performances</p>')
        self.assertEqual(record.message_ids[0].needaction_partner_ids, self.partners | self.user_portal.partner_id)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'emp')
    @warmup
    def test_complex_message_post_template(self):
        self.umbrella.message_subscribe(self.user_portal.partner_id.ids)
        record = self.umbrella.with_user(self.env.user)
        template_id = self.env.ref('test_mail.mail_test_tpl').id

        with self.assertQueryCount(__system__=93, emp=99):  # com runbot: 93 - 99 // test_mail only: 93 - 99
            record.message_post_with_template(template_id, message_type='comment', composition_mode='comment')

        self.assertEqual(record.message_ids[0].body, '<p>Adding stuff on %s</p>' % record.name)
        self.assertEqual(record.message_ids[0].needaction_partner_ids, self.partners | self.user_portal.partner_id | self.customer)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'emp')
    @warmup
    def test_complex_message_subscribe(self):
        pids = self.partners.ids
        cids = self.channel.ids
        subtypes = self.env.ref('mail.mt_comment') | self.env.ref('test_mail.st_mail_test_full_umbrella_upd')
        subtype_ids = subtypes.ids
        rec = self.env['mail.test.full'].create({
            'name': 'Test',
            'umbrella_id': False,
            'customer_id': False,
            'user_id': self.user_portal.id,
        })

        self.assertEqual(rec.message_partner_ids, self.env.user.partner_id | self.user_portal.partner_id)
        self.assertEqual(rec.message_channel_ids, self.env['mail.channel'])

        # subscribe new followers with forced given subtypes
        with self.assertQueryCount(__system__=8, emp=8):  # test_mail only: 8 - 8
            rec.message_subscribe(
                partner_ids=pids[:4],
                channel_ids=cids,
                subtype_ids=subtype_ids
            )

        self.assertEqual(rec.message_partner_ids, self.env.user.partner_id | self.user_portal.partner_id | self.partners[:4])
        self.assertEqual(rec.message_channel_ids, self.channel)

        # subscribe existing and new followers with force=False, meaning only some new followers will be added
        with self.assertQueryCount(__system__=6, emp=6):  # test_mail only: 6 - 6
            rec.message_subscribe(
                partner_ids=pids[:6],
                channel_ids=cids,
                subtype_ids=None
            )

        self.assertEqual(rec.message_partner_ids, self.env.user.partner_id | self.user_portal.partner_id | self.partners[:6])
        self.assertEqual(rec.message_channel_ids, self.channel)

        # subscribe existing and new followers with force=True, meaning all will have the same subtypes
        with self.assertQueryCount(__system__=7, emp=7):  # test_mail only: 7 - 7
            rec.message_subscribe(
                partner_ids=pids,
                channel_ids=cids,
                subtype_ids=subtype_ids
            )

        self.assertEqual(rec.message_partner_ids, self.env.user.partner_id | self.user_portal.partner_id | self.partners)
        self.assertEqual(rec.message_channel_ids, self.channel)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'emp')
    @warmup
    def test_complex_tracking_assignation(self):
        """ Assignation performance test on already-created record """
        rec = self.env['mail.test.full'].create({
            'name': 'Test',
            'umbrella_id': self.umbrella.id,
            'customer_id': self.customer.id,
            'user_id': self.env.uid,
        })
        self.assertEqual(rec.message_partner_ids, self.partners | self.env.user.partner_id)
        with self.assertQueryCount(__system__=54, emp=57):  # com runbot: 54 - 57 // test_mail only: 54 - 57
            rec.write({'user_id': self.user_portal.id})
        self.assertEqual(rec.message_partner_ids, self.partners | self.env.user.partner_id | self.user_portal.partner_id)
        # write tracking message
        self.assertEqual(rec.message_ids[0].subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(rec.message_ids[0].needaction_partner_ids, self.env['res.partner'])
        # creation message
        self.assertEqual(rec.message_ids[1].subtype_id, self.env.ref('test_mail.st_mail_test_full_umbrella_upd'))
        self.assertEqual(rec.message_ids[1].needaction_partner_ids, self.partners)
        self.assertEqual(len(rec.message_ids), 2)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'emp')
    @warmup
    def test_complex_tracking_subscription_create(self):
        """ Creation performance test involving auto subscription, assignation, tracking with subtype and template send. """
        umbrella_id = self.umbrella.id
        customer_id = self.customer.id
        user_id = self.user_portal.id

        with self.assertQueryCount(__system__=145, emp=149):  # com runbot: 145 - 149 // test_mail only: 145 - 149
            rec = self.env['mail.test.full'].create({
                'name': 'Test',
                'umbrella_id': umbrella_id,
                'customer_id': customer_id,
                'user_id': user_id,
            })

        self.assertEqual(rec.message_partner_ids, self.partners | self.env.user.partner_id | self.user_portal.partner_id)
        # creation message
        self.assertEqual(rec.message_ids[0].subtype_id, self.env.ref('test_mail.st_mail_test_full_umbrella_upd'))
        self.assertEqual(rec.message_ids[0].needaction_partner_ids, self.partners | self.user_portal.partner_id)
        self.assertEqual(len(rec.message_ids), 1)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'emp')
    @warmup
    def test_complex_tracking_subscription_subtype(self):
        """ Write performance test involving auto subscription, tracking with subtype """
        rec = self.env['mail.test.full'].create({
            'name': 'Test',
            'umbrella_id': False,
            'customer_id': False,
            'user_id': self.user_portal.id,
        })
        self.assertEqual(rec.message_partner_ids, self.user_portal.partner_id | self.env.user.partner_id)
        self.assertEqual(len(rec.message_ids), 1)
        with self.assertQueryCount(__system__=95, emp=100):  # com runbot: 95 - 100 // test_mail only: 95 - 100
            rec.write({
                'name': 'Test2',
                'umbrella_id': self.umbrella.id,
                })

        self.assertEqual(rec.message_partner_ids, self.partners | self.env.user.partner_id | self.user_portal.partner_id)
        # write tracking message
        self.assertEqual(rec.message_ids[0].subtype_id, self.env.ref('test_mail.st_mail_test_full_umbrella_upd'))
        self.assertEqual(rec.message_ids[0].needaction_partner_ids, self.partners | self.user_portal.partner_id)
        # creation message
        self.assertEqual(rec.message_ids[1].subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(rec.message_ids[1].needaction_partner_ids, self.env['res.partner'])
        self.assertEqual(len(rec.message_ids), 2)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'emp')
    @warmup
    def test_complex_tracking_subscription_write(self):
        """ Write performance test involving auto subscription, tracking with subtype and template send """
        umbrella_id = self.umbrella.id
        customer_id = self.customer.id
        umbrella2 = self.env['mail.test'].with_context(mail_create_nosubscribe=True).create({
            'name': 'Test Umbrella 2',
            'customer_id': False,
            'alias_name': False,
        })

        rec = self.env['mail.test.full'].create({
            'name': 'Test',
            'umbrella_id': umbrella2.id,
            'customer_id': False,
            'user_id': self.user_portal.id,
        })
        self.assertEqual(rec.message_partner_ids, self.user_portal.partner_id | self.env.user.partner_id)

        with self.assertQueryCount(__system__=100, emp=105):  # test_mail only: 100 - 105
            rec.write({
                'name': 'Test2',
                'umbrella_id': umbrella_id,
                'customer_id': customer_id,
                })

        self.assertEqual(rec.message_partner_ids, self.partners | self.env.user.partner_id | self.user_portal.partner_id)
        # write tracking message
        self.assertEqual(rec.message_ids[0].subtype_id, self.env.ref('test_mail.st_mail_test_full_umbrella_upd'))
        self.assertEqual(rec.message_ids[0].needaction_partner_ids, self.partners | self.user_portal.partner_id)
        # creation message
        self.assertEqual(rec.message_ids[1].subtype_id, self.env.ref('test_mail.st_mail_test_full_umbrella_upd'))
        self.assertEqual(rec.message_ids[1].needaction_partner_ids, self.user_portal.partner_id)
        self.assertEqual(len(rec.message_ids), 2)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'emp')
    @warmup
    def test_complex_tracking_template(self):
        """ Write performance test involving assignation, tracking with template """
        customer_id = self.customer.id
        self.assertTrue(self.env.registry.ready, "We need to simulate that registery is ready")
        rec = self.env['mail.test.full'].create({
            'name': 'Test',
            'umbrella_id': self.umbrella.id,
            'customer_id': False,
            'user_id': self.user_portal.id,
            'mail_template': self.env.ref('test_mail.mail_test_full_tracking_tpl').id,
        })
        self.assertEqual(rec.message_partner_ids, self.partners | self.env.user.partner_id | self.user_portal.partner_id)

        with self.assertQueryCount(__system__=50, emp=63):  # test_mail only: 50 - 63
            rec.write({
                'name': 'Test2',
                'customer_id': customer_id,
                'user_id': self.env.uid,
            })

        # write template message (sent to customer, mass mailing kept for history)
        self.assertEqual(rec.message_ids[0].subtype_id, self.env['mail.message.subtype'])
        self.assertEqual(rec.message_ids[0].subject, 'Test Template')
        # write tracking message
        self.assertEqual(rec.message_ids[1].subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(rec.message_ids[1].needaction_partner_ids, self.env['res.partner'])
        # creation message
        self.assertEqual(rec.message_ids[2].subtype_id, self.env.ref('test_mail.st_mail_test_full_umbrella_upd'))
        self.assertEqual(rec.message_ids[2].needaction_partner_ids, self.partners | self.user_portal.partner_id)
        self.assertEqual(len(rec.message_ids), 3)


@tagged('mail_performance')
class TestMailPerformancePost(BaseMailPerformance):

    def setUp(self):
        super(TestMailPerformancePost, self).setUp()

        # record
        self.customer = self.env['res.partner'].with_context(self._quick_create_ctx).create({
            'name': 'customer',
            'email': 'customer@example.com',
        })
        self.record = self.env['mail.test'].with_context(mail_create_nosubscribe=True).create({
            'name': 'Test record',
            'customer_id': self.customer.id,
            'alias_name': 'test-alias',
        })
        # followers
        self.user_follower_email = self.env['res.users'].with_context(self._quick_create_ctx).create({
            'name': 'user_follower_email',
            'login': 'user_follower_email',
            'email': 'user_follower_email@example.com',
            'notification_type': 'email',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        self.user_follower_inbox = self.env['res.users'].with_context(self._quick_create_ctx).create({
            'name': 'user_follower_inbox',
            'login': 'user_follower_inbox',
            'email': 'user_follower_inbox@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        self.partner_follower = self.env['res.partner'].with_context(self._quick_create_ctx).create({
            'name': 'partner_follower',
            'email': 'partner_follower@example.com',
        })
        self.record.message_subscribe([
            self.partner_follower.id,
            self.user_follower_inbox.partner_id.id,
            self.user_follower_email.partner_id.id
        ])

        # partner_ids
        self.user_inbox = self.env['res.users'].with_context(self._quick_create_ctx).create({
            'name': 'user_inbox',
            'login': 'user_inbox',
            'email': 'user_inbox@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        self.user_email = self.env['res.users'].with_context(self._quick_create_ctx).create({
            'name': 'user_email',
            'login': 'user_email',
            'email': 'user_email@example.com',
            'notification_type': 'email',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        self.partner = self.env['res.partner'].with_context(self._quick_create_ctx).create({
            'name': 'partner',
            'email': 'partner@example.com',
        })
        # channels user/partner
        self.partner_channel_inbox = self.env['res.partner'].with_context(self._quick_create_ctx).create({
            'name': 'partner_channel_inbox',
            'email': 'partner_channel_inbox@example.com',
        })
        self.partner_channel_email = self.env['res.partner'].with_context(self._quick_create_ctx).create({
            'name': 'partner_channel_email',
            'email': 'partner_channel_email@example.com',
        })
        self.user_channel_inbox = self.env['res.users'].with_context(self._quick_create_ctx).create({
            'name': 'user_channel_inbox',
            'login': 'user_channel_inbox',
            'email': 'user_channel_inbox@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        self.user_channel_email = self.env['res.users'].with_context(self._quick_create_ctx).create({
            'name': 'user_channel_email',
            'login': 'user_channel_email',
            'email': 'user_channel_email@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        # channels
        self.channel_inbox = self.env['mail.channel'].with_context(self._quick_create_ctx).create({
            'name': 'channel_inbox',
            'channel_partner_ids': [(4, self.partner_channel_inbox.id), (4, self.user_channel_inbox.partner_id.id)]
        })
        self.channel_email = self.env['mail.channel'].with_context(self._quick_create_ctx).create({
            'name': 'channel_email',
            'email_send': True,
            'channel_partner_ids': [(4, self.partner_channel_email.id), (4, self.user_channel_email.partner_id.id)]
        })
        self.vals = [{
            'datas': base64.b64encode(bytes("attachement content %s" % i, 'utf-8')),
            'name': 'fileText_test%s.txt' % i,
            'mimetype': 'text/plain',
            'res_model': 'mail.compose.message',
            'res_id': 0,
        } for i in range(3)]

        self.patch(self.env.registry, 'ready', True)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('emp')
    @warmup
    def test_complete_message_post(self):
        # aims to cover as much features of message_post as possible
        partner_ids = [self.user_inbox.partner_id.id, self.user_email.partner_id.id, self.partner.id]
        channel_ids = [self.channel_inbox.id, self.channel_email.id]
        record = self.record.with_user(self.env.user)
        attachements = [ # not linear on number of attachements
            ('attach tuple 1', "attachement tupple content 1"),
            ('attach tuple 2', "attachement tupple content 2", {'cid': 'cid1'}),
            ('attach tuple 3', "attachement tupple content 3", {'cid': 'cid2'}),
        ]
        self.attachements = self.env['ir.attachment'].with_user(self.env.user).create(self.vals) #-> 163-> 165 query
        attachement_ids = self.attachements.ids
        with self.assertQueryCount(emp=175):  # com runbot 154 // test_mail only: 133
            self.cr.sql_log = self.warm and self.cr.sql_log_count
            record.with_context({}).message_post(
                body='<p>Test body <img src="cid:cid1"> <img src="cid:cid2"></p>',
                subject='Test Subject',
                message_type='notification',
                subtype=None,
                partner_ids=partner_ids,
                channel_ids=channel_ids,
                parent_id=False,
                attachments=attachements,
                attachment_ids=attachement_ids,
                add_sign=True,
                model_description=False,
                mail_auto_delete=True
            )
            self.cr.sql_log = False
        self.assertTrue(record.message_ids[0].body.startswith('<p>Test body <img src="/web/image/'))
        self.assertEqual(self.attachements.mapped('res_model'), [record._name for i in range(3)])
        self.assertEqual(self.attachements.mapped('res_id'), [record.id for i in range(3)])
        # self.assertEqual(record.message_ids[0].needaction_partner_ids, [])
