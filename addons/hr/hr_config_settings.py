# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrConfigSettings(models.TransientModel):
    _name = 'hr.config.settings'
    _inherit = 'res.config.settings'

    module_hr_gamification = fields.Boolean('Evaluate and motivate the employees',
        help='This app gives you tools to challenge employees to reach specific targets.\n'
             'Goals are assigned through challenges to evaluate and compare team members with each other and through time.')
    module_hr_contract = fields.Boolean("Manage employees contracts",
        help='Add all information on the employee form to manage employees contracts \n'
             'like Contract, Place of Birth, Medical Examination Date and Company Vehicle.')
