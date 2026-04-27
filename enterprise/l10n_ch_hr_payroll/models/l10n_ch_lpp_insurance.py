# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class l10nChLppInsurance(models.Model):
    _name = 'l10n.ch.lpp.insurance'
    _description = 'Swiss: LPP Insurances'

    name = fields.Char(required=True)
    customer_number = fields.Char(required=True)
    contract_number = fields.Char(required=True)
    insurance_company_address_id = fields.Many2one('res.partner')
    insurance_company = fields.Char(required=True)
    insurance_code = fields.Char(required=True)
    fund_number = fields.Char(help="""Payroll units allow companies and pension institutions to create "packages" that are transmitted independently of one another using the ELM standard.""")
