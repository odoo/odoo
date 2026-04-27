# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import SQL


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def _get_extra_query_base_tax_line_mapping(self) -> SQL:
        """Override to add vehicle_id matching condition for tax details query.
        This ensures that tax lines are matched with base lines having the same vehicle_id when
        both are set, while allowing the match when either side has no vehicle_id. This avoids
        inconsistencies when a single tax line is shared across base lines with mixed vehicle
        assignments (one set, one NULL).
        """
        query = super()._get_extra_query_base_tax_line_mapping()
        return SQL("%s AND (base_line.vehicle_id = account_move_line.vehicle_id OR account_move_line.vehicle_id IS NULL)", query)
