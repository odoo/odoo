# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


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
        self._check_interviewer_access()
        action_vals = {
            "type": "ir.actions.act_window",
            "res_model": "hr.contract",
            "domain": [["applicant_id", "=", self.id], '|', ["active", "=", False], ["active", "=", True]],
            "name": _("Proposed Contracts"),
            "context": {'default_employee_id': self.emp_id.id, 'default_applicant_id': self.id},
        }
        if self.proposed_contracts_count == 1:
            action_vals.update({
                "views": [[False, "form"]],
                "res_id": self.env['hr.contract'].search([("applicant_id", "=", self.id)]).id,
            })
        else:
            action_vals.update({
                "views": [[False, "tree"], [False, "form"]],
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
