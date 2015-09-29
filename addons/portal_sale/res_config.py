# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv 

class sale_portal_config_settings(osv.TransientModel):
    _inherit = 'account.config.settings'

    _columns = {
        'group_payment_options': fields.boolean('Show payment buttons to employees too',
            implied_group='portal_sale.group_payment_options',
            help="Show online payment options on Sale Orders and Customer Invoices to employees. "
                 "If not checked, these options are only visible to portal users."),
    }