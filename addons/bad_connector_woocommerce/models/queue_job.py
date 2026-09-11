from odoo import _, models


class QueueJob(models.Model):
    _inherit = "queue.job"

    def open_related_action(self):
        """Inherited Method:Used to open related record of queue job."""
        self.ensure_one()
        if not self.args and not self.kwargs:
            return None
        record = False
        if self.args:
            if not len(self.args) > 1:
                return super().open_related_action()
            backend = self.args[0]
            external_id = self.args[1]
        elif self.kwargs:
            external_id = self.kwargs.get("external_id")
            backend = self.kwargs.get("backend")
            if not external_id:
                external_id = self.kwargs.get("record")
        if isinstance(external_id, str) or isinstance(external_id, int):
            record = self.env[self.model_name].search(
                [("external_id", "=", external_id), ("backend_id", "=", backend.id)],
                limit=1,
            )
            if self.model_name == "woo.stock.picking.refund":
                record |= self.env[self.model_name].search(
                    [
                        ("external_id", "ilike", "%s_%%" % external_id),
                        ("backend_id", "=", backend.id),
                    ],
                )
        else:
            record = external_id
        if hasattr(record, "odoo_id"):
            record = record.odoo_id
        if not record:
            return super().open_related_action()
        action = {
            "name": _("Related Record"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": record._name,
        }
        if len(record) == 1:
            action["res_id"] = record.id
        else:
            action.update(
                {
                    "name": _("Related Records"),
                    "view_mode": "tree,form",
                    "domain": [("id", "in", record.ids)],
                }
            )
        return action
