# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountTax(models.Model):
    _inherit = 'account.tax'

    unece_code_category = fields.Many2one('unedifact.code',
        string='UNECE Category Type',
        domain=[('type_id.name', '=', 'UN/ECE 5305')],
        help="Select the Tax Category Code of the official "
        "nomenclature of the United Nations Economic "
        "Commission for Europe (UNECE), DataElement 5305")