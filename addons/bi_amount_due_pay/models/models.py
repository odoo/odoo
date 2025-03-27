# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime,date, timedelta
from dateutil.relativedelta import relativedelta
import base64


class account_move(models.Model):
	
	_inherit = 'account.move'
	_order = 'date desc'
	
	def _get_result(self):
		for aml in self:
			aml.result = 0.0
			
			aml.result = abs(aml.amount_total_signed) - abs(aml.credit_amount)
	
					 

	def _get_credit(self):
		for aml in self:
			aml.credit_amount = 0.0
			aml.credit_amount = abs(aml.amount_total_signed) - abs(aml.amount_residual_signed)

	credit_amount = fields.Float(compute ='_get_credit',   string="Credit/paid")
	result = fields.Float(compute ='_get_result',   string="Balance") #'balance' field is not the sames

class Amountdue(models.Model):
	_inherit='res.partner'

	def _compute_amount_due(self):
		user_id = self._uid		
		current_date = fields.date.today()

		for partner in self:
			amount_due = amount_overdue = 0.0
			supplier_amount_due = supplier_amount_overdue = 0.0

			balance_invoice_moves = self.env['account.move'].sudo().search([
				('partner_id', '=', partner.id),
				('move_type', 'in', ['out_invoice', 'out_refund', 'entry']),
				('state', '=', 'posted')
			])

			for aml in balance_invoice_moves:
				date_maturity = aml.invoice_date_due or aml.date
				amount_due += aml.result
				if date_maturity and date_maturity <= current_date:
					amount_overdue += aml.result

			partner.payment_amount_due_amt = amount_due

			supplier_invoice_moves = self.env['account.move'].sudo().search([
				('partner_id', '=', partner.id),
				('move_type', 'in', ['in_invoice', 'in_refund', 'entry']),
				('state', '=', 'posted')
			])

			for aml in supplier_invoice_moves:
				date_maturity = aml.invoice_date_due or aml.date
				supplier_amount_due += aml.result
				if date_maturity and date_maturity <= current_date:
					supplier_amount_overdue += aml.result

			partner.payment_amount_due_amt_supplier = supplier_amount_due
			
		
	supplier_invoice_ids = fields.One2many('account.move', 'partner_id', 'Supplier move lines', domain=[('move_type', 'in', ['in_invoice','in_refund','entry']),('state', 'in', ['posted'])]) 
	balance_invoice_ids = fields.One2many('account.move', 'partner_id', 'Customer move lines', domain=[('move_type', 'in', ['out_invoice','out_refund','entry']),('state', 'in', ['posted'])]) 
	payment_amount_due_amt = fields.Float(string ='Amount Due',compute ='_compute_amount_due')
	payment_amount_due_amt_supplier = fields.Float(compute='_compute_amount_due', string="Amount To Pay")


	def action_view_amount_due(self):
		self.ensure_one()
		action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
		action['domain'] = [
			('move_type', 'in', ('out_invoice', 'out_refund')),
			('partner_id', 'child_of', self.id),
		]
		action['context'] = {'default_move_type':'out_invoice', 'move_type':'out_invoice', 'journal_type': 'sale', 'search_default_open': 1}
		return action		 

	def action_view_amount_to_pay(self):
		self.ensure_one()
		action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_in_invoice_type")
		action['domain'] = [
			('move_type', 'in', ('in_invoice','in_refund')),
			('partner_id', 'child_of', self.id),
		]
		action['context'] = {'default_move_type':'out_invoice', 'move_type':'out_invoice', 'journal_type': 'sale', 'search_default_open': 1}
		return action