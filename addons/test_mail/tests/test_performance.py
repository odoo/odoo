# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from email.utils import formataddr

from odoo.tests.common import TransactionCase, users, warmup
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('mail_performance')
class TestMailPerformance(TransactionCase):

    def setUp(self):
        super(TestMailPerformance, self).setUp()
        self.user_employee = self.env['res.users'].with_context({
            'no_reset_password': True,
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'mail_notrack': True,
        }).create({
            'name': 'Ernest Employee',
            'login': 'emp',
            'email': 'e.e@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })

        # patch registry to simulate a ready environment
        self.patch(self.env.registry, 'ready', True)

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

        with self.assertQueryCount(__system__=5, demo=5):  # test_mail only: 5 - 5
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
        with self.assertQueryCount(__system__=13, demo=13):  # test_mail only: 13 - 13
            self.env['test_performance.mail'].create({'name': 'X'})

    @users('__system__', 'emp')
    @warmup
    def test_create_mail_simple(self):
        with self.assertQueryCount(__system__=8, emp=8):  # test_mail only: 8 - 8
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
class TestAdvMailPerformance(TransactionCase):

    def setUp(self):
        super(TestAdvMailPerformance, self).setUp()
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

        # patch registry to simulate a ready environment
        self.patch(self.env.registry, 'ready', True)

        # automatically follow activities, for backward compatibility concerning query count
        self.env.ref('mail.mt_activities').write({'default': True})

    @users('__system__', 'emp')
    @warmup
    def test_adv_activity(self):
        model = self.env['mail.test.activity']

        with self.assertQueryCount(__system__=9, emp=8):  # test_mail only: 9 - 8
            model.create({'name': 'Test'})

    @users('__system__', 'emp')
    @warmup
    @mute_logger('odoo.models.unlink')
    def test_adv_activity_full(self):
        record = self.env['mail.test.activity'].create({'name': 'Test'})
        MailActivity = self.env['mail.activity'].with_context({
            'default_res_model': 'mail.test.activity',
        })

        with self.assertQueryCount(__system__=10, emp=15):  # com runbot: 9 - 15 // test_mail only: 10 - 14
            activity = MailActivity.create({
                'summary': 'Test Activity',
                'res_id': record.id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            })
            #read activity_type to normalize cache between enterprise and community
            #voip module read activity_type during create leading to one less query in enterprise on action_feedback
            category = activity.activity_type_id.category

        with self.assertQueryCount(__system__=26, emp=46):  # com runbot: 25 - 46 // test_mail only: 26 - 46
            activity.action_feedback(feedback='Zizisse Done !')

    @users('__system__', 'emp')
    @warmup
    @mute_logger('odoo.models.unlink')
    def test_adv_activity_mixin(self):
        record = self.env['mail.test.activity'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=10, emp=15):  # com runbot: 9 - 15 // test_mail only: 10 - 14
            activity = record.action_start('Test Start')
            #read activity_type to normalize cache between enterprise and community
            #voip module read activity_type during create leading to one less query in enterprise on action_close
            category = activity.activity_type_id.category

        record.write({'name': 'Dupe write'})

        with self.assertQueryCount(__system__=28, emp=48):  # com runbot: 27 - 86 // test_mail only: 28 - 48
            record.action_close('Dupe feedback')

        self.assertEqual(record.activity_ids, self.env['mail.activity'])

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'emp')
    @warmup
    def test_message_assignation_email(self):
        self.user_test.write({'notification_type': 'email'})
        record = self.env['mail.test.track'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=58, emp=77):  # com runbot: 58 - 77 // test_mail only: 56 - 70
            record.write({
                'user_id': self.user_test.id,
            })

    @users('__system__', 'emp')
    @warmup
    def test_message_assignation_inbox(self):
        record = self.env['mail.test.track'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=36, emp=47):  # test_mail only: 36 - 43
            record.write({
                'user_id': self.user_test.id,
            })

    @users('__system__', 'emp')
    @warmup
    def test_message_log(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=2, emp=2):  # test_mail only: 2 - 2
            record._message_log(
                body='<p>Test _message_log</p>',
                message_type='comment')

    @users('__system__', 'emp')
    @warmup
    def test_message_log_with_post(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=7, emp=13):  # test_mail only: 7 - 13
            record.message_post(
                body='<p>Test message_post as log</p>',
                subtype='mail.mt_note',
                message_type='comment')

    @users('__system__', 'emp')
    @warmup
    def test_message_post_no_notification(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=7, emp=13):  # test_mail only: 7 - 13
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

        with self.assertQueryCount(__system__=50, emp=70):  # com runbot: 47 - 67 // test_mail only: 50 - 67
            record.message_post(
                body='<p>Test Post Performances with an email ping</p>',
                partner_ids=self.customer.ids,
                message_type='comment',
                subtype='mail.mt_comment')

    @users('__system__', 'emp')
    @warmup
    def test_message_post_one_inbox_notification(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})

        with self.assertQueryCount(__system__=31, emp=43):  # com runbot 30 - 42 // test_mail only: 31 - 43
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

        with self.assertQueryCount(__system__=7, emp=7):  # test_mail only: 7 - 7
            record.message_subscribe(partner_ids=self.user_test.partner_id.ids)

        with self.assertQueryCount(__system__=3, emp=3):  # test_mail only: 3 - 3
            record.message_subscribe(partner_ids=self.user_test.partner_id.ids)

    @mute_logger('odoo.models.unlink')
    @users('__system__', 'emp')
    @warmup
    def test_message_subscribe_subtypes(self):
        record = self.env['mail.test.simple'].create({'name': 'Test'})
        subtype_ids = (self.env.ref('test_mail.st_mail_test_simple_external') | self.env.ref('mail.mt_comment')).ids

        with self.assertQueryCount(__system__=6, emp=6):  # test_mail only: 6 - 6
            record.message_subscribe(partner_ids=self.user_test.partner_id.ids, subtype_ids=subtype_ids)

        with self.assertQueryCount(__system__=2, emp=2):  # test_mail only: 2 - 2
            record.message_subscribe(partner_ids=self.user_test.partner_id.ids, subtype_ids=subtype_ids)


@tagged('mail_performance')
class TestHeavyMailPerformance(TransactionCase):

    def setUp(self):
        super(TestHeavyMailPerformance, self).setUp()
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
        self.patch(self.env.registry, 'ready', True)

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

        with self.assertQueryCount(__system__=14, emp=21):  # test_mail only: 14 - 21
            self.env['mail.mail'].browse(mail_ids).send()

        self.assertEqual(mail.body_html, '<p>Test</p>')
        self.assertEqual(mail.reply_to, formataddr(('%s %s' % (self.env.user.company_id.name, self.umbrella.name), 'test-alias@example.com')))

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'emp')
    @warmup
    def test_complex_message_post(self):
        self.umbrella.message_subscribe(self.user_portal.partner_id.ids)
        record = self.umbrella.sudo(self.env.user)

        with self.assertQueryCount(__system__=84, emp=107):  # com runbot 81 - 104 // test_mail only: 84 - 104
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
        record = self.umbrella.sudo(self.env.user)
        template_id = self.env.ref('test_mail.mail_test_tpl').id

        with self.assertQueryCount(__system__=103, emp=138):  # com runbot 100 - 135 // test_mail only: 103 - 135
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
        with self.assertQueryCount(__system__=9, emp=9):  # test_mail only: 9 - 9
            rec.message_subscribe(
                partner_ids=pids[:4],
                channel_ids=cids,
                subtype_ids=subtype_ids
            )

        self.assertEqual(rec.message_partner_ids, self.env.user.partner_id | self.user_portal.partner_id | self.partners[:4])
        self.assertEqual(rec.message_channel_ids, self.channel)

        # subscribe existing and new followers with force=False, meaning only some new followers will be added
        with self.assertQueryCount(__system__=7, emp=7):  # test_mail only: 7 - 7
            rec.message_subscribe(
                partner_ids=pids[:6],
                channel_ids=cids,
                subtype_ids=None
            )

        self.assertEqual(rec.message_partner_ids, self.env.user.partner_id | self.user_portal.partner_id | self.partners[:6])
        self.assertEqual(rec.message_channel_ids, self.channel)

        # subscribe existing and new followers with force=True, meaning all will have the same subtypes
        with self.assertQueryCount(__system__=8, emp=8):  # test_mail only: 8 - 8
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

        with self.assertQueryCount(__system__=60, emp=79):  # com runbot: 60 - 75 // test_mail only: 60 - 72
            rec.write({'user_id': self.user_portal.id})

        self.assertEqual(rec.message_partner_ids, self.partners | self.env.user.partner_id | self.user_portal.partner_id)
        # write tracking message
        self.assertEqual(rec.message_ids[0].subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(rec.message_ids[0].needaction_partner_ids, self.env['res.partner'])
        # create tracking message
        self.assertEqual(rec.message_ids[1].subtype_id, self.env.ref('test_mail.st_mail_test_full_umbrella_upd'))
        self.assertEqual(rec.message_ids[1].needaction_partner_ids, self.partners)
        # creation message
        self.assertEqual(rec.message_ids[2].subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(rec.message_ids[2].needaction_partner_ids, self.env['res.partner'])

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('__system__', 'emp')
    @warmup
    def test_complex_tracking_subscription_create(self):
        """ Creation performance test involving auto subscription, assignation, tracking with subtype and template send. """
        umbrella_id = self.umbrella.id
        customer_id = self.customer.id
        user_id = self.user_portal.id

        with self.assertQueryCount(__system__=162, emp=198):  # com runbot: 161 - 198 // test_mail only: 161 - 191
            rec = self.env['mail.test.full'].create({
                'name': 'Test',
                'umbrella_id': umbrella_id,
                'customer_id': customer_id,
                'user_id': user_id,
            })

        self.assertEqual(rec.message_partner_ids, self.partners | self.env.user.partner_id | self.user_portal.partner_id)
        # create tracking message
        self.assertEqual(rec.message_ids[0].subtype_id, self.env.ref('test_mail.st_mail_test_full_umbrella_upd'))
        self.assertEqual(rec.message_ids[0].needaction_partner_ids, self.partners | self.user_portal.partner_id)
        # creation message
        self.assertEqual(rec.message_ids[1].subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(rec.message_ids[1].needaction_partner_ids, self.env['res.partner'])

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

        with self.assertQueryCount(__system__=99, emp=119):  # com runbot: 98 - 119 // test_mail only: 98 - 116
            rec.write({
                'name': 'Test2',
                'umbrella_id': self.umbrella.id,
                })

        self.assertEqual(rec.message_partner_ids, self.partners | self.env.user.partner_id | self.user_portal.partner_id)
        # write tracking message
        self.assertEqual(rec.message_ids[0].subtype_id, self.env.ref('test_mail.st_mail_test_full_umbrella_upd'))
        self.assertEqual(rec.message_ids[0].needaction_partner_ids, self.partners | self.user_portal.partner_id)
        # create tracking message
        self.assertEqual(rec.message_ids[1].subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(rec.message_ids[1].needaction_partner_ids, self.env['res.partner'])
        # creation message
        self.assertEqual(rec.message_ids[2].subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(rec.message_ids[2].needaction_partner_ids, self.env['res.partner'])

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

        with self.assertQueryCount(__system__=104, emp=126):  # test_mail only: 104 - 122
            rec.write({
                'name': 'Test2',
                'umbrella_id': umbrella_id,
                'customer_id': customer_id,
                })

        self.assertEqual(rec.message_partner_ids, self.partners | self.env.user.partner_id | self.user_portal.partner_id)
        # write tracking message
        self.assertEqual(rec.message_ids[0].subtype_id, self.env.ref('test_mail.st_mail_test_full_umbrella_upd'))
        self.assertEqual(rec.message_ids[0].needaction_partner_ids, self.partners | self.user_portal.partner_id)
        # create tracking message
        self.assertEqual(rec.message_ids[1].subtype_id, self.env.ref('test_mail.st_mail_test_full_umbrella_upd'))
        self.assertEqual(rec.message_ids[1].needaction_partner_ids, self.user_portal.partner_id)
        # creation message
        self.assertEqual(rec.message_ids[2].subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(rec.message_ids[2].needaction_partner_ids, self.env['res.partner'])

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

        with self.assertQueryCount(__system__=55, emp=75):  # test_mail only: 55 - 75
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
        # create tracking message
        self.assertEqual(rec.message_ids[2].subtype_id, self.env.ref('test_mail.st_mail_test_full_umbrella_upd'))
        self.assertEqual(rec.message_ids[2].needaction_partner_ids, self.partners | self.user_portal.partner_id)
        # creation message
        self.assertEqual(rec.message_ids[3].subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(rec.message_ids[3].needaction_partner_ids, self.env['res.partner'])
