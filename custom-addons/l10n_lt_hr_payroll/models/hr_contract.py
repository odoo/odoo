# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    l10n_lt_benefits_in_kind = fields.Monetary(
        string="Benefits in Kind",
        help="""The following payments are not considered as benefits in kind:

- small value (not exceeding EUR 200) prizes, non-monetary presents received from employer;
- compensation received from employer for health treatment when required by law;
- working clothes, shoes, equipment and other assets given by employer to use only for work functions;
- directly to educational institutions paid amounts for individual‘s education;
- benefit received by an employee when an employer pays for rail and road public transport tickets which are used to travel to and from the work;
- personal income tax, social security and compulsory health insurance contributions paid on behalf of an individual.

Benefit in kind is taxed as employment income.""")
    l10n_lt_time_limited = fields.Boolean(
        string="Signed time-limited work agreement")
    l10n_lt_pension = fields.Boolean(
        string="Participate to pension accumulation system",
        help="""Employees can participate in an additional pension accumulation system. Inclusion into the accumulation system is used as one of the most effective methods to induce people to accumulate for additional pension if they have not started yet. However, it is not a coercive mechanism because any employed person may refuse accumulation if she/he does not want or has some other priorities.""")
