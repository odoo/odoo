# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.osv import expression


class HrCandidate(models.Model):
    _name = "hr.candidate"
    _inherit = [
        "hr.candidate",
    ]

    company_ids = fields.Many2many(
        comodel_name="res.company",
        compute="_compute_candidate_companies",
        default=lambda self: self.env.company,
        string="Companies",
        readonly=False,
        store=True,
    )

    @api.depends('applicant_ids')
    def _compute_candidate_companies(self):
        for candidate in self:
            candidate.company_ids = candidate.applicant_ids.mapped("company_id")
            candidate.company_id = False

    def _get_similar_candidates_domain(self):
        """
            This method returns a domain for the applicants whitch match with the
            current candidate according to email_from, partner_phone.
            Thus, search on the domain will return the current candidate as well if any of
            the following fields are filled.
        """
        self.ensure_one()
        if not self:
            return []
        domain = [('id', 'in', self.ids)]
        if self.email_normalized:
            domain = expression.OR([domain, [('email_normalized', '=', self.email_normalized)]])
        if self.partner_phone_sanitized:
            domain = expression.OR([domain, [('partner_phone_sanitized', '=', self.partner_phone_sanitized)]])
        domain = expression.AND([domain, [('company_ids', 'in', self.env.companies.ids)]])
        return domain
