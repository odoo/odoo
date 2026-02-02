# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    trade_registry = fields.Char()
    income_tax_id = fields.Char(string="Income Tax ID")


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    income_tax_id = fields.Char(related='company_id.income_tax_id')
