from odoo import api, models
from odoo.exceptions import UserError

from ..tools import debug_log as dbg


class IrSequence(models.Model):
    _inherit = "ir.sequence"

    @api.ondelete(at_uninstall=False)
    def _unlink_sequence(self):
        configs = self.env["pos.config"].search(
            domain=[
                "|",
                "|",
                "|",
                ("order_seq_id", "in", self.ids),
                ("order_line_seq_id", "in", self.ids),
                ("device_seq_id", "in", self.ids),
                ("order_backend_seq_id", "in", self.ids),
            ]
        )
        if len(configs):
            dbg.logic.debug(
                "ir.sequence unlink of %s refused: used by %s",
                dbg.rec(self),
                dbg.rec(configs),
            )
            raise UserError(
                self.env._(
                    "You cannot delete a sequence used in an active POS config: %s",
                    configs.order_seq_id.mapped("name"),
                )
            )
