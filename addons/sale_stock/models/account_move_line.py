from odoo import models

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    def _get_stock_moves(self):
        return super()._get_stock_moves() | self.sale_line_ids.move_ids

    # ------------------------------------------------------------
    # VAlIDATIONS
    # ------------------------------------------------------------

    def _sale_can_be_reinvoice(self):
        self.ensure_one()
        return (
            self.move_type != "entry"
            and self.display_type != "cogs"
            and super()._sale_can_be_reinvoice()
        )
