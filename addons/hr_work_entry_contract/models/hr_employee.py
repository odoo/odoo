# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee'

    def generate_work_entries(self, date_start, date_stop, force=False):
        date_start = fields.Date.to_date(date_start)
        date_stop = fields.Date.to_date(date_stop)

        if self:
            current_contracts = self._get_contracts(date_start, date_stop, states=['open', 'close'])
        else:
            current_contracts = self._get_all_contracts(date_start, date_stop, states=['open', 'close'])

        new_work_entries = False
        contracts_by_company = defaultdict(lambda: self.env['hr.contract'])
        for contract in current_contracts:
            contracts_by_company[contract.company_id] |= contract

        for company, contracts in contracts_by_company.items():
            new_work_entries = bool(contracts.with_company(company)._generate_work_entries(
                date_start, date_stop, force)) or new_work_entries
        return new_work_entries
