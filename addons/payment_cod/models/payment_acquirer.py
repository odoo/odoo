# -*- coding: utf-'8' "-*-"

from odoo import fields, models

class CodAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('cod', 'COD')])
