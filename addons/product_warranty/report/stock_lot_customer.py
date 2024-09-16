# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockLotReport(models.Model):
    _inherit = "stock.lot.report"

    warranty_end_date = fields.Date(readonly=True)

    def _select(self):
        select_str = super()._select()
        return f"""
            {select_str},
            lot.warranty_end_date
        """

    def _group_by(self):
        group_by_str = super()._group_by()
        return f"""
            {group_by_str},
            lot.warranty_end_date
        """
