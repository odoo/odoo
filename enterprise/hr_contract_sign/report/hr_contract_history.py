# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class HrContract(models.Model):
    _inherit = 'hr.contract.history'

    def action_sign_contract_wizard(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('hr_contract_sign.sign_contract_wizard_action')
        action['context'] = {
            'active_id': self.contract_id.id,
            'active_model': 'hr.contract',
        } if self.contract_id else {
            'active_id': self.employee_id.id,
            'active_model': 'hr.employee',
        }
        return action
