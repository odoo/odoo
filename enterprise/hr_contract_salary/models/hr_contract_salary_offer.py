# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.osv import expression
from werkzeug.urls import url_encode


class HrContractSalaryOffer(models.Model):
    _name = 'hr.contract.salary.offer'
    _description = 'Salary Package Offer'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        for field in fields:
            if field.startswith('x_') and 'active_id' in self.env.context:
                model = self.env.context.get('active_model')
                if model == "hr.contract" and field in self.env[model]:
                    contract = self.env[model].browse(self.env.context['active_id'])
                    result[field] = contract[field]
                elif model == "hr.applicant" and field in self.env["hr.contract"] and "default_contract_template_id" in self.env.context:
                    contract = self.env["hr.contract"].browse(self.env.context['default_contract_template_id'])
                    result[field] = contract[field]
        return result

    display_name = fields.Char(string="Title", compute="_compute_display_name", search="_search_display_name", readonly=False)  # TODO read-only=False, but not inversed?
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    contract_template_id = fields.Many2one(
        'hr.contract',
        domain="['|', ('employee_id', '=', False), ('id', '=', employee_contract_id)]", required=True, tracking=True)
    state = fields.Selection([
        ('open', 'In Progress'),
        ('half_signed', 'Partially Signed'),
        ('full_signed', 'Fully Signed'),
        ('expired', 'Expired'),
        ('refused', 'Refused'),
    ], default='open', tracking=True)
    refusal_reason = fields.Many2one('hr.contract.salary.offer.refusal.reason', string="Refusal Reason", tracking=True)
    offer_create_date = fields.Date("Offer Create Date", compute="_compute_offer_create_date", readonly=True)
    refusal_date = fields.Date("Refusal Date")
    sign_request_ids = fields.Many2many('sign.request', string='Requested Signatures')
    employee_contract_id = fields.Many2one('hr.contract', tracking=True)
    employee_id = fields.Many2one(related="employee_contract_id.employee_id", store=True, tracking=True)
    applicant_id = fields.Many2one('hr.applicant', tracking=True)
    applicant_name = fields.Char(related='applicant_id.partner_name')
    final_yearly_costs = fields.Monetary("Employer Budget", aggregator="avg", tracking=True)
    job_title = fields.Char(tracking=True)
    employee_job_id = fields.Many2one('hr.job', tracking=True)
    department_id = fields.Many2one('hr.department', tracking=True)
    contract_start_date = fields.Date(tracking=True,
                                      default=fields.Date.context_today)
    access_token = fields.Char('Access Token', copy=False, tracking=True)
    validity_days_count = fields.Integer("Validity Days Count",
                              compute="_compute_validity_days_count",
                              store=True, readonly=False)
    offer_end_date = fields.Date('Offer Validity Date',
                                 compute="_compute_offer_end_date",
                                 store=True, readonly=False,
                                 copy=False, tracking=True)
    url = fields.Char('Link', compute='_compute_url')
    contract_type_id = fields.Many2one(related='employee_job_id.contract_type_id', string='Contract Type', readonly=True, store=False)

    _sql_constraints = [
        ('check_validity_days_count', 'CHECK(validity_days_count >= 0)', 'The validity should not be negative.'),
    ]

    @api.depends("access_token", "applicant_id")
    def _compute_url(self):
        base_url = self.env['hr.contract.salary.offer'].get_base_url()
        for offer in self:
            offer.url = base_url \
                      + f"/salary_package/simulation/offer/{offer.id}" \
                      + f"?final_yearly_costs={round(offer.final_yearly_costs, 2)}" \
                      + (f"&token={offer.access_token}" if offer.applicant_id else "")

    @api.depends('applicant_id', 'employee_contract_id')
    def _compute_display_name(self):
        for offer in self:
            if offer.applicant_id:
                name = offer.applicant_id.employee_id.name or \
                    offer.applicant_id.partner_id.name or \
                    offer.applicant_id.partner_name
            else:
                name = offer.employee_contract_id.employee_id.name
            offer.display_name = _("Offer for %(recipient)s", recipient=name)

    def _search_display_name(self, operator, value):
        if neg := (operator in expression.NEGATIVE_TERM_OPERATORS):
            operator = expression.TERM_OPERATORS_NEGATION[operator]
        domain = [
            "|",
                ('applicant_id', 'any', [
                    ('employee_id.name', operator, value),
                    ('partner_id.name', operator, value),
                    ('partner_name', operator, value),
                ]),
            "&",
                ('applicant_id', '=', False),
                ('employee_contract_id.employee_id.name', operator, value),
        ]
        if neg:
            domain = ["!", *domain]
        return domain

    @api.depends('create_date')
    def _compute_offer_create_date(self):
        for offer in self:
            offer.offer_create_date = offer.create_date.date()

    @api.depends('offer_create_date', 'validity_days_count')
    def _compute_offer_end_date(self):
        for offer in self:
            offer.offer_end_date = offer.offer_create_date + relativedelta(days=offer.validity_days_count)

    @api.depends('offer_create_date', 'offer_end_date')
    def _compute_validity_days_count(self):
        for offer in self:
            offer.validity_days_count = (offer.offer_end_date - offer.offer_create_date).days \
                if offer.offer_end_date else False

    @api.onchange('employee_job_id')
    def _onchange_employee_job_id(self):
        self.job_title = self.employee_job_id.name
        if self.employee_job_id.department_id:
            self.department_id = self.employee_job_id.department_id

        if (
            self.employee_contract_id and
            (
                self.employee_job_id == self.employee_contract_id.job_id or
                not self.employee_job_id.default_contract_id
            )
        ):
            self.contract_template_id = self.employee_contract_id

        elif self.employee_job_id.default_contract_id:
            self.contract_template_id = self.employee_job_id.default_contract_id

    @api.onchange('contract_template_id')
    def _onchange_contract_template_id(self):
        self.final_yearly_costs = self.contract_template_id.final_yearly_costs

        if self.contract_template_id:
            self.company_id = self.contract_template_id.company_id
        else:
            self.company_id = self.env.company.id

    def action_open_refuse_wizard(self):
        action = self.env["ir.actions.actions"]._for_xml_id("hr_contract_salary.open_refuse_wizard")
        return {
            **action,
            'context': {
                'dialog_size': 'medium',
            },
        }

    def action_refuse_offer(self, message=None, refusal_reason=None):
        if not message:
            message = _("%s manually set the Offer to Refused", self.env.user.name)
        self.write({
            'state': 'refused',
            'refusal_reason': refusal_reason,
            'refusal_date': fields.Date.today()
        })
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
                    'mobile': self.applicant_id.partner_phone,
                })
                self.applicant_id.partner_id = partner_to

        ctx = {
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': "mail.mail_notification_light",
            'default_model': 'hr.contract.salary.offer',
            'default_res_ids': self.ids,
            'default_template_id': default_template_id,
            'default_record_name': _("%(company)s: Job Offer - %(job_title)s", company=self.company_id.name, job_title=self.job_title),
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

    def action_view_signature_request(self):
        self.ensure_one()
        pending_sign_request = self.sign_request_ids.filtered(lambda r: r.state != 'signed')
        sign_request_id = pending_sign_request[0].id if pending_sign_request else False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Requested Signature'),
            'view_mode': 'form',
            'res_model': 'sign.request',
            'res_id': sign_request_id,
            'target': 'new',
        }

    def action_view_contract(self):
        self.ensure_one()
        contract_id = self.employee_contract_id.id or self.env['hr.contract'].search([("applicant_id", "=", self.applicant_id.id)], limit=1).id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Contract'),
            'view_mode': 'form',
            'res_model': 'hr.contract',
            'res_id': contract_id,
            'target': 'current',
        }

    def _message_get_suggested_recipients(self):
        recipients = super()._message_get_suggested_recipients()
        if self.applicant_id:
            self._message_add_suggested_recipient(recipients, email=self.applicant_id.email_from, reason=_('Contact Email'))
        elif self.employee_id:
            self._message_add_suggested_recipient(recipients, partner=self.employee_id.work_contact_id.sudo(), reason=_('Contact'))
        return recipients
