# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountTax(models.Model):
    _inherit = 'account.tax'

    unece_code_type_tax = fields.Many2one('unece.code',
        string='UNECE Tax Type',
        domain=[('unece_type', '=', 'UN/ECE 5153')],
        help="Select the Tax Type Code of the official "
        "nomenclature of the United Nations Economic "
        "Commission for Europe (UNECE), DataElement 5153")

    unece_code_type_category = fields.Many2one('unece.code',
        string='UNECE Category Type',
        domain=[('unece_type', '=', 'UN/ECE 5305')],
        help="Select the Tax Category Code of the official "
        "nomenclature of the United Nations Economic "
        "Commission for Europe (UNECE), DataElement 5305")