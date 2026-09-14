from __future__ import annotations

from odoo import fields, models


class AiModel(models.Model):
    _inherit = "gateway.ml.model"

    kind = fields.Selection(
        selection_add=[("speech", "Speech")],
        ondelete={"speech": "cascade"},
    )
