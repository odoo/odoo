# -*- coding: utf-8 -*-
from openerp import fields, models


class ResCompany(models.Model):
	_inherit = 'res.company'

	x_rnc = fields.Char(string='RNC', required=True, default='')


class ResPartner(models.Model):
	_inherit = 'res.partner'

	x_rnc = fields.Char(string='RNC', required=True, default='')


class AccountInvoice(models.Model):
	_inherit = 'account.invoice'

	x_rnc = fields.Char(related='partner_id.x_rnc', store=True)