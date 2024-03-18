# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class CustomBaseConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    entry_strategy = fields.Selection([
        ('1', 'First Entry as Check In and last entry as Check Out'),
        ('2', 'Actual In/Out time as per the input from device'),
        ('3', 'Consider first entry as check-in, next entry as check-out, and next entry as check-in ..'),
    ], string='Attedance Entry as', default='1')

    update_device = fields.Boolean('Update Device Automatically', default=False)


    # @api.model
    # def get_default_entry_strategy(self, fields):
    #     # entry_strategy = 1
    #     # update_device = False
    #     params = self.env['ir.config_parameter'].sudo()
    #     entry_strategy=params.get_param('cams-attendance.entry_strategy') or '1'
    #     update_device=params.get_param('cams-attendance.update_device') or False
        
    #     return {
    #         'entry_strategy': entry_strategy,
    #         'update_device': update_device,
    #     }
        
    # def set_default_entry_strategy(self):
    #     for config in self:
    #         config.write({'entry_strategy': self.entry_strategy, 'update_device':self.update_device})
    @api.model
    def get_values(self):
        res = super(CustomBaseConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            entry_strategy=params.get_param('cams-attendance.entry_strategy', default='2'),
            update_device=params.get_param('cams-attendance.update_device'),
        )
        return res

    def set_values(self):
        super(CustomBaseConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param("cams-attendance.entry_strategy", self.entry_strategy)
        self.env['ir.config_parameter'].sudo().set_param("cams-attendance.update_device", self.update_device)
