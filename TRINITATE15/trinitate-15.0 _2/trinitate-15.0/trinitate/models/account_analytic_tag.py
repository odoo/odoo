# Copyright 2022, Jarsa Sistemas, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class AccountAnalyticTag(models.Model):
    _inherit = "account.analytic.tag"

    code = fields.Integer()
    product.tag = fields.Many2many(comodel_name = "product.product.tag") #linea nueva por isai
    name = fields.Char(required=True) #linea nueva por isai