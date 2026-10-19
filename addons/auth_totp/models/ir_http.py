# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _check_identity(cls, credential):
        if credential and credential.get("type") == "totp":
            credential["token"] = int(re.sub(r"\s", "", credential["token"]))

        return super()._check_identity(credential)
