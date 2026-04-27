# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo.tests import new_test_user, TransactionCase

class TestIndustryFsmCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fsm_project = cls.env['project.project'].create({
            'name': 'Field Service',
            'is_fsm': True,
            'allow_timesheets': True,
            'company_id': cls.env.company.id
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Partner',
        })
        cls.task = cls.env['project.task'].create({
            'name': 'Fsm task',
            'project_id': cls.fsm_project.id,
            'partner_id': cls.partner.id,
        })
        cls.second_task = cls.env['project.task'].create({
            'name': 'Fsm task 2',
            'project_id': cls.fsm_project.id,
            'partner_id': cls.partner.id,
        })
        cls.employee_user = cls.env['hr.employee'].create({
            'name': 'Employee User',
            'hourly_cost': 15,
        })
        cls.george_user = new_test_user(cls.env, login='george', name='George', groups='industry_fsm.group_fsm_user')
        cls.marcel_user = new_test_user(cls.env, login='marcel', name='Marcel', groups='industry_fsm.group_fsm_user')
        cls.henri_user = new_test_user(cls.env, login='henri', groups='industry_fsm.group_fsm_user')
        cls.employee_timer_timesheet = cls.env['hr.employee'].create({
            'name': 'Employee Timesheet Timer',
            'user_id': cls.marcel_user.id,
        })
        cls.employee_timer_task = cls.env['hr.employee'].create({
            'name': 'Employee Task Timer',
            'user_id': cls.henri_user.id,
        })
        cls.employee_mark_as_done = cls.env['hr.employee'].create({
            'name': 'Employee Mark As Done',
            'user_id': cls.george_user.id,
        })

        cls.base_user = new_test_user(cls.env, 'Base user', groups='base.group_user')
        cls.project_user = new_test_user(cls.env, 'Project user', groups='project.group_project_user')
        cls.project_manager = new_test_user(cls.env, 'Project admin', groups='project.group_project_manager')
        cls.portal_user = new_test_user(cls.env, 'Portal user', groups='base.group_portal')
        cls.fsm_user = new_test_user(cls.env, 'Fsm user', groups='industry_fsm.group_fsm_user')
