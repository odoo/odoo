# -*- coding: utf-8 -*-
from openerp.addons.payment.models.payment_acquirer import ValidationError
#from openerp import models, fields, api
from openerp.osv import osv, fields

from openerp.tools.float_utils import float_compare
from openerp.tools.translate import _

import logging
import pprint

_logger = logging.getLogger(__name__)

# class payment_mpesa(models.Model):
#     _name = 'payment_mpesa.payment_mpesa'

#     name = fields.Char()
class aquirer_mpesa(osv.Model):
      _inherit = 'payment.acquirer'

      def _get_providers(self, cr, uid, context=None):
        providers = super(aquirer_mpesa, self)._get_providers(cr, uid, context=context)
        providers.append(['mpesa', 'Safaricom M-PESA'])
        return providers
  
      def mpesa_get_form_action_url(self, cr, uid, id, context=None):
        return '/payment/mpesa/feedback'


      _columns = {
	'mpesa_option': fields.selection([('send_money','Send Money'), ('lipa_na_mpesa','Buy Goods & Services'), ('paybill','Pay Bill')], 
                        string="Select M-PESA Option", default='paybill'),
        'rcpt_msisdn': fields.char('Mobile Number', size=10),
	'till_number': fields.char('Till Number', size=5),
	'paybill_number': fields.char('PayBill Number', size=6),
      }
class Transaction_mpesa(osv.Model):
      _inherit = 'payment.transaction'

      _columns = {
	'mpesa_tx_code': fields.char('M-PESA Transaction Code', readonly=True, required=True, default='N/A'),
        'customer_tx_code': fields.char('Customer Code', size=9, required=True),
	'mpesa_tx_msisdn': fields.char('M-PESA Number', readonly=True, required=True, default='N/A'),
        'mpesa_tx_msg': fields.char('M-PESA Message', readonly=True, required=True, default='N/A'),
      }	
      
      def _mpesa_form_get_tx_from_data(self, cr, uid, data, context=None):
        reference, amount, currency_name = data.get('reference'), data.get('amount'), data.get('currency_name')
        tx_ids = self.search(
            cr, uid, [
                ('reference', '=', reference),
            ], context=context)

        if not tx_ids or len(tx_ids) > 1:
            error_msg = 'received data for Order reference %s' % (pprint.pformat(reference))
            if not tx_ids:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        return self.browse(cr, uid, tx_ids[0], context=context)

      def _mpesa_form_get_invalid_parameters(self, cr, uid, tx, data, context=None):
          invalid_parameters = []

          if float_compare(float(data.get('amount', '0.0')), tx.amount, 2) != 0:
            invalid_parameters.append(('amount', data.get('amount'), '%.2f' % tx.amount))
          if data.get('currency') != tx.currency_id.name:
            invalid_parameters.append(('currency', data.get('currency'), tx.currency_id.name))

          return invalid_parameters

      def _mpesa_form_validate(self, cr, uid, tx, data, context=None):
        vals = {}
        _logger.info('Validated M-PESA payment for Order %s: set as pending payment from customer' % tx.reference)
        vals['state'] = 'pending'
	if data.get('mpesa_option') == 'lipa_na_mpesa' or data.get('mpesa_option') == 'send_money':
           vals['customer_tx_code'] = str.upper(str(data.get('confirm_code')))
        
        return tx.write(vals)

