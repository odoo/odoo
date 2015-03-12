# -*- coding: utf-8 -*-

from openerp import models, fields


class sale_report(models.Model):
    _inherit = 'sale.report'

    margin = fields.Float('Margin')

    def _select(self):
        return super(sale_report, self)._select() + ", SUM(l.margin) AS margin"
