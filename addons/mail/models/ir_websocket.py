# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.mail.tools.discuss import Store


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _im_status_to_store(self, store: Store, /, *, im_status_ids_by_model):
        if partner_ids := im_status_ids_by_model.get("res.partner"):
            store.add(
                "res.partner",
                self.env["res.partner"]
                .with_context(active_test=False)
                .search_read([("id", "in", partner_ids)], ["im_status"]),
            )

    def _update_bus_presence(self, inactivity_period, im_status_ids_by_model):
        super()._update_bus_presence(inactivity_period, im_status_ids_by_model)
        if self.env.user and not self.env.user._is_public():
            store = Store()
            self._im_status_to_store(store, im_status_ids_by_model=im_status_ids_by_model)
            if res := store.get_result():
                self.env["bus.bus"]._sendone(self.env.user.partner_id, "mail.record/insert", res)
