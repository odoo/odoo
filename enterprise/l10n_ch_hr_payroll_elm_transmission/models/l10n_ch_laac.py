# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _


class l10nChAdditionalAccidentInsurance(models.Model):
    _inherit = "l10n.ch.additional.accident.insurance"

    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    insurance_company = fields.Char(required=False, store=True)
    active = fields.Boolean(default=True)


class l10nChAdditionalAccidentInsuranceLine(models.Model):
    _inherit = 'l10n.ch.additional.accident.insurance.line'

    solution_type = fields.Selection(selection=lambda self: [(str(i), str(i)) for i in range(10)] + [(chr(i), chr(i)) for i in range(ord('A'), ord('Z') + 1)], default='A')

    solution_number = fields.Selection(selection=lambda self: [(str(i), str(i)) for i in range(10)] + [(chr(i), chr(i)) for i in range(ord('A'), ord('Z') + 1)], default='1')

    solution_code = fields.Char(compute="_compute_solution_code")

    @api.depends('solution_type', 'solution_number')
    def _compute_solution_code(self):
        for line in self:
            line.solution_code = line.solution_type + line.solution_number
