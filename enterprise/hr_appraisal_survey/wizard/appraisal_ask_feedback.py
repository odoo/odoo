# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError
from odoo.tools import html_sanitize, is_html_empty

_logger = logging.getLogger(__name__)


class AppraisalAskFeedback(models.TransientModel):
    _name = 'appraisal.ask.feedback'
    _inherit = 'mail.composer.mixin'
    _description = "Ask Feedback for Appraisal"

    @api.model
    def default_get(self, fields):
        result = super(AppraisalAskFeedback, self).default_get(fields)
        appraisal = self.env['hr.appraisal'].browse(result.get('appraisal_id'))
        if 'survey_template_id' in fields and appraisal and not result.get('survey_template_id'):
            result['survey_template_id'] = appraisal.department_id.appraisal_survey_template_id.id or appraisal.company_id.appraisal_survey_template_id.id
        return result

    appraisal_id = fields.Many2one('hr.appraisal', default=lambda self: self.env.context.get('active_id', None))
    employee_id = fields.Many2one(related='appraisal_id.employee_id', string='Appraisal Employee')
    template_id = fields.Many2one(default=lambda self: self.env.ref('hr_appraisal_survey.mail_template_appraisal_ask_feedback', raise_if_not_found=False),
                                  domain=lambda self: [('model_id', '=', self.env['ir.model']._get('hr.appraisal').id)])
    attachment_ids = fields.Many2many(
        'ir.attachment', 'hr_appraisal_survey_mail_compose_message_ir_attachments_rel',
        'wizard_id', 'attachment_id', string='Attachments')
    author_id = fields.Many2one(
        'res.partner', string='Author', required=True,
        default=lambda self: self.env.user.partner_id.id,
    )
    survey_template_id = fields.Many2one('survey.survey', required=True, domain="[('survey_type', '=', 'appraisal')]")
    employee_ids = fields.Many2many(
        'hr.employee', string="Recipients", required=True)
    deadline = fields.Date(string="Answer Deadline", required=True, compute='_compute_deadline', store=True, readonly=False)

    # Overrides of mail.composer.mixin
    @api.depends('survey_template_id')  # fake trigger otherwise not computed in new mode
    def _compute_render_model(self):
        self.render_model = 'survey.user_input'

    @api.depends('employee_id')
    def _compute_subject(self):
        for wizard_su in self.filtered(lambda w: w.employee_id and w.template_id).sudo():
            wizard_su.subject = wizard_su._render_template(
                wizard_su.template_id.subject,
                'hr.appraisal',
                wizard_su.appraisal_id.ids,
                engine='inline_template',
                options={'post_process': True}
            )[wizard_su.appraisal_id.id]

    @api.depends('template_id', 'employee_ids')
    def _compute_body(self):
        for wizard in self:
            langs = set(wizard.employee_ids.user_partner_id.mapped('lang')) - {False}
            if len(langs) == 1:
                wizard = wizard.with_context(lang=langs.pop())
            super(AppraisalAskFeedback, wizard)._compute_body()

    @api.depends('appraisal_id.date_close')
    def _compute_deadline(self):
        date_in_month = fields.Date.today() + relativedelta(months=1)
        for wizard in self:
            # allow "last day" feedback fill by adding 1 day
            wizard.deadline = min(date_in_month, wizard.appraisal_id.date_close + relativedelta(days=1))

    @api.onchange('employee_ids')
    def _onchange_employee_ids(self):
        emailless_employees = self.employee_ids.filtered(lambda e: not (e.work_email or e.user_id.partner_id.email))
        if emailless_employees:
            warning = {
                'title': _('Missing email'),
                'message': _('The following employees do not have any email: \n%s',
                        ', '.join(emailless_employees.mapped('name'))),
                'type': 'notification',
            }
            self.employee_ids = self.employee_ids - emailless_employees
            return {'warning': warning}

    @api.onchange('template_id')
    def _onchange_template_id(self):
        self.attachment_ids = self.template_id.attachment_ids

    def _prepare_survey_anwers(self, employees):
        answers = self.env['survey.user_input']
        employees_info = employees.mapped(lambda employee: {
            'id': employee.id,
            'email': employee.work_email or employee.user_id.partner_id.email,
            'partner_id': employee.work_contact_id or employee.user_id.partner_id,
        })
        emails = [e['email'] for e in employees_info]
        partner_ids = [e['partner_id']['id'] for e in employees_info]

        existing_answers = self.env['survey.user_input'].search([
            '&', '&',
            ('survey_id', '=', self.survey_template_id.id),
            ('appraisal_id', '=', self.appraisal_id.id),
            '|',
            '&', ('partner_id', 'in', partner_ids), ('partner_id', '!=', False),
            '&', ('email', 'in', emails), ('email', '!=', False),
        ])
        employees_done = []
        if existing_answers:
            existing_answer_emails = existing_answers.filtered('email').mapped('email')
            existing_answer_partners_id = existing_answers.filtered('partner_id').mapped('partner_id')
            for employee_data in employees_info:
                if employee_data.get('email') in existing_answer_emails or employee_data.get('partner_id') in existing_answer_partners_id:
                    employees_done.append(employee_data)
            existing_answers = existing_answers.sorted(lambda answer: answer.create_date, reverse=True)
            for employee_done in employees_done:
                answers |= existing_answers\
                    .filtered(lambda a:
                        (a.partner_id and a.partner_id == employee_done.get('partner_id'))
                        or (a.email and a.email == employee_done.get('email'))
                    )[:1]

        for new_employee in filter(lambda e: e['id'] not in [e['id'] for e in employees_done], employees_info):
            answers |= self.survey_template_id.sudo()._create_answer(
                partner=new_employee['partner_id'], email=new_employee['email'], check_attempts=False, deadline=self.deadline)
        return answers

    def _send_mail(self, answer):
        """ Create mail specific for recipient containing notably its access token """
        ctx = {
            'logged_user': self.env.user.name,
            'employee': self.employee_id.name,
            'deadline': self.deadline,
        }
        body = self.with_context(**ctx)._render_field('body', answer.ids)[answer.id]
        mail_values = {
            'email_from': self.author_id.email_formatted,
            'author_id': self.author_id.id,
            'model': None,
            'res_id': None,
            'subject': self.subject,
            'body_html': body,
            'attachment_ids': [(4, att.id) for att in self.attachment_ids],
            'auto_delete': True,
        }
        if answer.partner_id:
            mail_values['recipient_ids'] = [Command.link(answer.partner_id.id)]
        else:
            mail_values['email_to'] = answer.email

        template_ctx = {
            'message': self.env['mail.message'].sudo().new(dict(body=mail_values['body_html'], record_name=self.survey_template_id.title)),
            'model_description': self.env['ir.model']._get('appraisal.ask.feedback').display_name,
            'company': self.env.company,
            'record': self,
        }
        body = self.env['ir.qweb']._render('mail.mail_notification_light', template_ctx, minimal_qcontext=True, raise_if_not_found=False)
        if body:
            mail_values['body_html'] = self.env['mail.render.mixin']._replace_local_links(body)
        else:
            _logger.warning('QWeb template mail.mail_notification_light not found when sending appraisal feedback mails. Sending without layouting.')

        return self.env['mail.mail'].sudo().create(mail_values)

    def action_send(self):
        self.ensure_one()

        answers = self._prepare_survey_anwers(self.employee_ids)
        answers.sudo().write({'appraisal_id': self.appraisal_id.id, 'deadline': self.deadline})
        for answer in answers:
            self._send_mail(answer)

        for employee in self.employee_ids.filtered(lambda e: e.user_id and e.user_id.has_group('hr_appraisal.group_hr_appraisal_user')):
            answer = answers.filtered(lambda l: l.partner_id and l.partner_id in [employee.user_id.partner_id, employee.work_contact_id])
            if answer:
                self.appraisal_id.with_context(mail_activity_quick_update=True).activity_schedule(
                    'mail.mail_activity_data_todo', self.deadline,
                    summary=_('Fill the feedback form on survey'),
                    note=_('An appraisal feedback was requested. Please take time to fill the <a href="%s" target="_blank">survey</a>',
                        answer.get_start_url()),
                    user_id=employee.user_id.id)

        self.appraisal_id.employee_feedback_ids |= self.employee_ids
        self.appraisal_id.survey_ids |= self.survey_template_id
        return {'type': 'ir.actions.act_window_close'}

    def action_save_as_template(self):
        """ hit save as template button: current form value will be a new
            template attached to the current document. """
        model = self.env['ir.model']._get('hr.appraisal')
        template_name = _("Appraisal: Ask Feedback new template")
        for record in self:
            values = {
                'name': template_name,
                'subject': record.subject or False,
                'body_html': record.body or False,
                'model_id': model.id,
                'use_default_to': True,
            }
            template = self.env['mail.template'].create(values)

            if record.attachment_ids:
                attachments = record.env['ir.attachment'].sudo().browse(record.attachment_ids.ids).filtered(lambda a: a.create_uid.id == record._uid)
                if attachments:
                    attachments.write({'res_model': template._name, 'res_id': template.id})
                template.attachment_ids |= record.attachment_ids

            # generate the saved template
            record.write({'template_id': template.id})

            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_id': template.id,
                'res_model': 'mail.template',
                'target': 'new',
            }
