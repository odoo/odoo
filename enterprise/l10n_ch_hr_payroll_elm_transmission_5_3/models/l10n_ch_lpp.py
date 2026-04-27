# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models, fields
from odoo.exceptions import UserError


class l10nChAdditionalAccidentInsuranceLineRate(models.Model):
    _name = 'l10n.lpp.coordination.amount'
    _description = 'BVG/LPP Coordination values'

    insurance_id = fields.Many2one('l10n.ch.lpp.insurance', required=True)
    date_from = fields.Date(string="From", required=True, default=lambda self: fields.Date.context_today(self).replace(month=1, day=1))
    date_to = fields.Date(string="To")
    lpp_coordination_deduction = fields.Float(string="Coordination Deduction", help="Yearly coordination deduction amount")
    lpp_maximum_amount = fields.Float(string="Maximum amount", help="Yearly maximum amount")


class l10nChLppInsurance(models.Model):
    _inherit = 'l10n.ch.lpp.insurance'

    @api.model
    def _get_default_lpp_coordination_ids(self):
        vals = [
            (0, 0, {
                'lpp_coordination_deduction': 26460,
                'lpp_maximum_amount': 90720,
            })
        ]
        return vals

    def _find_coordination_amount(self, target):
        if not self:
            return 0, 0
        for rate in self.lpp_coordination_ids:
            if rate.date_from <= target and (not rate.date_to or target <= rate.date_to):
                return rate.lpp_coordination_deduction / 12, (rate.lpp_maximum_amount / 12 - rate.lpp_coordination_deduction / 12)
        raise UserError(_('No LPP Coordination deduction amounts found for date %s', target))

    def _get_minimum_lpp_salary(self, date_to):
        minimum_lpp_salary = self.env['hr.rule.parameter']._get_parameter_from_code('minimum_lpp_salary', date_to, raise_if_not_found=False)
        if minimum_lpp_salary:
            return minimum_lpp_salary / 12
        else:
            return 22680 / 12

    lpp_coordination_ids = fields.One2many('l10n.lpp.coordination.amount', 'insurance_id', default=_get_default_lpp_coordination_ids)
