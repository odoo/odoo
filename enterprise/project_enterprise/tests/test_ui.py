# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

import logging

from odoo import fields
from odoo.tests import HttpCase, tagged
from odoo.addons.mail.tests.common import mail_new_test_user

_logger = logging.getLogger(__name__)


@tagged('-at_install', 'post_install')
class ProjectEnterpriseTestUi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        user_groups = 'base.group_user,project.group_project_manager'
        if 'account.move.line' in cls.env:
            user_groups += ',account.group_account_invoice'
        cls.user_project_manager = mail_new_test_user(
            cls.env,
            company_id=cls.env.company.id,
            email='gilbert.testuser@test.example.com',
            login='user_project_manager',
            groups=user_groups,
            name='Gilbert ProjectManager',
            tz='Europe/Brussels',
        )
        # The test checks that the 'danger' state appears when an employee is
        # overworked. This ensures that creating a task in the gantt view
        # during the tour, triggers that warning.
        project = cls.env['project.project'].create({
            'name': 'Test Project',
        })
        # Allocated hours is only computed without _origin
        task = cls.env['project.task'].new({
            'project_id': project.id,
            'name': 'Test Task',
            'planned_date_begin': fields.Datetime.now() - relativedelta(days=30),
            'date_deadline': fields.Datetime.now() + relativedelta(days=30),
            'user_ids': cls.env.ref('base.user_admin'),
        })
        task._compute_allocated_hours()
        task.create(task._convert_to_write(task._cache))

    def test_01_ui(self):
        self.start_tour("/", 'project_test_tour', login='admin')
