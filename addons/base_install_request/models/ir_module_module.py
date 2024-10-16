# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.addons import base


class IrModuleModule(base.IrModuleModule):

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
