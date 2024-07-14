# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class l10nChAccidentInsurance(models.Model):
    _inherit = "l10n.ch.accident.insurance"

    insurance_company = fields.Char(required=True, store=True)
    insurance_code = fields.Char(required=True, store=True, compute=False)


class l10nChAccidentInsuranceLine(models.Model):
    _inherit = 'l10n.ch.accident.insurance.line'

    solution_code = fields.Char(compute='_compute_solution_code', store=True)

    @api.depends('solution_type', 'solution_number')
    def _compute_solution_code(self):
        for line in self:
            line.solution_code = line.solution_type + line.solution_number
