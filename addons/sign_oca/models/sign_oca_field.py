# Copyright 2023 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SignOcaField(models.Model):
    _name = "sign.oca.field"
    _description = "Signature Field Type"

    name = fields.Char(required=True)
    field_type = fields.Selection(
        [("text", "Text"), ("signature", "Signature"), ("check", "Check")],
        required=True,
        default="text",
    )
    default_value = fields.Char()
