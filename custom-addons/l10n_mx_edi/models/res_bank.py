# -*- coding: utf-8 -*-

from odoo import fields, models


class ResBank(models.Model):
    _inherit = "res.bank"

    l10n_mx_edi_vat = fields.Char(
        string="VAT",
        help="Indicate the VAT of this institution, the value could be used in the payment complement in Mexico "
             "documents")
