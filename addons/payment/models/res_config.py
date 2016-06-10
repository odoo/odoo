# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class AccountPaymentConfig(osv.TransientModel):
    _inherit = 'account.config.settings'

    _columns = {
        'module_payment_paypal': fields.boolean(
            'Manage Payments Using Paypal',
            help='-It installs the module payment_paypal.'),
        'module_payment_ogone': fields.boolean(
            'Manage Payments Using Ogone',
            help='-It installs the module payment_ogone.'),
        'module_payment_adyen': fields.boolean(
            'Manage Payments Using Adyen',
            help='-It installs the module payment_adyen.'),
        'module_payment_buckaroo': fields.boolean(
            'Manage Payments Using Buckaroo',
            help='-It installs the module payment_buckaroo.'),
        'module_payment_authorize': fields.dummy(
            'Manage Payments Using Authorize.Net',
            help='-It installs the module payment_authorize.'),
    }
