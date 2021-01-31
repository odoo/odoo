# ©  2015-2020 Deltatech
# See README.rst file on addons root folder for license details


from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    company_standard = fields.Char("Standard of Company", size=64)
    data_sheet = fields.Integer("Data Sheet")
    technical_specification = fields.Integer("Technical Specification")
    standards = fields.Text("Standards")
