# -*- coding: utf-8 -*-
from openerp import fields, models


class FiscalPrinter(models.Model):
	_name = 'fiscal.printer'

	nif = fields.Char(string='NIF', required=True)
	desc = fields.Char(string='Descripcion', required=True)
	company = fields.Many2one(comodel_name='res.company')


class ResCompany(models.Model):
	_inherit = 'res.company'

	x_rnc = fields.Char(string='RNC', required=True, default='')
	x_nif = fields.One2many(comodel_name='fiscal.printer', inverse_name='res.company')


class ResPartner(models.Model):
	_inherit = 'res.partner'

	x_rnc = fields.Char(string='RNC', required=True, default='')


class AccountInvoice(models.Model):
	_inherit = 'account.invoice'

	x_partner_rnc = fields.Char(related='partner_id.x_rnc', store=True)
	x_nif = fields.Char(related='company_id.x_nif', store=True)