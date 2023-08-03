# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import mute_logger


class TestMailAliasCommon(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._activate_multi_company()


@tagged('mail_gateway', 'mail_alias', 'multi_company')
class TestMailAlias(TestMailAliasCommon):
    """ Test alias model features, constraints and behavior. """

    def test_alias_domain_allowed_validation(self):
        """ Check the validation of `mail.catchall.domain.allowed` system parameter"""
        for value in [',', ',,', ', ,']:
            with self.assertRaises(exceptions.ValidationError,
                 msg="The value '%s' should not be allowed" % value):
                self.env['ir.config_parameter'].set_param('mail.catchall.domain.allowed', value)

        for value, expected in [
            ('', False),
            ('hello.com', 'hello.com'),
            ('hello.com,,', 'hello.com'),
            ('hello.com,bonjour.com', 'hello.com,bonjour.com'),
            ('hello.COM, BONJOUR.com', 'hello.com,bonjour.com'),
        ]:
            self.env['ir.config_parameter'].set_param('mail.catchall.domain.allowed', value)
            self.assertEqual(self.env['ir.config_parameter'].get_param('mail.catchall.domain.allowed'), expected)

    def test_alias_name_unique(self):
        alias_model_id = self.env['ir.model']._get('mail.test.gateway').id
        catchall_alias = self.env['ir.config_parameter'].sudo().get_param('mail.catchall.alias')
        bounce_alias = self.env['ir.config_parameter'].sudo().get_param('mail.bounce.alias')

        # test you cannot create aliases matching bounce / catchall
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            self.env['mail.alias'].create({'alias_model_id': alias_model_id, 'alias_name': catchall_alias})
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            self.env['mail.alias'].create({'alias_model_id': alias_model_id, 'alias_name': bounce_alias})

        new_mail_alias = self.env['mail.alias'].create({
            'alias_model_id': alias_model_id,
            'alias_name': 'unused.test.alias'
        })

        # test that re-using catchall and bounce alias raises UserError
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            new_mail_alias.write({
                'alias_name': catchall_alias
            })
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            new_mail_alias.write({
                'alias_name': bounce_alias
            })

        new_mail_alias.write({'alias_name': 'another.unused.test.alias'})

        # test that duplicating an alias should have blank name
        copy_new_mail_alias = new_mail_alias.copy()
        self.assertFalse(copy_new_mail_alias.alias_name)

        # cannot set catchall / bounce to used alias
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            self.env['ir.config_parameter'].sudo().set_param('mail.catchall.alias', new_mail_alias.alias_name)
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            self.env['ir.config_parameter'].sudo().set_param('mail.bounce.alias', new_mail_alias.alias_name)

    def test_alias_name_sanitize(self):
        alias = self.env['mail.alias'].create({
            'alias_model_id': self.env['ir.model']._get('mail.test.container').id,
            'alias_name': 'bidule...inc.',
        })
        self.assertEqual(alias.alias_name, 'bidule.inc', 'Emails cannot start or end with a dot, there cannot be a sequence of dots.')

        alias = self.env['mail.alias'].create({
            'alias_model_id': self.env['ir.model']._get('mail.test.container').id,
            'alias_name': 'b4r+_#_R3wl$$',
        })
        self.assertEqual(alias.alias_name, 'b4r+_-_r3wl-', 'Disallowed chars should be replaced by hyphens')

        with self.assertRaises(exceptions.ValidationError):
            alias.write({'alias_defaults': "{'custom_field': brokendict"})


@tagged('mail_gateway', 'mail_alias', 'multi_company')
class TestMailAliasMixin(TestMailAliasCommon):
    """ Test alias mixin implementation, synchornization of alias records
    based on owner records. """

    @users('employee')
    @mute_logger('odoo.addons.base.models.ir_model')
    def test_alias_creation(self):
        record = self.env['mail.test.container'].create({
            'name': 'Test Record',
            'alias_name': 'alias.test',
            'alias_contact': 'followers',
        })
        self.assertEqual(record.alias_id.alias_model_id, self.env['ir.model']._get('mail.test.container'))
        self.assertEqual(record.alias_id.alias_force_thread_id, record.id)
        self.assertEqual(record.alias_id.alias_parent_model_id, self.env['ir.model']._get('mail.test.container'))
        self.assertEqual(record.alias_id.alias_parent_thread_id, record.id)
        self.assertEqual(record.alias_id.alias_name, 'alias.test')
        self.assertEqual(record.alias_id.alias_contact, 'followers')

        record.write({
            'alias_name': 'better.alias.test',
            'alias_defaults': "{'default_name': 'defaults'}"
        })
        self.assertEqual(record.alias_id.alias_name, 'better.alias.test')
        self.assertEqual(record.alias_id.alias_defaults, "{'default_name': 'defaults'}")

        with self.assertRaises(exceptions.AccessError):
            record.write({
                'alias_force_thread_id': 0,
            })

        with self.assertRaises(exceptions.AccessError):
            record.write({
                'alias_model_id': self.env['ir.model']._get('mail.test.gateway').id,
            })

        with self.assertRaises(exceptions.ValidationError):
            record.write({'alias_defaults': "{'custom_field': brokendict"})

    @users('employee')
    def test_alias_mixin_copy_content(self):
        self.assertFalse(self.env.user.has_group('base.group_system'), 'Test user should not have Administrator access')

        record = self.env['mail.test.container'].create({
            'name': 'Test Record',
            'alias_name': 'test.record',
            'alias_contact': 'followers',
            'alias_bounced_content': False,
        })
        self.assertFalse(record.alias_bounced_content)
        record_copy = record.copy()
        self.assertFalse(record_copy.alias_bounced_content)

        new_content = '<p>Bounced Content</p>'
        record_copy.write({'alias_bounced_content': new_content})
        self.assertEqual(record_copy.alias_bounced_content, new_content)
        record_copy2 = record_copy.copy()
        self.assertEqual(record_copy2.alias_bounced_content, new_content)
