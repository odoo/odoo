# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _

class project_configuration(osv.osv_memory):
    _name = 'project.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'module_sale_service': fields.selection([
            (0, "No automatic task creation"),
            (1, 'Generate tasks from sale orders')
            ], "Sale Service",
            help='This feature automatically creates project tasks from service products in sale orders. '
                 'In order to make it work,  the product has to be a service and \'Create Task Automatically\' '
                 'has to be flagged on the procurement tab in the product form.\n'
                 '-This installs the module sale_service.'),
        'module_pad': fields.selection([
            (0, "Task description is a plain text"),
            (1, "Collaborative rich text on task description")
            ], "Pads",
            help='Lets the company customize which Pad installation should be used to link to new pads '
                 '(for example: http://ietherpad.com/).\n'
                 '-This installs the module pad.'),
        'module_project_timesheet': fields.selection([
            (0, "Do not record timesheets on tasks"),
            (1, "Record timesheet lines per tasks")
            ], "Timesheets on Project",
            help='This allows you to transfer the entries under tasks defined for Project Management to '
                 'the timesheet line entries for particular date and user, with the effect of creating, '
                 'editing and deleting either ways.\n'
                 '-This installs the module project_timesheet.'),
        'module_rating_project': fields.selection([
            (0, "No customer rating"),
            (1, 'Allow activating customer rating on projects, at issue completion')
            ], "Rating",
            help="This allows customers to give rating on provided services"),
        'module_project_issue_sheet': fields.selection([
            (0, "Do not track working hours on issues"),
            (1, "Activate timesheets on issues")
            ], "Timesheets Invoicing",
            help='Provides timesheet support for the issues/bugs management in project.\n'
                 '-This installs the module project_issue_sheet.'),
        'group_time_work_estimation_tasks': fields.selection([
            (0, "Do not estimate working time on tasks"),
            (1, "Manage time estimation on tasks")
            ], "Time on Tasks",
            implied_group='project.group_time_work_estimation_tasks',
            help="Allows you to compute Time Estimation on tasks."),
        'generate_project_alias': fields.selection([
            (0, "Do not create an email alias automatically"),
            (1, "Automatically generate an email alias at the project creation")
            ], "Project Alias",
            help="Odoo will generate an email alias at the project creation from project name."),
        'module_project_timesheet_synchro': fields.boolean("Timesheet app for Chrome/Android/iOS"),
        'module_project_forecast': fields.boolean("Forecasts, planning and Gantt charts"),
    }

    def onchange_time_estimation_project_timesheet(self, cr, uid, ids, group_time_work_estimation_tasks):
        if group_time_work_estimation_tasks:
            return {'value': {'group_tasks_work_on_tasks': True}}
        return {}

    def set_default_generate_project_alias(self, cr, uid, ids, context=None):
        config_value = self.browse(cr, uid, ids, context=context).generate_project_alias
        check = self.pool['res.users'].has_group(cr, uid, 'base.group_system')
        self.pool.get('ir.values').set_default(cr, check and SUPERUSER_ID or uid, 'project.config.settings', 'generate_project_alias', config_value)
