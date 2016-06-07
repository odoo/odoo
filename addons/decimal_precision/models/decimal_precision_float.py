# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class DecimalPrecisionFloat(models.AbstractModel):
    """ Override qweb.field.float to add a `decimal_precision` domain option
    and use that instead of the column's own value if it is specified
    """
    _inherit = 'ir.qweb.field.float'

    @api.model
    def precision(self, field, options=None):
        dp = options and options.get('decimal_precision')
        if dp:
            return self.env['decimal.precision'].precision_get(dp)
        return super(DecimalPrecisionFloat, self).precision(field, options=options)
