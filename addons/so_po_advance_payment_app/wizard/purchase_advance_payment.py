# -*- coding: utf-8 -*-

from odoo import models,fields,api,_
from odoo.exceptions import ValidationError

class PurchaseAdvancePayment(models.TransientModel):
	_name = 'purchase.advance.payment'
	_description = "Purchase Advance Payment"

	purchase_id = fields.Many2one('purchase.order', string="PO")
	journal_id = fields.Many2one('account.journal', string="Payment (Journal)")
	name = fields.Char(string="Origin", readonly=True)
	payment_date = fields.Datetime(string="Payment Date")
	total_amount = fields.Float(string="Total Amount", readonly=True)
	advance_amount = fields.Monetary(string="Advance Pay Amount", required=True)
	currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
	multi_currency_id = fields.Many2one('res.currency', string='Multi Currency')
	company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', readonly=True)
	partner_id = fields.Many2one('res.partner', string="Partner")
	# == Payment methods fields ==
	payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
		readonly=False, store=True,
		compute='_compute_payment_method_line_id',
		domain="[('id', 'in', available_payment_method_line_ids)]",
		help="Manual: Pay or Get paid by any method outside of Odoo.\n"
		"Payment Acquirers: Each payment acquirer has its own Payment Method. Request a transaction on/to a card thanks to a payment token saved by the partner when buying or subscribing online.\n"
		"Check: Pay bills by check and print it from Odoo.\n"
		"Batch Deposit: Collect several customer checks at once generating and submitting a batch deposit to your bank. Module account_batch_payment is necessary.\n"
		"SEPA Credit Transfer: Pay in the SEPA zone by submitting a SEPA Credit Transfer file to your bank. Module account_sepa is necessary.\n"
		"SEPA Direct Debit: Get paid in the SEPA zone thanks to a mandate your partner will have granted to you. Module account_sepa is necessary.\n")
	available_payment_method_line_ids = fields.Many2many('account.payment.method.line',
		compute='_compute_payment_method_line_fields')
	hide_payment_method_line = fields.Boolean(
		compute='_compute_payment_method_line_fields',
		help="Technical field used to hide the payment method if the selected journal has only one available which is 'manual'")
	payment_method_id = fields.Many2one(
		related='payment_method_line_id.payment_method_id',
		string="Method",
		store=True
	)

	payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type')
	journal_id = fields.Many2one('account.journal', string='Payment (Journal)', required=True, domain=[('type', 'in',['bank','cash'])])
	company_curr_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Company Currency', readonly=True)
	paid_payment = fields.Monetary(compute='_compute_advance_amount_diff', readonly=True, currency_field='company_curr_id')
	payment_difference = fields.Monetary(compute='_compute_payment_difference', readonly=True, currency_field='company_curr_id')

	@api.model
	def default_get(self,default_fields):
		res = super(PurchaseAdvancePayment, self).default_get(default_fields)
		context = self._context
		payment_data = {
			'name':context.get('name'), 
			'currency_id': context.get('currency_id'),
			'total_amount': context.get('total_amount'),
			'payment_date': context.get('date_order'),
			'company_id': context.get('company_id'),
			'purchase_id': context.get('order_id'),
			'partner_id': context.get('partner_id'),
		}
		res.update(payment_data)
		if 'journal_id' not in res:
			res['journal_id'] = self.env['account.journal'].search([('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('bank', 'cash'))], limit=1).id
		return res

	@api.depends('payment_type', 'journal_id')
	def _compute_payment_method_line_id(self):
		''' Compute the 'payment_method_line_id' field.
		This field is not computed in '_compute_payment_method_fields' because it's a stored editable one.
		'''
		for pay in self:
			available_payment_method_lines = pay.journal_id._get_available_payment_method_lines(pay.payment_type)

			# Select the first available one by default.
			if pay.payment_method_line_id in available_payment_method_lines:
				pay.payment_method_line_id = pay.payment_method_line_id
			elif available_payment_method_lines:
				pay.payment_method_line_id = available_payment_method_lines[0]._origin
			else:
				pay.payment_method_line_id = False

	@api.depends('payment_type', 'journal_id')
	def _compute_payment_method_line_fields(self):
		for pay in self:
			pay.available_payment_method_line_ids = pay.journal_id._get_available_payment_method_lines(pay.payment_type)
			to_exclude = self._get_payment_method_codes_to_exclude()
			if to_exclude:
				pay.available_payment_method_line_ids = pay.available_payment_method_line_ids.filtered(lambda x: x.code not in to_exclude)
			if pay.payment_method_line_id.id not in pay.available_payment_method_line_ids.ids:
				# In some cases, we could be linked to a payment method line that has been unlinked from the journal.
				# In such cases, we want to show it on the payment.
				pay.hide_payment_method_line = False
			else:
				pay.hide_payment_method_line = len(pay.available_payment_method_line_ids) == 1 and pay.available_payment_method_line_ids.code == 'manual'

	def _get_payment_method_codes_to_exclude(self):
		# can be overriden to exclude payment methods based on the payment characteristics
		self.ensure_one()
		return []

	@api.onchange('currency_id')
	def _onchange_currency(self):
		if self.currency_id and self.journal_id and self.payment_date:
			advance_amount = abs(self._compute_payment_amount(self.currency_id, self.journal_id, self.payment_date))
			self.advance_amount = advance_amount
		else:
			self.advance_amount = 0.0

		if self.journal_id:  # TODO: only return if currency differ?
			return

		# Set by default the first liquidity journal having this currency if exists.
		domain = [('type', 'in', ('bank', 'cash')), 
				  ('currency_id', '=', self.currency_id.id),
				  ('company_id', '=', self.company_id.id),]
		journal = self.env['account.journal'].search(domain, limit=1)
		if journal:
			return {'value': {'journal_id': journal.id}}

	@api.model
	def _compute_payment_amount(self, currency, journal, date):
		company = journal.company_id
		date = date or fields.Date.today()
		total = 0.0
		if company.currency_id == currency:
			if self.advance_amount == 0.0:
				total += self.advance_amount
			else:
				if self.multi_currency_id:
					total += self.multi_currency_id._convert(self.advance_amount, company.currency_id, company, date)
					self.multi_currency_id = False
				else:
					total += company.currency_id._convert(self.advance_amount, currency, company, date)
		else:
			total += company.currency_id._convert(self.advance_amount, currency, company, date)
			self.multi_currency_id = currency
		return total

	@api.depends('advance_amount', 'payment_date')
	def _compute_advance_amount_diff(self):
		self.paid_payment = 0.0
		active_id = self._context.get('active_id')
		purchase_id = self.env['purchase.order'].browse(active_id)
		if len(purchase_id.payment_history_ids) == 0:
			return
		self.paid_payment= self._compute_total_amount()

	@api.model
	def _compute_total_amount(self):
		""" Compute the sum of the residual of invoices, expressed in the payment currency """
		total = 0
		active_id = self._context.get('active_id')
		purchase_id = self.env['purchase.order'].browse(active_id)
		for pay in purchase_id.payment_history_ids:
			total += pay.advance_amount
		return abs(total)

	@api.depends('payment_date','total_amount')
	def _compute_payment_difference(self):
		active_id = self._context.get('active_id')
		purchase_id = self.env['purchase.order'].browse(active_id)
		payment_difference = 0.0
		if purchase_id.payment_history_ids:
			for pay in purchase_id.payment_history_ids:
				payment_difference += pay.advance_amount
			self.payment_difference = (self.total_amount - payment_difference)
		else:
			self.payment_difference = payment_difference

	def gen_purchase_advance_payment(self):
		if self.total_amount < self.advance_amount or self.advance_amount == 0.00:
			raise ValidationError(_('Please enter valid advance payment amount..!'))

		payment_obj = self.env['account.payment']
		payment_data = {
			'currency_id':self.currency_id.id,
			'payment_type':'outbound',
			'partner_type':'supplier',
			'partner_id':self.partner_id.id, 
			'amount':self.advance_amount,
			'journal_id':self.journal_id.id,
			'date':self.payment_date,
			'ref':self.purchase_id.name,
			'payment_method_id':self.payment_method_id.id,
			'check_advance_payment': True
		}
		account_payment_id = self.env['account.payment'].with_context(check_advance_payment=True).create(payment_data)
		account_payment_id.with_context(check_advance_payment=True).action_post()

		if self.currency_id != self.company_id.currency_id:
			amount_currency = self.advance_amount
			advance_amount = self.currency_id._convert(self.advance_amount, self.company_id.currency_id, self.company_id, self.payment_date)
			currency_id = self.currency_id
		else:
			advance_amount = abs(self._compute_payment_amount(self.currency_id, self.journal_id, self.payment_date))
			amount_currency = 0.0
			currency_id = self.company_id.currency_id

		if account_payment_id.state == 'posted':
			self.purchase_id.write({'payment_history_ids':[(0,0,{
				'name': self.name,
				'payment_date':self.payment_date,
				'partner_id':self.partner_id.id,
				'journal_id':self.journal_id.id,
				'payment_method_id':self.payment_method_id.id,
				'amount_currency': amount_currency,
				'currency_id': currency_id.id,
				'advance_amount': advance_amount,
				'total_amount':self.total_amount})]})
		action_vals = {
			'name': _('Advance Payment'),
			'domain': [('id', 'in', account_payment_id.ids), ('state', '=', 'posted')],
			'view_type': 'form',
			'res_model': 'account.payment',
			'view_id': False,
			'type': 'ir.actions.act_window',
		}

		if len(account_payment_id) == 1:
			action_vals.update({'res_id': account_payment_id[0].id, 'view_mode': 'form'})
		return action_vals


# Purchase Advance Payment History
class AdvancePaymentHistoryPurchase(models.Model):
	_name = 'purchase.payment.history'
	_description = 'Purchase Advance Payment History'

	purchase_id = fields.Many2one('purchase.order', string="Purchase")
	name = fields.Char(string="Name", readonly=True)
	journal_id = fields.Many2one('account.journal', string="Payment (Journal)", readonly=True)
	payment_date = fields.Datetime(string="Payment Date", readonly=True)
	company_currency_id = fields.Many2one('res.currency', string="Company Currency", readonly=True, default=lambda self: self.env.user.company_id.currency_id)
	total_amount = fields.Monetary(string="Total Amount", readonly=True, currency_field='company_currency_id')
	amount_currency = fields.Monetary(string="Amount in Currency", readonly=True)
	advance_amount = fields.Monetary(string="Advance Paid Amount", readonly=True, currency_field='company_currency_id')
	currency_id = fields.Many2one('res.currency', string="Currency", readonly=True)
	partner_id = fields.Many2one('res.partner', string="Partner")
	payment_method_id = fields.Many2one('account.payment.method', string="Payment Method", readonly=True)

