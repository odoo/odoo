# -*- coding: utf-8 -*-

#from openerp import models, fields, api
from openerp.osv import fields, osv
# class mpesa_payment(models.Model):
#     _name = 'mpesa_payment.mpesa_payment'

#     name = fields.Char()
class account_mobile_money_config(osv.TransientModel):
      _inherit = 'account.config.settings'
      _columns = {
        'module_payment_mpesa': fields.boolean('Manage Payments Using Safaricom MPESA', help='-It installs the module payment_mpesa.'),
        'module_payment_airtel': fields.boolean('Manage Payments Using Airtel Money', help='-It installs the module payment_airtel.'),
      }
