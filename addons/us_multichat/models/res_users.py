
from odoo import models


class Users(models.Model):
    _inherit = "res.users"

    def _init_messaging(self):
        values = super()._init_messaging()
        values["us_multichat"] = self.env["mail.channel"].multi_livechat_info()
        return values
