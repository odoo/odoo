# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class AccountPaymentConfig(osv.TransientModel):
    _inherit = 'account.config.settings'

    _columns = {
        'module_payment_allpay': fields.boolean(
            'Manage Payments Using allPay',
            help='-It installs the module payment_allpay.'),
    }
