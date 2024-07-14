# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _get_employee_start_date_field(self):
        self.ensure_one()
        return 'first_contract_date'
