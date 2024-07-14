from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_line_data_for_external_taxes(self):
        """ Override to set the originating warehouse per line. """
        res = super()._get_line_data_for_external_taxes()
        for i, line in enumerate(self._get_lines_eligible_for_external_taxes()):
            res[i]['warehouse_id'] = line.move_ids.location_id.warehouse_id if len(line.move_ids) == 1 else None
        return res
