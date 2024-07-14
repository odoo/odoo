# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.http import request

from odoo.addons.hr_contract_salary.controllers import main
from odoo.addons.sign.controllers.main import Sign

class SignContract(Sign):

    def _update_contract_on_signature(self, request_item, contract, offer):
        result = super()._update_contract_on_signature(request_item, contract, offer)
        if request_item.sign_request_id.nb_closed == 2 and not contract.leave_allocation_id:
            auto_allocation = contract.company_id.hr_contract_timeoff_auto_allocation
            if auto_allocation and contract.holidays:
                time_off_type = contract.company_id.hr_contract_timeoff_auto_allocation_type_id
                # Sudo is required here because it isn't guaranteed that the second person signing will be a manager.
                records = request.env['hr.leave.allocation'].sudo().create({
                    'name': time_off_type.name,
                    'employee_id': contract.employee_id.id,
                    'number_of_days': contract.holidays,
                    'holiday_status_id': time_off_type.id,
                    'state': 'validate',
                    'notes': _('Allocation automatically created from Contract Signature.'),
                })
                contract.leave_allocation_id = records[0]
        return result
