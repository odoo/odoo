# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime
import unittest

from odoo.exceptions import AccessError

from .common import TestCommonForecast


class TestForecastAccessRights(TestCommonForecast):

    @classmethod
    def setUpClass(cls):
        super(TestForecastAccessRights, cls).setUpClass()

        cls.setUpEmployees()
        cls.setUpProjects()

        user_group_portal = cls.env.ref('base.group_portal')
        user_group_employee = cls.env.ref('base.group_user')
        user_group_project_user = cls.env.ref('project.group_project_user')
        user_group_project_manager = cls.env.ref('project.group_project_manager')

        # public user
        cls.user_public = cls.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': 'Bert Tartignole',
            'login': 'bert',
            'email': 'b.t@example.com',
            'signature': 'SignBert',
            'notification_type': 'email',
            'groups_id': [(6, 0, [cls.env.ref('base.group_public').id])]
        })
        # portal user
        cls.user_portal = cls.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': 'portal',
            'login': 'portal_user',
            'email': 'portal@example.com',
            'groups_id': [(6, 0, [user_group_portal.id])]
        })
        # employee user
        cls.user_projectuser_joseph = cls.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': 'Joseph',
            'login': 'Joseph',
            'email': 'Joseph@test.com',
            'groups_id': [(6, 0, [user_group_employee.id, user_group_project_user.id])],
        })
        cls.employee_joseph.write({
            'user_id': cls.user_projectuser_joseph.id
        })
        # manager user
        cls.user_projectmanager_bert = cls.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': 'Bert',
            'login': 'Bert',
            'email': 'Bert@test.com',
            'groups_id': [(6, 0, [user_group_employee.id, user_group_project_manager.id])],
        })
        cls.employee_bert.write({
            'user_id': cls.user_projectmanager_bert.id
        })

        # Tinyhouse project, on invitation
        cls.tinyhouse_followers = [cls.user_projectmanager_bert.partner_id]
        cls.project_tinyhouse = cls.env['project.project'].create({
            'name': 'Tinyhouse',
            'color': 1,
            'privacy_visibility': 'followers',
        })
        values_list = []
        for partner in cls.tinyhouse_followers:
            values_list.append({
                'res_model': 'project.project',
                'res_id': cls.project_tinyhouse.id,
                'partner_id': partner.id,
            })
        cls.env['mail.followers'].create(values_list)

        # create a forecast in each project
        forecast_values = {
            'employee_id': cls.employee_joseph.id,
            'start_datetime': datetime(2019, 6, 5, 8),
            'end_datetime': datetime(2019, 6, 5, 17),
            'allocated_hours': 8,
        }

        cls.project_tinyhouse_forecast = cls.env['planning.slot'].create({'project_id': cls.project_tinyhouse.id, **forecast_values})
        cls.project_opera_forecast = cls.env['planning.slot'].create({'project_id': cls.project_opera.id, **forecast_values})
        cls.project_horizon_forecast = cls.env['planning.slot'].create({'project_id': cls.project_horizon.id, **forecast_values})

    def test_public_user_access_rights(self):
        # create
        with self.assertRaises(AccessError):
            self.env['planning.slot'].with_user(self.user_public.id).create({
                'employee_id': self.employee_bert.id,
                'start_datetime': datetime(2019, 6, 5, 8),
                'end_datetime': datetime(2019, 6, 5, 17),
                'project_id': self.project_horizon.id,
                'allocated_hours': 8,
            })
        # read
        with self.assertRaises(AccessError):
            self.project_opera_forecast.with_user(self.user_public.id).read()
        # update
        with self.assertRaises(AccessError):
            self.project_opera_forecast.with_user(self.user_public.id).write({'allocated_hours': 6})
        # delete
        with self.assertRaises(AccessError):
            self.project_opera_forecast.with_user(self.user_public.id).unlink()

    def test_portal_user_access_right(self):
        # create
        with self.assertRaises(AccessError):
            self.env['planning.slot'].with_user(self.user_portal.id).create({
                'employee_id': self.employee_bert.id,
                'start_datetime': datetime(2019, 6, 5, 8),
                'end_datetime': datetime(2019, 6, 5, 17),
                'project_id': self.project_horizon.id,
                'allocated_hours': 8,
            })
        # read
        with self.assertRaises(AccessError):
            self.project_opera_forecast.with_user(self.user_portal.id).read()
        # update
        with self.assertRaises(AccessError):
            self.project_opera_forecast.with_user(self.user_portal.id).write({'allocated_hours': 6})
        # delete
        with self.assertRaises(AccessError):
            self.project_opera_forecast.with_user(self.user_portal.id).unlink()

    def test_regular_user_access_rights(self):
        # create
        with self.assertRaises(AccessError):
            self.env['planning.slot'].with_user(self.employee_joseph.user_id.id).create({
                'employee_id': self.employee_bert.id,
                'start_datetime': datetime(2019, 6, 5, 8),
                'end_datetime': datetime(2019, 6, 5, 17),
                'allocated_hours': 8,
            })
        # update
        with self.assertRaises(AccessError):
            self.project_opera_forecast.with_user(self.employee_joseph.user_id.id).write({'allocated_hours': 6})
        # delete
        with self.assertRaises(AccessError):
            self.project_opera_forecast.with_user(self.employee_joseph.user_id.id).unlink()
        # joseph is not part of the tinyhouse project which is restricted to followers
        with self.assertRaises(AccessError):
            self.project_tinyhouse_forecast.with_user(self.employee_joseph.user_id).read()
        self.project_opera_forecast.with_user(self.employee_joseph.user_id).read()

    def test_manager_access_rights(self):
        # read
        self.project_tinyhouse_forecast.with_user(self.employee_bert.user_id.id).read()
        # create
        self.env['planning.slot'].with_user(self.employee_bert.user_id.id).create({
            'employee_id': self.employee_bert.id,
            'start_datetime': datetime(2019, 6, 5, 8),
            'project_id': self.project_horizon.id,
            'end_datetime': datetime(2019, 6, 5, 17),
            'allocated_hours': 8,
        })
        # update
        self.project_opera_forecast.with_user(self.employee_bert.user_id.id).write({'allocated_hours': 6})
        # delete
        self.project_opera_forecast.with_user(self.employee_bert.user_id.id).unlink()
