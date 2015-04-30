# -*- coding: utf-8 -*-

from openerp import fields, models

class CrmPhonecall(models.Model):
	_inherit = 'crm.phonecall'

	claim_id = fields.Many2one('crm.claim', string='Claim')