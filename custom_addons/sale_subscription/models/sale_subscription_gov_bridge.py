from odoo import models


class SaleSubscription(models.Model):
    _inherit = "sale.subscription"

    def _get_lifecycle_event_type(self):
        """
        Returns a string key describing the current subscription
        lifecycle event. Consumable by base_automation rules
        without creating a hard dependency on gov_processos.

        Keys: subscription_draft, subscription_active,
              subscription_to_renew, subscription_closed,
              subscription_cancelled
        """
        self.ensure_one()
        if not self.stage_id:
            return "subscription_draft"
        stage_name = (self.stage_id.name or "").lower()
        if "progress" in stage_name or "active" in stage_name:
            return "subscription_active"
        if "renew" in stage_name:
            return "subscription_to_renew"
        if "close" in stage_name or "cancel" in stage_name:
            return "subscription_closed"
        return "subscription_draft"

