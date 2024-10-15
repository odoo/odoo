# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import UserError
from odoo.addons import point_of_sale


class AccountFiscalPosition(point_of_sale.AccountFiscalPosition):

    def write(self, vals):
        if "tax_ids" in vals:
            if self.env["pos.order"].sudo().search_count([("fiscal_position_id", "in", self.ids)]):
                raise UserError(
                    _(
                        "You cannot modify a fiscal position used in a POS order. "
                        "You should archive it and create a new one."
                    )
                )
        return super(AccountFiscalPosition, self).write(vals)
