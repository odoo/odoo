from odoo import api, fields, models


class IapAccount(models.Model):
    _name = "iap.account"
    _inherit = ["iap.account", "mixin.mail.thread"]

    # Add tracking to the base fields
    company_ids = fields.Many2many(
        comodel_name="res.company",
        tracking=True,
    )
    warning_threshold = fields.Float(
        string="Email Alert Threshold",
        tracking=True,
    )
    warning_user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Email Alert Recipients",
        tracking=True,
    )

    @api.model
    def _send_success_notification(self, message, title=None):
        self._send_status_notification(message, "success", title=title)

    @api.model
    def _send_error_notification(self, message, title=None):
        self._send_status_notification(message, "danger", title=title)

    @api.model
    def _send_status_notification(self, message, status, title=None):
        params = {
            "message": message,
            "type": status,
        }
        if title is not None:
            params["title"] = title
        self.env.user._bus_send("iap_notification", params)

    @api.model
    def _send_no_credit_notification(self, service_name, title):
        params = {
            "title": title,
            "type": "no_credit",
            "get_credits_url": self.get_credits_url(service_name),
        }
        self.env.user._bus_send("iap_notification", params)
