# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    def action_open_install_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'name': _('Activation Request of "%s"', self.shortdesc),
            'view_mode': 'form',
            'res_model': 'base.module.install.request',
            'context': {'default_module_id': self.id},
        }
