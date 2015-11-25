# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv, fields

class AccountInvoice(osv.osv):
    _name = "account.invoice"
    _inherit = ['account.invoice', 'utm.mixin']
