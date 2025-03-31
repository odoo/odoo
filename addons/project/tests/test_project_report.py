# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from .test_project_base import TestProjectCommon

@tagged('post_install', '-at_install')
class TestProjectReport(TestProjectCommon):
    def test_avg_rating_measure(self):
        rating_vals = {
            'res_model_id': self.env['ir.model']._get('project.task').id,
            'rated_partner_id': self.partner_1.id,
            'partner_id': self.partner_1.id,
            'consumed': True,
        }
        self.env['rating.rating'].create([
            {**rating_vals, 'rating': 5, 'res_id': self.task_1.id},
            {**rating_vals, 'rating': 4, 'res_id': self.task_1.id},
            {**rating_vals, 'rating': 4.25, 'res_id': self.task_2.id},
        ])
        self.assertEqual(self.task_1.rating_avg, 4.5)
        self.assertEqual(self.task_1.rating_last_value, 4.0)

        self.assertEqual(self.task_2.rating_avg, 4.25)
        self.assertEqual(self.task_2.rating_last_value, 4.25)

        task_3 = self.env['project.task'].create({
            'name': 'task 3',
            'project_id': self.project_pigs.id,
            'partner_id': self.partner_1.id,
            'user_ids': self.task_1.user_ids,
        })
        self.assertEqual(task_3.rating_avg, 0)
        self.assertEqual(task_3.rating_last_value, 0)

        # fix cache consistency
        self.env['project.task'].invalidate_model(['rating_avg', 'rating_last_value'])

        tasks = [self.task_1, self.task_2, task_3]
        for task in tasks:
            rating_values = task.read(['rating_avg', 'rating_last_value'])[0]
            task_report = self.env['report.project.task.user'].search_read([('project_id', '=', self.project_pigs.id), ('task_id', '=', task.id)], ['rating_avg', 'rating_last_value'])[0]
            self.assertDictEqual(task_report, rating_values, 'The rating average and the last rating value for the task 1 should be the same in the report and on the task.')
