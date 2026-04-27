# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrCandidate(models.Model):
    _inherit = 'hr.candidate'

    salary_offers_count = fields.Integer(compute='_compute_salary_offers_count', compute_sudo=True)

    def _compute_salary_offers_count(self):
        for candidate in self:
            candidate.salary_offers_count = sum(candidate.applicant_ids.mapped('salary_offers_count'))

    def action_show_offers(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('hr_contract_salary.hr_contract_salary_offer_action')
        action['domain'] = [('id', 'in', self.applicant_ids.salary_offer_ids.ids)]
        if self.applicant_ids:
            action['context'] = {'default_applicant_id': self.applicant_ids.ids[0]}
        if self.salary_offers_count == 1:
            action.update({
                "views": [[False, "form"]],
                "res_id": self.applicant_ids.salary_offer_ids.id,
            })
        return action
