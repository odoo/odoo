# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models
from openerp.tools.translate import _


class PurchaseConfigSettings(models.TransientModel):
    _name = 'purchase.config.settings'
    _inherit = 'purchase.config.settings'

    @api.onchange('group_costing_method')
    def onchange_costing_method(self):
        if self.group_costing_method == 0:
            return {
                'warning': {
                    'title': _('Warning!'),
                    'message': _('Disabling the costing methods will prevent you to use the landed costs feature.'),
                },
                'value': {
                    'group_costing_method': 1
                }
            }
        return {}
