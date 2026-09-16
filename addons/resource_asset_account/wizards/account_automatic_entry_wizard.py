from typing import Any

from odoo import models
from odoo.fields import Date


class AccountAutomaticEntryWizard(models.TransientModel):
    _inherit = "account.automatic.entry.wizard"

    def _get_move_line_dict_vals_change_period(
        self, aml: models.Model, date: Date
    ) -> list[tuple[int, int, dict[str, Any]]]:
        res = super()._get_move_line_dict_vals_change_period(aml, date)
        if aml.asset_id:
            for move_line_data in res:
                if move_line_data[2]["account_id"] == aml.account_id.id:
                    move_line_data[2]["asset_id"] = aml.asset_id.id
        return res
