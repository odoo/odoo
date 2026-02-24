# -*- coding: utf-8 -*-

import json
import logging
import datetime
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class GanttChartController(http.Controller):

    @http.route(['/get_project_tasks'], type='json', auth='user', website=True)
    def get_project_tasks(self, **kwargs):
        project_id = request.session['project_id_wizard']
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry
        wizard = request.env['wizard.gantt']
        result = wizard.get_data(project_id)

        if result:
            return json.dumps(result)
        else:
            return False

    @http.route(['/save_project_tasks'], type='json', auth='user', website=True, csrf=False)
    def save_project_tasks(self, **kwargs):
        if 'project' in kwargs:
            if 'tasks' in kwargs['project']:
                for task in kwargs['project']['tasks']:
                    if  task['depends']:
                        project_task_new = request.env['project.task'].search([('id', '=', task['dbid'])])
                        if project_task_new:
                            project_task_new.depend_id = task['depends']
                    project_task = request.env['project.task'].search([('id', '=', task['dbid'])])
                    start = datetime.datetime.fromtimestamp(task['start'] / 1000).strftime('%Y-%m-%d')
                    end = datetime.datetime.fromtimestamp(task['end'] / 1000).strftime('%Y-%m-%d')
                    if project_task:
                        project_task.planed_start_date = start
                        project_task.planned_finish_date = end
                        project_task.day_count = task['duration']

        return kwargs['project']
    
