# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _

class purchase_config_settings(osv.osv_memory):
    _name = 'purchase.config.settings'
    _inherit = 'purchase.config.settings'

    def onchange_costing_method(self, cr, uid, ids, group_costing_method, context=None):
        if not group_costing_method:
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
