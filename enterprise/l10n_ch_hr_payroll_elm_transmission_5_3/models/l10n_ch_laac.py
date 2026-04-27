# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class l10nChAdditionalAccidentInsuranceLine(models.Model):
    _inherit = 'l10n.ch.additional.accident.insurance.line'

    def _get_rates(self, target, gender="male"):
        if not self:
            return 0, 0, 0, 0
        for rate in self.rate_ids:
            if rate.date_from <= target and (not rate.date_to or target <= rate.date_to):
                wage_from, wage_to = rate.wage_from, rate.wage_to
                if gender == "male":
                    employee_rate = rate.male_rate
                    if not rate.custom_employer_rates:
                        employer_rate = float(rate.employer_part)
                    else:
                        employee_rate = rate.male_rate + rate.employer_rate_male
                        employer_rate = (rate.employer_rate_male / employee_rate * 100) if employee_rate > 0 else 0
                    return wage_from, wage_to, employee_rate, employer_rate
                elif gender == "female":
                    employee_rate = rate.female_rate
                    if not rate.custom_employer_rates:
                        employer_rate = float(rate.employer_part)
                    else:
                        employee_rate = rate.female_rate + rate.employer_rate_female
                        employer_rate = (rate.employer_rate_female / employee_rate * 100) if employee_rate > 0 else 0
                    return wage_from, wage_to, employee_rate, employer_rate
                else:
                    raise UserError(_('No rate found for gender %s', gender))
        raise UserError(_('No LAAC rates found for date %s', target))


class l10nChAdditionalAccidentInsuranceLineRate(models.Model):
    _inherit = 'l10n.ch.additional.accident.insurance.line.rate'

    custom_employer_rates = fields.Boolean(help="If your insurance has company parts other than 0/50/100% you can define your own customized rates.")

    employer_rate_male = fields.Float(string="Male Company Rate (%)", digits='Payroll Rate')
    employer_rate_female = fields.Float(string="Female Company Rate (%)", digits='Payroll Rate')
