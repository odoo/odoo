# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import fields, models, _
from odoo.exceptions import UserError


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    salary_offer_ids = fields.One2many('hr.contract.salary.offer', 'applicant_id')
    salary_offers_count = fields.Integer(compute='_compute_salary_offers_count', compute_sudo=True)
    proposed_contracts = fields.Many2many('hr.contract', string="Proposed Contracts", domain="[('company_id', '=', company_id)]")
    proposed_contracts_count = fields.Integer(compute="_compute_proposed_contracts_count", string="Proposed Contracts Count", compute_sudo=True)

    def _compute_proposed_contracts_count(self):
        contracts_data = self.env['hr.contract'].with_context(active_test=False)._read_group(
            domain=[
                ('applicant_id', 'in', self.ids),
                ('active', '=', True),
            ],
            groupby=['applicant_id'],
            aggregates=['__count'])
        mapped_data = {applicant.id: count for applicant, count in contracts_data}
        for applicant in self:
            applicant.proposed_contracts_count = mapped_data.get(applicant.id, 0)

    def _compute_salary_offers_count(self):
        offers_data = self.env['hr.contract.salary.offer']._read_group(
            domain=[('applicant_id', 'in', self.ids)],
            groupby=['applicant_id'],
            aggregates=['__count'])
        mapped_data = {applicant.id: count for applicant, count in offers_data}
        for applicant in self:
            applicant.salary_offers_count = mapped_data.get(applicant.id, 0)

    def _move_to_hired_stage(self):
        self.ensure_one()
        first_hired_stage = self.env['hr.recruitment.stage'].search([
            '|',
            ('job_ids', '=', False),
            ('job_ids', '=', self.job_id.id),
            ('hired_stage', '=', True)])

        if first_hired_stage:
            self.stage_id = first_hired_stage[0].id

    def action_show_proposed_contracts(self):
        self.candidate_id._check_interviewer_access()
        action_vals = {
            "type": "ir.actions.act_window",
            "res_model": "hr.contract",
            "domain": [["applicant_id", "=", self.id], '|', ["active", "=", False], ["active", "=", True]],
            "name": _("Proposed Contracts"),
            "context": {'default_employee_id': self.employee_id.id, 'default_applicant_id': self.id},
        }
        if self.proposed_contracts_count == 1:
            action_vals.update({
                "views": [[False, "form"]],
                "res_id": self.env['hr.contract'].search([("applicant_id", "=", self.id)]).id,
            })
        else:
            action_vals.update({
                "views": [[False, "list"], [False, "form"]],
            })
        return action_vals

    def action_show_offers(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('hr_contract_salary.hr_contract_salary_offer_action')
        action['domain'] = [('id', 'in', self.salary_offer_ids.ids)]
        action['context'] = {'default_applicant_id': self.id}
        if self.salary_offers_count == 1:
            action.update({
                "views": [[False, "form"]],
                "res_id": self.salary_offer_ids.id,
            })
        return action

    def archive_applicant(self):
        message = _("The offer has been marked as refused when the linked applicant was declined.")
        refuse_reason = self.env.ref("hr_contract_salary.refusal_reason_others", raise_if_not_found=False)

        self.salary_offer_ids.filtered(lambda o: o.state != "refused").action_refuse_offer(message=message, refusal_reason=refuse_reason)
        return super().archive_applicant()

    def action_generate_offer(self):
        if not self.partner_name or not self.email_from:
            raise UserError(_('Offer link can not be send. The applicant needs to have a name and email.'))

        offer_validity_period = int(self.env['ir.config_parameter'].sudo().get_param(
            'hr_contract_salary.access_token_validity', default=30))
        validity_end = (fields.Date.context_today(self) + relativedelta(days=offer_validity_period))
        offer_values = self._get_offer_values()

        if not offer_values['contract_template_id']:
            raise UserError(_('You have to define contract templates to be used for offers. Go to Configuration / Contract Templates to define a contract template'))

        offer_values['validity_days_count'] = offer_validity_period
        offer_values['offer_end_date'] = validity_end
        offer = self.env['hr.contract.salary.offer'].with_context(
            default_contract_template_id=self._get_contract_template().id).create(offer_values)

        self.message_post(
            body=_("An %(offer)s has been sent by %(user)s to the applicant (mail: %(email)s)",
                    offer=Markup("<a href='#' data-oe-model='hr.contract.salary.offer' data-oe-id='{offer_id}'>Offer</a>")
                    .format(offer_id=offer.id),
                    user=self.env.user.name,
                    email=self.partner_id.email or self.email_from
            )
        )

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.contract.salary.offer',
            'res_id': offer.id,
            'views': [(False, 'form')],
            'context': {'active_model': 'hr.applicant', 'default_applicant_id': self.id}
        }

    def _get_offer_values(self):
        self.ensure_one()
        contract_template = self._get_contract_template()
        return {
            'company_id': contract_template.company_id.id,
            'contract_template_id': contract_template.id,
            'applicant_id': self.id,
            'final_yearly_costs': contract_template.final_yearly_costs,
            'job_title': self.job_id.name,
            'employee_job_id': self.job_id.id,
            'department_id': self.department_id.id,
            'access_token':  uuid.uuid4().hex,
        }

    def _get_contract_template(self):
        contract_template = self.job_id.default_contract_id if self.job_id else False
        if not contract_template:
            contract_template = self.env['hr.contract'].search(domain=[
                ('company_id', '=', self.company_id.id), ('employee_id', '=', False)
            ],
            limit=1)
        return contract_template
