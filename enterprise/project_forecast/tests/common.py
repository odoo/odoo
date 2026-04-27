# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from contextlib import contextmanager

from odoo import fields

from odoo.addons.planning.tests.common import TestCommonPlanning


class TestCommonForecast(TestCommonPlanning):

    @classmethod
    def setUpProjects(cls):
        Project = cls.env['project.project'].with_context(tracking_disable=True)
        Task = cls.env['project.task'].with_context(tracking_disable=True)

        cls.project_opera = Project.create({
            'name': 'Opera',
            'color': 2,
            'privacy_visibility': 'employees',
        })
        cls.task_opera_place_new_chairs = Task.create({
            'name': 'Add the new chairs in room 9',
            'project_id': cls.project_opera.id,
        })
        cls.project_horizon = Project.create({
            'name': 'Horizon',
            'color': 1,
            'privacy_visibility': 'employees',
        })
        cls.task_horizon_dawn = Task.create({
            'name': 'Dawn',
            'project_id': cls.project_horizon.id,
        })

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------

    @contextmanager
    def _patch_now(self, datetime_str):
        datetime_now_old = getattr(fields.Datetime, 'now')
        datetime_today_old = getattr(fields.Datetime, 'today')

        def new_now():
            return fields.Datetime.from_string(datetime_str)

        def new_today():
            return fields.Datetime.from_string(datetime_str).replace(hour=0, minute=0, second=0)

        try:
            setattr(fields.Datetime, 'now', new_now)
            setattr(fields.Datetime, 'today', new_today)

            yield
        finally:
            # back
            setattr(fields.Datetime, 'now', datetime_now_old)
            setattr(fields.Datetime, 'today', datetime_today_old)

    def get_by_employee(self, employee):
        return self.env['planning.slot'].search([('employee_id', '=', employee.id)])
