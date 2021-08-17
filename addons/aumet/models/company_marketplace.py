import logging

from odoo.exceptions import ValidationError
from odoo import fields, models
from ..marketplace_apis.profile import ProfileAPI

_logger = logging.getLogger(__name__)


class MarketplaceUser(models.Model):
    _inherit = "res.users"
    marketplace_id = fields.Char(string="Marketplace ID")
    marketplace_email = fields.Char(string="Marketplace email")
    marketplace_name = fields.Char(string="Marketplace name")
    marketplace_password = fields.Char(string="Marketplace Password", store=False)
    marketplace_token = fields.Char(string="Token")
    marketplace_pharmacy_id = fields.Char(string="Marketplace Pharmacy ID")

    def write(self, vals):
        if "marketplace_password" not in vals:
            raise ValidationError("Password can't be empty")

        login_resp = ProfileAPI.login(vals.get("marketplace_email", self.marketplace_email), vals["marketplace_password"])

        profile_data = ProfileAPI.get_profile_info(login_resp["data"]["accessToken"])

        vals["marketplace_id"] = login_resp["data"]["id"]
        vals["marketplace_token"] = login_resp["data"]["accessToken"]
        vals["marketplace_email"] = login_resp["data"]["email"]
        vals["marketplace_name"] = login_resp["data"]["fullName"]
        vals["marketplace_pharmacy_id"] = list(profile_data["data"]["entityList"].keys())[0]

        return super(MarketplaceUser, self).write(vals)
