# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from werkzeug.urls import url_encode


class GenerateSimulationLink(models.TransientModel):
    _name = 'generate.simulation.link'
    _description = 'Create an Offer'

    def _default_validity(self):
        validity = 30
        active_model = self.env.context.get('active_model')
        if active_model == 'hr.applicant':
            validity = self.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.access_token_validity', default=30)
        elif active_model == 'hr.contract':
            validity = self.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.employee_salary_simulator_link_validity', default=30)
        return validity

    contract_id = fields.Many2one(
        'hr.contract', string="Contract Template", required=True,
        domain="['|', ('employee_id', '=', False), ('employee_id', '=', employee_id)]")
    employee_contract_id = fields.Many2one('hr.contract')
    employee_id = fields.Many2one('hr.employee', related='employee_contract_id.employee_id')
    final_yearly_costs = fields.Monetary(string="Yearly Cost", compute='_compute_final_yearly_costs', store=True, readonly=False, required=True)
    currency_id = fields.Many2one(related='contract_id.currency_id')
    applicant_id = fields.Many2one('hr.applicant')
    job_title = fields.Char("Job Title", store=True, readonly=False)
    company_id = fields.Many2one('res.company', compute="_compute_company_id")
    employee_job_id = fields.Many2one(
        'hr.job', string="Job Position",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    department_id = fields.Many2one(
        'hr.department', string="Department",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    contract_start_date = fields.Date("Contract Start Date", default=fields.Date.context_today)

    email_to = fields.Char('Email To', compute='_compute_email_to', store=True, readonly=False)
    display_warning_message = fields.Boolean(compute='_compute_warning_message', compute_sudo=True)
    validity = fields.Integer("Link Expiration Date", default=_default_validity)

    @api.depends('contract_id.final_yearly_costs')
    def _compute_final_yearly_costs(self):
        for wizard in self:
            wizard.final_yearly_costs = wizard.contract_id.final_yearly_costs

    @api.depends('contract_id')
    def _compute_company_id(self):
        for wizard in self:
            if wizard.contract_id:
                wizard.company_id = wizard.contract_id.company_id
            else:
                wizard.company_id = wizard.env.company.id

    @api.depends('employee_id.work_email', 'applicant_id.email_from')
    def _compute_email_to(self):
        for wizard in self:
            if wizard.employee_id:
                wizard.email_to = wizard.employee_id.work_email
            elif wizard.applicant_id and wizard.env.context.get('active_model') == 'hr.applicant':
                wizard.email_to = wizard.applicant_id.email_from

    def _get_url_triggers(self):
        return ['applicant_id', 'final_yearly_costs', 'employee_contract_id', 'job_title', 'employee_job_id', 'department_id', 'contract_start_date']

    @api.depends(lambda self: [key for key in self._fields.keys()])
    def _compute_url(self):
        for wizard in self:
            if wizard.contract_id:
                url = wizard.contract_id.get_base_url() + '/salary_package/simulation/contract/%s?' % (wizard.contract_id.id)
                params = {}
                for trigger in self._get_url_triggers():
                    if wizard[trigger]:
                        params[trigger] = wizard[trigger].id if isinstance(wizard[trigger], models.BaseModel) else wizard[trigger]
                if wizard.applicant_id:
                    params['token'] = wizard.applicant_id.access_token
                if wizard.contract_start_date:
                    params['contract_start_date'] = wizard.contract_start_date
                if params:
                    url = url + url_encode(params)
                wizard.url = url
            else:
                wizard.url = ""

    @api.depends('contract_id')
    def _compute_warning_message(self):
        for wizard in self:
            if (wizard.env.context.get('active_model') == 'hr.applicant' and not wizard.applicant_id.partner_name) and wizard.contract_id:
                wizard.display_warning_message = True
            else:
                wizard.display_warning_message = False

    @api.onchange('applicant_id', 'employee_contract_id')
    def _onchange_job_selection(self):
        self.employee_job_id = self.employee_contract_id.job_id or self.applicant_id.job_id

    @api.onchange('employee_job_id')
    def _onchange_employee_job_id(self):
        self.job_title = self.employee_job_id.name
        if self.employee_job_id.department_id:
            self.department_id = self.employee_job_id.department_id

        if self.employee_contract_id and (self.employee_job_id == self.employee_contract_id.job_id or not self.employee_job_id.default_contract_id):
            self.contract_id = self.employee_contract_id
        else:
            self.contract_id = self.employee_job_id.default_contract_id

    @api.depends('employee_id', 'applicant_id')
    def _compute_display_name(self):
        for w in self:
            w.display_name = w.employee_id.name or w.applicant_id.partner_name

    def _get_offer_values(self):
        self.ensure_one()
        return {
            'company_id': self.env.company.id,
            'contract_template_id': self.contract_id.id,
            'employee_contract_id': self.employee_contract_id.id,
            'applicant_id': self.applicant_id.id,
            'final_yearly_costs': self.final_yearly_costs,
            'job_title': self.job_title,
            'employee_job_id': self.employee_job_id.id,
            'department_id': self.department_id.id,
            'contract_start_date': self.contract_start_date,
            'access_token': uuid.uuid4().hex if self.applicant_id else False,
        }

    def action_save(self):
        if self.env.context.get('active_model') == "hr.applicant" and not self.applicant_id.partner_name:
            raise UserError(_('Offer link can not be send. The applicant needs to have a name.'))

        validity_end = (fields.Date.context_today(self) + relativedelta(days=self.validity))
        offer_values = self._get_offer_values()
        offer_values['offer_end_date'] = validity_end if (self.applicant_id or self.employee_contract_id) else False
        offer = self.env['hr.contract.salary.offer'].create(offer_values)

        if self.applicant_id:
            self.applicant_id.message_post(
                body=Markup(_("An <a href='#' data-oe-model='hr.contract.salary.offer' data-oe-id='%s'>Offer</a> as been sent by %s to the applicant (mail: %s)")) % (offer.id, self.env.user.name, self.applicant_id.partner_id.email or self.applicant_id.email_from))
        else:
            self.employee_contract_id.message_post(
                body=Markup(_("An <a href='#' data-oe-model='hr.contract.salary.offer' data-oe-id='%s'>Offer</a> as been sent by %s to the employee (mail: %s)")) % (offer.id, self.env.user.name, self.employee_id.work_email))

        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.contract.salary.offer',
            'res_id': offer.id,
            'views': [(False, 'form')],
        }

    def action_send_offer(self):
        if self.env.context.get('active_model') == "hr.applicant" and not self.applicant_id.partner_name:
            raise UserError(_('Offer link can not be send. The applicant needs to have a name.'))

        try:
            template_id = self.env.ref('hr_contract_salary.mail_template_send_offer').id
        except ValueError:
            template_id = False
        try:
            template_applicant_id = self.env.ref('hr_contract_salary.mail_template_send_offer_applicant').id
        except ValueError:
            template_applicant_id = False
        partner_to = False
        email_to = False
        if self.employee_id:
            email_to = self.employee_id.work_email
        elif self.applicant_id:
            partner_to = self.applicant_id.partner_id
            if not partner_to:
                partner_to = self.env['res.partner'].create({
                    'is_company': False,
                    'name': self.applicant_id.partner_name,
                    'email': self.applicant_id.email_from,
                    'phone': self.applicant_id.partner_phone,
                    'mobile': self.applicant_id.partner_mobile
                })
                self.applicant_id.partner_id = partner_to

        validity_end = (fields.Date.context_today(self) + relativedelta(days=self.validity))
        if self.applicant_id:
            default_template_id = template_applicant_id
        else:
            default_template_id = template_id

        offer_values = self._get_offer_values()
        offer_values['offer_end_date'] = validity_end if (self.applicant_id or self.employee_contract_id) else False
        offer = self.env['hr.contract.salary.offer'].create(offer_values)
        if self.applicant_id:
            self.applicant_id.message_post(
                body=Markup(_("An <a href='#' data-oe-model='hr.contract.salary.offer' data-oe-id='%s'>Offer</a> as been sent by %s to the applicant (mail: %s)")) % (offer.id, self.env.user.name, self.applicant_id.partner_id.email or self.applicant_id.email_from))
        else:
            self.employee_contract_id.message_post(
                body=Markup(_("An <a href='#' data-oe-model='hr.contract.salary.offer' data-oe-id='%s'>Offer</a> as been sent by %s to the employee (mail: %s)")) % (offer.id, self.env.user.name, self.employee_id.work_email))

        ctx = {
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': "mail.mail_notification_light",
            'default_model': 'hr.contract.salary.offer',
            'default_res_ids': offer.ids,
            'default_template_id': default_template_id,
            'default_record_name': _("%s: Job Offer - %s", self.company_id.name, self.job_title),
            'offer_id': offer.id,
            'access_token': offer.access_token,
            'partner_to': partner_to and partner_to.id or False,
            'validity_end': validity_end,
            'email_to': email_to or False,
            'mail_post_autofollow': False,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [[False, 'form']],
            'target': 'new',
            'context': ctx,
        }
