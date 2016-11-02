# -*- coding: utf-8 -*-

from odoo import models, fields

class PaymentModeType(models.Model):
    _inherit = 'payment.mode.type'

    unece_code_type_payment_mean = fields.Many2one('unece.code.list',
        string='UNECE Payment Mean Type',
        domain=[('type', '=', 'UN/ECE 4461')],
        help="Standard nomenclature of the United Nations Economic "
        "Commission for Europe (UNECE) defined in UN/EDIFACT Data "
        "Element 4461")