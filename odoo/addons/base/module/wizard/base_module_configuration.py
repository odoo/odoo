# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class BaseModuleConfiguration(models.TransientModel):
    _name = "base.module.configuration"

    @api.multi
    def start(self):
        todos_domain = ['|', ('type','=','recurring'), ('state', '=', 'open')]
        if self.env['ir.actions.todo'].search_count(todos_domain):
            # Run the config wizards
            return self.env['res.config'].start()
        else:
            # When there is no wizard todo it will display message
            view = self.env.ref('base.view_base_module_configuration_form')
            return {
                'name': _('System Configuration done'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'base.mdule.configuration',
                'view_id': [view.id],
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
