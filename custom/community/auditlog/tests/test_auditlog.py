# -*- coding: utf-8 -*-
# © 2015 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests.common import TransactionCase


class TestAuditlog(object):

    def test_LogCreation(self):
        """First test, caching some data."""
        auditlog_log = self.env['auditlog.log']
        group = self.env['res.groups'].create({
            'name': 'testgroup1',
        })
        self.assertTrue(auditlog_log.search([
            ('model_id', '=', self.groups_model_id),
            ('method', '=', 'create'),
            ('res_id', '=', group.id),
        ]).ensure_one())
        group.write({'name': 'Testgroup1'})
        self.assertTrue(auditlog_log.search([
            ('model_id', '=', self.groups_model_id),
            ('method', '=', 'write'),
            ('res_id', '=', group.id),
        ]).ensure_one())
        group.unlink()
        self.assertTrue(auditlog_log.search([
            ('model_id', '=', self.groups_model_id),
            ('method', '=', 'unlink'),
            ('res_id', '=', group.id),
        ]).ensure_one())

    def test_LogCreation2(self):
        """Second test, using cached data of the first one."""
        auditlog_log = self.env['auditlog.log']
        testgroup2 = self.env['res.groups'].create({
            'name': 'testgroup2',
        })
        self.assertTrue(auditlog_log.search([
            ('model_id', '=', self.groups_model_id),
            ('method', '=', 'create'),
            ('res_id', '=', testgroup2.id),
        ]).ensure_one())

    def test_LogCreation3(self):
        """Third test, two groups, the latter being the parent of the former.
        Then we remove it right after (with (2, X) tuple) to test the creation
        of a 'write' log with a deleted resource (so with no text
        representation).
        """
        auditlog_log = self.env['auditlog.log']
        testgroup3 = testgroup3 = self.env['res.groups'].create({
            'name': 'testgroup3',
        })
        testgroup4 = self.env['res.groups'].create({
            'name': 'testgroup4',
            'implied_ids': [(4, testgroup3.id)],
        })
        testgroup4.write({'implied_ids': [(2, testgroup3.id)]})
        self.assertTrue(auditlog_log.search([
            ('model_id', '=', self.groups_model_id),
            ('method', '=', 'create'),
            ('res_id', '=', testgroup3.id),
        ]).ensure_one())
        self.assertTrue(auditlog_log.search([
            ('model_id', '=', self.groups_model_id),
            ('method', '=', 'create'),
            ('res_id', '=', testgroup4.id),
        ]).ensure_one())
        self.assertTrue(auditlog_log.search([
            ('model_id', '=', self.groups_model_id),
            ('method', '=', 'write'),
            ('res_id', '=', testgroup4.id),
        ]).ensure_one())


class TestAuditlogFull(TransactionCase, TestAuditlog):

    def setUp(self):
        super(TestAuditlogFull, self).setUp()
        self.groups_model_id = self.env.ref('base.model_res_groups').id
        self.groups_rule = self.env['auditlog.rule'].create({
            'name': 'testrule for groups',
            'model_id': self.groups_model_id,
            'log_read': True,
            'log_create': True,
            'log_write': True,
            'log_unlink': True,
            'state': 'subscribed',
            'log_type': 'full',
        })

    def tearDown(self):
        self.groups_rule.unlink()
        super(TestAuditlogFull, self).tearDown()


class TestAuditlogFast(TransactionCase, TestAuditlog):

    def setUp(self):
        super(TestAuditlogFast, self).setUp()
        self.groups_model_id = self.env.ref('base.model_res_groups').id
        self.groups_rule = self.env['auditlog.rule'].create({
            'name': 'testrule for groups',
            'model_id': self.groups_model_id,
            'log_read': True,
            'log_create': True,
            'log_write': True,
            'log_unlink': True,
            'state': 'subscribed',
            'log_type': 'fast',
        })

    def tearDown(self):
        self.groups_rule.unlink()
        super(TestAuditlogFast, self).tearDown()
