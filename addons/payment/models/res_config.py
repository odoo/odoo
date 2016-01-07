# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class AccountPaymentConfig(osv.TransientModel):
    _inherit = 'account.config.settings'

    _columns = {
        'module_payment_transfer': fields.boolean(
            'Wire Transfer',
            help='-This installs the module payment_transfer.'),
        'module_payment_paypal': fields.boolean(
            'Paypal',
            help='-This installs the module payment_paypal.'),
        'module_payment_ogone': fields.boolean(
            'Ogone',
            help='-This installs the module payment_ogone.'),
        'module_payment_adyen': fields.boolean(
            'Adyen',
            help='-This installs the module payment_adyen.'),
        'module_payment_buckaroo': fields.boolean(
            'Buckaroo',
            help='-This installs the module payment_buckaroo.'),
        'module_payment_authorize': fields.boolean(
            'Authorize.Net',
            help='-This installs the module payment_authorize.'),
        'module_payment_sips': fields.boolean(
            'Sips',
            help='-This installs the module payment_sips.'),
    }

    _defaults = {
        'module_payment_transfer': True
    }
