from odoo import fields, models


class SignRequest(models.Model):
    _inherit = "sign.request"

    sale_subscription_id = fields.Many2one(
        "sale.subscription",
        string="Related Subscription",
        ondelete="set null",
        index=True,
    )

    def action_signed(self):
        res = super().action_signed()
        for request in self:
            if request.sale_subscription_id:
                try:
                    request.sale_subscription_id.action_start_subscription()
                except Exception:
                    pass
        return res

    def _get_signing_event_type(self):
        """
        Lifecycle key for base_automation rules.
        Keys: sign_draft, sign_sent, sign_signed,
              sign_refused, sign_cancelled, sign_expired
        """
        self.ensure_one()
        if self.state == "canceled":
            return "sign_cancelled"
        return "sign_%s" % (self.state or "draft")

