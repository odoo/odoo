# -*- coding: utf-8 -*-
#from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from datetime import date, datetime, timedelta
from openerp.osv import osv, orm, fields
from openerp import models, fields, api, _
from openerp.tools.float_utils import float_compare
from openerp.tools.translate import _

import logging
import pprint

_logger = logging.getLogger(__name__)

# class payment_mpesa(models.Model):
#     _name = 'payment_mpesa.payment_mpesa'

#     name = fields.Char()
#MPESA_DATA = {}
#
#class SaleOrder(models.Model):
#      _inherit = 'sale.order'
#       
#      def _get_website_data(self, cr, uid, order, context=None):
#         """ Override to add mpesa related DATA. """
#         values = super(SaleOrder, self)._get_website_data(cr, uid, order, context=context)
#         _logger.info('SSSSSSSSSSSSSSSSSSSSSSSSSSSS INHERITED VALEUSDSSSSSSSSSSSSSSSSSSSSSSSSS   is: %s', values)
#
#         # We need to add confirm_tx_code
#         values.update({'MPESA': MPESA_DATA})
#	 global MPESA_DATA
#	 MPESA_DATA ={}
#         return values
#      def _set_mpesa_data(self, data):
#	global MPESA_DATA
#        # set data
#	all_fields = ["acquirer", "amount", "confirm_code", "currency", "mpesa_option", "reference", "return_url"]
#        if isinstance(data, dict):
#            post = dict((field_name, data[field_name])
#                for field_name in all_fields if field_name in data)
# 
#	MPESA_DATA = {
#		'confirm_code': str(post.get('confirm_code')),
#		'acquirer': str(post.get('acquirer')),
#	}
#	return True
#
class aquirer_mpesa(models.Model):
      _inherit = 'payment.acquirer'

      def _get_providers(self, cr, uid, context=None):
        providers = super(aquirer_mpesa, self)._get_providers(cr, uid, context=context)
        providers.append(['mpesa', 'Safaricom M-PESA'])
        return providers
  
      def mpesa_get_form_action_url(self, cr, uid, id, context=None):
        return '/payment/mpesa/feedback'


      
      mpesa_option = fields.Selection([('send_money','Send Money'), ('lipa_na_mpesa','Buy Goods & Services'), ('paybill','Pay Bill')],
                        string="Select M-PESA Option", default='paybill')
      rcpt_msisdn = fields.Char('Mobile Number', size=10)
      till_number = fields.Char('Till Number', size=5)
      paybill_number = fields.Char('PayBill Number', size=6)
      
class mpesa_messages(models.Model):
	_name = "mpesa.message"	
	_inherit = 'mail.thread'
	_description = "MPESA Message"
	_order = "id desc"
	
	code = fields.Char('MPESA Code', readonly=True)
	name = fields.Char('Sender Name', readonly=True)
	msg = fields.Char('Message', readonly=True)
	time = fields.Datetime('Timestamp', readonly=True)
	phone = fields.Char('Phone Number', readonly=True)
	amount = fields.Float('Amount', digits=(32,2), readonly=True)
	bal = fields.Float('MPESA Balance', digits=(32,2), readonly=True)
	processed = fields.Boolean('Processed', default =False, readonly=True)

	@api.multi
	def mpesa_message_process(self):
           """ Function to be called by odoo  workflow to process MPESA messages as soon as they arrive into odoo database. This is important for ,             messages arriving late after the customer has placed order and made payment through MPESA """

	   txn_obj = self.env['payment.transaction']
	   for record in self:
	       # check if MPESA message is valid for processing
	       if record.code and record.msg and record.amount:
		  txn = txn_obj.search([('customer_tx_code', '=', record.code), ('state', '=', 'pending')])
		  # check if payment transactin and Sales order exist
		  if txn and txn.sale_order_id:
		     # find out which MPESA Account is used
		     if txn.acquirer_id.mpesa_option == 'send_money':
		       acquirer_reference = txn.acquirer_id.rcpt_msisdn
		     elif txn.acquirer_id.mpesa_option == 'lipa_na_mpesa':
		       acquirer_reference = txn.acquirer_id.till_number
		     else:
		       acquirer_reference = txn.acquirer_id.paybill_number
		     vals = {
		      'bal': record.amount - txn.amount,
		      'date_validate': datetime.now(),
		      'acquirer_reference': acquirer_reference,
		      'mpesa_tx_msisdn': record.phone,
		      'mpesa_tx_code': record.code,
		      'mpesa_amount': record.amount,
		      'mpesa_tx_sender': record.name,
		      'mpesa_tx_msg': record.msg,
		      }
		     # check if customer paid sufficient money
		     if record.amount >= txn.amount:
			vals['state'] = 'done'
			vals['state_message'] = 'OK'
			txn.write(vals)
			record.write({'processed': True})
			# Confirm the Sale order if txn state is 'done'
			if txn.sale_order_id.state in ['draft', 'sent']:
			   txn.sale_order_id.with_context(send_email=True).action_button_confirm()
			if txn.state not in ['cancel'] and txn.sale_order_id.state in ['draft']:
			   txn.sale_order_id.force_quotation_send()
		     else: # customer paid less
			vals['state'] = 'pending'
			vals['state_message'] = 'Customer paid less than order value'
			txn.write(vals)
			record.write({'processed': True})

class Transaction_mpesa(models.Model):
      _inherit = 'payment.transaction'

      mpesa_tx_code = fields.Char('M-PESA Transaction Code', readonly=True, required=True, default='N/A')
      bal = fields.Float('Balance', digits=(32,2))
      customer_tx_code = fields.Char('Customer Code', size=9, required=True, default='N/A')
      mpesa_tx_msisdn = fields.Char('M-PESA Number', readonly=True, required=True, default='N/A')
      mpesa_tx_msg = fields.Char('M-PESA Message', readonly=True, required=True, default='N/A')
      mpesa_tx_sender = fields.Char('M-PESA Sender', readonly=True, required=True, default='N/A')
      mpesa_amount = fields.Float('MPESA Amount', digits=(32,2), required=True, readonly=True, default=0.00)
      #mpesa_comment = fields.Char('Comment', readonly=True)
      
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
          #if data.get('confirm_code') == '' and  (data.get('mpesa_option') in ['lipa_na_mpesa', 'send_money']):
           # invalid_parameters.append(('confirm_code', '""', '9 characters of MPESA confirm code'))

          return invalid_parameters

      def _mpesa_form_validate(self, cr, uid, tx, data, context=None):
        vals = {}
        _logger.info('Validating M-PESA payment for Order %s:' % tx.reference)
	customer_tx_code = str.upper(str(data.get('confirm_code')))
	if customer_tx_code:
	   #MPESA_CODE = customer_tx_code
	   order_amount = float(data.get('amount'))
	   mpesa_obj = self.pool.get('mpesa.message')
	   mpesa_id = mpesa_obj.search(cr, uid, [('code', '=', customer_tx_code), ('processed', '=', False)], context=context)
	   mpesa = mpesa_obj.browse(cr, uid, mpesa_id, context=context)
	   if mpesa_id and mpesa.code and mpesa.amount:
	      # find out which MPESA Account is used
	      if tx.acquirer_id.mpesa_option == 'send_money':
	         acquirer_reference = tx.acquirer_id.rcpt_msisdn
	      elif tx.acquirer_id.mpesa_option == 'lipa_na_mpesa':
	         acquirer_reference = tx.acquirer_id.till_number
	      else:
	         acquirer_reference = tx.acquirer_id.paybill_number
	      vals['acquirer_reference'] = acquirer_reference
	      vals['mpesa_tx_msg'] = mpesa.msg
	      vals['mpesa_tx_msisdn'] = mpesa.phone
	      vals['mpesa_tx_code'] = mpesa.code
	      vals['mpesa_amount'] = mpesa.amount
	      vals['mpesa_tx_sender'] = mpesa.name
	      vals['date_validate'] = datetime.now()
	      vals['bal'] = mpesa.amount - order_amount
 	      if mpesa.amount >= order_amount:
	         vals['state'] = 'done'
	         vals['state_message'] = 'OK'
		 mpesa.write({'processed': True})
	      else:
	         vals['state_message'] = "Customer paid less than order value"
		 vals['state'] = 'pending'
		 mpesa.write({'processed': True})
	   else:
	      vals['state'] = 'pending'
	else:
	   vals['state'] = 'error' 
	if data.get('mpesa_option') in ['lipa_na_mpesa', 'send_money']:
           vals['customer_tx_code'] = customer_tx_code
        
        return tx.write(vals)

