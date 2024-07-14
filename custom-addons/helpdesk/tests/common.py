# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from freezegun import freeze_time
from unittest.mock import patch

from odoo.addons.mail.tests.common import MockEmail
from odoo.tests.common import TransactionCase


class HelpdeskCommon(TransactionCase, MockEmail):

    @classmethod
    def setUpClass(cls):
        super(HelpdeskCommon, cls).setUpClass()
        cls._init_mail_gateway()
        cls.env.user.tz = 'Europe/Brussels'
        cls.env['resource.calendar'].search([]).write({'tz': 'Europe/Brussels'})

        # we create a helpdesk user and a manager
        Users = cls.env['res.users'].with_context(tracking_disable=True)
        cls.main_company_id = cls.env.user.company_id.id
        cls.partner = cls.env['res.partner'].create({
            'name': 'Customer Credee'
        })

        cls.helpdesk_manager = Users.create({
            'company_id': cls.main_company_id,
            'name': 'Helpdesk Manager',
            'login': 'hm',
            'email': 'hm@example.com',
            'groups_id': [(6, 0, [cls.env.ref('helpdesk.group_helpdesk_manager').id,
                                  cls.env.ref('base.group_partner_manager').id])],
            'tz': 'Europe/Brussels',
        })
        cls.helpdesk_user = Users.create({
            'company_id': cls.main_company_id,
            'name': 'Helpdesk User',
            'login': 'hu',
            'email': 'hu@example.com',
            'groups_id': [(6, 0, [cls.env.ref('helpdesk.group_helpdesk_user').id])],
            'tz': 'Europe/Brussels',
        })
        cls.helpdesk_portal = Users.create({
            'company_id': cls.main_company_id,
            'name': 'Helpdesk Portal',
            'login': 'hp',
            'email': 'hp@example.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id])],
            'tz': 'Europe/Brussels',
        })
        # the manager defines a team for our tests (the .sudo() at the end is to avoid potential uid problems)
        cls.test_team = cls.env['helpdesk.team'].with_user(cls.helpdesk_manager).create({'name': 'Test Team'}).sudo()
        cls.test_team.stage_ids = False
        # He then defines its stages
        stage_as_manager = cls.env['helpdesk.stage'].with_user(cls.helpdesk_manager)
        cls.stage_new = stage_as_manager.create({
            'name': 'New',
            'sequence': 10,
            'team_ids': [(4, cls.test_team.id, 0)],
        })
        cls.stage_progress = stage_as_manager.create({
            'name': 'In Progress',
            'sequence': 20,
            'team_ids': [(4, cls.test_team.id, 0)],
        })
        cls.stage_done = stage_as_manager.create({
            'name': 'Done',
            'sequence': 30,
            'team_ids': [(4, cls.test_team.id, 0)],
            'fold': True,
        })
        cls.stage_cancel = stage_as_manager.create({
            'name': 'Cancelled',
            'sequence': 40,
            'team_ids': [(4, cls.test_team.id, 0)],
            'fold': True,
        })

        # He also creates a ticket types for Question and Issue
        cls.type_question = cls.env['helpdesk.ticket.type'].with_user(cls.helpdesk_manager).create({
            'name': 'Question_test',
        }).sudo()
        cls.type_issue = cls.env['helpdesk.ticket.type'].with_user(cls.helpdesk_manager).create({
            'name': 'Issue_test',
        }).sudo()

    @contextmanager
    def _ticket_patch_now(self, datetime):
        with freeze_time(datetime), patch.object(self.env.cr, 'now', lambda: datetime):
            yield
            self.env.flush_all()

    def flush_tracking(self):
        """ Force the creation of tracking values. """
        self.env.flush_all()
        self.cr.flush()
