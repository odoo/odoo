# -*- coding: utf-8 -*-

from odoo import api, fields, models


class HrLeaveConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    alias_prefix = fields.Char(string='Default Alias Name for Leave', help='Default Alias Name for Leave')
    alias_domain = fields.Char(string='Alias Domain', help='Default Alias Domain for Leave',
                               default=lambda self: self.env["ir.config_parameter"].get_param("mail.catchall.domain"))

    def set_values(self):
        super(HrLeaveConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].set_param
        set_param('alias_prefix', self.alias_prefix)
        set_param('alias_domain', self.alias_domain ),


    @api.model
    def get_values(self):
        res = super(HrLeaveConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            alias_prefix=get_param('alias_prefix', default=''),
            alias_domain=get_param('alias_domain', default=''),
        )
        return res

