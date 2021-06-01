# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_encode

from odoo import api, fields, models

STATUS_COLOR = {
    'on_track': 10,  # green
    'at_risk': 2,  # orange
    'off_track': 1,  # red
    'on_hold': 4,  # light blue
}

class ProjectUpdate(models.Model):
    _name = 'project.update'
    _description = 'Project Update'
    _order = 'create_date desc'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']

    def default_get(self, fields):
        result = super().default_get(fields)
        if 'project_id' in fields and not result.get('project_id'):
            result['project_id'] = self.env.context.get('active_id')
        if result.get('project_id'):
            project = self.env['project.project'].browse(result['project_id'])
            if 'progress' in fields and not result.get('progress'):
                result['progress'] = project.last_update_id.progress
            if 'description' in fields and not result.get('description'):
                result['description'] = self._build_description(project)
            if 'status' in fields and not result.get('status'):
                result['status'] = project.last_update_status
        return result

    name = fields.Char("Title", required=True, tracking=True)
    status = fields.Selection(selection=[
        ('on_track', 'On Track'),
        ('at_risk', 'At Risk'),
        ('off_track', 'Off Track'),
        ('on_hold', 'On Hold')
    ], required=True, tracking=True)
    color = fields.Integer(compute='_compute_color')
    progress = fields.Integer(tracking=True)
    progress_percentage = fields.Float(compute='_compute_progress_percentage')
    user_id = fields.Many2one('res.users', string='Author', required=True, default=lambda self: self.env.user)
    description = fields.Html()
    date = fields.Date(default=fields.Date.context_today, tracking=True)
    project_id = fields.Many2one('project.project', required=True)
    name_cropped = fields.Char(compute="_compute_name_cropped")

    @api.depends('status')
    def _compute_color(self):
        for update in self:
            update.color = STATUS_COLOR[update.status]

    @api.depends('progress')
    def _compute_progress_percentage(self):
        for u in self:
            u.progress_percentage = u.progress / 100

    @api.depends('name')
    def _compute_name_cropped(self):
        for u in self:
            u.name_cropped = (u.name[:57] + '...') if len(u.name) > 60 else u.name

    # ---------------------------------
    # ORM Override
    # ---------------------------------
    @api.model
    def create(self, vals):
        update = super().create(vals)
        update.project_id.last_update_id = update
        return update

    # ---------------------------------
    # Build default description
    # ---------------------------------
    @api.model
    def _build_description(self, project):
        template = self.env.ref('project.project_update_default_description')
        return template._render(self._get_template_values(project), engine='ir.qweb')

    @api.model
    def _get_template_values(self, project):
        return {
            'user': self.env.user,
            'project': project,
            'tasks': self._get_tasks_values(project),
            'milestones': self._get_milestone_values(project)
        }

    @api.model
    def _get_tasks_values(self, project):
        counts = project._get_tasks_analysis_counts(created=True)
        return {
            'open_tasks': counts['open_tasks_count'],
            'total_tasks': counts['tasks_count'],
            'created_tasks': counts['created_tasks_count'],
            'closed_tasks': self._get_last_stage_changes(project=project),
            'action': {
                'url_default': '/web#' + url_encode({
                    'menu_id': self.env.ref('project.menu_projects').id,
                    'action': self.env.ref('project.action_project_task_burndown_chart_report').id,
                    'active_id': project.id
                }),
                'name': 'action_burndown_open_tasks',
            }
        }

    @api.model
    def _get_last_stage_changes(self, project):
        query = """
            SELECT DISTINCT pt.id as task_id
                  FROM mail_message mm
            INNER JOIN mail_tracking_value mtv
                    ON mm.id = mtv.mail_message_id
            INNER JOIN ir_model_fields imf
                    ON mtv.field = imf.id
                   AND imf.model = 'project.task'
                   AND imf.name = 'stage_id'
            INNER JOIN project_task_type new_stage
                    ON mtv.new_value_integer = new_stage.id
            INNER JOIN project_task pt
                    ON mm.res_id = pt.id
                   AND pt.stage_id = new_stage.id
                 WHERE mm.model = 'project.task'
                   AND mm.message_type = 'notification'
                   AND pt.display_project_id = %(project_id)s
                   AND (new_stage.fold OR new_stage.is_closed)
                   AND mm.date > (now() at time zone 'utc')::date - '1 month'::interval
                   AND pt.active
        """
        self.env.cr.execute(query, {'project_id': project.id})
        task_ids = [res['task_id'] for res in self.env.cr.dictfetchall()]
        return self.env['project.task'].search_count([('id', 'in', task_ids)])

    @api.model
    def _get_milestone_values(self, project):
        Milestone = self.env['project.milestone']
        list_milestones = Milestone.search(
            [('project_id', '=', project.id),
             '|', ('deadline', '<', fields.Date.context_today(self) + relativedelta(years=1)), ('deadline', '=', False)])._get_data_list()
        updated_milestones = self._get_last_updated_milestone(project)
        created_milestones = Milestone.search(
            [('project_id', '=', project.id),
             ('create_date', '>', fields.Datetime.now() + timedelta(days=-30))])._get_data_list()
        return {
            'show_section': (list_milestones or updated_milestones or created_milestones) and True or False,
            'list': list_milestones,
            'updated': updated_milestones,
            'created': created_milestones,
        }

    @api.model
    def _get_last_updated_milestone(self, project):
        query = """
            SELECT DISTINCT pm.id as milestone_id,
                            pm.deadline as deadline,
                            FIRST_VALUE(old_value_datetime::date) OVER w_partition as old_value,
                            pm.deadline as new_value
                       FROM mail_message mm
                 INNER JOIN mail_tracking_value mtv
                         ON mm.id = mtv.mail_message_id
                 INNER JOIN ir_model_fields imf
                         ON mtv.field = imf.id
                        AND imf.model = 'project.milestone'
                        AND imf.name = 'deadline'
                 INNER JOIN project_milestone pm
                         ON mm.res_id = pm.id
                      WHERE mm.model = 'project.milestone'
                        AND mm.message_type = 'notification'
                        AND pm.project_id = %(project_id)s
                        AND mm.date > (now() at time zone 'utc')::date - '1 month'::interval
                     WINDOW w_partition AS (
                             PARTITION BY pm.id
                             ORDER BY mm.date ASC
                            )
                   ORDER BY pm.deadline ASC;
        """
        self.env.cr.execute(query, {'project_id': project.id})
        results = self.env.cr.dictfetchall()
        mapped_result = {res['milestone_id']: {'new_value': res['new_value'], 'old_value': res['old_value']} for res in results}
        milestones = self.env['project.milestone'].search([('id', 'in', list(mapped_result.keys()))])
        return [{
            **milestone._get_data(),
            'new_value': mapped_result[milestone.id]['new_value'],
            'old_value': mapped_result[milestone.id]['old_value'],
        } for milestone in milestones]

    def action_burndown_open_tasks(self):
        if not self.id or not self.project_id:
            return False
        action = self.env['ir.actions.act_window']._for_xml_id('project.action_project_task_burndown_chart_report')
        context = {
            'active_id': self.project_id.id,
            'search_default_project_id': self.project_id.id,
            'graph_mode': 'bar',
        }
        return dict(action, context=context)
