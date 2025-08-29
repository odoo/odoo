# Copyright (C) 2019, Patrick Wilson
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FSMLocation(models.Model):
    _inherit = "fsm.location"

    opportunity_count = fields.Integer(
        compute="_compute_opportunity_count", string="# Opportunities"
    )

    def _compute_opportunity_count(self):
        for fsm_location in self:
            fsm_location.opportunity_count = self.env["crm.lead"].search_count(
                [("fsm_location_id", "=", fsm_location.id)]
            )
