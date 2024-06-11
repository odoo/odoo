# -*- coding: utf-8 -*-


from odoo import fields, models

class Company(models.Model):
	_inherit = 'res.company'

	adv_account_id = fields.Many2one('account.account',string="Advance Receivable Account")
	adv_account_creditors_id = fields.Many2one('account.account',string="Advance Payable Account")
