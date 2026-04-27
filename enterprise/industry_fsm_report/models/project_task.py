# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval

from odoo import api, fields, models, _


class ProjectTask(models.Model):
    _inherit = "project.task"

    allow_worksheets = fields.Boolean(related='project_id.allow_worksheets')
    worksheet_template_id = fields.Many2one(
        'worksheet.template', string="Worksheet Template",
        compute='_compute_worksheet_template_id', store=True, readonly=False, tracking=True,
        domain="[('res_model', '=', 'project.task'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        group_expand='_group_expand_worksheet_template_id',
        help="Create templates for each type of intervention you have and customize their content with your own custom fields.")
    worksheet_count = fields.Integer(compute='_compute_worksheet_count', compute_sudo=True, export_string_translation=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS | {
            'allow_worksheets',
            'worksheet_count',
            'worksheet_template_id',
        }

    @api.depends('worksheet_count', 'allow_worksheets')
    def _compute_display_conditions_count(self):
        super()._compute_display_conditions_count()
        for task in self:
            enabled = task.display_enabled_conditions_count
            satisfied = task.display_satisfied_conditions_count
            enabled += task.allow_worksheets
            satisfied += task.allow_worksheets and task.worksheet_count
            task.update({
                'display_enabled_conditions_count': enabled,
                'display_satisfied_conditions_count': satisfied
            })

    @api.depends(
        'allow_worksheets', 'timer_start', 'worksheet_signature',
        'display_satisfied_conditions_count', 'display_enabled_conditions_count',
    )
    def _compute_display_sign_report_buttons(self):
        for task in self:
            sign_p, sign_s = True, True
            if (
                not task.allow_worksheets
                or task.timer_start
                or task.worksheet_signature
                or not task.display_satisfied_conditions_count
            ):
                sign_p, sign_s = False, False
            else:
                if task.display_enabled_conditions_count == task.display_satisfied_conditions_count:
                    sign_s = False
                else:
                    sign_p = False
            task.update({
                'display_sign_report_primary': sign_p,
                'display_sign_report_secondary': sign_s,
            })

    @api.depends(
        'allow_worksheets', 'timer_start', 'display_satisfied_conditions_count',
        'display_enabled_conditions_count', 'fsm_is_sent',
    )
    def _compute_display_send_report_buttons(self):
        for task in self:
            send_p, send_s = True, True
            if (
                not task.allow_worksheets
                or task.timer_start
                or not task.display_satisfied_conditions_count
                or task.fsm_is_sent
            ):
                send_p, send_s = False, False
            else:
                if task.display_enabled_conditions_count == task.display_satisfied_conditions_count:
                    send_s = False
                else:
                    send_p = False
            task.update({
                'display_send_report_primary': send_p,
                'display_send_report_secondary': send_s,
            })

    @api.depends('project_id')
    def _compute_worksheet_template_id(self):
        # Change worksheet when the project changes, not project.allow_worksheet
        for task in self:
            if not task.worksheet_template_id and task.allow_worksheets:
                task.worksheet_template_id = task.parent_id.worksheet_template_id.id\
                    if task.parent_id else task.project_id.worksheet_template_id.id

    @api.depends('worksheet_template_id')
    def _compute_worksheet_count(self):
        for record in self:
            worksheet_count = 0
            if record.worksheet_template_id:
                Worksheet = self.env[record.worksheet_template_id.sudo().model_id.model]
                worksheet_count = Worksheet.search_count([('x_project_task_id', 'in', record.ids)])
            record.worksheet_count = worksheet_count

    @api.model
    def _group_expand_worksheet_template_id(self, worksheets, domain):
        start_date = self._context.get('gantt_start_date')
        scale = self._context.get('gantt_scale')
        if not (start_date and scale):
            return worksheets
        domain = self._expand_domain_dates(domain)
        search_on_comodel = self._search_on_comodel(domain, "worksheet_template_id", "worksheet.template")
        if search_on_comodel:
            return search_on_comodel
        else:
            return self.search(domain).worksheet_template_id

    def action_fsm_worksheet(self):
        if self.env.user.has_group('industry_fsm.group_fsm_manager'):
            worksheets_count = self.env['worksheet.template'].search_count([('res_model', '=', 'project.task')], limit=2)
            if worksheets_count == 1:
                current_template = self.worksheet_template_id
                if not current_template.worksheet_count and current_template.name == 'Default Worksheet':
                    wizard = self.env['worksheet.template.load.wizard'].create({'task_id': self.id})
                    action = {
                        'name': _('Explore Worksheets Using an Example Template'),
                        'type': 'ir.actions.act_window',
                        'res_model': 'worksheet.template.load.wizard',
                        'views': [[False, 'form']],
                        'view_id': 'view_worksheet_template_load_form',
                        'target': 'new',
                        'res_id': wizard.id,
                    }
                    return action
        return self.open_fsm_worksheet()

    def open_fsm_worksheet(self):
        action = self.worksheet_template_id.action_id.sudo().read()[0]
        worksheet = self.env[self.worksheet_template_id.sudo().model_id.model].search([('x_project_task_id', '=', self.id)])
        context = literal_eval(action.get('context', '{}'))
        action.update({
            'res_id': worksheet.id,
            'views': [(False, 'form')],
            'context': {
                **context,
                'edit': True,
                'default_x_project_task_id': self.id,
            },
        })
        return action

    def _get_action_fsm_task_mobile_view(self):
        action = super()._get_action_fsm_task_mobile_view()
        action['context']['industry_fsm_has_same_worksheet_template'] = self.worksheet_template_id == self.project_id.sudo().worksheet_template_id
        return action

    def _is_fsm_report_available(self):
        self.ensure_one()
        return super()._is_fsm_report_available() or self.worksheet_count
