from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_line_data_for_external_taxes(self):
        """ Override to set the originating warehouse per line. Set a warehouse if the line is shipped from a single location. """
        res = super()._get_line_data_for_external_taxes()
        for i, line in enumerate(self._get_lines_eligible_for_external_taxes()):
            locations = line.sale_line_ids.move_ids.filtered(lambda move: move.state != 'cancel').location_id
            shipping_addresses = locations.mapped(lambda loc: loc.warehouse_id.partner_id or loc.company_id.partner_id)
            res[i]['warehouse_id'] = locations.warehouse_id[:1] if len(shipping_addresses) == 1 else None
        return res
