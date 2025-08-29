# Copyright (C) 2019, Patrick Wilson
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class Lead(models.Model):
    _inherit = "crm.lead"

    fsm_order_ids = fields.One2many(
        "fsm.order", "opportunity_id", string="Service Orders"
    )
    fsm_location_id = fields.Many2one("fsm.location", string="FSM Location")
    fsm_order_count = fields.Integer(
        compute="_compute_fsm_order_count", string="# FSM Orders"
    )

    def _compute_fsm_order_count(self):
        for rec in self:
            rec.fsm_order_count = len(rec.fsm_order_ids)
