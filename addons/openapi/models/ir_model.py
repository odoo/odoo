# Copyright 2018 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import fields, models


class IrModel(models.Model):
    _inherit = "ir.model"

    api_access_ids = fields.One2many("openapi.access", "model_id", "Access via API")
    api_accesses_count = fields.Integer(
        compute="_compute_related_accesses_count",
        string="Related openapi accesses count",
        store=False,
    )

    def _compute_related_accesses_count(self):
        for record in self:
            record.api_accesses_count = len(record.api_access_ids)
