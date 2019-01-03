# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import fields, models


class L10nBeIndividualAccountWizard(models.TransientModel):
    _name = 'l10n_be.individual.account.wizard'
    _description = 'HR Individual Account Report By Employee'

    def _get_selection(self):
        current_year = datetime.datetime.now().year
        return [(str(i), i) for i in range(1990, current_year + 1)]

    year = fields.Selection(
        selection='_get_selection', string='Year', required=True,
        default=lambda x: str(datetime.datetime.now().year - 1))

    def print_report(self):
        self.ensure_one()
        active_ids = self.env.context.get('active_ids', [])
        data = {
            'employee_ids': active_ids,
            'year': int(self.year)
        }
        return self.env.ref('l10n_be_hr_payroll.action_report_individual_account').report_action(active_ids, data=data)
