# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	adv_account_id = fields.Many2one('account.account',string="Advance Receivable Account", related='company_id.adv_account_id', readonly=False)
	adv_account_creditors_id = fields.Many2one('account.account',string="Advance Payable Account", related='company_id.adv_account_creditors_id', readonly=False)