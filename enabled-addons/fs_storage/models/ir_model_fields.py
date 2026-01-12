# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class IrModelFields(models.Model):
    _inherit = "ir.model.fields"

    storage_id = fields.Many2one(
        "fs.storage",
        help="If specified, all attachments linked to this field will be "
        "stored in the provided storage.",
    )
