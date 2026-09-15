from odoo import models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_domain_valid_moves(self):
        domain = super()._get_domain_valid_moves()
        _debug.logic(
            "valid_moves_domain",
            anglo_saxon=self.env.user.company_id.anglo_saxon_accounting,
        )
        if self.env.user.company_id.anglo_saxon_accounting:
            domain = Domain.AND(
                [
                    domain,
                    [("product_id.expense_policy", "not in", ("sales_price", "cost"))],
                ]
            )
        return domain
