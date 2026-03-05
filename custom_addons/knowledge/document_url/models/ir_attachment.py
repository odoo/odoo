# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _compute_mimetype(self, values):
        if values.get("url") and values.get("type", "url") == "url":
            return "application/link"
        return super()._compute_mimetype(values)
