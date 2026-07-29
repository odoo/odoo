# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    income_tax_id = fields.Char(string="Income Tax ID")

    def _commercial_fields(self):
        return super()._commercial_fields() + ['income_tax_id']
