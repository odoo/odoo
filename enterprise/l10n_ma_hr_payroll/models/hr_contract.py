# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class HrContract(models.Model):
    _inherit = 'hr.contract'

    l10n_ma_kilometric_exemption = fields.Monetary(
        string='Kilometric Exemption',
        tracking=True)
    l10n_ma_transport_exemption = fields.Monetary(
        string='Transportation Exemption',
        tracking=True)
    l10n_ma_hra = fields.Monetary(string='HRA', tracking=True, help="House rent allowance.")
    l10n_ma_da = fields.Monetary(string="DA", help="Dearness allowance")
    l10n_ma_meal_allowance = fields.Monetary(string="Meal Allowance", help="Meal allowance")
    l10n_ma_medical_allowance = fields.Monetary(string="Medical Allowance", help="Medical allowance")
