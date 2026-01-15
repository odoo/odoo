# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrModuleModule(models.Model):
    _name = 'ir.module.module'
    _inherit = ['ir.module.module']

    def action_view_delivery_methods(self):
        self.ensure_one()

        module_name = self.name  # e.g., delivery_dhl
        if not module_name.startswith('delivery_'):
            return False

        delivery_type = module_name.removeprefix('delivery_')  # dhl, fedex, etc.
        action = self.env.ref('delivery.action_delivery_carrier_form').read()[0]
        if delivery_type == 'mondialrelay':
            action['context'] = {'search_default_is_mondialrelay': True}
        else:
            action['context'] = {'search_default_delivery_type': delivery_type}
        return action
