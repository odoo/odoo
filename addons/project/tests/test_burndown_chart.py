# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime
from freezegun import freeze_time

from odoo.fields import Command, Domain
from odoo.tests.common import tagged, HttpCase
from odoo.addons.mail.tests.common import MailCase

from .test_project_base import TestProjectCommon


class TestBurndownChartCommon(TestProjectCommon, MailCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.current_year = datetime.now().year
        create_date = datetime(cls.current_year - 1, 1, 5)
        Stage = cls.env['project.task.type']
        with cls.mock_datetime_and_now(cls, create_date):
            cls.todo_stage, cls.in_progress_stage, cls.testing_stage, cls.done_stage = Stage.create([{
                'sequence': 1,
                'name': 'TODO',
            }, {
                'sequence': 10,
                'name': 'In Progress',
            }, {
                'sequence': 20,
                'name': 'Testing',
            }, {
                'sequence': 30,
                'name': 'Done',
            }])

            cls.stages = cls.todo_stage + cls.in_progress_stage + cls.testing_stage + cls.done_stage
            cls.project = cls.env['project.project'].create({
                'name': 'Burndown Chart Test',
                'privacy_visibility': 'employees',
                'alias_name': 'project_burndown_chart',
                'type_ids': [Command.link(stage_id) for stage_id in cls.stages.ids],
            })
            cls.milestone = cls.env['project.milestone'].with_context({'mail_create_nolog': True}).create({
                'name': 'Test Milestone',
                'project_id': cls.project.id,
            })
            cls.task_a = cls.env['project.task'].create({
                'name': 'Task A',
                'priority': 0,
                'project_id': cls.project.id,
                'stage_id': cls.todo_stage.id,
            })
            cls.task_b = cls.task_a.copy({
                'name': 'Task B',
                'user_ids': [Command.set([cls.user_projectuser.id, cls.user_projectmanager.id])],
            })
            cls.task_c = cls.task_a.copy({
                'name': 'Task C',
                'partner_id': cls.partner_1.id,
                'user_ids': [Command.link(cls.user_projectuser.id)],
            })
            cls.task_d = cls.task_a.copy({
                'name': 'Task D',
                'milestone_id': cls.milestone.id,
                'user_ids': [Command.link(cls.user_projectmanager.id)],
            })
            cls.task_e = cls.task_a.copy({
                'name': 'Task E',
                'partner_id': cls.partner_1.id,
            })

            cls.project_2 = cls.env['project.project'].create({
                'name': 'Burndown Chart Test 2 mySearchTag',
                'privacy_visibility': 'employees',
                'alias_name': 'project_burndown_chart_2',
                'type_ids': [Command.link(stage_id) for stage_id in cls.stages.ids],
            })
            cls.task_g = cls.env['project.task'].create({
                'name': 'Task G',
                'priority': 0,
                'project_id': cls.project_2.id,
                'stage_id': cls.todo_stage.id,
                'user_ids': [Command.link(cls.user_projectuser.id)],
            })
            cls.task_h = cls.task_g.copy({
                'name': 'Task H',
                'user_ids': [Command.link(cls.user_projectmanager.id)],
            })
            cls.stage_1, cls.stage_2, cls.stage_3, cls.stage_4 = Stage.create([{
                'sequence': 1,
                'name': '1',
            }, {
                'sequence': 10,
                'name': '2',
            }, {
                'sequence': 20,
                'name': '3',
            }, {
                'sequence': 30,
                'name': '4',
            }])
            cls.stages_bis = cls.stage_1 | cls.stage_2 | cls.stage_3 | cls.stage_4
            cls.project_1 = cls.env['project.project'].create({
                'name': 'Burndown Chart Test',
                'privacy_visibility': 'employees',
                'alias_name': 'project_burndown_chart_bis',
                'type_ids': [Command.link(stage_id) for stage_id in cls.stages_bis.ids],
            })
            cls.task_bis = cls.env['project.task'].create({
                'name': 'Task',
                'priority': 0,
                'project_id': cls.project_1.id,
                'stage_id': cls.stage_1.id,
            })
            (cls.task_bis + cls.task_a + cls.task_b + cls.task_c + cls.task_d + cls.task_g + cls.task_h).invalidate_recordset(['duration_tracking'])

        with cls.mock_datetime_and_now(cls, datetime(cls.current_year - 1, 12, 20)):
            # Create a new task to check if a task without changing its stage is taken into account
            cls.task_f = cls.env['project.task'].create({
                'name': 'Task F',
                'priority': 0,
                'project_id': cls.project.id,
                'milestone_id': cls.milestone.id,
                'stage_id': cls.todo_stage.id,
            })
            cls.task_f.invalidate_recordset(['duration_tracking'])

        cls.deleted_domain = Domain('project_id', '!=', False) & Domain('project_id', '=', cls.project_1.id)

        # Precommit to have the records in db and allow to rollback at the end of test
        cls.env.cr.flush()

        with cls.mock_datetime_and_now(cls, datetime(cls.current_year - 1, 2, 10)):
            (cls.task_a + cls.task_b).write({'stage_id': cls.in_progress_stage.id})
            cls.env.cr.flush()

        with cls.mock_datetime_and_now(cls, datetime(cls.current_year - 1, 2, 20)):
            cls.task_c.write({'stage_id': cls.in_progress_stage.id})
            cls.env.cr.flush()

        with cls.mock_datetime_and_now(cls, datetime(cls.current_year - 1, 3, 15)):
            (cls.task_d + cls.task_e).write({'stage_id': cls.in_progress_stage.id})
            cls.env.cr.flush()

        with cls.mock_datetime_and_now(cls, datetime(cls.current_year - 1, 4, 10)):
            (cls.task_a + cls.task_b).write({'stage_id': cls.testing_stage.id})
            cls.env.cr.flush()

        with cls.mock_datetime_and_now(cls, datetime(cls.current_year - 1, 5, 12)):
            cls.task_c.write({'stage_id': cls.testing_stage.id})
            cls.env.cr.flush()

        with cls.mock_datetime_and_now(cls, datetime(cls.current_year - 1, 6, 25)):
            cls.task_d.write({'stage_id': cls.testing_stage.id})
            cls.env.cr.flush()

        with cls.mock_datetime_and_now(cls, datetime(cls.current_year - 1, 7, 25)):
            cls.task_e.write({'stage_id': cls.testing_stage.id})
            cls.env.cr.flush()

        with cls.mock_datetime_and_now(cls, datetime(cls.current_year - 1, 8, 5)):
            cls.task_a.write({'stage_id': cls.done_stage.id, 'state': '1_done'})
            cls.env.cr.flush()

        with cls.mock_datetime_and_now(cls, datetime(cls.current_year - 1, 9, 10)):
            cls.task_b.write({'stage_id': cls.done_stage.id, 'state': '1_done'})
            cls.env.cr.flush()

        with cls.mock_datetime_and_now(cls, datetime(cls.current_year - 1, 10, 5)):
            cls.task_c.write({'stage_id': cls.done_stage.id, 'state': '1_done'})
            cls.task_a.write({'state': '1_canceled'})
            cls.env.cr.flush()

        with cls.mock_datetime_and_now(cls, datetime(cls.current_year - 1, 11, 25)):
            cls.task_d.write({'stage_id': cls.done_stage.id, 'state': '1_done'})
            cls.task_b.write({'state': '1_canceled'})
            cls.env.cr.flush()

        with cls.mock_datetime_and_now(cls, datetime(cls.current_year - 1, 12, 12)):
            cls.task_e.write({'stage_id': cls.done_stage.id, 'state': '1_done'})
            cls.env.cr.flush()

        with cls.mock_datetime_and_now(cls, datetime(cls.current_year - 1, 12, 24)):
            cls.task_f.write({'state': '1_canceled'})
            cls.env.cr.flush()

        with cls.mock_datetime_and_now(cls, datetime(cls.current_year - 1, 2, 10)):
            cls.task_bis.write({'stage_id': cls.stage_2.id})
            cls.env.cr.flush()

        with cls.mock_datetime_and_now(cls, datetime(cls.current_year - 1, 3, 10)):
            (cls.task_bis).write({'stage_id': cls.stage_3.id})
            cls.env.cr.flush()

        with cls.mock_datetime_and_now(cls, datetime(cls.current_year - 1, 4, 10)):
            (cls.task_bis).write({'stage_id': cls.stage_4.id})
            cls.env.cr.flush()


class TestBurndownChart(TestBurndownChartCommon):

    def map_read_group_result(self, read_group_result):
        return [(res['date:month'][1], res['stage_id'][0], int(res['__count'])) for res in read_group_result if res['stage_id'][1]]

    def check_read_group_results(self, domain, expected_results_dict):
        read_group_result = self.env['project.task.burndown.chart.report'].formatted_read_group(
            domain, ['date:month', 'stage_id'], ['__count'])
        read_group_result_dict = self.map_read_group_result(read_group_result)
        parsed = []
        for month_year, stage, value in read_group_result_dict:
            parsed.append((month_year, stage, value))
        result = defaultdict(dict)
        stage_cumulative = defaultdict(int)

        for year_month, stage, value in parsed:
            stage_cumulative[stage] += value
            result[year_month, stage] = stage_cumulative[stage]
        result = {k: v for k, v in result.items() if v}
        self.assertDictEqual(result, expected_results_dict)

    def test_burndown_chart(self):
        burndown_chart_domain = [('project_id', '!=', False)]
        project_domain = [('project_id', '=', self.project.id)]

        # Check that we get the expected results for the complete data of `self.project`.
        project_expected_dict = {
            ('January %s' % (self.current_year - 1), self.todo_stage.id): 5,
            ('February %s' % (self.current_year - 1), self.todo_stage.id): 2,
            ('February %s' % (self.current_year - 1), self.in_progress_stage.id): 3,
            ('March %s' % (self.current_year - 1), self.in_progress_stage.id): 5,
            ('April %s' % (self.current_year - 1), self.in_progress_stage.id): 3,
            ('April %s' % (self.current_year - 1), self.testing_stage.id): 2,
            ('May %s' % (self.current_year - 1), self.in_progress_stage.id): 2,
            ('May %s' % (self.current_year - 1), self.testing_stage.id): 3,
            ('June %s' % (self.current_year - 1), self.in_progress_stage.id): 1,
            ('June %s' % (self.current_year - 1), self.testing_stage.id): 4,
            ('July %s' % (self.current_year - 1), self.testing_stage.id): 5,
            ('August %s' % (self.current_year - 1), self.testing_stage.id): 4,
            ('August %s' % (self.current_year - 1), self.done_stage.id): 1,
            ('September %s' % (self.current_year - 1), self.testing_stage.id): 3,
            ('September %s' % (self.current_year - 1), self.done_stage.id): 2,
            ('October %s' % (self.current_year - 1), self.testing_stage.id): 2,
            ('October %s' % (self.current_year - 1), self.done_stage.id): 3,
            ('November %s' % (self.current_year - 1), self.testing_stage.id): 1,
            ('November %s' % (self.current_year - 1), self.done_stage.id): 4,
            ('December %s' % (self.current_year - 1), self.todo_stage.id): 1,
            ('December %s' % (self.current_year - 1), self.done_stage.id): 5,
        }

        # Check that we get the expected results for the complete data of `self.project`.
        self.check_read_group_results(Domain.AND([burndown_chart_domain, project_domain]), project_expected_dict)
        # Check that we get the expected results for the complete data of `self.project` & `self.project_2` using an
        # `ilike` in the domain.
        all_projects_domain_with_ilike = Domain.OR([project_domain, [('project_id', 'ilike', 'mySearchTag')]])
        project_expected_dict = {key: val if key[1] != self.todo_stage.id else val + 2 for key, val in project_expected_dict.items()}
        project_expected_dict['March %s' % (self.current_year - 1), self.todo_stage.id] = 2

        self.check_read_group_results(Domain.AND([burndown_chart_domain, all_projects_domain_with_ilike]), project_expected_dict)

        date_from, date_to = ('%s-01-01' % (self.current_year - 1), '%s-03-01' % (self.current_year - 1))

        date_and_user_domain = [('date', '>=', date_from), ('date', '<', date_to), ('user_ids', 'ilike', 'ProjectUser')]
        complex_domain_expected_dict = {
            ('January %s' % (self.current_year - 1), self.todo_stage.id): 3,
            ('February %s' % (self.current_year - 1), self.todo_stage.id): 1,
            ('February %s' % (self.current_year - 1), self.in_progress_stage.id): 2,
        }
        complex_domain = Domain.AND([burndown_chart_domain, all_projects_domain_with_ilike, date_and_user_domain])
        self.check_read_group_results(complex_domain, complex_domain_expected_dict)

        date_and_user_domain = [('date', '>=', date_from), ('date', '<', date_to)]
        milestone_domain = [('milestone_id', 'ilike', 'Test')]
        complex_domain = Domain.AND([burndown_chart_domain, all_projects_domain_with_ilike, date_and_user_domain, milestone_domain])
        # There were no changes in February, and because the graph is cumulative, it only reflects the data from January.
        complex_domain_expected_dict = {
            ('January %s' % (self.current_year - 1), self.todo_stage.id): 1,
        }
        self.check_read_group_results(complex_domain, complex_domain_expected_dict)

    def burndown_chart_stage_delete_stage_1(self):
        """
        Currently, this behavior is not working as expected. The key 'Jan year-1, stage_1.id' is not present as expected, but there's an extra unwanted key
        'Jan year-1, stage_2.id' is present instead
        """
        with freeze_time('%s-08-10' % (self.current_year - 1)):
            self.stage_1.unlink()
            self.env.cr.flush()
        expected_dict = self.get_expected_dict()
        del expected_dict[('January %s' % (self.current_year - 1), self.stage_1.id)]
        self.check_read_group_results(self.deleted_domain, expected_dict)

    def burndown_chart_stage_delete_stage_2(self):
        """
        Currently, this behavior is not working as expected. The key 'Feb year-1, stage_2.id' is not present as expected, but there's an extra unwanted key
        'Feb year-1, stage_3.id' is present instead
        """
        with freeze_time('%s-08-10' % (self.current_year - 1)):
            self.stage_2.unlink()
            self.env.cr.flush()
        expected_dict = self.get_expected_dict()
        del expected_dict[('February %s' % (self.current_year - 1), self.stage_2.id)]
        self.check_read_group_results(self.deleted_domain, expected_dict)

    def test_burndown_chart_stage_delete_stage_3(self):
        """
        We assume that the timeline is based on the duration spent in each specific stage. Therefore, if a stage is deleted, the related
        time spent in that stage will also be removed.
        """
        with self.mock_datetime_and_now(datetime(self.current_year - 1, 1, 15)):
            self.stage_3.unlink()
            self.env.cr.flush()
        expected_dict = {
            ('January %s' % (self.current_year - 1), self.stage_1.id): 1,
            ('February %s' % (self.current_year - 1), self.stage_2.id): 1,
            ('March %s' % (self.current_year - 1), self.stage_4.id): 1,
        }
        self.check_read_group_results(self.deleted_domain, expected_dict)

    def burndown_chart_all_stage_deleted(self):
        """
        Currently, this behavior is not working as expected. An extra task is added for every month fetched by the query.
        e.a. If the expected dict is :
        {('April 2022', 390): 1, ('May 2022', 390): 1, ('June 2022', 390): 1, ('July 2022', 390): 1, ('August 2022', 390): 1, ('September 2022', 390): 1, etc : 1}
        The fetched dict will be :
        {('January 2022', 389): 1, ('February 2022', 389): 1, ('March 2022', 389): 1, ('April 2022', 390): 2, ('May 2022', 390): 2, ('June 2022', 390): 2, ('July 2022', 390): 2,
        ('August 2022', 390): 2, ('September 2022', 390): 2, etc :2 }
        """
        with freeze_time('%s-08-10' % (self.current_year - 1)):
            (self.stage_1 | self.stage_2 | self.stage_3).unlink()
            self.env.cr.flush()
        expected_dict = self.get_expected_dict()
        del expected_dict[('January %s' % (self.current_year - 1), self.stage_1.id)]
        del expected_dict[('February %s' % (self.current_year - 1), self.stage_2.id)]
        del expected_dict[('March %s' % (self.current_year - 1), self.stage_3.id)]
        self.check_read_group_results(self.deleted_domain, expected_dict)

    def get_expected_dict(self):
        expected_dict = {
            ('January %s' % (self.current_year - 1), self.stage_1.id): 1,
            ('February %s' % (self.current_year - 1), self.stage_2.id): 1,
            ('March %s' % (self.current_year - 1), self.stage_3.id): 1,
            ('April %s' % (self.current_year - 1), self.stage_4.id): 1,
            ('May %s' % (self.current_year - 1), self.stage_4.id): 1,
            ('June %s' % (self.current_year - 1), self.stage_4.id): 1,
            ('July %s' % (self.current_year - 1), self.stage_4.id): 1,
            ('August %s' % (self.current_year - 1), self.stage_4.id): 1,
            ('September %s' % (self.current_year - 1), self.stage_4.id): 1,
            ('October %s' % (self.current_year - 1), self.stage_4.id): 1,
            ('November %s' % (self.current_year - 1), self.stage_4.id): 1,
            ('December %s' % (self.current_year - 1), self.stage_4.id): 1,
        }
        months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
                  'November', 'December']
        current_month = datetime.now().month

        for i in range(current_month):
            month_key = f"{months[i]} {self.current_year}"
            expected_dict[(month_key, self.stage_4.id)] = 1
        return expected_dict


@tagged('-at_install', 'post_install')
class TestBurndownChartTour(HttpCase, TestBurndownChartCommon):

    def test_burndown_chart_tour(self):
        # Test customizing personal stages as a project user
        self.start_tour('/odoo', 'burndown_chart_tour', login="admin")
