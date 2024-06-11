# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
	_inherit = 'sale.order'

	payment_history_ids = fields.One2many('advance.payment.history','order_id',string="Advanvce Payment Information")

	def set_sale_advance_payment(self):
		view_id = self.env.ref('so_po_advance_payment_app.sale_advance_payment_wizard')
		if view_id:
			pay_wiz_data={
				'name' : _('Sale Advance Payment'),
				'type' : 'ir.actions.act_window',
				'view_type' : 'form',
				'view_mode' : 'form',
				'res_model' : 'sale.advance.payment',
				'view_id' : view_id.id,
				'target' : 'new',
				'context' : {
							'name':self.name,
							'order_id':self.id,
							'total_amount':self.amount_total,
							'company_id':self.company_id.id,
							'currency_id':self.currency_id.id,
							'date_order':self.date_order,
							'currency_rate':self.currency_rate,
							'partner_id':self.partner_id.id,
							 },
			}
		return pay_wiz_data


class AccountPayment(models.Model):
	_inherit = "account.payment"

	check_advance_payment = fields.Boolean('Check Advance Payment', default=False)


	def _prepare_move_line_default_vals(self, write_off_line_vals=None):
		''' Prepare the dictionary to create the default account.move.lines for the current payment.
		:param write_off_line_vals: Optional dictionary to create a write-off account.move.line easily containing:
			* amount:       The amount to be added to the counterpart amount.
			* name:         The label to set on the line.
			* account_id:   The account on which create the write-off.
		:return: A list of python dictionary to be passed to the account.move.line's 'create' method.
		'''
		self.ensure_one()
		write_off_line_vals = write_off_line_vals or {}

		if not self.company_id.adv_account_id and not self.company_id.adv_account_creditors_id:
			raise UserError(_(
				"You can't create a new advance payment without an customer/supplier receivable/payable account"))

		if not self.outstanding_account_id:
			raise UserError(_(
				"You can't create a new payment without an outstanding payments/receipts account set either on the company or the %s payment method in the %s journal.",
				self.payment_method_line_id.name, self.journal_id.display_name))

		# Compute amounts.
		write_off_amount_currency = write_off_line_vals.get('amount', 0.0)

		if self.payment_type == 'inbound':
			# Receive money.
			liquidity_amount_currency = self.amount
		elif self.payment_type == 'outbound':
			# Send money.
			liquidity_amount_currency = -self.amount
			write_off_amount_currency *= -1
		else:
			liquidity_amount_currency = write_off_amount_currency = 0.0

		write_off_balance = self.currency_id._convert(
			write_off_amount_currency,
			self.company_id.currency_id,
			self.company_id,
			self.date,
		)
		liquidity_balance = self.currency_id._convert(
			liquidity_amount_currency,
			self.company_id.currency_id,
			self.company_id,
			self.date,
		)
		counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
		counterpart_balance = -liquidity_balance - write_off_balance
		currency_id = self.currency_id.id

		if self.is_internal_transfer:
			if self.payment_type == 'inbound':
				liquidity_line_name = _('Transfer to %s', self.journal_id.name)
			else: # payment.payment_type == 'outbound':
				liquidity_line_name = _('Transfer from %s', self.journal_id.name)
		else:
			liquidity_line_name = self.payment_reference

		# Compute a default label to set on the journal items.

		payment_display_name = {
			'outbound-customer': _("Customer Reimbursement"),
			'inbound-customer': _("Customer Payment"),
			'outbound-supplier': _("Vendor Payment"),
			'inbound-supplier': _("Vendor Reimbursement"),
		}

		default_line_name = self.env['account.move.line']._get_default_line_name(
			_("Internal Transfer") if self.is_internal_transfer else payment_display_name['%s-%s' % (self.payment_type, self.partner_type)],
			self.amount,
			self.currency_id,
			self.date,
			partner=self.partner_id,
		)
		if self._context.get('check_advance_payment') == True:
			if self.partner_type == 'customer':
				destination_account_id = self.company_id.adv_account_id.id
			else:
				destination_account_id = self.company_id.adv_account_creditors_id.id
		else:
			destination_account_id = self.destination_account_id.id
		line_vals_list = [
			# Liquidity line.
			{
				'name': liquidity_line_name or default_line_name,
				'date_maturity': self.date,
				'amount_currency': liquidity_amount_currency,
				'currency_id': currency_id,
				'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
				'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
				'partner_id': self.partner_id.id,
				'account_id': self.outstanding_account_id.id,
			},
			# Receivable / Payable.
			{
				'name': self.payment_reference or default_line_name,
				'date_maturity': self.date,
				'amount_currency': counterpart_amount_currency,
				'currency_id': currency_id,
				'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
				'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
				'partner_id': self.partner_id.id,
				'account_id': destination_account_id,
			},
		]
		if not self.currency_id.is_zero(write_off_amount_currency):
			# Write-off line.
			line_vals_list.append({
				'name': write_off_line_vals.get('name') or default_line_name,
				'amount_currency': write_off_amount_currency,
				'currency_id': currency_id,
				'debit': write_off_balance if write_off_balance > 0.0 else 0.0,
				'credit': -write_off_balance if write_off_balance < 0.0 else 0.0,
				'partner_id': self.partner_id.id,
				'account_id': write_off_line_vals.get('account_id'),
			})
		return line_vals_list