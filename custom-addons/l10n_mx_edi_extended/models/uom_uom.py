# coding: utf-8

from odoo import fields, models


class ProductUoM(models.Model):
    _inherit = 'uom.uom'

    l10n_mx_edi_code_aduana = fields.Char(
        string="Customs code",
        help="Used in the complement of 'Comercio Exterior' to indicate in the products the UoM. It is based in the "
             "SAT catalog.")
