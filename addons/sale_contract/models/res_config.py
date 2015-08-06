# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

class sale_configuration(osv.osv_memory):
    _inherit = 'sale.config.settings'

    _columns = {
        'group_template_required': fields.selection([
            (0, "Optional contract templates"),
            (1, "Force setting a contract templates for every contract")
            ], "Contract Templates",
            implied_group='sale_contract.group_template_required'),
    }
