from datetime import datetime, timedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UniversityTimetableSlot(models.Model):
    _inherit = "university.timetable.slot"

    allow_on_holiday = fields.Boolean(
        string="Allow on Holiday",
        default=False,
        help="Permit scheduling this session on a public holiday (requires Administrator privileges and a reason).",
    )
    holiday_override_reason = fields.Char(
        string="Holiday Override Reason",
        help="Justification for holding this class on a public holiday.",
    )
    cancel_reason = fields.Char(
        string="Cancellation Reason",
    )
    on_holiday = fields.Boolean(
        string="Falls on Holiday",
        compute="_compute_on_holiday",
        store=True,
        index=True,
    )
    holiday_name = fields.Char(
        string="Holiday Name",
        compute="_compute_on_holiday",
        store=True,
    )

    @api.depends("start_time", "section_id")
    def _compute_on_holiday(self):
        PubHoliday = self.env["public.holiday"]
        for slot in self:
            if not slot.start_time:
                slot.on_holiday = False
                slot.holiday_name = False
                continue
            slot_date = fields.Datetime.context_timestamp(slot, slot.start_time).date()
            matched_name = False
            if "university.holiday" in self.env:
                univ_h = self.env["university.holiday"].search([
                    ("active", "=", True),
                    "|",
                    "&", ("date_start", "<=", slot_date), ("date_end", ">=", slot_date),
                    "&", ("date_from", "<=", slot_date), ("date_to", ">=", slot_date),
                ])
                for uh in univ_h:
                    if not slot.section_id or (hasattr(uh, "_applies_to_section") and uh._applies_to_section(slot.section_id)):
                        matched_name = uh.name
                        break
            if not matched_name:
                pub_h = PubHoliday.get_holiday_on(slot_date)
                if pub_h:
                    matched_name = pub_h.name
            if matched_name:
                slot.on_holiday = True
                slot.holiday_name = matched_name
            else:
                slot.on_holiday = False
                slot.holiday_name = False

    @api.onchange("start_time", "section_id")
    def _onchange_start_time_holiday_warning(self):
        if self.start_time:
            slot_date = fields.Datetime.context_timestamp(self, self.start_time).date()
            PubHoliday = self.env["public.holiday"]
            holiday = PubHoliday.get_holiday_on(slot_date)
            if not holiday and PubHoliday.is_holiday(slot_date, self.section_id):
                univ_h = self.env["university.holiday"].search([
                    ("active", "=", True),
                    "|",
                    "&", ("date_start", "<=", slot_date), ("date_end", ">=", slot_date),
                    "&", ("date_from", "<=", slot_date), ("date_to", ">=", slot_date),
                ], limit=1) if "university.holiday" in self.env else None
                holiday_name = univ_h.name if univ_h else _("University Holiday")
            elif holiday:
                holiday_name = holiday.name
            else:
                holiday_name = None

            if holiday_name:
                return {
                    "warning": {
                        "title": _("Public Holiday Warning"),
                        "message": _(
                            "Warning: The date %(date)s falls on holiday '%(holiday)s'. "
                            "Classes should not be scheduled on this date unless permitted by university policy."
                        ) % {
                            "date": slot_date,
                            "holiday": holiday_name,
                        },
                    }
                }

    def _get_holiday_conflict(self):
        """Override to detect public holiday and university holiday conflicts."""
        self.ensure_one()
        if self.state == "cancelled" or not self.start_time:
            return False
        if self.env.context.get("skip_holiday_check"):
            return False
        if getattr(self, "allow_on_holiday", False) and self.env["public.holiday"]._is_holiday_admin():
            return False
        slot_date = fields.Datetime.context_timestamp(self, self.start_time).date()
        holiday = self.env["public.holiday"].get_holiday_on(slot_date)
        if holiday:
            return holiday
        return super()._get_holiday_conflict()

    @api.constrains("start_time", "section_id", "allow_on_holiday", "holiday_override_reason", "state")
    def _check_holiday_conflict(self):
        """Constrain sessions on holidays: non-admins are blocked; admins can proceed or override."""
        if self.env.context.get("skip_holiday_check"):
            return
        PubHoliday = self.env["public.holiday"]
        is_admin = PubHoliday._is_holiday_admin()

        for slot in self:
            if slot.state == "cancelled" or not slot.start_time:
                continue
            slot_date = fields.Datetime.context_timestamp(slot, slot.start_time).date()
            holiday = PubHoliday.get_holiday_on(slot_date)
            if not holiday:
                if not PubHoliday.is_holiday(slot_date, slot.section_id):
                    continue
                univ_h = self.env["university.holiday"].search([
                    ("active", "=", True),
                    "|",
                    "&", ("date_start", "<=", slot_date), ("date_end", ">=", slot_date),
                    "&", ("date_from", "<=", slot_date), ("date_to", ">=", slot_date),
                ], limit=1) if "university.holiday" in self.env else None
                holiday_name = univ_h.name if univ_h else _("University Holiday")
            else:
                holiday_name = holiday.name

            if slot.allow_on_holiday:
                if not is_admin:
                    raise ValidationError(
                        _("Only School Administrators can schedule classes on a public holiday.")
                    )
                if not (slot.holiday_override_reason and slot.holiday_override_reason.strip()):
                    raise ValidationError(
                        _("Please provide an override reason for scheduling '%s' on holiday '%s' (%s).")
                        % (slot.name or slot.section_id.name, holiday_name, slot_date)
                    )
            else:
                raise ValidationError(
                    _(
                        "Cannot schedule session '%(session)s' on %(date)s because it falls on public holiday '%(holiday)s'. "
                        "University policy blocks classes on holidays. "
                        "Only School Administrators can override this by ticking 'Allow on Holiday' with an explicit reason."
                    )
                    % {
                        "session": slot.name or (slot.section_id.name if slot.section_id else "Class"),
                        "date": slot_date,
                        "holiday": holiday_name,
                    }
                )

    def action_cancel_for_holiday(self, holiday_name=None):
        """Mark slot cancelled due to holiday conflict."""
        self.ensure_one()
        reason = holiday_name or self.holiday_name or _("Public Holiday")
        self.write({
            "state": "cancelled",
            "cancel_reason": reason,
        })
        return True

    def action_open_reschedule_wizard(self):
        """Open the interactive session reschedule wizard."""
        self.ensure_one()
        return {
            "name": _("Reschedule Session - %s") % (self.name or self.display_name),
            "type": "ir.actions.act_window",
            "res_model": "wizard.reschedule.session",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_slot_id": self.id,
                "default_current_start_time": self.start_time,
                "default_current_end_time": self.end_time,
                "default_current_classroom_id": self.classroom_id.id if self.classroom_id else False,
            },
        }

    @api.model
    def get_schedule(self, start_date_str, end_date_str, filters=None, limit=1000, offset=0):
        res = super().get_schedule(start_date_str, end_date_str, filters=filters, limit=limit, offset=offset)
        if not isinstance(res, dict) or "holidays" not in res:
            return res
        existing_names = {h.get("name") for h in res["holidays"]}
        start_d = fields.Date.to_date(start_date_str)
        end_d = fields.Date.to_date(end_date_str)
        if start_d and end_d:
            pub_holidays = self.env["public.holiday"].sudo().search([
                ("active", "=", True),
                ("date_from", "<=", end_d),
                ("date_to", ">=", start_d),
            ])
            for ph in pub_holidays:
                if ph.name not in existing_names:
                    res["holidays"].append({
                        "id": ph.id,
                        "name": ph.name,
                        "name_km": ph.name_km or "",
                        "date_start": fields.Date.to_string(ph.date_from),
                        "date_end": fields.Date.to_string(ph.date_to),
                        "date_from": fields.Date.to_string(ph.date_from),
                        "date_to": fields.Date.to_string(ph.date_to),
                        "holiday_type": "public",
                        "faculty_name": _("University-Wide"),
                    })
        return res

    @api.model
    def get_holiday_schedule_indicators(self, start_date_str, end_date_str, filters=None, **kwargs):
        """Return dictionary of holiday indicators indexed by exact ISO date string."""
        filters = filters or {}
        start_d = fields.Date.to_date(str(start_date_str).split("T")[0].split(" ")[0]) if start_date_str else False
        end_d = fields.Date.to_date(str(end_date_str).split("T")[0].split(" ")[0]) if end_date_str else False
        holiday_days = {}
        applicable_holidays = []
        if start_d and end_d:
            cur = start_d
            while cur <= end_d:
                name = False
                holiday_id = False
                d_start_str = fields.Date.to_string(cur)
                d_end_str = d_start_str
                holiday_type = "public"
                if "university.holiday" in self.env:
                    univ_h = self.env["university.holiday"].search([
                        ("active", "=", True),
                        "|",
                        "&", ("date_start", "<=", cur), ("date_end", ">=", cur),
                        "&", ("date_from", "<=", cur), ("date_to", ">=", cur),
                    ], limit=1)
                    if univ_h:
                        name = univ_h.name
                        holiday_id = univ_h.id
                        d_start_str = fields.Date.to_string(univ_h.date_from or univ_h.date_start)
                        d_end_str = fields.Date.to_string(univ_h.date_to or univ_h.date_end)
                        holiday_type = getattr(univ_h, "holiday_type", "university")
                if not name:
                    pub_h = self.env["public.holiday"].get_holiday_on(cur)
                    if pub_h:
                        name = pub_h.name
                        holiday_id = pub_h.id
                        d_start_str = fields.Date.to_string(pub_h.date_from)
                        d_end_str = fields.Date.to_string(pub_h.date_to)
                        holiday_type = "public"
                if name:
                    d_str = fields.Date.to_string(cur)
                    holiday_days[d_str] = {
                        "id": holiday_id,
                        "name": name,
                        "date_start": d_start_str,
                        "date_end": d_end_str,
                        "holiday_type": holiday_type,
                    }
                cur += timedelta(days=1)

        # Unique holidays list
        seen_holidays = set()
        for h in holiday_days.values():
            key = (h.get("id"), h.get("name"))
            if key not in seen_holidays:
                seen_holidays.add(key)
                applicable_holidays.append(h)

        # Detect slot conflicts in this date range
        slot_conflicts = {}
        if start_d and end_d:
            domain = [
                ("start_time", ">=", datetime.combine(start_d, datetime.min.time())),
                ("start_time", "<=", datetime.combine(end_d, datetime.max.time())),
            ]
            section_id = filters.get("section_id") or filters.get("section")
            if section_id:
                domain.append(("section_id", "=", int(section_id)))
            teacher_id = filters.get("teacher_id") or filters.get("teacher")
            if teacher_id:
                domain.append(("teacher_id", "=", int(teacher_id)))
            classroom_id = filters.get("classroom_id") or filters.get("classroom")
            if classroom_id:
                domain.append(("classroom_id", "=", int(classroom_id)))

            slots = self.search(domain)
            for slot in slots:
                if not slot.start_time:
                    continue
                slot_date = fields.Datetime.context_timestamp(slot, slot.start_time).date()
                slot_date_str = fields.Date.to_string(slot_date)
                h_info = holiday_days.get(slot_date_str)
                if h_info:
                    h_name = h_info.get("name")
                    h_start = h_info.get("date_start", slot_date_str)
                    h_end = h_info.get("date_end", slot_date_str)
                    h_dates = h_start if h_start == h_end else f"{h_start} to {h_end}"
                    is_cancelled = (slot.state == "cancelled")
                    is_override = bool(getattr(slot, "allow_on_holiday", False) and getattr(slot, "holiday_override_reason", False))
                    is_conflict = not is_override and not is_cancelled
                    slot_conflicts[slot.id] = {
                        "holiday_id": h_info.get("id"),
                        "holiday_name": h_name,
                        "holiday_dates": h_dates,
                        "date_from": h_start,
                        "date_to": h_end,
                        "is_conflict": is_conflict,
                        "is_cancelled": is_cancelled,
                        "is_override": is_override,
                        "allow_on_holiday": getattr(slot, "allow_on_holiday", False),
                        "override_reason": getattr(slot, "holiday_override_reason", "") or "",
                    }

        return {
            "holiday_days": holiday_days,
            "slot_conflicts": slot_conflicts,
            "holidays": applicable_holidays,
        }
