# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    model_names = fields.Char(config_parameter='hide.action.buttons.models')

    def execute(self):

        existing_record = self.env['hide.action.buttons'].search([])
        if existing_record:
            existing_record.update({
            'model_names': self.model_names ,

        })
        else:
            self.env['hide.action.buttons'].create({'model_names': self.model_names})


        return  super(ResConfigSettings,self).execute()