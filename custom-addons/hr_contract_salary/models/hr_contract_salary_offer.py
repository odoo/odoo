# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.misc import format_amount
from werkzeug.urls import url_encode


class HrContractSalaryOffer(models.Model):
    _name = 'hr.contract.salary.offer'
    _description = 'Salary Package Offer'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    display_name = fields.Char(string="Title", compute="_compute_display_name")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    contract_template_id = fields.Many2one(
        'hr.contract',
        domain=[('employee_id', '=', False)], required=True, tracking=True)
    state = fields.Selection([
        ('open', 'In Progress'),
        ('half_signed', 'Partially Signed'),
        ('full_signed', 'Fully Signed'),
        ('expired', 'Expired'),
        ('refused', 'Refused'),
    ], default='open', tracking=True)
    sign_request_ids = fields.Many2many('sign.request', string='Requested Signatures')
    employee_contract_id = fields.Many2one('hr.contract', tracking=True)
    employee_id = fields.Many2one(related="employee_contract_id.employee_id", store=True, tracking=True)
    applicant_id = fields.Many2one('hr.applicant', tracking=True)
    applicant_name = fields.Char(related='applicant_id.partner_name')
    final_yearly_costs = fields.Monetary("Employer Budget", group_operator="avg", tracking=True)
    job_title = fields.Char(tracking=True)
    employee_job_id = fields.Many2one('hr.job', tracking=True)
    department_id = fields.Many2one('hr.department', tracking=True)
    contract_start_date = fields.Date(tracking=True)
    access_token = fields.Char('Access Token', copy=False, tracking=True)
    offer_end_date = fields.Date('Offer Validity Date', copy=False, tracking=True)
    url = fields.Char('Link', compute='_compute_url')

    @api.depends("access_token", "applicant_id")
    def _compute_url(self):
        base_url = self.get_base_url()
        for offer in self:
            offer.url = base_url + f"/salary_package/simulation/offer/{offer.id}" + (f"?token={offer.access_token}" if offer.applicant_id else "")

    def _compute_state(self):
        for offer in self:
            offer.state = 'open'

    @api.depends('applicant_id', 'employee_contract_id', 'final_yearly_costs', 'offer_end_date')
    def _compute_display_name(self):
        for offer in self:
            if offer.applicant_id:
                name = offer.applicant_id.emp_id.name or offer.applicant_id.partner_id.name or offer.applicant_id.partner_name
            else:
                name = offer.employee_contract_id.employee_id.name
            offer.display_name = _("Offer [%s] for %s / Budget: %s", offer.create_date and offer.create_date.date() or 'No create date', name, format_amount(offer.env, offer.final_yearly_costs, offer.currency_id))

    def action_refuse_offer(self):
        self.write({'state': 'refused'})
        message = _("%s manually set the Offer to Refused", self.env.user.name)
        for offer in self:
            offer.message_post(body=message)

    def action_jump_to_offer(self):
        self.ensure_one()
        url = f'/salary_package/simulation/offer/{self.id}'
        if self.applicant_id:
            url += '?' + url_encode({'token': self.access_token})
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def _cron_update_state(self):
        self.search([
            ('state', 'in', ['open', 'half_signed']),
            ('offer_end_date', '<', fields.Date.today()),
        ]).write({'state': 'expired'})

    def action_send_by_email(self):
        self.ensure_one()
        try:
            template_id = self.env.ref('hr_contract_salary.mail_template_send_offer').id
        except ValueError:
            template_id = False
        try:
            template_applicant_id = self.env.ref('hr_contract_salary.mail_template_send_offer_applicant').id
        except ValueError:
            template_applicant_id = False
        if self.applicant_id:
            default_template_id = template_applicant_id
        else:
            default_template_id = template_id

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

        ctx = {
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': "mail.mail_notification_light",
            'default_model': 'hr.contract.salary.offer',
            'default_res_ids': self.ids,
            'default_template_id': default_template_id,
            'default_record_name': _("%s: Job Offer - %s", self.company_id.name, self.job_title),
            'offer_id': self.id,
            'access_token': self.access_token,
            'partner_to': partner_to and partner_to.id or False,
            'validity_end': self.offer_end_date,
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
