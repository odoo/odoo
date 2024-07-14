# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.models import MAGIC_COLUMNS
from odoo.fields import Date
from odoo.exceptions import ValidationError
from odoo.tools import html_sanitize

_logger = logging.getLogger(__name__)


class HrContract(models.Model):
    _inherit = 'hr.contract'

    origin_contract_id = fields.Many2one('hr.contract', string="Origin Contract", domain="[('company_id', '=', company_id)]", help="The contract from which this contract has been duplicated.")
    is_origin_contract_template = fields.Boolean(compute='_compute_is_origin_contract_template', string='Is origin contract a contract template?', readonly=True)
    hash_token = fields.Char('Created From Token', copy=False)
    applicant_id = fields.Many2one('hr.applicant', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    contract_reviews_count = fields.Integer(compute="_compute_contract_reviews_count", string="Proposed Contracts Count")
    default_contract_id = fields.Many2one(
        'hr.contract', string="Contract Template",
        compute="_compute_default_contract", store=True, readonly=False,
        domain="[('company_id', '=', company_id), ('employee_id', '=', False)]",
        help="Default contract used when making an offer to an applicant.")
    sign_template_id = fields.Many2one('sign.template', compute='_compute_sign_template_id', readonly=False, store=True, string="New Contract Document Template",
        help="Default document that the applicant will have to sign to accept a contract offer.")
    contract_update_template_id = fields.Many2one(
        'sign.template', string="Contract Update Document Template",
        compute='_compute_contract_update_template_id', store=True, readonly=False,
        help="Default document that the employee will have to sign to update his contract.")
    signatures_count = fields.Integer(compute='_compute_signatures_count', string='# Signatures',
        help="The number of signatures on the pdf contract with the most signatures.")
    image_1920_filename = fields.Char()
    image_1920 = fields.Image(related='employee_id.image_1920', groups="hr_contract.group_hr_contract_manager", readonly=False)
    # YTI FIXME: holidays and wage_with_holidays are defined twice...
    holidays = fields.Float(string='Extra Time Off',
        help="Number of days of paid leaves the employee gets per year.")
    wage_with_holidays = fields.Monetary(compute='_compute_wage_with_holidays', inverse='_inverse_wage_with_holidays',
        tracking=True, string="Wage with Holidays")
    wage_on_signature = fields.Monetary(string="Wage on Payroll", help="Wage on contract signature", tracking=True, group_operator="avg")
    salary_offer_ids = fields.One2many('hr.contract.salary.offer', 'employee_contract_id')
    salary_offers_count = fields.Integer(compute='_compute_salary_offers_count', compute_sudo=True)

    # Employer costs fields
    final_yearly_costs = fields.Monetary(
        compute='_compute_final_yearly_costs',
        readonly=False, store=True,
        string="Yearly Cost (Real)",
        tracking=True,
        help="Total real yearly cost of the employee for the employer.",
        group_operator="avg")
    monthly_yearly_costs = fields.Monetary(
        compute='_compute_monthly_yearly_costs', string='Monthly Cost (Real)', readonly=True,
        help="Total real monthly cost of the employee for the employer.")

    @api.constrains('hr_responsible_id', 'sign_template_id')
    def _check_hr_responsible_id(self):
        for contract in self:
            if contract.sign_template_id and not (contract.hr_responsible_id.has_group('sign.group_sign_user') and contract.hr_responsible_id.email_formatted):
                raise ValidationError(_("HR Responsible %s should be a User of Sign and have a valid email address when New Contract Document Template is specified", contract.hr_responsible_id.name))

    @api.depends('wage', 'wage_on_signature')
    def _compute_contract_wage(self):
        super()._compute_contract_wage()

    def _get_contract_wage_field(self):
        self.ensure_one()
        if self._is_struct_from_country('BE'):
            return 'wage_on_signature'
        return super()._get_contract_wage_field()

    @api.depends('origin_contract_id')
    def _compute_is_origin_contract_template(self):
        for contract in self:
            contract.is_origin_contract_template = contract.origin_contract_id and not contract.origin_contract_id.employee_id

    @api.depends('job_id')
    def _compute_default_contract(self):
        for contract in self:
            if not contract.job_id or not contract.job_id.default_contract_id:
                continue
            contract.default_contract_id = contract.job_id.default_contract_id

    @api.onchange('default_contract_id')
    def _onchange_default_contract_id(self):
        if self.default_contract_id.hr_responsible_id:
            self.hr_responsible_id = self.default_contract_id.hr_responsible_id

    def _compute_salary_offers_count(self):
        offers_data = self.env['hr.contract.salary.offer']._read_group(
            domain=[('employee_contract_id', 'in', self.ids)],
            groupby=['employee_contract_id'],
            aggregates=['__count'])
        mapped_data = {contract.id: count for contract, count in offers_data}
        for contract in self:
            contract.salary_offers_count = mapped_data.get(contract.id, 0)

    def _get_yearly_cost_sacrifice_ratio(self):
        return 1.0 - self.holidays / 231.0

    def _get_yearly_cost_sacrifice_fixed(self):
        return 0.0

    def _get_yearly_cost_from_wage_with_holidays(self, wage_with_holidays=False):
        self.ensure_one()
        ratio = self._get_yearly_cost_sacrifice_ratio()
        fixed = self._get_yearly_cost_sacrifice_fixed()
        if wage_with_holidays:
            return (self._get_benefits_costs() + self._get_salary_costs_factor() * wage_with_holidays + fixed) / ratio
        return self.final_yearly_costs * ratio - fixed

    def _get_yearly_cost_from_wage(self):
        self.ensure_one()
        fixed = self._get_yearly_cost_sacrifice_fixed()
        return self._get_benefits_costs() + self._get_salary_costs_factor() * self.wage + fixed

    def _is_salary_sacrifice(self):
        self.ensure_one()
        return self.holidays

    @api.depends('holidays', 'wage', 'final_yearly_costs')
    def _compute_wage_with_holidays(self):
        for contract in self:
            if contract._is_salary_sacrifice():
                yearly_cost = contract._get_yearly_cost_from_wage_with_holidays()
                contract.wage_with_holidays = contract._get_gross_from_employer_costs(yearly_cost)
            else:
                contract.wage_with_holidays = contract.wage

    def _inverse_wage_with_holidays(self):
        for contract in self:
            if contract._is_salary_sacrifice():
                yearly = contract._get_yearly_cost_from_wage_with_holidays(self.wage_with_holidays)
                contract.wage = contract._get_gross_from_employer_costs(yearly)
            else:
                if contract.wage != contract.wage_with_holidays:
                    contract.wage = contract.wage_with_holidays

    def _get_benefit_description(self, benefit, new_value=None):
        self.ensure_one()
        if hasattr(self, '_get_description_%s' % benefit.field):
            description = getattr(self, '_get_description_%s' % benefit.field)(new_value)
        else:
            description = benefit.description
        return html_sanitize(description)

    def _get_benefit_fields(self, triggers=True):
        types = ('float', 'integer', 'monetary', 'boolean')
        if not triggers:
            types += ('text',)
        nonstored_whitelist = self._benefit_white_list()
        benefit_fields = set(
            field.name for field in self._fields.values() if field.type in types and (field.store or not field.store and field.name in nonstored_whitelist))
        if not triggers:
            benefit_fields |= {'wage_with_holidays'}
        return tuple(benefit_fields - self._benefit_black_list())

    @api.model
    def _benefit_black_list(self):
        return set(MAGIC_COLUMNS + [
            'wage_on_signature', 'active',
            'date_generated_from', 'date_generated_to'])

    @api.model
    def _benefit_white_list(self):
        return []

    @api.depends(lambda self: (
        'wage',
        'structure_type_id.salary_benefits_ids.res_field_id',
        'structure_type_id.salary_benefits_ids.impacts_net_salary',
        *self._get_benefit_fields()))
    def _compute_final_yearly_costs(self):
        for contract in self:
            if abs(contract.final_yearly_costs - contract._get_yearly_cost_from_wage()) > 0.10:
                contract.final_yearly_costs = contract._get_yearly_cost_from_wage()

    @api.depends('company_id', 'job_id')
    def _compute_structure_type_id(self):
        contracts = self.env['hr.contract']
        for contract in self:
            if contract.job_id and contract.job_id.default_contract_id and contract.job_id.default_contract_id.structure_type_id:
                contract.structure_type_id = contract.job_id.default_contract_id.structure_type_id
            else:
                contracts |= contract
        super(HrContract, contracts)._compute_structure_type_id()

    @api.onchange("wage_with_holidays")
    def _onchange_wage_with_holidays(self):
        self._inverse_wage_with_holidays()

    @api.onchange('final_yearly_costs')
    def _onchange_final_yearly_costs(self):
        final_yearly_costs = self.final_yearly_costs
        self.wage = self._get_gross_from_employer_costs(final_yearly_costs)
        self.env.remove_to_compute(self._fields['final_yearly_costs'], self)
        self.final_yearly_costs = final_yearly_costs

    @api.depends('final_yearly_costs')
    def _compute_monthly_yearly_costs(self):
        for contract in self:
            contract.monthly_yearly_costs = contract.final_yearly_costs / 12.0

    def _get_salary_costs_factor(self):
        self.ensure_one()
        return 12.0

    def _get_benefits_costs(self):
        self.ensure_one()
        benefits = self.env['hr.contract.salary.benefit'].search([
            ('impacts_net_salary', '=', True),
            ('structure_type_id', '=', self.structure_type_id.id),
            ('cost_res_field_id', '!=', False),
        ])
        if not benefits:
            return 0
        monthly_benefits = benefits.filtered(lambda a: a.benefit_type_id.periodicity == 'monthly')
        monthly_cost = sum(self[benefit.cost_field] if benefit.cost_field in self else 0 for benefit in monthly_benefits)
        yearly_cost = sum(self[benefit.cost_field] if benefit.cost_field in self else 0 for benefit in benefits - monthly_benefits)
        return monthly_cost * 12 + yearly_cost

    def _get_gross_from_employer_costs(self, yearly_cost):
        self.ensure_one()
        remaining_for_gross = yearly_cost - self._get_benefits_costs()
        return remaining_for_gross / self._get_salary_costs_factor()

    @api.depends('sign_request_ids.nb_closed')
    def _compute_signatures_count(self):
        for contract in self:
            contract.signatures_count = max(contract.sign_request_ids.mapped('nb_closed') or [0])

    @api.depends('origin_contract_id')
    def _compute_contract_reviews_count(self):
        for contract in self:
            contract.contract_reviews_count = self.with_context(active_test=False).search_count(
                [('origin_contract_id', '=', contract.id)])

    @api.depends('default_contract_id')
    def _compute_sign_template_id(self):
        for contract in self:
            if contract.default_contract_id:
                contract.sign_template_id = contract.default_contract_id.sign_template_id

    @api.depends('default_contract_id')
    def _compute_contract_update_template_id(self):
        for contract in self:
            if contract.default_contract_id and contract.id != contract.default_contract_id.id:
                contract.contract_update_template_id = contract.default_contract_id.contract_update_template_id

    def _get_redundant_salary_data(self):
        employees = self.mapped('employee_id').filtered(lambda employee: not employee.active)
        partners = employees.work_contact_id.filtered(lambda partner: not partner.active)
        return [employees, partners]

    def _clean_redundant_salary_data(self):
        # Unlink archived draft contract older than 7 days linked to a signature
        # Unlink the related employee, partner, and new car (if any)
        seven_days_ago = date.today() + relativedelta(days=-7)
        contracts = self.search([
            ('state', '=', 'draft'),
            ('active', '=', False),
            ('sign_request_ids', '!=', False),
            ('create_date', '<=', Date.to_string(seven_days_ago))])
        records_to_unlink = contracts._get_redundant_salary_data()
        for records in records_to_unlink:
            if not records:
                continue
            _logger.info('Salary: About to unlink %s: %s' % (records._name, records.ids))
            for record in records:
                try:
                    record.unlink()
                except ValueError:
                    pass

    def action_show_contract_reviews(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.contract",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [["origin_contract_id", "=", self.id], '|', ["active", "=", False], ["active", "=", True]],
            "name": "Contracts Reviews",
        }

    def action_view_origin_contract(self):
        action = self.env["ir.actions.actions"]._for_xml_id("hr_contract.action_hr_contract")
        action['views'] = [(self.env.ref('hr_contract.hr_contract_view_form').id, 'form')]
        action['res_id'] = self.origin_contract_id.id
        return action

    def action_show_offers(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('hr_contract_salary.hr_contract_salary_offer_action')
        action['domain'] = [('id', 'in', self.salary_offer_ids.ids)]
        action['context'] = {'default_employee_contract_id': self.id}
        if self.salary_offers_count == 1:
            action.update({
                "views": [[False, "form"]],
                "res_id": self.salary_offer_ids.id,
            })
        return action

    def send_offer(self):
        self.ensure_one()
        try:
            template_id = self.env.ref('hr_contract_salary.mail_template_send_offer').id
        except ValueError:
            template_id = False
        path = '/salary_package/contract/' + str(self.id)
        ctx = {
            'default_email_layout_xmlid': 'mail.mail_notification_light',
            'default_model': 'hr.contract',
            'default_res_ids': self.ids,
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'salary_package_url': self.get_base_url() + path,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [[False, 'form']],
            'target': 'new',
            'context': ctx,
        }

    def action_archive(self):
        res = super().action_archive()
        job_positions = self.env['hr.job'].search([('default_contract_id', 'in', self.ids)])
        job_positions.default_contract_id = False
        return res
