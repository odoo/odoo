# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectTask(models.Model):
    _inherit = "project.task"

    allow_worksheets = fields.Boolean(related='project_id.allow_worksheets')
    worksheet_template_id = fields.Many2one(
        'worksheet.template', string="Worksheet Template",
        compute='_compute_worksheet_template_id', store=True, readonly=False, tracking=True,
        domain="[('res_model', '=', 'project.task'), '|', ('company_ids', '=', False), ('company_ids', 'in', company_id)]",
        group_expand='_group_expand_worksheet_template_id',
        help="Create templates for each type of intervention you have and customize their content with your own custom fields.")
    worksheet_count = fields.Integer(compute='_compute_worksheet_count', compute_sudo=True)
    worksheet_color = fields.Integer(related='worksheet_template_id.color')
    display_sign_report_primary = fields.Boolean(compute='_compute_display_sign_report_buttons')
    display_sign_report_secondary = fields.Boolean(compute='_compute_display_sign_report_buttons')
    display_send_report_primary = fields.Boolean(compute='_compute_display_send_report_buttons')
    display_send_report_secondary = fields.Boolean(compute='_compute_display_send_report_buttons')
    worksheet_signature = fields.Binary('Signature', copy=False, attachment=True)
    worksheet_signed_by = fields.Char('Signed By', copy=False)
    fsm_is_sent = fields.Boolean('Is Worksheet sent', readonly=True, copy=False)

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
        'allow_worksheets', 'worksheet_template_id', 'timer_start', 'worksheet_signature',
        'display_satisfied_conditions_count', 'display_enabled_conditions_count')
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
        'allow_worksheets', 'worksheet_template_id', 'timer_start',
        'display_satisfied_conditions_count', 'display_enabled_conditions_count',
        'fsm_is_sent')
    def _compute_display_send_report_buttons(self):
        for task in self:
            send_p, send_s = True, True
            if (
                not task.allow_worksheets
                or task.timer_start
                or not task.display_satisfied_conditions_count
                or task.fsm_is_sent
                or not task.worksheet_template_id
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
                worksheet_count = Worksheet.search_count([('x_project_task_id', '=', record.id)])
            record.worksheet_count = worksheet_count

    @api.model
    def _group_expand_worksheet_template_id(self, worksheets, domain, order):
        start_date = self._context.get('gantt_start_date')
        scale = self._context.get('gantt_scale')
        if not (start_date and scale):
            return worksheets
        domain = self._expand_domain_dates(domain)
        search_on_comodel = self._search_on_comodel(domain, "worksheet_template_id", "worksheet.template", order)
        if search_on_comodel:
            return search_on_comodel
        else:
            return self.search(domain).worksheet_template_id

    def has_to_be_signed(self):
        self.ensure_one()
        return self._is_fsm_report_available() and not self.worksheet_signature

    def action_fsm_worksheet(self):
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

    def action_preview_worksheet(self):
        self.ensure_one()
        if not self.worksheet_template_id:
            raise UserError(_("To send the report, you need to select a worksheet template"))
        source = 'fsm' if self._context.get('fsm_mode', False) else 'project'
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(query_string=f'&source={source}')
        }

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Worksheet %s - %s' % (self.name, self.partner_id.name)

    def _is_fsm_report_available(self):
        self.ensure_one()
        return self.worksheet_count or self.timesheet_ids

    def action_send_report(self):
        tasks_with_report = self.filtered(
            lambda task:
                (task.display_send_report_primary or task.display_send_report_secondary)
                and task._is_fsm_report_available()
        )
        if not tasks_with_report:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("There are no reports to send."),
                    'sticky': False,
                    'type': 'danger',
                }
            }

        template_id = self.env.ref('industry_fsm_report.mail_template_data_task_report').id
        self.message_subscribe(partner_ids=tasks_with_report.partner_id.ids)
        return {
            'name': _("Send report"),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_composition_mode': 'mass_mail' if len(tasks_with_report.ids) > 1 else 'comment',
                'default_model': 'project.task',
                'default_res_ids': tasks_with_report.ids,
                'default_template_id': template_id,
                'fsm_mark_as_sent': True,
                'mailing_document_based': True,
            },
        }

    def _message_post_after_hook(self, message, msg_vals):
        if self.env.context.get('fsm_mark_as_sent') and not self.fsm_is_sent:
            self.fsm_is_sent = True
        return super()._message_post_after_hook(message, msg_vals)
