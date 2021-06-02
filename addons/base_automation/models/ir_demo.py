# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrDemo(models.TransientModel):
    _inherit = 'ir.demo'

    def install_demo(self):
        # Prevent the registry to reload while loading demo data, since `create` calls
        # `_update_registry`.
        self.pool.ready = False
        try:
            result = super().install_demo()
        finally:
            self.pool.ready = True

        # Reload the registry
        self.env['base.automation']._update_registry()

        return result
