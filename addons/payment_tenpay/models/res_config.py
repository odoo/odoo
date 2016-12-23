# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class AccountPaymentConfig(osv.TransientModel):
    _inherit = 'account.config.settings'

    _columns = {
        'module_payment_tenpay': fields.boolean(
            'Manage Payments Using Tenpay',
            help='-It installs the module payment_tenpay.'),
    }
