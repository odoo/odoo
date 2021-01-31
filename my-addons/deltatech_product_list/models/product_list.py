# ©  2008-2020 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo import fields, models


class ProductList(models.Model):
    _name = "product.list"
    _description = "Product List"

    name = fields.Char(string="Name", required=True)
    products_domain = fields.Char(string="Products", default=[["sale_ok", "=", True]])
    active = fields.Boolean(default=True)
    limit = fields.Integer(string="Limit", default=80, required=True)
