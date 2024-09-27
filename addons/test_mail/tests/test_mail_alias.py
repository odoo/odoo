# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2

from ast import literal_eval

from odoo import exceptions
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import formataddr, mute_logger


class TestMailAliasCommon(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_alias_mc = cls.env['mail.alias'].create({
            'alias_domain_id': cls.mail_alias_domain.id,
            'alias_model_id': cls.env['ir.model']._get('mail.test.container.mc').id,
            'alias_name': 'test.alias',
        })


@tagged('mail_gateway', 'mail_alias', 'multi_company')
class TestMailAlias(TestMailAliasCommon):
    """ Test alias model features, constraints and behavior. """

    @users('admin')
    def test_alias_domain_allowed_validation(self):
        """ Check the validation of `mail.catchall.domain.allowed` system parameter"""
        for value in [',', ',,', ', ,']:
            with self.assertRaises(exceptions.ValidationError):
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

    @users('erp_manager')
    def test_alias_domain_company_check(self):
        """ Check constraint trying to avoid ill-defined company setup aka
        having an alias domain on parent record / record to update that does
        not match the alias domain. """
        misc_alias_domain = self.env['mail.alias.domain'].create({'name': 'misc.com'})
        record_mc_c1, record_mc_c2 = self.env['mail.test.container.mc'].create([
            {
                'alias_name': 'Test1',
                'company_id': self.company_admin.id,
            }, {
                'alias_name': 'Test2',
                'company_id': self.company_2.id,
            }
        ])
        alias_mc_c1, alias_mc_c2 = record_mc_c1.alias_id, record_mc_c2.alias_id
        self.assertEqual(
            (alias_mc_c1 + alias_mc_c2).alias_parent_model_id,
            self.env['ir.model']._get('mail.test.container.mc'))
        self.assertEqual(
            (alias_mc_c1 + alias_mc_c2).mapped('alias_parent_thread_id'),
            (record_mc_c1 + record_mc_c2).ids)
        self.assertEqual(alias_mc_c1.alias_domain_id, self.mail_alias_domain)
        self.assertEqual(alias_mc_c2.alias_domain_id, self.mail_alias_domain_c2)

        # mail_alias_domain_c2 is linked to a conflicting company
        with self.assertRaises(exceptions.ValidationError):
            record_mc_c1.alias_domain_id = self.mail_alias_domain_c2
        with self.assertRaises(exceptions.ValidationError):
            alias_mc_c1.sudo().alias_domain_id = self.mail_alias_domain_c2
        # misc_alias_domain is not linked to any company, therefore ok
        record_mc_c1.alias_domain_id = misc_alias_domain

        # alias updating records
        record_upd_c1, record_upd_c2 = self.env['mail.test.alias.optional'].sudo().create([
            {
                'alias_name': 'Update C1',
                'company_id': self.company_admin.id,
            }, {
                'alias_name': 'Update C2',
                'company_id': self.company_2.id,
            }
        ])
        alias_update_c1, alias_update_c2 = record_upd_c1.alias_id, record_upd_c2.alias_id
        self.assertEqual(
            (alias_update_c1 + alias_update_c2).mapped('alias_force_thread_id'),
            (record_upd_c1 + record_upd_c2).ids)
        self.assertEqual(alias_update_c1.alias_domain_id, self.mail_alias_domain)
        self.assertEqual(alias_update_c2.alias_domain_id, self.mail_alias_domain_c2)

        # mail_alias_domain_c2 is linked to a conflicting company
        with self.assertRaises(exceptions.ValidationError):
            record_upd_c1.alias_domain_id = self.mail_alias_domain_c2
        with self.assertRaises(exceptions.ValidationError):
            alias_update_c1.sudo().alias_domain_id = self.mail_alias_domain_c2
        # misc_alias_domain is not linked to any company, therefore ok
        record_upd_c1.alias_domain_id = misc_alias_domain

    @users('admin')
    def test_alias_name_unique(self):
        """ Check uniqueness constraint on alias names, at create and update.
        Also check conflict management with bounce / catchall defined on
        alias domains. """
        mail_alias_domain = self.mail_alias_domain.with_env(self.env)
        mail_alias_domain_c2 = self.mail_alias_domain_c2.with_env(self.env)
        alias_model_id = self.env['ir.model']._get('mail.test.gateway').id

        new_mail_alias = self.env['mail.alias'].create({
            'alias_model_id': alias_model_id,
            'alias_name': 'unused.test.alias',
        })
        other_alias = self.env['mail.alias'].create({
            'alias_model_id': alias_model_id,
            'alias_name': 'other.test.alias',
        })
        self.assertEqual((new_mail_alias + other_alias).alias_domain_id, mail_alias_domain)

        # test you cannot create  or update aliases matching bounce / catchall of same alias domain
        with self.assertRaises(exceptions.ValidationError), self.cr.savepoint():
            self.env['mail.alias'].create({
                'alias_model_id': alias_model_id,
                'alias_name': mail_alias_domain.catchall_alias,
            })
        with self.assertRaises(exceptions.ValidationError), self.cr.savepoint():
            self.env['mail.alias'].create({
                'alias_model_id': alias_model_id,
                'alias_name': mail_alias_domain.bounce_alias,
            })
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            new_mail_alias.write({'alias_name': mail_alias_domain.catchall_alias})
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            new_mail_alias.write({'alias_name': mail_alias_domain.bounce_alias})

        # other domains bounce / catchall do not prevent
        new_aliases = self.env['mail.alias'].create([
            {'alias_model_id': alias_model_id, 'alias_name': self.alias_catchall_c2},
            {'alias_model_id': alias_model_id, 'alias_name': self.alias_bounce_c2},
        ])
        self.assertEqual(new_aliases.alias_domain_id, mail_alias_domain)
        new_aliases.unlink()
        # bounce/catchall of another domain is ok
        new_mail_alias.write({'alias_name': mail_alias_domain_c2.bounce_alias})
        other_alias.write({'alias_name': mail_alias_domain_c2.catchall_alias})
        # changing domain would clash with existing catchall
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            new_mail_alias.write({'alias_domain_id': mail_alias_domain_c2.id,})

        new_mail_alias.write({'alias_name': 'unused.test.alias'})
        # test that alias {name, alias_domain_id} should be unique
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            self.env['mail.alias'].create({
                'alias_model_id': alias_model_id,
                'alias_name': 'unused.test.alias',
            })
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            self.env['mail.alias'].create([
                {
                    'alias_model_id': alias_model_id,
                    'alias_name': alias_name,
                }
                for alias_name in ('new.alias.1', 'new.alias.2', 'new.alias.1')
            ])
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            other_alias.write({'alias_name': 'unused.test.alias'})

        # also valid for void domain
        nodom_alias = self.env['mail.alias'].create({
            'alias_domain_id': False,
            'alias_model_id': alias_model_id,
            'alias_name': 'no.domain',
        })
        self.assertFalse(nodom_alias.alias_domain_id)
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            self.env['mail.alias'].create({
                'alias_domain_id': False,
                'alias_model_id': alias_model_id,
                'alias_name': 'no.domain',
            })
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            self.env['mail.alias'].create([
                {
                    'alias_domain_id': False,
                    'alias_model_id': alias_model_id,
                    'alias_name': 'dupes.wo.domain',
                } for _x in range(2)
            ])
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            other_alias.write({
                'alias_domain_id': False,
                'alias_name': 'no.domain',
            })

        # test that alias name can be duplicated in case of different alias domains
        other_domain_alias = self.env['mail.alias'].create({
            'alias_domain_id': mail_alias_domain_c2.id,
            'alias_model_id': alias_model_id,
            'alias_name': 'unused.test.alias'
        })
        self.assertEqual(other_domain_alias.alias_domain_id, mail_alias_domain_c2)
        # changing domain would violate uniqueness
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            other_domain_alias.write({'alias_domain_id': mail_alias_domain.id})

    @users('admin')
    def test_alias_name_unique_copy(self):
        """ Check uniqueness constraint check when copying aliases """
        mail_alias_domain = self.mail_alias_domain.with_env(self.env)
        alias_model_id = self.env['ir.model']._get('mail.test.gateway').id
        new_mail_alias = self.env['mail.alias'].create({
            'alias_model_id': alias_model_id,
            'alias_name': 'unused.test.alias'
        })

        with mute_logger('odoo.sql_db'), self.assertRaises(psycopg2.errors.UniqueViolation), self.cr.savepoint():
            new_mail_alias.copy({'alias_name': 'unused.test.alias'})

        # test that duplicating an alias should have blank name
        copy_1 = new_mail_alias.copy()
        self.assertFalse(copy_1.alias_name)
        self.assertEqual(copy_1.alias_domain_id, mail_alias_domain)
        # test sanitize of copy with new name
        copy_2 = new_mail_alias.copy({'alias_name': 'test.alias.2.éè#'})
        self.assertEqual(copy_2.alias_name, 'test.alias.2.ee#')
        self.assertEqual(copy_2.alias_domain_id, mail_alias_domain)

        # cannot batch update, would create duplicates
        with self.assertRaises(exceptions.UserError):
            (copy_1 + copy_2).write({'alias_name': 'test.alias.other'})

    @users('admin')
    @mute_logger('odoo.models.unlink')
    def test_alias_name_sanitize(self):
        """ Check sanitizer, at both create, copy and write on alias name. """
        alias_names = [
            'bidule...inc.',
            'b4r+=*R3wl_#_-$€{}[]()~|\\/!?&%^\'"`~',
            'hélène.prôvâïder',
            '😊',
            'Déboulonneur 😊',
            'ぁ',
        ]
        expected_names = [
            'bidule.inc',
            'b4r+=*r3wl_#_-$-{}-~|-/!?&%^\'-`~',
            'helene.provaider',
            '-',
            'deboulonneur-',
            '?',
        ]
        msgs = [
            'Emails cannot start or end with a dot, there cannot be a sequence of dots.',
            'Disallowed chars should be replaced by hyphens',
            'Email alias should be unaccented',
            'Only a subset of unaccented latin chars are valid, others are replaced',
            'Only a subset of unaccented latin chars are valid, others are replaced',
            'Only a subset of unaccented latin chars are valid, others are replaced',
        ]
        for alias_name, expected, msg in zip(alias_names, expected_names, msgs):
            with self.subTest(alias_name=alias_name):
                alias = self.env['mail.alias'].create({
                    'alias_model_id': self.env['ir.model']._get('mail.test.container').id,
                    'alias_name': alias_name,
                })
                self.assertEqual(alias.alias_name, expected, msg)
                alias.unlink()

        alias = self.env['mail.alias'].create({
            'alias_model_id': self.env['ir.model']._get('mail.test.container').id,
        })
        # check at write
        for alias_name, expected, msg in zip(alias_names, expected_names, msgs):
            with self.subTest(alias_name=alias_name):
                alias.write({'alias_name': alias_name})
                self.assertEqual(alias.alias_name, expected, msg)

    @users('admin')
    def test_alias_name_sanitize_false(self):
        """ Check empty-like aliases are forced to False, as otherwise unique
        constraint might fail with empty strings. """
        aliases = self.env['mail.alias'].create([
            {
                'alias_model_id': self.env['ir.model']._get('mail.test.container').id,
                'alias_name': falsy_name,
            }
            # '.' -> not allowed to start with a "." hence False
            for falsy_name in [False, None, '', ' ', '.']
        ])
        for alias in aliases:
            with self.subTest(alias_name=alias.alias_name):
                self.assertFalse(alias.alias_name, 'Void values should resolve to False')

        # try to reset names in batch: should work
        for idx, alias in enumerate(aliases):
            alias.write({'alias_name': f'unique-{idx}'})
        aliases.write({'alias_name': ''})
        for alias in aliases:
            self.assertEqual(alias.alias_name, False)

    @users('admin')
    def test_search(self):
        """ Test search on aliases, notably searching on display_name which should
        be split on searching on alias_name and alias_domain_id. """
        # ensure existing aliases to ease future asserts
        existing = self.env['mail.alias'].search([('alias_domain_id', '!=', False)])
        self.assertEqual(existing.alias_domain_id, self.mail_alias_domain)
        existing.write({'alias_name': False})  # don't be annoyed by existing aliases

        mail_alias_domain = self.mail_alias_domain.with_env(self.env)
        mail_alias_domain_c2 = self.mail_alias_domain_c2.with_env(self.env)
        self.assertEqual(mail_alias_domain.name, 'test.mycompany.com')
        self.assertEqual(mail_alias_domain_c2.name, 'test.mycompany2.com')

        aliases = self.env['mail.alias'].create([
            {
                'alias_model_id': self.env['ir.model']._get('mail.test.container.mc').id,
                'alias_name': f'test.search.{idx}',
                'alias_domain_id': domain.id,
            }
            for idx in range(5)
            for domain in (mail_alias_domain + mail_alias_domain_c2)
        ])
        aliases_d1 = aliases.filtered(lambda a: a.alias_domain_id == mail_alias_domain)
        aliases_d2 = aliases.filtered(lambda a: a.alias_domain_id == mail_alias_domain_c2)

        # search on alias_name: classic search
        self.assertEqual(
            self.env['mail.alias'].search([('alias_name', 'ilike', 'test.search')]),
            aliases
        )

        # search on alias_fullname: search on aggregated of {name}@{domain}
        for search_term, expected, msg in [
            ('mycompany', aliases,
             'Match all aliases on both domains as "mycompany" is contained in those two'),
            (mail_alias_domain.name, aliases_d1,
             'Exact match on domain 1: should find all aliases in that domain'),
            (mail_alias_domain_c2.name, aliases_d2,
             'Exact match on domain 2: should find all aliases in that domain'),
            ('search.0@test.mycompany', aliases.filtered(lambda a: a.alias_name == 'test.search.0'),
             'Match in both domains'),
            ('search.0@test.mycompany.com', aliases.filtered(lambda a: a.alias_name == 'test.search.0' and a.alias_domain_id == mail_alias_domain),
             'Match only in domain 1'),
            ('search@test.mycompany.com', self.env['mail.alias'],
             'Does not match even as ilike'),
        ]:
            with self.subTest(search_term=search_term):
                self.assertEqual(
                    self.env['mail.alias'].search([('alias_full_name', 'ilike', search_term)]),
                    expected, msg
                )

        # search using IN operator
        for search_term, expected, msg in [
            (['mycompany'], self.env['mail.alias'], 'mycompany is too vague: does not match a left- and right- part (!= ilike)'),
            ([mail_alias_domain.name], self.env['mail.alias'], 'Match only right-part of aliases emails'),
        ]:
            with self.subTest(search_term=search_term):
                self.assertEqual(self.env['mail.alias'].search([('alias_full_name', 'in', search_term)]),
                    expected, msg
                )

    @users('admin')
    def test_alias_setup(self):
        """ Test various constraints / configuration of alias model"""
        alias = self.env['mail.alias'].create({
            'alias_model_id': self.env['ir.model']._get('mail.test.container.mc').id,
            'alias_name': 'unused.test.alias'
        })
        self.assertEqual(alias.alias_status, 'not_tested')

        # validation of alias_defaults
        with self.assertRaises(exceptions.ValidationError):
            alias.write({'alias_defaults': "{'custom_field': brokendict"})
        alias.write({'alias_defaults': "{'custom_field': 'validdict'}"})


@tagged('mail_alias', 'multi_company')
class TestAliasCompany(TestMailAliasCommon):
    """ Test company / alias domain and configuration synchronization """

    def test_alias_domain_setup_archived_company(self):
        """Test initialization of alias domain with at least one archived company
        and at least one mail.alias record points to one mail.thread of the
        archived company"""

        # add archived company to multi company setup
        self.company_archived = self.env['res.company'].create({
                'country_id': self.env.ref('base.be').id,
                'currency_id': self.env.ref('base.EUR').id,
                'email': 'company_archived@test.example.com',
                'name': 'Company Archived Test',
            })
        self.company_archived.action_archive()

        # create record inheriting from mail.thread to be used as owner/target thread
        test_record_archived_company = self.env['mail.test.simple.unfollow'].create({
                'name': 'Test record (mail.thread) specific to archived company',
                'company_id': self.company_archived.id,
            })

        unfollow_model_id = self.env['ir.model']._get_id('mail.test.simple.unfollow')
        mc_archived_parent = self.env['mail.alias'].create({
                'alias_name': 'alias_parent_specific_to_archived_company',
                'alias_parent_model_id': unfollow_model_id,
                'alias_model_id': unfollow_model_id,
                'alias_parent_thread_id': test_record_archived_company.id,
            })  # case where the parent thread is specific to archived company

        mc_archived_target = self.env['mail.alias'].create({
                'alias_name': 'alias_target_specific_to_archived_company',
                'alias_parent_model_id': unfollow_model_id,
                'alias_model_id': unfollow_model_id,
                'alias_force_thread_id': test_record_archived_company.id,
            })  # case where the target thread is specific to archived company

        # eject linked aliases then remove all alias domains; should
        # trigger the init condition at next create() call
        all_mail_aliases = self.env['mail.alias'].search([])
        all_mail_aliases.write({'alias_domain_id': False})
        self.env['mail.alias.domain'].search([]).unlink()

        self.assertFalse(any(all_mail_aliases.mapped("alias_domain_id")),
                         'Mail aliases should have no linked alias domain at this stage')

        # since we nuked all alias domain records, creating a new alias domain
        # will initialize it as the default for all mail.alias records.
        # Should not raise any errors (see _check_alias_domain_id_mc)
        mc_alias_domain = self.env['mail.alias.domain'].create({
                'bounce_alias': 'bounce.mc.archived',
                'catchall_alias': 'catchall.bounce.mc.archived',
                'name': 'test.init.mc.archived.com',
            })

        self.assertEqual(mc_archived_parent.alias_domain_id.id, mc_alias_domain.id,
                         'Parent thread has the wrong alias domain')
        self.assertEqual(mc_archived_target.alias_domain_id.id, mc_alias_domain.id,
                         'Target thread has the wrong alias domain')
        self.assertEqual(self.company_archived.alias_domain_id.id, mc_alias_domain.id,
                         'Archived company was attributed wrong alias domain')

    @mute_logger('odoo.models.unlink')
    @users('erp_manager')
    def test_alias_domain_setup(self):
        """ Test synchronization of alias domain with companies when adding /
        updating / removing alias domains """
        mail_alias_domain = self.mail_alias_domain.with_env(self.env)
        mail_alias_domain_c2 = self.mail_alias_domain_c2.with_env(self.env)

        self.assertEqual(self.company_admin.alias_domain_id, mail_alias_domain)
        self.assertEqual(self.company_2.alias_domain_id, mail_alias_domain_c2)

        # cannot unlink alias domain as there are aliases linked to it
        with self.assertRaises(psycopg2.errors.ForeignKeyViolation), self.cr.savepoint(), mute_logger('odoo.sql_db'):
            mail_alias_domain.unlink()

        # eject linked aliases then remove alias domain of first company; should
        # not impact second company
        self.env['mail.alias'].sudo().search([]).write({'alias_domain_id': False})
        mail_alias_domain.unlink()
        self.assertFalse(self.company_admin.alias_domain_id)
        self.assertEqual(self.company_2.alias_domain_id, mail_alias_domain_c2)
        self.assertFalse(self.test_alias_mc.alias_domain_id)

        # remove all alias domains
        self.env['mail.alias.domain'].search([]).unlink()
        self.assertFalse(self.company_2.alias_domain_id)
        self.assertEqual(self.company_2.bounce_email, '')
        self.assertEqual(self.company_2.bounce_formatted, '')
        self.assertEqual(self.company_2.catchall_email, '')
        self.assertEqual(self.company_2.catchall_formatted, '')
        self.assertFalse(self.company_2.default_from_email, '')
        self.assertFalse(self.company_3.alias_domain_id)

        # create a new alias domain -> consider as re-init, populate all companies
        alias_domain_new = self.env['mail.alias.domain'].create({
            'bounce_alias': 'bounce.new',
            'catchall_alias': 'catchall.new',
            'name': 'test.global.bitnurk.com',
        })
        self.assertEqual(self.company_admin.alias_domain_id, alias_domain_new,
                         'MC Alias: first domain should populate void companies')
        self.assertEqual(self.company_2.alias_domain_id, alias_domain_new,
                         'MC Alias: should take alias domain with lower sequence')
        self.assertEqual(self.company_3.alias_domain_id, alias_domain_new,
                         'MC Alias: should take alias domain with lower sequence')
        self.assertEqual(self.test_alias_mc.alias_domain_id, alias_domain_new,
                         'MC Alias: first domain should populate void aliases')

        # manual update
        self.company_2.alias_domain_id = alias_domain_new.id
        self.assertEqual(self.company_2.alias_domain_id, alias_domain_new)
        self.assertEqual(self.company_2.bounce_email, 'bounce.new@test.global.bitnurk.com')
        self.assertEqual(self.company_2.catchall_email, 'catchall.new@test.global.bitnurk.com')

    def test_assert_initial_values(self):
        """ Test initial setup values: currently all companies share the same
        alias configuration as it is unique. """
        self.assertEqual(self.test_alias_mc.alias_domain_id, self.mail_alias_domain)

        self.assertEqual(self.company_admin.alias_domain_id, self.mail_alias_domain)
        self.assertEqual(self.company_admin.bounce_email, f'{self.alias_bounce}@{self.alias_domain}')
        self.assertEqual(
            self.company_admin.bounce_formatted,
            formataddr((self.company_admin.name, f'{self.alias_bounce}@{self.alias_domain}'))
        )
        self.assertEqual(self.company_admin.catchall_email, f'{self.alias_catchall}@{self.alias_domain}')
        self.assertEqual(
            self.company_admin.catchall_formatted,
            formataddr((self.company_admin.name, f'{self.alias_catchall}@{self.alias_domain}'))
        )
        self.assertEqual(self.company_admin.default_from_email, f'{self.default_from}@{self.alias_domain}')

        self.assertEqual(self.company_2.alias_domain_id, self.mail_alias_domain_c2)
        self.assertEqual(self.company_2.bounce_email, f'{self.alias_bounce_c2}@{self.alias_domain_c2_name}')
        self.assertEqual(
            self.company_2.bounce_formatted,
            formataddr((self.company_2.name, f'{self.alias_bounce_c2}@{self.alias_domain_c2_name}'))
        )
        self.assertEqual(self.company_2.catchall_email, f'{self.alias_catchall_c2}@{self.alias_domain_c2_name}')
        self.assertEqual(
            self.company_2.catchall_formatted,
            formataddr((self.company_2.name, f'{self.alias_catchall_c2}@{self.alias_domain_c2_name}'))
        )
        self.assertEqual(self.company_2.default_from_email, f'{self.alias_default_from_c2}@{self.alias_domain_c2_name}')

        self.assertEqual(self.company_3.alias_domain_id, self.mail_alias_domain_c3)
        self.assertEqual(self.company_3.bounce_email, f'{self.alias_bounce_c3}@{self.alias_domain_c3_name}')
        self.assertEqual(
            self.company_3.bounce_formatted,
            formataddr((self.company_3.name, f'{self.alias_bounce_c3}@{self.alias_domain_c3_name}'))
        )
        self.assertEqual(self.company_3.catchall_email, f'{self.alias_catchall_c3}@{self.alias_domain_c3_name}')
        self.assertEqual(
            self.company_3.catchall_formatted,
            formataddr((self.company_3.name, f'{self.alias_catchall_c3}@{self.alias_domain_c3_name}'))
        )
        self.assertEqual(self.company_3.default_from_email, f'{self.alias_default_from_c3}@{self.alias_domain_c3_name}')

    @users('erp_manager')
    def test_res_company_creation_alias_domain(self):
        """ Test alias domain configuration when creating new companies """
        company = self.env['res.company'].create({
            'email': '"Super Company" <super.company@test3.mycompany.com>',
            'name': 'Super Company',
        })
        company.flush_recordset()
        self.assertEqual(
            company.alias_domain_id, self.mail_alias_domain,
            'Default alias domain: sequence based')

        # respect forced value
        company = self.env['res.company'].create({
            'alias_domain_id': self.mail_alias_domain_c2.id,
            'email': '"Yet Another Company" <yet.another.company@test.embed.mycompany.com>',
            'name': 'Yet Another Company',
        })
        self.assertEqual(company.alias_domain_id, self.mail_alias_domain_c2)


@tagged('mail_gateway', 'mail_alias', 'multi_company')
class TestMailAliasDomain(TestMailAliasCommon):

    @users('admin')
    def test_alias_domain_config_alias_clash(self):
        """ Domain names are not unique e.g. owning multiple gmail.com accounts.
        However bounce / catchall should not clash with aliases. """
        alias_domain = self.mail_alias_domain.with_env(self.env)

        for domain_config in {'bounce_alias', 'catchall_alias'}:
            with self.subTest(domain_config=domain_config):
                with self.assertRaises(exceptions.ValidationError):
                    self.env['mail.alias.domain'].create({
                        domain_config: self.test_alias_mc.alias_name,
                        'name': self.test_alias_mc.alias_domain_id.name,
                    })
        # left-part should not clech
        self.env['mail.alias.domain'].create({
            domain_config: self.test_alias_mc.alias_name,
            'name': 'another.domain.name.com',
        })

        # should not clash with existing aliases, to avoid valid aliases be
        # considered as bounce / catchall
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            alias_domain.write({'bounce_alias': self.test_alias_mc.alias_name})
        with self.assertRaises(exceptions.UserError), self.cr.savepoint():
            alias_domain.write({'catchall_alias': self.test_alias_mc.alias_name})

    @users('admin')
    def test_alias_domain_config_unique(self):
        """ Domain names are not unique e.g. owning multiple gmail.com accounts.
        However bounce / catchall should be unique. """
        alias_domain = self.mail_alias_domain.with_env(self.env)

        # copying directly would duplicate bounce / catchall emails
        with mute_logger('odoo.sql_db'), self.assertRaises(psycopg2.errors.UniqueViolation), self.cr.savepoint():
            new_alias_domain = alias_domain.copy()

        # same domain name is authorized if bounce and catchall are different
        new_alias_domain = alias_domain.copy({
            'bounce_alias': 'new.bounce',
            'catchall_alias': 'new.catchall',
            })
        self.assertEqual(new_alias_domain.bounce_email, f'new.bounce@{alias_domain.name}')
        self.assertEqual(new_alias_domain.catchall_email, f'new.catchall@{alias_domain.name}')
        self.assertEqual(new_alias_domain.name, alias_domain.name)

        # check bounce / catchall are unique at create
        self.env['mail.alias.domain'].create({
            'bounce_alias': 'unique.bounce',
            'catchall_alias': 'unique.catchall',
            'name': alias_domain.name,
        })
        # any not unique should raise UniqueViolation (SQL constraint fired after check)
        with mute_logger('odoo.sql_db'), self.assertRaises(psycopg2.errors.UniqueViolation), self.cr.savepoint():
            self.env['mail.alias.domain'].create({
                'bounce_alias': alias_domain.bounce_alias,
                'name': alias_domain.name,
            })
        with mute_logger('odoo.sql_db'), self.assertRaises(psycopg2.errors.UniqueViolation), self.cr.savepoint():
            self.env['mail.alias.domain'].create({
                'catchall_alias': alias_domain.catchall_alias,
                'name': alias_domain.name,
            })

        # also check write operation
        with self.assertRaises(exceptions.ValidationError):
            new_alias_domain.write({'bounce_alias': alias_domain.bounce_alias})
        with self.assertRaises(exceptions.ValidationError):
            new_alias_domain.write({'catchall_alias': alias_domain.catchall_alias})

    @users('admin')
    def test_alias_domain_parameters_validation(self):
        """ Test validation of bounce and catchall fields of alias domain as
        well as sanitization. """
        alias_domain = self.mail_alias_domain.with_env(self.env)

        # sanitization of name (both create and write)
        for failing_name in [
            'outlook.fr, gmail.com',
            # accents
            'provaïder',
            'provaïder.cöm',
            # fail
            '', ' ',
        ]:
            with self.subTest(failing_name=failing_name):
                with self.assertRaises(exceptions.ValidationError):
                    _new_domain = self.env['mail.alias.domain'].create({'name': failing_name})

                with self.assertRaises(exceptions.ValidationError):
                    alias_domain.write({'name': failing_name})

        # sanitization of bounce / catchall
        for (
            (bounce_alias, catchall_alias, default_from),
            (exp_bounce, exp_catchall, exp_default_from),
            (exp_bounce_email, exp_catchall_email, exp_default_from_email),
        ) in zip(
            [
                (
                    'bounce+b4r=*R3wl_#_-$€{}[]()~|\\/!?&%^\'"`~',
                    'catchall+b4r=*R3wl_#_-$€{}[]()~|\\/!?&%^\'"`~',
                    'notifications+b4r=*R3wl_#_-$€{}[]()~|\\/!?&%^\'"`~',
                ),
                ('bounce+😊', 'catchall+😊', 'notifications+😊'),
                ('Bouncâïde 😊', 'Catchôïee 😊', 'Notificâtïons 😊'),
                ('ぁ', 'ぁぁ', 'ぁぁぁ'),
                # only default_from can be a valid email and taken as such
                (
                    'bounce@wrong.complete.com',
                    'catchall@wrong.complete.com',
                    'notifications@valid.complete.com',
                ),
            ],
            [
                (
                    'bounce+b4r=*r3wl_#_-$-{}-~|-/!?&%^\'-`~',
                    'catchall+b4r=*r3wl_#_-$-{}-~|-/!?&%^\'-`~',
                    'notifications+b4r=*r3wl_#_-$-{}-~|-/!?&%^\'-`~',
                ),
                ('bounce+-', 'catchall+-', 'notifications+-'),
                ('bouncaide-', 'catchoiee-', 'notifications-'),
                ('?', '??', '???'),
                # only default_from can be a valid email and taken as such
                (
                    'bounce',
                    'catchall',
                    'notifications@valid.complete.com',
                ),
            ],
            [
                (
                    f'bounce+b4r=*r3wl_#_-$-{{}}-~|-/!?&%^\'-`~@{alias_domain.name}',
                    f'catchall+b4r=*r3wl_#_-$-{{}}-~|-/!?&%^\'-`~@{alias_domain.name}',
                    f'notifications+b4r=*r3wl_#_-$-{{}}-~|-/!?&%^\'-`~@{alias_domain.name}',
                ),
                (
                    f'bounce+-@{alias_domain.name}',
                    f'catchall+-@{alias_domain.name}',
                    f'notifications+-@{alias_domain.name}'),
                (
                    f'bouncaide-@{alias_domain.name}',
                    f'catchoiee-@{alias_domain.name}',
                    f'notifications-@{alias_domain.name}'
                ),
                (
                    f'?@{alias_domain.name}',
                    f'??@{alias_domain.name}',
                    f'???@{alias_domain.name}'
                ),
                # only default_from can be a valid email and taken as such
                (
                    f'bounce@{alias_domain.name}',
                    f'catchall@{alias_domain.name}',
                    'notifications@valid.complete.com',
                ),
            ]
        ):
            with self.subTest(bounce_alias=bounce_alias):
                alias_domain.write({'bounce_alias': bounce_alias})
                self.assertEqual(alias_domain.bounce_alias, exp_bounce)
                self.assertEqual(alias_domain.bounce_email, exp_bounce_email)
            with self.subTest(catchall_alias=catchall_alias):
                alias_domain.write({'catchall_alias': catchall_alias})
                self.assertEqual(alias_domain.catchall_alias, exp_catchall)
                self.assertEqual(alias_domain.catchall_email, exp_catchall_email)
            with self.subTest(default_from=default_from):
                alias_domain.write({'default_from': default_from})
                self.assertEqual(alias_domain.default_from, exp_default_from)
                self.assertEqual(alias_domain.default_from_email, exp_default_from_email)

        # falsy values
        for config_value in [False, None, '', ' ']:
            with self.subTest(config_value=config_value):
                alias_domain.write({'bounce_alias': config_value})
                self.assertFalse(alias_domain.bounce_alias)
                alias_domain.write({'catchall_alias': config_value})
                self.assertFalse(alias_domain.catchall_alias)
                alias_domain.write({'default_from': config_value})
                self.assertFalse(alias_domain.default_from)

        # check successive param set, should not raise for unicity against itself
        for _ in range(2):
            alias_domain.write({
                'bounce_alias': 'bounce+double.test',
                'catchall_alias': 'catchall+double.test',
            })
            self.assertEqual(alias_domain.bounce_alias, 'bounce+double.test')
            self.assertEqual(alias_domain.catchall_alias, 'catchall+double.test')


@tagged('mail_gateway', 'mail_alias', 'mail_alias_mixin', 'multi_company')
class TestMailAliasMixin(TestMailAliasCommon):
    """ Test alias mixin implementation, synchronization of alias records
    based on owner records. """

    @users('employee')
    @mute_logger('odoo.addons.base.models.ir_model')
    def test_alias_mixin(self):
        """ Various base checks on alias mixin behavior """
        self.assertEqual(self.env.company.alias_domain_id, self.mail_alias_domain)

        record = self.env['mail.test.container'].create({
            'name': 'Test Record',
            'alias_name': 'alias.test',
            'alias_contact': 'followers',
        })
        self.assertEqual(record.alias_id.alias_domain_id, self.mail_alias_domain)
        self.assertEqual(record.alias_id.alias_model_id, self.env['ir.model']._get('mail.test.container'))
        self.assertEqual(record.alias_id.alias_force_thread_id, record.id)
        self.assertEqual(record.alias_id.alias_parent_model_id, self.env['ir.model']._get('mail.test.container'))
        self.assertEqual(record.alias_id.alias_parent_thread_id, record.id)
        self.assertEqual(record.alias_id.alias_name, 'alias.test')
        self.assertEqual(record.alias_id.alias_contact, 'followers')

        record.write({
            'alias_domain_id': self.mail_alias_domain_c2.id,
            'alias_name': 'better.alias.test',
            'alias_defaults': "{'default_name': 'defaults'}"
        })
        self.assertEqual(record.alias_domain, self.mail_alias_domain_c2.name)
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

    @users('erp_manager')
    def test_alias_mixin_alias_email(self):
        """ Test 'alias_email' mixin field computation and search capability """
        Model = self.env['mail.test.container.mc']
        records = Model.create([
            {
                'alias_name': f'alias.email.{idx}',  # will be present in all companies
                'company_id': company.id,
                'name': f'Test {company.id} {idx}',
            }
            for company in (self.company_admin, self.company_2)
            for idx in range(5)
        ])
        self.assertEqual(
            Model.search([('alias_email', 'ilike', 'alias.email')]), records,
            'Search: partial search: any domain, matching all left parts')
        self.assertEqual(
            Model.search([('alias_email', 'ilike', 'alias.email.0')]), records[0] + records[5],
            'Search: partial search: any domain, matching some left parts')
        self.assertEqual(
            Model.search([('alias_email', '=', self.mail_alias_domain.name)]), Model,
            'Search: partial search: does not match any complete email')
        self.assertEqual(
            Model.search([('alias_email', '=', f'alias.email.1@{self.mail_alias_domain.name}')]), records[1],
            'Search: both part search: search on name + domain')

    @users('employee')
    @mute_logger('odoo.addons.base.models.ir_model')
    def test_alias_mixin_alias_id_management(self):
        """ Test alias_id being not mandatory """
        record_wo_alias, record_w_alias = self.env['mail.test.alias.optional'].create([
            {
                'name': 'Test WoAlias Name',
            }, {
                'alias_name': 'Alias Name',
                'name': 'Test WoAlias Name',
            }
        ])
        self.assertFalse(record_wo_alias.alias_id, 'Alias record not created if not necessary (no alias_name)')
        self.assertFalse(record_wo_alias.alias_id.alias_name)
        self.assertFalse(record_wo_alias.alias_id.alias_defaults)
        self.assertFalse(record_wo_alias.alias_name)
        self.assertTrue(record_w_alias.alias_id, 'Alias record created as alias_name was given')
        self.assertEqual(record_w_alias.alias_id.alias_name, 'alias-name', 'Alias name should go through sanitize')
        self.assertEqual(
            literal_eval(record_w_alias.alias_id.alias_defaults),
            {'company_id': self.env.company.id}
        )
        self.assertEqual(record_w_alias.alias_name, 'alias-name', 'Alias name should go through sanitize')
        self.assertEqual(
            literal_eval(record_w_alias.alias_defaults),
            {'company_id': self.env.company.id}
        )

        # update existing alias
        record_w_alias.write({'alias_contact': 'followers', 'alias_name': 'Updated Alias Name'})
        self.assertEqual(record_w_alias.alias_id.alias_contact, 'followers')
        self.assertEqual(record_w_alias.alias_id.alias_name, 'updated-alias-name')
        self.assertEqual(record_w_alias.alias_name, 'updated-alias-name')

        # update non existing alias -> creates alias
        record_wo_alias.write({'alias_name': 'trying a name'})
        self.assertTrue(record_wo_alias.alias_id, 'Alias record should have been created to store the name')
        self.assertEqual(record_wo_alias.alias_id.alias_name, 'trying-a-name')
        self.assertEqual(
            literal_eval(record_wo_alias.alias_id.alias_defaults),
            {'company_id': self.env.company.id}
        )
        self.assertEqual(record_wo_alias.alias_name, 'trying-a-name')
        self.assertEqual(
            literal_eval(record_wo_alias.alias_defaults),
            {'company_id': self.env.company.id}
        )

        # reset alias -> keep the alias as void, don't remove it
        existing_aliases = record_wo_alias.alias_id + record_w_alias.alias_id
        (record_wo_alias + record_w_alias).write({'alias_name': False})
        self.assertEqual((record_wo_alias + record_w_alias).alias_id, existing_aliases)
        self.assertFalse(list(filter(None, existing_aliases.mapped('alias_name'))))

    @users('employee')
    def test_copy_content(self):
        self.assertFalse(
            self.env.user.has_group('base.group_system'),
            'Test user should not have Administrator access')

        record = self.env['mail.test.container'].create({
            'name': 'Test Record',
            'alias_name': 'test.record',
            'alias_contact': 'followers',
            'alias_bounced_content': False,
        })
        record_alias = record.alias_id
        self.assertFalse(record.alias_bounced_content)
        record_copy = record.copy()
        record_alias_copy = record_copy.alias_id
        self.assertNotEqual(record_alias, record_alias_copy)
        self.assertEqual(record_alias.alias_force_thread_id, record.id)
        self.assertEqual(record_alias_copy.alias_force_thread_id, record_copy.id)
        self.assertFalse(record_copy.alias_bounced_content)
        self.assertEqual(record_copy.alias_contact, record.alias_contact)
        self.assertFalse(record_copy.alias_name, 'Copy should not duplicate name')

        new_content = '<p>Bounced Content</p>'
        record_copy.write({'alias_bounced_content': new_content})
        self.assertEqual(record_copy.alias_bounced_content, new_content)
        record_copy2 = record_copy.copy()
        self.assertEqual(record_copy2.alias_bounced_content, new_content)

    @users('employee')
    def test_copy_optional_alias_model(self):
        """ Do not propagate alias_id to duplicate record as it could lead to
        overwriting alias_name of old record. """
        record = self.env['mail.test.alias.optional'].create({
            'name': 'Test Optional Alias Record',
            'alias_name': 'test.optional.alias.record',
        })
        self.assertTrue(record.alias_id)
        record_copy = record.copy()
        self.assertFalse(record_copy.alias_id)

    @users('erp_manager')
    def test_multi_company_setup(self):
        """ Test company impact on alias domains when creating or updating
        records in a MC environment. """
        counter = 0
        for create_cid, exp_company, exp_alias_domain in [
            (None, self.company_2, self.mail_alias_domain_c2),
            (False, self.env['res.company'], self.mail_alias_domain_c2),
            (self.env.user.company_id.id, self.company_2, self.mail_alias_domain_c2),
            (self.company_admin.id, self.company_admin, self.mail_alias_domain),
        ]:
            with self.subTest(create_cid=create_cid, exp_company=exp_company, exp_alias_domain=exp_alias_domain):
                counter += 1
                base_values = {
                    'name': f'Test Record {counter}',
                    'alias_name': f'alias.test.{counter}',
                    'alias_contact': 'followers',
                }
                if create_cid is not None:
                    base_values['company_id'] = create_cid
                record = self.env['mail.test.container.mc'].create(base_values)
                self.assertEqual(record.alias_domain_id, exp_alias_domain)
                self.assertEqual(record.company_id, exp_company)

                # copy: keep company
                record_copy = record.copy(
                    default={
                        'alias_name': f'alias.copy.{counter}',
                        'name': f'Copy of {record.name}',
                    }
                )
                self.assertEqual(record_copy.alias_domain_id, exp_alias_domain)
                self.assertEqual(record_copy.company_id, record.company_id)

                # copy: force company
                record_copy_2 = record.copy(
                    default={
                        'alias_name': f'alias.copy.{counter}.2',
                        'company_id': self.company_admin.id,
                        'name': f'Copy 2 of {record.name}',
                    }
                )
                self.assertEqual(record_copy_2.alias_domain_id, self.mail_alias_domain)
                self.assertEqual(record_copy_2.company_id, self.company_admin)

                # updating company: force same alias domain
                record.write({'company_id': self.company_admin.id})
                self.assertEqual(record.alias_domain_id, self.mail_alias_domain)
                self.assertEqual(record.company_id, self.company_admin)

                # reset company: should not impact alias_domain if set
                record.write({'company_id': False})
                self.assertEqual(record.alias_domain_id, self.mail_alias_domain)
                self.assertFalse(record.company_id)
