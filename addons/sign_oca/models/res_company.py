# Copyright 2024 ForgeFlow S.L. (http://www.forgeflow.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    sign_oca_send_sign_request_copy = fields.Boolean(
        string="Send signers a copy of the final signed document",
        help="Once all signers have signed the request, a copy of "
        "the final document will be sent to each of them.",
    )
