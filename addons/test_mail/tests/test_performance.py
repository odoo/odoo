# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from email.utils import formataddr

from odoo.tests.common import TransactionCase, users, warmup
from odoo.tools import mute_logger


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

    @users('admin', 'demo')
    @warmup
    def test_read_mail(self):
        """ Read records inheriting from 'mail.thread'. """
        records = self.env['test_performance.mail'].search([])
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
        records = self.env['test_performance.mail'].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(admin=3, demo=3):  # test_mail only: 3 - 3
            records.write({'name': 'X'})

    @users('admin', 'demo')
    @warmup
    def test_write_mail_with_recomputation(self):
        """ Write records inheriting from 'mail.thread' (with recomputation). """
        records = self.env['test_performance.mail'].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(admin=5, demo=5):  # test_mail only: 5 - 5
            records.write({'value': 42})

    @users('admin', 'demo')
    @warmup
    def test_write_mail_with_tracking(self):
        """ Write records inheriting from 'mail.thread' (with field tracking). """
        record = self.env['test_performance.mail'].create({
            'name': 'Test',
            'track': 'Y',
            'value': 40,
            'partner_id': self.env.ref('base.res_partner_12').id,
        })

        with self.assertQueryCount(admin=32, demo=44):  # test_mail only: 30 - 41
            record.track = 'X'

    @users('admin', 'demo')
    @warmup
    def test_create_mail(self):
        """ Create records inheriting from 'mail.thread' (without field tracking). """
        model = self.env['test_performance.mail']

        with self.assertQueryCount(admin=3, demo=3):  # test_mail only: 3 - 3
            model.with_context(tracking_disable=True).create({'name': 'X'})

    @users('admin', 'demo')
    @warmup
    def test_create_mail_with_tracking(self):
        """ Create records inheriting from 'mail.thread' (with field tracking). """
        with self.assertQueryCount(admin=62, demo=84):  # test_mail only: 58 - 78
            self.env['test_performance.mail'].create({'name': 'X'})

    @users('admin', 'emp')
    @warmup
    def test_create_mail_simple(self):
        with self.assertQueryCount(admin=32, emp=42):  # test_mail only: 30 - 39
            self.env['mail.test.simple'].create({'name': 'Test'})


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

    @users('admin', 'emp')
    @warmup
    def test_adv_activity(self):
        model = self.env['mail.test.activity']

        with self.assertQueryCount(admin=35, emp=45):  # test_mail only: 33 - 42
            model.create({'name': 'Test'})

    @users('admin', 'emp')
    @warmup
    @mute_logger('odoo.models.unlink')
    def test_adv_activity_full(self):
        record = self.env['mail.test.activity'].create({'name': 'Test'})
        model = self.env['mail.activity'].with_context({
            'default_res_model': 'mail.test.activity',
        })

        with self.assertQueryCount(admin=47, emp=52):  # com runbot 46 - 51 // test_mail only: 35 - 40
            model.create({
                'summary': 'Test Activity',
                'res_id': record.id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            })


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
        self.admin.login = 'admin'

        # setup mail gateway
        self.env['ir.config_parameter'].sudo().set_param('mail.catchall.domain', 'example.com')
        self.env['ir.config_parameter'].sudo().set_param('mail.catchall.alias', 'test-catchall')
        self.env['ir.config_parameter'].sudo().set_param('mail.bounce.alias', 'test-bounce')

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
    @users('admin', 'emp')
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

        with self.assertQueryCount(admin=17, emp=25):  # com runbot 17 - 25 // test_mail only: 15 - 23
            self.env['mail.mail'].browse(mail_ids).send()

        self.assertEqual(mail.body_html, '<p>Test</p>')
        self.assertEqual(mail.reply_to, formataddr(('%s %s' % (self.env.user.company_id.name, self.umbrella.name), 'test-alias@example.com')))

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('admin', 'emp')
    @warmup
    def test_complex_message_post(self):
        self.umbrella.message_subscribe(self.user_portal.partner_id.ids)
        record = self.umbrella.sudo(self.env.user)

        with self.assertQueryCount(admin=131, emp=163):  # com runbot 129 - 161 // test_mail only: 125 - 156
            record.message_post(
                body='<p>Test Post Performances</p>',
                message_type='comment',
                subtype='mail.mt_comment')

        self.assertEqual(record.message_ids[0].body, '<p>Test Post Performances</p>')
        self.assertEqual(record.message_ids[0].needaction_partner_ids, self.partners | self.user_portal.partner_id)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('admin', 'emp')
    @warmup
    def test_complex_message_post_template(self):
        self.umbrella.message_subscribe(self.user_portal.partner_id.ids)
        record = self.umbrella.sudo(self.env.user)
        template_id = self.env.ref('test_mail.mail_test_tpl').id

        with self.assertQueryCount(admin=192, emp=239):  # com runbot 190 - 237 // test_mail only: 182 - 227
            record.message_post_with_template(template_id, message_type='comment', composition_mode='comment')

        self.assertEqual(record.message_ids[0].body, '<p>Adding stuff on %s</p>' % record.name)
        self.assertEqual(record.message_ids[0].needaction_partner_ids, self.partners | self.user_portal.partner_id | self.customer)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('admin', 'emp')
    @warmup
    def test_complex_create_tracking_subscription(self):
        """ Create record using most features: auto subscription, tracking
        and templates. """
        umbrella_id = self.umbrella.id
        customer_id = self.customer.id
        user_id = self.user_portal.id

        with self.assertQueryCount(admin=355, emp=428):  # test_mail only: 337 - 407
            rec = self.env['mail.test.full'].create({
                'name': 'Test',
                'umbrella_id': umbrella_id,
                'customer_id': customer_id,
                'user_id': user_id,
            })

        self.assertEqual(rec.message_partner_ids, self.partners | self.env.user.partner_id | self.user_portal.partner_id)
        # tracking message
        self.assertEqual(rec.message_ids[0].subtype_id, self.env.ref('test_mail.st_mail_test_full_umbrella_upd'))
        self.assertEqual(rec.message_ids[0].needaction_partner_ids, self.partners | self.user_portal.partner_id)
        # creation message
        self.assertEqual(rec.message_ids[1].subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(rec.message_ids[1].needaction_partner_ids, self.env['res.partner'])
