# Copyright 2024 ForgeFlow S.L. (http://www.forgeflow.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sign_oca_send_sign_request_copy = fields.Boolean(
        related="company_id.sign_oca_send_sign_request_copy", readonly=False
    )
