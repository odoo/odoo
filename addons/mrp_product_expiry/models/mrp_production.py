from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def pre_button_mark_done(self):
        confirm_expired_lots = self._get_expired_lots_action()
        if confirm_expired_lots:
            return confirm_expired_lots
        return super().pre_button_mark_done()

    def _get_expired_lots_action(self):
        if self.env.context.get("skip_expired"):
            _debug.logic("expiry_check_skipped", productions=self, by="context")
            return False
        expired_lot_ids = self.move_raw_ids.move_line_ids._filtered_expired().lot_id.ids
        _debug.logic(
            "expiry_checked", productions=self, expired_lots=len(expired_lot_ids)
        )
        if expired_lot_ids:
            return {
                "name": self.env._("Confirmation"),
                "type": "ir.actions.act_window",
                "res_model": "expiry.picking.confirmation",
                "view_mode": "form",
                "views": [(False, "form")],
                "target": "new",
                "context": self._get_expired_context(expired_lot_ids),
            }
        return False

    def _get_expired_context(self, expired_lot_ids):
        context = dict(self.env.context)
        context.update(
            {
                "default_lot_ids": [(6, 0, expired_lot_ids)],
                "default_production_ids": self.ids,
            }
        )
        return context
