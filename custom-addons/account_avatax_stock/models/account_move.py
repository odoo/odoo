from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_line_data_for_external_taxes(self):
        """ Override to set the originating warehouse per line. """
        res = super()._get_line_data_for_external_taxes()
        for i, line in enumerate(self._get_lines_eligible_for_external_taxes()):
            res[i]['warehouse_id'] = line.sale_line_ids.move_ids.location_id.warehouse_id if len(line.sale_line_ids.move_ids) == 1 else None
        return res
