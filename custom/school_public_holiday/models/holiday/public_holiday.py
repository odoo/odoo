import logging
import re
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)


class PublicHoliday(models.Model):
    _name = "public.holiday"
    _description = "Public Holiday"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_from desc, name asc"

    name = fields.Char(string="Holiday Name", required=True, tracking=True, index=True)
    name_km = fields.Char(string="Khmer Name", tracking=True)
    date_from = fields.Date(string="From Date", required=True, tracking=True, index=True)
    date_to = fields.Date(string="To Date", required=True, tracking=True, index=True)

    # Aliases to integrate seamlessly with Excel imports (e.g. date_start / date_end)
    date_start = fields.Date(
        string="Start Date",
        compute="_compute_date_aliases",
        inverse="_inverse_date_start",
        search="_search_date_start",
        help="Alias for From Date for Excel import integration.",
    )
    date_end = fields.Date(
        string="End Date",
        compute="_compute_date_aliases",
        inverse="_inverse_date_end",
        search="_search_date_end",
        help="Alias for To Date for Excel import integration.",
    )

    academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Academic Year",
        index=True,
    )
    semester_id = fields.Many2one(
        "university.semester",
        string="Term",
        compute="_compute_term_and_year",
        store=True,
        readonly=False,
        index=True,
    )
    number_of_days = fields.Integer(
        string="Public Holiday Days",
        compute="_compute_number_of_days",
        store=True,
    )
    status = fields.Selection(
        [
            ("upcoming", "Upcoming"),
            ("ongoing", "Ongoing"),
            ("past", "Past"),
        ],
        string="Status",
        compute="_compute_status",
        store=True,
        index=True,
    )
    affected_sessions = fields.Char(
        string="Affected Sessions Note",
        help="Imported description of affected sessions (e.g. All Sessions).",
    )
    active = fields.Boolean(string="Active", default=True, tracking=True)
    note = fields.Text(string="Note")
    notice_id = fields.Many2one(
        "university.notice.board",
        string="Linked Notice",
        ondelete="set null",
        index=True,
        copy=False,
        readonly=True,
    )
    auto_publish_notice = fields.Boolean(
        string="Auto-publish Notice",
        help="Create or update the linked Notice Board announcement when this holiday is saved.",
    )

    session_count = fields.Integer(
        string="Session Count",
        compute="_compute_session_count",
        search="_search_session_count",
    )

    def _search_session_count(self, operator, value):
        holidays_with_sessions = []
        for h in self.search([]):
            if h.session_count > 0:
                holidays_with_sessions.append(h.id)
        if (operator in (">", "!=") and value == 0) or (operator == ">=" and value == 1):
            return [("id", "in", holidays_with_sessions)]
        return [("id", "not in", holidays_with_sessions)]

    # -------------------------------------------------------------------------
    # MULTI-DAY HOLIDAY NORMALIZATION & CLUSTERING
    # -------------------------------------------------------------------------
    @classmethod
    def _normalize_holiday_base_name(cls, name):
        """Extract canonical base holiday name by stripping day indicators.

        Examples:
        - 'Water Festival (Day 1)' => 'Water Festival'
        - 'Water Festival (Day 2)' => 'Water Festival'
        - 'Khmer New Year Day (Day 1)' => 'Khmer New Year Day'
        - 'Khmer New Year Day 1' => 'Khmer New Year'
        - 'Pchum Ben Festival (Day 3)' => 'Pchum Ben Festival'
        - 'ពិធីបុណ្យចូលឆ្នាំថ្មីប្រពៃណីជាតិ ថ្ងៃទី១' => 'ពិធីបុណ្យចូលឆ្នាំថ្មីប្រពៃណីជាតិ'
        """
        if not name:
            return ""
        s = name.strip()
        digit_pat = r"[0-9០-៩]+"
        s1 = re.sub(r"\s*[\(\[](?:Day|ថ្ងៃទី|Part)\s*" + digit_pat + r"[\)\]]\s*$", "", s, flags=re.IGNORECASE)
        if s1 != s:
            return s1.strip()
        s2 = re.sub(r"[\s\-]+(?:Day|ថ្ងៃទី|Part)\s*" + digit_pat + r"\s*$", "", s, flags=re.IGNORECASE)
        if s2 != s:
            return s2.strip()
        return s

    def _get_base_holiday_name(self):
        self.ensure_one()
        return self._normalize_holiday_base_name(self.name)

    def _get_holiday_cluster(self):
        """Return all public holidays in the database belonging to the same holiday event cluster as self."""
        self.ensure_one()
        base_name = self._get_base_holiday_name().strip().lower()
        if not base_name or not self.date_from:
            return self

        domain = [("active", "in", [True, False])]
        if self.academic_year_id:
            domain.append(("academic_year_id", "=", self.academic_year_id.id))

        candidates = self.search(domain)
        cluster = self.browse()
        for cand in candidates:
            if cand._get_base_holiday_name().strip().lower() == base_name and cand.date_from:
                if abs((cand.date_from - self.date_from).days) <= 7:
                    cluster |= cand
        return cluster if cluster else self

    # -------------------------------------------------------------------------
    # CANONICAL HOOK METHODS
    # -------------------------------------------------------------------------
    @api.model
    def get_holiday_on(self, date):
        """Find an active public holiday affecting classes on the given date."""
        d = fields.Date.to_date(date)
        if not d:
            return self.browse()
        return self.search([
            ("active", "=", True),
            ("date_from", "<=", d),
            ("date_to", ">=", d),
        ], limit=1)

    @api.model
    def is_holiday(self, date, section=None):
        """Single hook to check if a date is a holiday (national public holiday or school-specific closure)."""
        d = fields.Date.to_date(date)
        if not d:
            return False
        if self.get_holiday_on(d):
            return True
        if "university.holiday" in self.env:
            domain = [
                ("active", "=", True),
                "|",
                "&", ("date_start", "<=", d), ("date_end", ">=", d),
                "&", ("date_from", "<=", d), ("date_to", ">=", d),
            ]
            if section:
                holidays = self.env["university.holiday"].search(domain)
                for h in holidays:
                    if hasattr(h, "_applies_to_section"):
                        if h._applies_to_section(section):
                            return True
                    else:
                        return True
            else:
                if self.env["university.holiday"].search_count(domain):
                    return True
        return False

    @api.model
    def _is_holiday_admin(self):
        """Check if current user has administrator privileges for holiday overrides."""
        return (
            self.env.is_system()
            or self.env.user.has_group("school_management.group_school_admin")
        )

    # -------------------------------------------------------------------------
    # COMPUTES & ONCHANGE
    # -------------------------------------------------------------------------
    @api.depends("date_from", "date_to")
    def _compute_date_aliases(self):
        for record in self:
            record.date_start = record.date_from
            record.date_end = record.date_to

    def _inverse_date_start(self):
        for record in self:
            if record.date_start:
                record.date_from = record.date_start

    def _inverse_date_end(self):
        for record in self:
            if record.date_end:
                record.date_to = record.date_end

    def _search_date_start(self, operator, value):
        return [("date_from", operator, value)]

    def _search_date_end(self, operator, value):
        return [("date_to", operator, value)]

    @api.onchange("date_from")
    def _onchange_date_from(self):
        if self.date_from and (not self.date_to or self.date_to < self.date_from):
            self.date_to = self.date_from
        if not self.academic_year_id and self.date_from:
            ay = self.env["university.academic.year"].search([
                ("date_start", "<=", self.date_from),
                ("date_end", ">=", self.date_from),
            ], limit=1)
            if ay:
                self.academic_year_id = ay

    @api.onchange("date_from", "date_to")
    def _onchange_dates_warning(self):
        if self.date_from and self.date_to:
            dt_start = datetime.combine(self.date_from, datetime.min.time())
            dt_end = datetime.combine(self.date_to, datetime.max.time())
            count = self.env["university.timetable.slot"].search_count([
                ("state", "!=", "cancelled"),
                ("start_time", "<=", dt_end),
                ("end_time", ">=", dt_start),
            ])
            if count > 0:
                return {
                    "warning": {
                        "title": _("Timetable Conflict Warning"),
                        "message": _(
                            "There are %d active timetable sessions scheduled within this holiday date range (%s to %s)."
                        ) % (count, self.date_from, self.date_to),
                    }
                }

    @api.depends("date_from", "date_to")
    def _compute_session_count(self):
        Slot = self.env["university.timetable.slot"]
        for holiday in self:
            if not holiday.date_from or not holiday.date_to:
                holiday.session_count = 0
                continue
            dt_start = datetime.combine(holiday.date_from, datetime.min.time())
            dt_end = datetime.combine(holiday.date_to, datetime.max.time())
            holiday.session_count = Slot.search_count([
                ("state", "!=", "cancelled"),
                ("start_time", "<=", dt_end),
                ("end_time", ">=", dt_start),
            ])

    @api.depends("date_from", "date_to")
    def _compute_number_of_days(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                rec.number_of_days = max(1, (rec.date_to - rec.date_from).days + 1)
            elif rec.date_from:
                rec.number_of_days = 1
            else:
                rec.number_of_days = 0

    @api.depends("date_from", "date_to")
    def _compute_status(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.date_from:
                rec.status = "upcoming"
            elif rec.date_to and rec.date_to < today:
                rec.status = "past"
            elif rec.date_from <= today <= (rec.date_to or rec.date_from):
                rec.status = "ongoing"
            else:
                rec.status = "upcoming"

    @api.depends("date_from", "date_to")
    def _compute_term_and_year(self):
        Semester = self.env["university.semester"]
        for rec in self:
            if not rec.date_from:
                rec.semester_id = False
                continue
            sem = Semester.search([
                ("date_start", "<=", rec.date_from),
                ("date_end", ">=", rec.date_from),
            ], limit=1)
            if not sem and rec.date_to:
                sem = Semester.search([
                    ("date_start", "<=", rec.date_to),
                    ("date_end", ">=", rec.date_to),
                ], limit=1)
            rec.semester_id = sem.id if sem else False

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------
    @api.constrains("date_from", "date_to")
    def _check_dates_order(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError(
                    _("Holiday '%s': End date (%s) cannot be earlier than start date (%s).")
                    % (rec.name, rec.date_to, rec.date_from)
                )

    @api.constrains("name", "date_from", "date_to", "active")
    def _check_overlapping_duplicates(self):
        for rec in self:
            if not rec.active or not rec.date_from or not rec.date_to or not rec.name:
                continue
            name_clean = rec.name.strip().lower()
            duplicates = self.search([
                ("id", "!=", rec.id),
                ("active", "=", True),
                ("date_from", "<=", rec.date_to),
                ("date_to", ">=", rec.date_from),
            ])
            for dup in duplicates:
                if dup.name and dup.name.strip().lower() == name_clean:
                    raise ValidationError(
                        _(
                            "Overlapping holiday with name '%(name)s' already exists for dates %(date_from)s to %(date_to)s."
                        )
                        % {
                            "name": rec.name,
                            "date_from": dup.date_from,
                            "date_to": dup.date_to,
                        }
                    )

    # -------------------------------------------------------------------------
    # ORM LIFECYCLE
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("date_from") and vals.get("date_start"):
                vals["date_from"] = vals["date_start"]
            if not vals.get("date_to") and vals.get("date_end"):
                vals["date_to"] = vals["date_end"]
            vals.pop("date_start", None)
            vals.pop("date_end", None)

            if not vals.get("date_from"):
                holiday_name = vals.get("name") or _("Unnamed")
                raise ValidationError(_("Holiday '%s' is missing a From Date.") % holiday_name)

            if not vals.get("date_to"):
                vals["date_to"] = vals["date_from"]

            if not vals.get("academic_year_id") and vals.get("date_from"):
                target_d = fields.Date.to_date(vals["date_from"])
                ay = self.env["university.academic.year"].search([
                    ("date_start", "<=", target_d),
                    ("date_end", ">=", target_d),
                ], limit=1)
                if not ay:
                    if target_d.month >= 9:
                        ay_name = f"{target_d.year}-{target_d.year + 1}"
                        s_date = f"{target_d.year}-09-01"
                        e_date = f"{target_d.year + 1}-06-30"
                    else:
                        ay_name = f"{target_d.year - 1}-{target_d.year}"
                        s_date = f"{target_d.year - 1}-09-01"
                        e_date = f"{target_d.year}-06-30"
                    ay = self.env["university.academic.year"].search([("name", "=", ay_name)], limit=1)
                    if not ay:
                        ay = self.env["university.academic.year"].sudo().create({
                            "name": ay_name,
                            "date_start": s_date,
                            "date_end": e_date,
                        })
                if ay:
                    vals["academic_year_id"] = ay.id

        if self.env.context.get("import_file"):
            created_or_updated = []
            to_create_vals = []
            to_create_indices = []
            for idx, vals in enumerate(vals_list):
                name = (vals.get("name") or "").strip().lower()
                d_from = vals.get("date_from")
                d_to = vals.get("date_to")
                existing = self.search([
                    ("active", "=", True),
                    ("date_from", "<=", d_to),
                    ("date_to", ">=", d_from),
                ]).filtered(lambda h: h.name.strip().lower() == name)
                if existing:
                    existing[:1].write(vals)
                    created_or_updated.append((idx, existing[:1]))
                else:
                    to_create_indices.append(idx)
                    to_create_vals.append(vals)

            new_recs = super().create(to_create_vals) if to_create_vals else self.browse()
            for idx, rec in zip(to_create_indices, new_recs):
                created_or_updated.append((idx, rec))

            created_or_updated.sort(key=lambda x: x[0])
            result_ids = [rec.id for _, rec in created_or_updated]
            holidays = self.browse(result_ids)
        else:
            holidays = super().create(vals_list)
        if len(holidays) <= 20:
            for h in holidays:
                if h.session_count > 0:
                    _logger.warning("Created holiday '%s' affects %d sessions.", h.name, h.session_count)
        return holidays

    def write(self, vals):
        if not vals.get("date_from") and vals.get("date_start"):
            vals["date_from"] = vals["date_start"]
        if not vals.get("date_to") and vals.get("date_end"):
            vals["date_to"] = vals["date_end"]
        vals.pop("date_start", None)
        vals.pop("date_end", None)

        if "date_from" in vals and "date_to" not in vals:
            for rec in self:
                if not rec.date_to or rec.date_to < fields.Date.to_date(vals["date_from"]):
                    vals["date_to"] = vals["date_from"]
        res = super().write(vals)
        if not self.env.context.get("skip_notice_sync"):
            notice_fields_changed = bool(
                {"name", "date_from", "date_to", "academic_year_id", "active"} & set(vals)
            )
            if notice_fields_changed:
                for holiday in self:
                    if holiday.notice_id:
                        cluster = holiday._get_holiday_cluster() | self.search([("notice_id", "=", holiday.notice_id.id)])
                        if "active" in vals and not vals["active"]:
                            remaining_active = cluster.filtered(lambda h: h.id != holiday.id and h.active)
                            if not remaining_active:
                                holiday.notice_id.write({"active": False})
                            else:
                                primary = min(remaining_active, key=lambda h: (h.date_from or fields.Date.today(), h.id))
                                holiday.notice_id.write(primary._prepare_notice_values(cluster_holidays=remaining_active))
                        else:
                            primary = min(cluster, key=lambda h: (h.date_from or fields.Date.today(), h.id))
                            holiday.notice_id.write(primary._prepare_notice_values(cluster_holidays=cluster))
        if len(self) <= 20:
            for h in self:
                if h.session_count > 0:
                    _logger.warning("Holiday '%s' affects %d sessions.", h.name, h.session_count)
        return res

    def unlink(self):
        notices = self.mapped("notice_id")
        for notice in notices:
            remaining_holidays = self.env["public.holiday"].search([
                ("notice_id", "=", notice.id),
                ("id", "not in", self.ids),
            ])
            if remaining_holidays:
                primary = min(remaining_holidays, key=lambda h: (h.date_from or fields.Date.today(), h.id))
                notice.write(primary._prepare_notice_values(cluster_holidays=remaining_holidays))
            else:
                notice.write({"active": False, "holiday_id": False})
        return super().unlink()

    def _next_working_day(self, value):
        """Return the next weekday which is not another active holiday."""
        candidate = fields.Date.to_date(value) + timedelta(days=1)
        while candidate.weekday() >= 5 or self.is_holiday(candidate):
            candidate += timedelta(days=1)
        return candidate

    def _prepare_notice_values(self, cluster_holidays=None):
        self.ensure_one()
        holidays = cluster_holidays or self
        active_holidays = holidays.filtered(lambda h: h.active)
        target = active_holidays if active_holidays else holidays
        primary = min(target, key=lambda h: (h.date_from or fields.Date.today(), h.id))

        all_starts = [h.date_from for h in target if h.date_from]
        all_ends = [h.date_to or h.date_from for h in target if (h.date_to or h.date_from)]
        start_date = min(all_starts) if all_starts else primary.date_from
        end_date = max(all_ends) if all_ends else (primary.date_to or primary.date_from)

        display_name = primary._get_base_holiday_name() if len(holidays) > 1 else primary.name

        start = fields.Date.to_string(start_date)
        end = fields.Date.to_string(end_date)
        next_working_day = fields.Date.to_string(self._next_working_day(end_date))

        if start_date == end_date:
            content = _(
                "<p>Please be informed that the university will be closed on %(date)s in observance of %(name)s.</p>"
                "<p>Classes and regular campus operations will resume on %(next_working_day)s.</p>"
            ) % {
                "date": start,
                "name": display_name,
                "next_working_day": next_working_day,
            }
        else:
            content = _(
                "<p>Please be informed that the university will be closed from %(start)s to %(end)s in observance of %(name)s.</p>"
                "<p>Classes and regular campus operations will resume on %(next_working_day)s.</p>"
            ) % {
                "start": start,
                "end": end,
                "name": display_name,
                "next_working_day": next_working_day,
            }

        vals = {
            "name": display_name,
            # The notice calendar uses this field as its event date.  Using
            # today here makes every holiday appear on the day it was
            # published instead of on the actual holiday date.
            "date": start_date,
            "notice_type": "holiday",
            "target_audience": "all",
            "priority": "medium",
            "academic_year_id": primary.academic_year_id.id or False,
            "content": content,
            "holiday_id": primary.id,
            "active": any(h.active for h in holidays),
        }
        if "expiry_date" in self.env["university.notice.board"]._fields:
            vals["expiry_date"] = end_date
        elif "date_end" in self.env["university.notice.board"]._fields:
            vals["date_end"] = end_date
        return vals

    def _check_publish_access(self):
        user = self.env.user
        if not (
            self.env.is_system()
            or user.has_group("school_management.group_school_admin")
            or user.has_group("school_management.group_school_registrar")
        ):
            raise AccessError(_("Only administrators and registrars can announce holidays on the Notice Board."))

    def action_publish_notice(self):
        self._check_publish_access()
        Notice = self.env["university.notice.board"]
        visited = self.browse()
        last_notice = Notice.browse()

        for holiday in self:
            if holiday in visited:
                continue

            cluster = holiday._get_holiday_cluster() | holiday
            visited |= cluster

            linked_notices = (
                cluster.mapped("notice_id")
                | Notice.search([("holiday_id", "in", cluster.ids)])
            )

            primary = min(cluster, key=lambda h: (h.date_from or fields.Date.today(), h.id))
            vals = primary._prepare_notice_values(cluster_holidays=cluster)

            if linked_notices:
                notice = linked_notices.sorted(lambda n: n.id)[0]
                notice.write(vals)
                extra_notices = linked_notices - notice
                if extra_notices:
                    extra_notices.write({"holiday_id": False, "active": False})
                    extra_notices.unlink()
            else:
                notice = Notice.create(vals)

            cluster.with_context(skip_notice_sync=True).write({"notice_id": notice.id})
            last_notice = notice

        if len(self) == 1 and last_notice:
            return {
                "type": "ir.actions.act_window",
                "name": _("Published Notice"),
                "res_model": "university.notice.board",
                "view_mode": "form",
                "res_id": last_notice.id,
                "target": "current",
            }
        return True

    def action_publish_as_notice(self):
        return self.action_publish_notice()

    def action_open_notice(self):
        self.ensure_one()
        if not self.notice_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": _("Notice: %s") % self.name,
            "res_model": "university.notice.board",
            "view_mode": "form",
            "res_id": self.notice_id.id,
            "target": "current",
        }

    def init(self):
        """Repair dates on notices created before holiday dates were used and consolidate multi-day duplicate notices."""
        super().init()
        self.env.cr.execute("""
            UPDATE university_notice_board AS notice
               SET date = holiday.date_from
              FROM public_holiday AS holiday
             WHERE notice.holiday_id = holiday.id
               AND notice.date IS DISTINCT FROM holiday.date_from
        """)
        self._consolidate_existing_duplicate_notices()

    @api.model
    def _consolidate_existing_duplicate_notices(self):
        """Consolidate existing duplicate notices for multi-day public holidays into 1 notice row."""
        Notice = self.env["university.notice.board"]
        holidays_with_notices = self.search([("notice_id", "!=", False)], order="date_from asc, id asc")
        visited_clusters = set()

        for h in holidays_with_notices:
            b_name = h._get_base_holiday_name().strip().lower()
            year = h.date_from.year if h.date_from else 0
            cluster_key = (b_name, year)
            if cluster_key in visited_clusters:
                continue

            cluster = h._get_holiday_cluster()
            if len(cluster) > 1:
                visited_clusters.add(cluster_key)
                linked_notices = (
                    cluster.mapped("notice_id")
                    | Notice.search([("holiday_id", "in", cluster.ids)])
                )
                if len(linked_notices) > 1:
                    primary_notice = linked_notices.sorted(lambda n: n.id)[0]
                    primary_holiday = min(cluster, key=lambda item: (item.date_from or fields.Date.today(), item.id))
                    vals = primary_holiday._prepare_notice_values(cluster_holidays=cluster)
                    primary_notice.write(vals)

                    extra_notices = linked_notices - primary_notice
                    extra_notices.write({"holiday_id": False, "active": False})
                    extra_notices.unlink()

                    cluster.with_context(skip_notice_sync=True).write({"notice_id": primary_notice.id})

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------
    def action_view_affected_sessions(self):
        self.ensure_one()
        dt_start = datetime.combine(self.date_from or fields.Date.today(), datetime.min.time())
        dt_end = datetime.combine(self.date_to or fields.Date.today(), datetime.max.time())
        slots = self.env["university.timetable.slot"].search([
            ("start_time", "<=", dt_end),
            ("end_time", ">=", dt_start),
        ])
        return {
            "name": _("Affected Sessions: %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "university.timetable.slot",
            "view_mode": "list,form,calendar",
            "domain": [("id", "in", slots.ids)],
            "context": {"default_state": "scheduled"},
        }

    def action_cancel_affected_sessions(self):
        self.ensure_one()
        if not self._is_holiday_admin():
            raise UserError(_("Only administrators can cancel affected sessions."))
        if not self.date_from or not self.date_to:
            return
        dt_start = datetime.combine(self.date_from, datetime.min.time())
        dt_end = datetime.combine(self.date_to, datetime.max.time())
        slots = self.env["university.timetable.slot"].search([
            ("state", "!=", "cancelled"),
            ("start_time", "<=", dt_end),
            ("end_time", ">=", dt_start),
        ])
        count = len(slots)
        if count > 0:
            slots.write({
                "state": "cancelled",
            })
            if hasattr(slots, "cancel_reason"):
                slots.write({"cancel_reason": f"Public Holiday: {self.name}"})
            if hasattr(self, "message_post"):
                self.message_post(body=_(
                    "Cancelled %d timetable session(s) due to holiday '%s' (%s to %s)."
                ) % (count, self.name, self.date_from, self.date_to))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Sessions Cancelled"),
                "message": _("%d timetable sessions have been cancelled.") % count,
                "type": "warning" if count > 0 else "info",
                "sticky": False,
            },
        }


class UniversityAcademicYear(models.Model):
    _inherit = "university.academic.year"

    @api.model
    def name_create(self, name):
        """Allow auto-creating academic year by name during import."""
        name_clean = name.strip()
        existing = self.search([("name", "=ilike", name_clean)], limit=1)
        if existing:
            return existing.id, existing.display_name
        parts = [p.strip() for p in name_clean.replace("/", "-").split("-") if p.strip().isdigit()]
        if len(parts) >= 2:
            s_year = int(parts[0])
            e_year = int(parts[1])
            rec = self.create({
                "name": name_clean,
                "date_start": f"{s_year}-09-01",
                "date_end": f"{e_year}-06-30",
            })
            return rec.id, rec.display_name
        elif len(parts) == 1:
            s_year = int(parts[0])
            rec = self.create({
                "name": name_clean,
                "date_start": f"{s_year}-01-01",
                "date_end": f"{s_year}-12-31",
            })
            return rec.id, rec.display_name
        return super().name_create(name)


class UniversityHoliday(models.Model):
    """Institutional holiday / recess model in school_management.

    Represents school-specific closures (e.g. exam week, semester break, faculty recesses)
    scoped to an academic year or faculty.
    Statutory national public holidays are managed by public.holiday.
    """
    _inherit = "university.holiday"
    _order = "date_from desc, date_start desc, name asc"

    date_from = fields.Date(
        string="From Date",
        index=True,
    )
    date_to = fields.Date(
        string="To Date",
        index=True,
    )
    year = fields.Integer(
        string="Year",
        compute="_compute_year",
        store=True,
        index=True,
    )
    number_of_days = fields.Integer(
        string="Number of Days",
        compute="_compute_number_of_days",
        store=True,
    )
    holiday_type = fields.Selection(
        [
            ("public", "Public Holiday"),
            ("school_break", "School Break"),
            ("exam_break", "Exam Break"),
        ],
        string="Holiday Type",
        default="public",
        required=True,
        index=True,
    )
    applies_to = fields.Selection(
        [
            ("all", "All (University-Wide)"),
            ("faculty", "Selected Faculties"),
            ("department", "Selected Departments"),
            ("program", "Selected Programs"),
        ],
        string="Applies To",
        default="all",
        required=True,
    )
    faculty_ids = fields.Many2many(
        "university.faculty",
        "university_holiday_faculty_rel",
        "holiday_id",
        "faculty_id",
        string="Faculties",
    )
    department_ids = fields.Many2many(
        "university.department",
        "university_holiday_dept_rel",
        "holiday_id",
        "department_id",
        string="Departments",
    )
    program_ids = fields.Many2many(
        "university.program",
        "university_holiday_program_rel",
        "holiday_id",
        "program_id",
        string="Programs",
    )
    work_pay_multiplier = fields.Float(
        string="Work Pay Multiplier",
        default=2.0,
        help="Pay rate for staff who work on this holiday (Labour Law Art. 164: double pay).",
    )
    note = fields.Text(string="Note")
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    import_batch_id = fields.Many2one(
        "school.holiday.import.log",
        string="Import Batch",
        ondelete="set null",
        index=True,
    )
    conflict_count = fields.Integer(
        string="Class Conflicts",
        compute="_compute_conflict_count",
        search="_search_conflict_count",
    )

    @api.model
    def is_holiday(self, day, section=None, company=None):
        return self.env["public.holiday"].is_holiday(day, section=section)

    @api.model
    def get_holiday_dates(self, date_from, date_to, section=None, company=None):
        d_start = fields.Date.to_date(date_from)
        d_end = fields.Date.to_date(date_to)
        if not d_start or not d_end or d_start > d_end:
            return set()
        matching_days = set()
        cur = d_start
        while cur <= d_end:
            if self.is_holiday(cur, section=section):
                matching_days.add(cur)
            cur += timedelta(days=1)
        return matching_days

    def _search_conflict_count(self, operator, value):
        holidays_with_conflicts = []
        for h in self.search([]):
            if h.conflict_count > 0:
                holidays_with_conflicts.append(h.id)
        if (operator in (">", "!=") and value == 0) or (operator == ">=" and value == 1):
            return [("id", "in", holidays_with_conflicts)]
        return [("id", "not in", holidays_with_conflicts)]

    @api.depends("date_from", "date_start")
    def _compute_year(self):
        for rec in self:
            d = rec.date_from or rec.date_start
            rec.year = d.year if d else 0

    @api.depends("date_from", "date_to", "date_start", "date_end")
    def _compute_number_of_days(self):
        for rec in self:
            d_from = rec.date_from or rec.date_start
            d_to = rec.date_to or rec.date_end
            if d_from and d_to:
                rec.number_of_days = max(0, (d_to - d_from).days + 1)
            else:
                rec.number_of_days = 0

    @api.onchange("date_from")
    def _onchange_date_from(self):
        if self.date_from and (not self.date_to or self.date_to < self.date_from):
            self.date_to = self.date_from

    @api.depends("date_from", "date_to", "applies_to", "faculty_ids", "department_ids", "program_ids")
    def _compute_conflict_count(self):
        Slot = self.env["university.timetable.slot"]
        for holiday in self:
            d_from = holiday.date_from or holiday.date_start
            d_to = holiday.date_to or holiday.date_end
            if not d_from or not d_to:
                holiday.conflict_count = 0
                continue
            dt_start = datetime.combine(d_from, datetime.min.time())
            dt_end = datetime.combine(d_to, datetime.max.time())
            slots = Slot.search([
                ("state", "!=", "cancelled"),
                ("start_time", "<=", dt_end),
                ("end_time", ">=", dt_start),
            ])
            conflicting = slots.filtered(lambda s: holiday._applies_to_section(s.section_id))
            holiday.conflict_count = len(conflicting)

    @api.constrains("date_from", "date_to", "date_start", "date_end")
    def _check_date_order(self):
        for rec in self:
            d_from = rec.date_from or rec.date_start
            d_to = rec.date_to or rec.date_end
            if d_from and d_to and d_to < d_from:
                raise ValidationError(
                    _("Holiday '%s': End date (%s) cannot be before start date (%s).")
                    % (rec.name, d_to, d_from)
                )

    @api.constrains(
        "date_from",
        "date_to",
        "date_start",
        "date_end",
        "applies_to",
        "faculty_ids",
        "department_ids",
        "program_ids",
        "active",
        "company_id",
    )
    def _check_scope_overlap(self):
        for rec in self:
            if not rec.active:
                continue
            d_from = rec.date_from or rec.date_start
            d_to = rec.date_to or rec.date_end
            if not d_from or not d_to:
                continue
            candidates = self.search([
                ("id", "!=", rec.id),
                ("active", "=", True),
                ("company_id", "=", rec.company_id.id),
                ("date_start", "<=", d_to),
                ("date_end", ">=", d_from),
            ])
            for other in candidates:
                if rec._scopes_overlap(other):
                    o_from = other.date_from or other.date_start
                    o_to = other.date_to or other.date_end
                    raise ValidationError(
                        _(
                            "Holiday conflict: '%(new_name)s' (%(new_from)s to %(new_to)s) "
                            "overlaps with existing holiday '%(other_name)s' (%(other_from)s to %(other_to)s) "
                            "within the same scope."
                        )
                        % {
                            "new_name": rec.name,
                            "new_from": d_from,
                            "new_to": d_to,
                            "other_name": other.name,
                            "other_from": o_from,
                            "other_to": o_to,
                        }
                    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            d_from = vals.get("date_from") or vals.get("date_start")
            d_to = vals.get("date_to") or vals.get("date_end") or d_from
            if d_from:
                vals["date_start"] = d_from
                vals["date_from"] = d_from
            if d_to:
                vals["date_end"] = d_to
                vals["date_to"] = d_to

            if not vals.get("academic_year_id") and d_from:
                target_d = fields.Date.to_date(d_from)
                ay = self.env["university.academic.year"].search([
                    ("date_start", "<=", target_d),
                    ("date_end", ">=", target_d),
                ], limit=1)
                if not ay:
                    ay = self.env["university.academic.year"].search([], order="date_start desc", limit=1)
                if ay:
                    vals["academic_year_id"] = ay.id

        return super().create(vals_list)

    def write(self, vals):
        if "date_from" in vals and "date_start" not in vals:
            vals["date_start"] = vals["date_from"]
        elif "date_start" in vals and "date_from" not in vals:
            vals["date_from"] = vals["date_start"]

        if "date_to" in vals and "date_end" not in vals:
            vals["date_end"] = vals["date_to"]
        elif "date_end" in vals and "date_to" not in vals:
            vals["date_to"] = vals["date_end"]

        return super().write(vals)

    def init(self):
        super().init()
        self.env.cr.execute("""
            UPDATE university_holiday
            SET date_from = date_start
            WHERE date_from IS NULL AND date_start IS NOT NULL;
            UPDATE university_holiday
            SET date_to = date_end
            WHERE date_to IS NULL AND date_end IS NOT NULL;
        """)

    def _scopes_overlap(self, other):
        self.ensure_one()
        if self.applies_to == "all" or other.applies_to == "all":
            return True

        s_fac = set(self.faculty_ids.ids)
        if self.faculty_id:
            s_fac.add(self.faculty_id.id)
        o_fac = set(other.faculty_ids.ids)
        if other.faculty_id:
            o_fac.add(other.faculty_id.id)

        s_dept = set(self.department_ids.ids)
        o_dept = set(other.department_ids.ids)

        s_prog = set(self.program_ids.ids)
        o_prog = set(other.program_ids.ids)

        if self.applies_to == "faculty" and other.applies_to == "faculty":
            return bool(s_fac & o_fac)
        if self.applies_to == "department" and other.applies_to == "department":
            return bool(s_dept & o_dept)
        if self.applies_to == "program" and other.applies_to == "program":
            return bool(s_prog & o_prog)

        if self.applies_to == "faculty" and other.applies_to == "department":
            o_dept_facs = {d.faculty_id.id for d in other.department_ids if d.faculty_id}
            return bool(s_fac & o_dept_facs)
        if self.applies_to == "department" and other.applies_to == "faculty":
            s_dept_facs = {d.faculty_id.id for d in self.department_ids if d.faculty_id}
            return bool(s_dept_facs & o_fac)

        if self.applies_to == "faculty" and other.applies_to == "program":
            o_prog_facs = {
                (p.faculty_id.id or (p.department_id and p.department_id.faculty_id.id))
                for p in other.program_ids
            }
            return bool(s_fac & o_prog_facs)
        if self.applies_to == "program" and other.applies_to == "faculty":
            s_prog_facs = {
                (p.faculty_id.id or (p.department_id and p.department_id.faculty_id.id))
                for p in self.program_ids
            }
            return bool(s_prog_facs & o_fac)

        if self.applies_to == "department" and other.applies_to == "program":
            o_prog_depts = {p.department_id.id for p in other.program_ids if p.department_id}
            return bool(s_dept & o_prog_depts)
        if self.applies_to == "program" and other.applies_to == "department":
            s_prog_depts = {p.department_id.id for p in self.program_ids if p.department_id}
            return bool(s_prog_depts & o_dept)

        return False

    def _applies_to_section(self, section):
        self.ensure_one()
        if self.applies_to == "all":
            return True
        if not section:
            return True

        if self.applies_to == "faculty":
            sec_faculty = (
                (section.department_id and section.department_id.faculty_id)
                or (section.program_id and section.program_id.faculty_id)
                or (section.program_id and section.program_id.department_id and section.program_id.department_id.faculty_id)
            )
            valid_facs = self.faculty_ids
            if self.faculty_id:
                valid_facs |= self.faculty_id
            return bool(sec_faculty and sec_faculty in valid_facs)

        elif self.applies_to == "department":
            sec_dept = section.department_id or (section.program_id and section.program_id.department_id)
            return bool(sec_dept and sec_dept in self.department_ids)

        elif self.applies_to == "program":
            return bool(section.program_id and section.program_id in self.program_ids)

        return True

    def action_view_conflicts(self):
        self.ensure_one()
        d_from = self.date_from or self.date_start
        d_to = self.date_to or self.date_end
        dt_start = datetime.combine(d_from, datetime.min.time())
        dt_end = datetime.combine(d_to, datetime.max.time())
        slots = self.env["university.timetable.slot"].search([
            ("state", "!=", "cancelled"),
            ("start_time", "<=", dt_end),
            ("end_time", ">=", dt_start),
        ])
        conflicting_slots = slots.filtered(lambda s: self._applies_to_section(s.section_id))
        return {
            "name": _("Class Conflicts for %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "university.timetable.slot",
            "view_mode": "list,form,calendar",
            "domain": [("id", "in", slots.ids)],
            "context": {
                "search_default_group_by_section": 1,
                "default_holiday_id": self.id,
            },
        }

    @api.constrains("date_start", "date_end", "academic_year_id")
    def _check_dates_within_year(self):
        for holiday in self:
            if holiday.holiday_type == "public":
                continue
            year = holiday.academic_year_id
            if not year:
                continue
            d_start = holiday.date_from or holiday.date_start
            d_end = holiday.date_to or holiday.date_end
            if not d_start or not d_end:
                continue
            if d_start < year.date_start or d_end > year.date_end:
                raise ValidationError(
                    _("Holiday dates must fall within the selected academic year.")
                )
