# -*- coding: utf-8 -*-

from unittest.mock import patch, MagicMock

from odoo import Command
from odoo.addons.hr_timesheet.controllers.portal import TimesheetCustomerPortal
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tools.discuss import Store
from odoo.http import Response
from odoo.tests import tagged

from odoo.addons.project.tests.test_project_sharing import TestProjectSharingCommon

@tagged('post_install', '-at_install')
class TestPortalTimesheet(TestProjectSharingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_user = mail_new_test_user(cls.env, login='portal_user', groups='base.group_portal')
        cls.employee = cls.env['hr.employee'].create({'name': 'Grouping Employee'})

        # one full page plus two lines, all on the same day,
        # so that day's group is split across two pages
        cls.project_portal.message_subscribe(partner_ids=cls.portal_user.partner_id.ids)
        cls.page_size = 100
        cls.all_ts = cls.env['account.analytic.line'].create([{
            'name': 'work',
            'date': '2026-11-24',
            'project_id': cls.project_portal.id,
            'task_id': cls.task_portal.id,
            'employee_id': cls.employee.id,
            'unit_amount': 1,
        } for __ in range(cls.page_size + 2)])

    def test_ensure_fields_view_get_access(self):
        """ Ensure that the method _fields_view_get is accessible without
            raising an error for all portal users
        """
        # A portal collaborator is added to a project to enable the rule analytic.account.analytic.line.timesheet.portal.user
        self.project_portal.write({
            'collaborator_ids': [
                Command.create({'partner_id': self.user_portal.partner_id.id}),
            ],
        })
        for view in ['form', 'list']:
            # Ensure that uom.uom records are not present in cache
            self.env.invalidate_all()
            # Should not raise any access error
            self.env['account.analytic.line'].with_user(self.user_portal).get_view(view_type=view)

    def test_action_view_subtask_timesheet(self):
        """ Ensure that the action view_subtask_timesheet is accessible without
            raising an error for all portal users
        """
        # A portal collaborator is added to a project to enable the rule analytic.account.analytic.line.timesheet.portal.user
        self.project_portal.write({
            'collaborator_ids': [
                Command.create({'partner_id': self.user_portal.partner_id.id}),
            ],
        })
        action = self.task_portal.action_view_subtask_timesheet()
        tree_view_id = form_view_id = kanban_view_id = False
        for view_id, view_type in action['views']:
            if view_type == 'list':
                tree_view_id = view_id
            elif view_type == 'form':
                form_view_id = view_id
            elif view_type == 'kanban':
                kanban_view_id = view_id

        action = self.task_portal.with_user(self.user_portal).action_view_subtask_timesheet()
        portal_tree_view_id = self.env['ir.model.data']._xmlid_to_res_id('hr_timesheet.hr_timesheet_line_portal_tree')
        portal_form_view_id = self.env['ir.model.data']._xmlid_to_res_id('hr_timesheet.timesheet_view_form_portal_user')
        portal_kanban_view_id = self.env['ir.model.data']._xmlid_to_res_id('hr_timesheet.view_kanban_account_analytic_line_portal_user')
        if portal_tree_view_id and portal_form_view_id and portal_kanban_view_id:
            # no need to check that if the views are not installed or already removed
            for view_id, view_type in action['views']:
                if view_type == 'list':
                    self.assertEqual(view_id, portal_tree_view_id)
                elif view_type == 'form':
                    self.assertEqual(view_id, portal_form_view_id)
                elif view_type == 'kanban':
                    self.assertEqual(view_id, portal_kanban_view_id)

            self.env['ir.ui.view'].browse([portal_tree_view_id, portal_form_view_id, portal_kanban_view_id]).unlink()

        action = self.task_portal.with_user(self.user_portal).action_view_subtask_timesheet()
        for view_id, view_type in action['views']:
            if view_type == 'list':
                self.assertEqual(view_id, tree_view_id)
            elif view_type == 'form':
                self.assertEqual(view_id, form_view_id)
            elif view_type == 'kanban':
                self.assertEqual(view_id, kanban_view_id)

    def test_collaborators_accessible_by_timesheet_user(self):
        """Test that a restricted user (with only HR Timesheet User access) can
        access project collaborators (fetched when fetching a project) without
        getting an AccessError.
        """
        user = mail_new_test_user(
            self.env,
            login="employee_user",
            groups="hr_timesheet.group_hr_timesheet_user",
        )
        self.project_portal.collaborator_ids = [
            Command.create({"partner_id": self.partner_portal.id})
        ]
        store = Store()
        self.project_portal.with_user(user)._thread_to_store(store, request_list=["followers"])
        self.assertEqual(
            store.get_result()["mail.thread"][0]["collaborator_ids"],
            [{"id": self.partner_portal.id, "type": "partner"}],
        )

    def _call(self, user, **kwargs):
        controller = TimesheetCustomerPortal()
        controller.env = self.env(user=user, context=dict(self.env.context, lang='en_US'))
        captured = {}

        def mock_render(template, values=None, **kw):
            captured['template'] = template
            captured['values'] = values
            return Response('ok')  # a valid response, so route_wrapper is happy

        # Minimal stand-in for the request object the controller reads from.
        mock_request = MagicMock()
        mock_request.env = controller.env
        mock_request.render.side_effect = mock_render
        mock_request.httprequest.path = '/my/timesheets'

        with patch('odoo.addons.hr_timesheet.controllers.portal.request', mock_request), \
            patch('odoo.addons.portal.controllers.portal.request', mock_request):
            controller.portal_my_timesheets(**kwargs)

        return captured['values']

    def _assert_single_day_group(self, values, expected_lines):
        self.assertEqual(values['pager']['page_count'], 2, "portal user sees wrong number of pages")
        self.assertEqual(len(values['grouped_timesheets']), 1, "all lines are on one day, so one group")
        lines, displayed_hours = values['grouped_timesheets'][0]
        self.assertEqual(len(lines), expected_lines, "portal user sees wrong number of timesheets on page")
        self.assertEqual(
            displayed_hours, sum(self.all_ts.mapped('unit_amount')),
            "the day total must cover every page, not only this one",
        )

    def test_date_totals_first_page(self):
        values = self._call(self.portal_user, groupby='date')
        self._assert_single_day_group(values, expected_lines=self.page_size)

    def test_date_totals_last_page(self):
        values = self._call(self.portal_user, groupby='date', page=2)
        self._assert_single_day_group(values, expected_lines=2)
