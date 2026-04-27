# -*- coding: utf-8 -*-

import threading
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hr_contract_timeoff_auto_allocation = fields.Boolean(related="company_id.hr_contract_timeoff_auto_allocation", readonly=False)
    hr_contract_timeoff_auto_allocation_type_id = fields.Many2one(
        'hr.leave.type', related='company_id.hr_contract_timeoff_auto_allocation_type_id', readonly=False)
