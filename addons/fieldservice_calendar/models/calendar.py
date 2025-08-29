# Copyright (C) 2021 Raphaël Reverdy <raphael.reverdy@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class Meeting(models.Model):
    _inherit = "calendar.event"

    fsm_order_id = fields.One2many(
        string="Order id",
        comodel_name="fsm.order",
        inverse_name="calendar_event_id",
    )

    def _update_fsm_order_date(self):
        self.ensure_one()
        if self._context.get("recurse_order_calendar"):
            # avoid recursion
            return
        to_apply = {}
        to_apply["scheduled_date_start"] = self.start
        to_apply["scheduled_duration"] = self.duration
        self.fsm_order_id.with_context(recurse_order_calendar=True).write(to_apply)

    def _update_fsm_assigned(self):
        # update back fsm_order when an attenndee is member of a team
        self.ensure_one()
        if self._context.get("recurse_order_calendar"):
            # avoid recursion
            return
        person_id = None
        for partner in self.partner_ids:
            if partner.fsm_person:
                person_id = (
                    self.env["fsm.person"]
                    .search([["partner_id", "=", partner.id]], limit=1)
                    .id
                )
                break
        self.fsm_order_id.with_context(recurse_order_calendar=True).write(
            {"person_id": person_id}
        )

    def write(self, values):
        res = super().write(values)
        if self.fsm_order_id:
            if "start" in values or "duration" in values:
                self._update_fsm_order_date()
            if "partner_ids" in values:
                self._update_fsm_assigned()
        return res
