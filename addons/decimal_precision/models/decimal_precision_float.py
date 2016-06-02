# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import orm


class DecimalPrecisionFloat(orm.AbstractModel):
    """ Override qweb.field.float to add a `decimal_precision` domain option
    and use that instead of the column's own value if it is specified
    """
    _inherit = 'ir.qweb.field.float'

    def precision(self, cr, uid, field, options=None, context=None):
        dp = options and options.get('decimal_precision')
        if dp:
            return self.pool['decimal.precision'].precision_get(
                cr, uid, dp)

        return super(DecimalPrecisionFloat, self).precision(
            cr, uid, field, options=options, context=context)
