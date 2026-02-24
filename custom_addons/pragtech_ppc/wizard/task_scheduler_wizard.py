# -*- coding: utf-8 -*-

from odoo.tools.translate import _
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class TaskScheduler(models.TransientModel):
    _name = 'task.scheduler'
    _description = 'Task Scheduler'

    project_id = fields.Many2one('project.project', 'Project Name', required=True)
    project_wbs = fields.Many2one('project.task', 'Project Wbs', required=True)

    sub_project = fields.Many2one('sub.project', 'Sub Project', required=True)

    task_category = fields.Many2one('task.category', 'Task Category')
    task_sub_category = fields.Many2one('task.sub.category', 'Task Sub Category')
    status = fields.Selection([
        ('all', 'All'),
        ('unplanned', 'Unplanned'),
        ('non_started', 'Non Started'),
        ('started', 'Started'),
        ('in_complete', 'In Complete'),
        ('completed', 'Completed'),
    ], string='Status', default='all')
    tasks_having = fields.Selection([
        ('planned', 'Planned'),
        ('actual', 'Actual')
    ], string='Tasks Having')
    from_date = fields.Date('From Date', default=str(datetime.now() + timedelta(days=-30)), required=True)
    to_date = fields.Date('To Date', default=fields.date.today(), required=True)
    start_finish_dates = fields.Selection([('start_date', 'Start Date'), ('finish_date', 'Finish Date')], 'Date', default='start_date')
    is_use = fields.Boolean('Select All')
    update_action = fields.Selection([
        ('planned_start', 'Planned Start'),
        ('planned_finish', 'Planned Finish'),
        ('actual_start', 'Actual Start'),
        ('actual_finish', 'Actual Finish'),
        ('status', 'Status'),
        ('completion', 'Completion %'),
        ('plannedstart_actualstart', 'Copy Planned Start to Actual Start'),
        ('plannedfinish_actualfinish', 'Copy Planned Finish to Actual Finish'),
    ], string='Update Action')
    scheduler_line_ids = fields.One2many('task.scheduler.line', 'scheduler_id', 'Scheduler Line')
    updated_date = fields.Date('Updated Date', default=fields.date.today())
    updated_percent = fields.Float("% Completion")
    updated_status = fields.Selection([
        ('unplanned', 'Unplanned'),
        ('non_started', 'Non Started'),
        ('started', 'Started'),
        ('in_complete', 'In Complete'),
        ('completed', 'Completed'),
        ], string='current Status')

    note = fields.Text('Note:', default='Completion (%) and actual finish date can be updated for only non billable tasks')

    """This method applies domain on all dropdown,as wbs of selected project and group of selected wbs and so on"""

    @api.depends('project_id', 'project_wbs', 'task_category')
    @api.onchange('project_id', 'project_wbs', 'task_category')
    def project_onchange(self):
        project_lst = []
        group_lst = []
        # self.name_lst = []
        if self.project_id:
            project_ids = self.env['project.task'].search([('project_id', '=', self.project_id.id)])
            for i in project_ids:
                for line in i.labour_estimate_line:
                    if line:
                        group_lst.append(line.labour_line_id.category_id.id)

                for line in i.material_estimate_line:
                    if line:
                        group_lst.append(line.material_line_id.category_id.id)

                project_lst.append(i.name)

        return {
            'domain': {
                'task_category': [('id', 'in', group_lst)],
            }
        }

    @api.onchange('project_id', 'sub_project')
    def onchange_project(self):
        if not self.project_id or not self.sub_project:
            self.project_wbs = None

    @api.onchange('project_id', 'project_wbs')
    def onchange_project_wbs(self):
        task_list = []
        estimated_material_obj = self.env['task.material.line'].search([('wbs_id', '=', self.project_wbs.id)])
        for i in estimated_material_obj:
            task_list.append(i.material_line_id.id)

        return {
            'domain': {
                'task_id': [('id', 'in', task_list)]
            }
        }

    @api.onchange('task_category')
    def onchange_task_category(self):
        return {
            'domain': {
                'task_sub_category': [('category_id', '=', self.task_category.id)]
            }
        }

    @api.onchange('is_use')
    @api.depends('is_use')
    def is_use_onchange(self):
        for line in self.scheduler_line_ids:
            line.update({'is_use': self.is_use})

    @api.onchange('scheduler_line_ids')
    def scheduler_line_ids_onchange(self):
        for scheduler_line in self.scheduler_line_ids:
            if not scheduler_line.is_use:
                self.is_use = False

    @api.depends('project_id', 'project_wbs', 'task_category', 'task_sub_category', 'status', 'tasks_having')
    def compute_task_lines(self):
        self.scheduler_line_ids.unlink()
        project_task_obj = self.env['project.task'].search([('project_id', '=', self.project_id.id), ('name', '=', self.project_wbs.name)])
        domain = []
        domain1 = []
        lines = []
        task_list = []
        if self.tasks_having == "planned" and self.start_finish_dates == 'start_date':
            domain1.append(('planed_start_date', '>=', self.from_date))
            domain1.append(('planed_start_date', '<=', self.to_date))
        if self.tasks_having == "planned" and self.start_finish_dates == 'finish_date':
            domain1.append(('planned_finish_date', '>=', self.from_date))
            domain1.append(('planned_finish_date', '<=', self.to_date))
        if self.tasks_having == "actual" and self.start_finish_dates == 'start_date':
            domain1.append(('actual_start_date', '>=', self.from_date))
            domain1.append(('actual_start_date', '<=', self.to_date))
        if self.tasks_having == "actual" and self.start_finish_dates == 'finish_date':
            domain1.append(('actual_finish_date', '>=', self.from_date))
            domain1.append(('actual_finish_date', '<=', self.to_date))
        if self.task_category:
            domain1.append(('category_id', '=', self.task_category.id))
        if self.task_sub_category:
            domain1.append(('sub_category_id', '=', self.task_sub_category.id))
        if self.status == 'unplanned':
            domain1.append(('planed_start_date', '=', None))
            domain1.append(('planned_finish_date', '=', None))
        if self.status == 'in_complete':
            domain1.append(('actual_finish_date', '=', None))

        domain.append(('wbs_id', '=', self.project_wbs.id))

        material_estimate_obj = project_task_obj.material_estimate_line.search(domain)

        estimated_task_ids = [line.material_line_id.id for line in material_estimate_obj]
        domain1.append(('id', 'in', list(set(estimated_task_ids))))
        tasks_to_schedule = self.env['project.task'].search(domain1)
        for project_task in tasks_to_schedule:
            vals = {
                'task_id': project_task.id,
                'group_id': project_task.parent_task_id.id,
                'task_category': project_task.category_id.id,
                'planned_start_date': project_task.planed_start_date,
                'planned_finish_date': project_task.planned_finish_date,
                'current_status': project_task.status,
                'actual_start_date': project_task.actual_start_date,
                'actual_finish_date': project_task.actual_finish_date,
                'completion_percent': project_task.percentage,
            }
            task_list.append((0, 0, vals))
            self.update({'scheduler_line_ids': task_list})

        return {
            'name': 'Task Scheduler',
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'task.scheduler',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.onchange('update_action')
    @api.depends('update_action')
    def onchange_update_action(self):
        for schedule_id in self.scheduler_line_ids:
            if self.update_action == 'completion' or self.update_action == 'actual_finish':
                if schedule_id.is_billable and schedule_id.is_use:
                    raise UserError(_('You cannot update % completion or actual finish date for billable tasks.'))

    def Update_tasks(self):
        status_list = []
        if self.scheduler_line_ids:
            for scheduler_line in self.scheduler_line_ids:
                if scheduler_line.is_use == True:
                    if self.update_action == 'plannedstart_actualstart':
                        scheduler_line.task_id.write({
                            'actual_start_date': scheduler_line.planned_start_date
                        })
                    if self.update_action == 'plannedfinish_actualfinish':
                        scheduler_line.task_id.write({
                            'actual_finish_date': scheduler_line.planned_finish_date
                        })
                    if self.update_action == 'planned_start':
                        scheduler_line.task_id.write({
                            'planed_start_date': self.updated_date
                        })
                    if self.update_action == 'planned_finish':
                        scheduler_line.task_id.write({
                            'planned_finish_date': self.updated_date
                        })
                    if self.update_action == 'actual_start':
                        scheduler_line.task_id.write({
                            'actual_start_date': self.updated_date
                        })

                    if self.update_action == 'status':
                        status_list.append(scheduler_line.current_status)
                        compressed_list = set(status_list)
                        if len(compressed_list) > 1:
                            raise UserError(_("Please select records having same status."))
                        else:
                            scheduler_line.task_id.write({
                                'status': self.updated_status
                            })

                    if self.update_action == 'actual_finish' or self.update_action == 'completion':
                        for line in self.scheduler_line_ids:
                            if line.is_use:
                                if line.task_id.is_billable:
                                    raise UserError(_('You cannot update % completion or actual finish date for billable tasks.'))
                                else:
                                    if self.update_action == 'actual_finish':
                                        scheduler_line.task_id.write({
                                            'actual_finish_date': self.updated_date
                                        })
                                    if self.update_action == 'completion':
                                        scheduler_line.task_id.write({
                                            'percentage': self.updated_percent
                                        })


class TaskSchedulerLine(models.TransientModel):
    _name = 'task.scheduler.line'
    _description = 'Task Scheduler Line'

    scheduler_id = fields.Many2one('task.scheduler', 'Scheduler')
    task_id = fields.Many2one('project.task', 'Task', readonly=True)
    group_id = fields.Many2one('project.task', 'Parent Group', readonly=True)
    task_category = fields.Many2one('task.category', 'Task Category', readonly=True)
    planned_start_date = fields.Date('Planned Start Date', readonly=True)
    planned_finish_date = fields.Date('Planned Finish Date', readonly=True)
    current_status = fields.Selection([
        ('unplanned', 'Unplanned'),
        ('non_started', 'Non Started'),
        ('started', 'Started'),
        ('in_complete', 'In Complete'),
        ('completed', 'Completed'),
        ], string='current Status', readonly=True)
    actual_start_date = fields.Date('Actual Start Date', readonly=True)
    actual_finish_date = fields.Date('Actual Finish Date', readonly=True)
    completion_percent = fields.Float("% Completion", readonly=True)
    is_use = fields.Boolean('Use')
    update_action = fields.Selection([
        ('planned_start', 'Planned Start'),
        ('planned_finish', 'Planned Finish'),
        ('actual_start', 'Actual Start'),
        ('actual_finish', 'Actual Finish'),
        ('status', 'Status'),
        ('completion', 'Completion %'),
        ('plannedstart_actualstart', 'Copy Planned Start to Actual Start'),
        ('plannedfinish_actualfinish', 'Copy Planned Finish to Actual Finish'),
    ], string='Update Action')

    is_billable = fields.Boolean('Billable', related='task_id.is_billable')

    @api.onchange('is_use')
    @api.depends('is_use', 'update_action', )
    def onchange_is_use(self):
        if self.is_use == True:
            self.update_action = self.scheduler_id.update_action

