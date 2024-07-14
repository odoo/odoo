# coding: utf-8

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_mx_edi_tariff_fraction_id = fields.Many2one(
        comodel_name='l10n_mx_edi.tariff.fraction',
        string="Tariff Fraction",
        help="It is used to express the key of the tariff fraction corresponding to the description of the product to "
             "export.")
    l10n_mx_edi_umt_aduana_id = fields.Many2one(
        comodel_name='uom.uom',
        string="UMT Aduana",
        help="Used in complement 'Comercio Exterior' to indicate in the products the TIGIE Units of Measurement. "
             "It is based in the SAT catalog.")
