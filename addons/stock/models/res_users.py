from odoo import models

from ..tools import debug_log as dbg


class ResUsers(models.Model):
    _inherit = "res.users"

    def _get_default_warehouse_id(self):
        warehouse = self.env["stock.warehouse"]._get_default_for_company(
            self.env.company
        )
        dbg.logic.debug(
            "_get_default_warehouse_id: company %s -> %s",
            self.env.company.id,
            warehouse.id,
        )
        return warehouse
