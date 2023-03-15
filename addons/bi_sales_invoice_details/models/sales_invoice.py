# -*- coding : utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrderUpdate(models.Model):
	_inherit = 'sale.order'

	invoiced_amount = fields.Float(String = 'Invoiced Amount' ,compute ='_compute_invoice_amount')
	amount_due = fields.Float(String ='Amount Due',compute ='_compute_amount_due')
	paid_amount = fields.Float(String ='Paid Amount',compute ='_compute_amount_paid')
	amount_paid_percent = fields.Float(compute = 'action_amount_paid')
	currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id)
	

	def _compute_invoice_amount(self):
		for record in self:
			invoice_id = self.env['account.move'].search(['&',('invoice_origin','=', record.name),'|',('state','=','draft'),('state','=','posted'),('payment_state', 'not in', ['reversed', 'invoicing_legacy'])])
			total = 0

			if invoice_id:
				for invoice in invoice_id:
					total += invoice.amount_total
					record.invoiced_amount = total
			else:
				record.invoiced_amount = total


	@api.depends('paid_amount','invoiced_amount', 'amount_due')
	def _compute_amount_due(self):
		for record in self:
			invoice_ids = self.env['account.move'].search(['&',('invoice_origin','=', record.name),'|',('state','=','draft'),('state','=','posted'),('payment_state', 'not in', ['reversed', 'invoicing_legacy'])])
			amount = 0

			if invoice_ids:
				for inv in invoice_ids:
					amount  += inv.amount_residual   
					record.amount_due = amount
			else:
				record.amount_due = amount



	@api.onchange('invoiced_amount','amount_due')
	def _compute_amount_paid(self):
		self.paid_amount = float(self.invoiced_amount) - float(self.amount_due)		


	@api.depends('paid_amount','invoiced_amount')
	def action_amount_paid(self):
		if self.invoiced_amount :
			self.amount_paid_percent = round(100 * self.paid_amount / self.invoiced_amount, 3)
		return self.amount_paid_percent

