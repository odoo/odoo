# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    max_unused_cars = fields.Integer(string='Maximum unused cars')

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        Param = self.env['ir.config_parameter'].sudo()
        Param.set_param("l10n_be_hr_payroll_fleet.max_unused_cars", self.max_unused_cars)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(max_unused_cars=int(params.get_param('l10n_be_hr_payroll_fleet.max_unused_cars', default=1000)))
        return res
