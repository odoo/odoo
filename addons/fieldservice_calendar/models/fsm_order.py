# Copyright (C) 2021 Raphaël Reverdy <raphael.reverdy@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    calendar_event_id = fields.Many2one(
        "calendar.event",
        string="Meeting",
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._create_calendar_event()
        return res

    def _create_calendar_event(self):
        """Create entry in calendar of the team."""
        for order in self._should_have_calendar_event():
            order.calendar_event_id = (
                self.env["calendar.event"]
                .with_context(no_mail_to_attendees=True)
                .create(order._prepare_calendar_event())
            )

    def _should_have_calendar_event(self):
        return self.filtered("team_id.calendar_user_id").filtered(
            "scheduled_date_start"
        )

    def _prepare_calendar_event(self):
        model_id = self.env.ref("fieldservice.model_fsm_order").id
        vals = {
            "name": self.name,
            "description": self.description,
            "start": self.scheduled_date_start,
            "stop": self.scheduled_date_end,
            "allday": False,
            "res_model_id": model_id,  # link back with "Document" button
            "res_id": self.id,  # link back with "Document" button
            "location": self._serialize_location(),
            "user_id": self.team_id.calendar_user_id.id,
        }
        partners = self.team_id.calendar_user_id.partner_id | self.person_id.partner_id
        vals["partner_ids"] = [(6, False, partners.ids)]
        # we let calendar_user has a partner_ids in order
        # to have the meeting in the team's calendar
        return vals

    def write(self, vals):
        old_persons = {}
        for rec in self:
            old_persons[rec.id] = rec.person_id
        res = super().write(vals)
        to_update = self.create_or_delete_calendar()
        with_calendar = to_update.filtered("calendar_event_id")
        if "scheduled_date_start" in vals or "scheduled_date_end" in vals:
            with_calendar.update_calendar_date(vals)
        if "location_id" in vals:
            with_calendar.update_calendar_location()
        if "person_id" in vals:
            with_calendar.update_calendar_person(old_persons)
        return res

    def unlink(self):
        self._rm_calendar_event()
        return super().unlink()

    def create_or_delete_calendar(self):
        to_update = self._should_have_calendar_event()
        to_rm = self - to_update
        to_create = to_update.filtered(lambda x: x.calendar_event_id.id is False)
        to_create._create_calendar_event()
        to_rm._rm_calendar_event()
        return to_update

    def _rm_calendar_event(self):
        # it can be archived instead if desired
        self.calendar_event_id.unlink()

    def update_calendar_date(self, vals):
        if self._context.get("recurse_order_calendar"):
            # avoid recursion
            return
        to_apply = {}
        to_apply["start"] = self.scheduled_date_start
        to_apply["stop"] = self.scheduled_date_end
        # always write start and stop in order to calc duration
        self.mapped("calendar_event_id").with_context(
            recurse_order_calendar=True
        ).write(to_apply)

    def update_calendar_location(self):
        for rec in self:
            rec.calendar_event_id.location = rec._serialize_location()

    def _serialize_location(self):
        partner_id = self.location_id.partner_id
        return f"{partner_id.name} {partner_id._display_address()}"

    def update_calendar_person(self, old_persons):
        if self._context.get("recurse_order_calendar"):
            # avoid recursion
            return
        for rec in self:
            with_ctx = rec.calendar_event_id.with_context(recurse_order_calendar=True)
            if old_persons.get(rec.id):
                # remove buddy
                with_ctx.partner_ids = [(3, old_persons[rec.id].partner_id.id, False)]
            if rec.person_id:
                # add the new one
                with_ctx.partner_ids = [(4, rec.person_id.partner_id.id, False)]
