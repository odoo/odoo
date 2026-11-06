from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WizardRescheduleSession(models.TransientModel):
    _name = "wizard.reschedule.session"
    _description = "Reschedule Conflicting Session"

    slot_id = fields.Many2one(
        "university.timetable.slot",
        string="Session",
        required=True,
    )
    session_name = fields.Char(related="slot_id.name", readonly=True)
    section_id = fields.Many2one(related="slot_id.section_id", readonly=True)
    teacher_id = fields.Many2one(related="slot_id.teacher_id", readonly=True)
    current_start_time = fields.Datetime(related="slot_id.start_time", readonly=True)
    current_end_time = fields.Datetime(related="slot_id.end_time", readonly=True)
    current_classroom_id = fields.Many2one(related="slot_id.classroom_id", readonly=True)
    new_start_time = fields.Datetime(string="New Start Time", required=True)
    new_end_time = fields.Datetime(string="New End Time", required=True)
    new_classroom_id = fields.Many2one("university.classroom", string="New Classroom")
    reschedule_reason = fields.Char(
        string="Reason",
        default="Rescheduled due to university holiday",
        required=True,
    )

    @api.onchange("new_start_time", "current_start_time", "current_end_time")
    def _onchange_new_start_time(self):
        if self.new_start_time and self.current_start_time and self.current_end_time:
            duration = self.current_end_time - self.current_start_time
            self.new_end_time = self.new_start_time + duration

    def action_reschedule(self):
        self.ensure_one()
        slot = self.slot_id
        if self.new_end_time <= self.new_start_time:
            raise ValidationError(_("End time must be after start time."))

        # 1. Holiday Check
        new_date = fields.Datetime.context_timestamp(slot, self.new_start_time).date()
        Holiday = self.env["public.holiday"]
        if Holiday.is_holiday(new_date, section=slot.section_id):
            holiday_name = slot.holiday_name or _("University Holiday")
            raise ValidationError(
                _("The selected new date (%s) is a university holiday. Please select a non-holiday date.") % new_date
            )

        # 2. Teacher Availability Check
        overlap_domain = [
            ("id", "!=", slot.id),
            ("state", "!=", "cancelled"),
            ("start_time", "<", self.new_end_time),
            ("end_time", ">", self.new_start_time),
        ]
        Slot = self.env["university.timetable.slot"]
        if slot.teacher_id:
            teacher_clashes = Slot.sudo().search_count(overlap_domain + [("teacher_id", "=", slot.teacher_id.id)])
            if teacher_clashes:
                raise ValidationError(
                    _("Teacher '%s' is already scheduled for another class during this time.")
                    % slot.teacher_id.name
                )

        # 3. Classroom Availability Check
        target_room = self.new_classroom_id or slot.classroom_id
        if target_room:
            if target_room.status in ("maintenance", "inactive"):
                raise ValidationError(
                    _("Classroom '%s' is under maintenance or inactive.") % target_room.name
                )
            room_clashes = Slot.sudo().search_count(overlap_domain + [("classroom_id", "=", target_room.id)])
            if room_clashes:
                raise ValidationError(
                    _("Classroom '%s' is already occupied during this time.") % target_room.name
                )

        # 4. Perform Reschedule
        slot.action_reschedule_session(
            new_start_time=self.new_start_time,
            new_end_time=self.new_end_time,
            new_classroom_id=target_room.id if target_room else None,
        )
        if self.reschedule_reason:
            slot.notes = f"{slot.notes or ''}\nRescheduled: {self.reschedule_reason}".strip()

        return {"type": "ir.actions.act_window_close"}
