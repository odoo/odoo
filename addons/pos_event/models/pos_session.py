# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_hr_employee(self):
        if len(self.config_id.employee_ids) > 0:
            domain = ['&', ('company_id', '=', self.config_id.company_id.id), '|', ('user_id', '=', self.user_id.id), ('id', 'in', self.config_id.employee_ids.ids)]
        else:
            domain = [('company_id', '=', self.config_id.company_id.id)]
        return {'search_params': {'domain': domain, 'fields': ['name', 'id', 'user_id'], 'load': False}}

    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        result['search_params']['fields'].append('detailed_type')
        return result
