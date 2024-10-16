# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields
from odoo.addons import account


class ResCompany(account.ResCompany):

    sst_registration_number = fields.Char(related='partner_id.sst_registration_number', readonly=False)
    ttx_registration_number = fields.Char(related='partner_id.ttx_registration_number', readonly=False)


class BaseDocumentLayout(account.BaseDocumentLayout):

    account_fiscal_country_id = fields.Many2one(related="company_id.account_fiscal_country_id")
    sst_registration_number = fields.Char(related='company_id.sst_registration_number')
    ttx_registration_number = fields.Char(related='company_id.ttx_registration_number')
