import os

model_file = "custom/school_management/models/timetable.py"
with open(model_file, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add View selection extensions at the beginning/imports if not present
if "class IrUiView(models.Model):" not in code:
    view_extensions = '''

class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    type = fields.Selection(selection_add=[("gantt", "Gantt")])


class IrActionsActWindowView(models.Model):
    _inherit = "ir.actions.act_window.view"

    view_mode = fields.Selection(selection_add=[("gantt", "Gantt")])


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    teacher_id = fields.Many2one("university.teacher", string="Teacher", index=True)
    role = fields.Char(string="Role", compute="_compute_role", store=True, readonly=False)
    weekly_capacity_hours = fields.Float(string="Weekly Capacity Hours", default=40.0)

    @api.depends("teacher_id", "teacher_id.title", "teacher_id.position", "resource_type")
    def _compute_role(self):
        for res in self:
            if res.teacher_id:
                title = res.teacher_id.title or ""
                position = res.teacher_id.position or ""
                if position:
                    role_str = position.replace("_", " ").title()
                elif title:
                    role_str = title.upper() if title in ["dr", "prof"] else title.title()
                else:
                    role_str = "Instructor"
                res.role = role_str
            else:
                res.role = "Resource"


class UniversityTeacher(models.Model):
    _inherit = "university.teacher"

    resource_id = fields.Many2one("resource.resource", string="Planning Resource", copy=False, index=True)

    def _get_or_create_resource(self):
        self.ensure_one()
        if self.resource_id:
            return self.resource_id
        Resource = self.env["resource.resource"].sudo()
        existing = Resource.search([("teacher_id", "=", self.id)], limit=1)
        if not existing:
            existing = Resource.create({
                "name": self.name,
                "resource_type": "user",
                "user_id": self.user_id.id if self.user_id else False,
                "teacher_id": self.id,
                "weekly_capacity_hours": 35.0,
            })
        self.resource_id = existing
        return existing
'''
    # Append after models imports
    code = code.replace("from odoo.osv import expression", "from odoo.osv import expression" + view_extensions, 1)

# 2. Add resource_id, start_datetime, end_datetime, allocated_hours, color, role, state into UniversityTimetableSlot
fields_to_add = '''
    resource_id = fields.Many2one(
        "resource.resource",
        string="Resource",
        compute="_compute_resource_id",
        inverse="_inverse_resource_id",
        store=True,
        index=True,
        ondelete="set null",
        help="Assigned resource (teacher/instructor). Empty represents an Open Shift.",
    )
    start_datetime = fields.Datetime(
        string="Start Datetime",
        compute="_compute_start_datetime",
        inverse="_inverse_start_datetime",
        store=True,
        index=True,
        readonly=False,
    )
    end_datetime = fields.Datetime(
        string="End Datetime",
        compute="_compute_end_datetime",
        inverse="_inverse_end_datetime",
        store=True,
        index=True,
        readonly=False,
    )
    allocated_hours = fields.Float(
        string="Allocated Hours",
        compute="_compute_allocated_hours",
        store=True,
        readonly=False,
        help="Duration of the shift/session in hours.",
    )
    color = fields.Integer(
        string="Color Index",
        compute="_compute_color",
        store=True,
        readonly=False,
        default=0,
        help="Pastel color index for Gantt pills.",
    )
    role = fields.Char(
        string="Role",
        compute="_compute_role",
        store=True,
        readonly=False,
    )
'''

if "resource_id = fields.Many2one(" not in code:
    code = code.replace("location = fields.Char(string=\"Location\")", "location = fields.Char(string=\"Location\")\n" + fields_to_add, 1)

# 3. Add compute methods for the new fields if not present
compute_methods = '''
    @api.depends("teacher_id")
    def _compute_resource_id(self):
        for slot in self:
            if slot.teacher_id:
                slot.resource_id = slot.teacher_id._get_or_create_resource().id
            elif not slot.resource_id:
                slot.resource_id = False

    def _inverse_resource_id(self):
        for slot in self:
            if slot.resource_id and slot.resource_id.teacher_id:
                slot.teacher_id = slot.resource_id.teacher_id.id
            elif not slot.resource_id:
                slot.teacher_id = False

    @api.depends("start_time")
    def _compute_start_datetime(self):
        for slot in self:
            slot.start_datetime = slot.start_time

    def _inverse_start_datetime(self):
        for slot in self:
            if slot.start_datetime:
                slot.start_time = slot.start_datetime

    @api.depends("end_time")
    def _compute_end_datetime(self):
        for slot in self:
            slot.end_datetime = slot.end_time

    def _inverse_end_datetime(self):
        for slot in self:
            if slot.end_datetime:
                slot.end_time = slot.end_datetime

    @api.depends("start_time", "end_time", "start_datetime", "end_datetime")
    def _compute_allocated_hours(self):
        for slot in self:
            st = slot.start_datetime or slot.start_time
            et = slot.end_datetime or slot.end_time
            if st and et:
                delta = et - st
                slot.allocated_hours = max(0.0, round(delta.total_seconds() / 3600.0, 2))
            else:
                slot.allocated_hours = 0.0

    @api.depends("subject_id", "section_id", "session_type")
    def _compute_color(self):
        for slot in self:
            if slot.subject_id:
                slot.color = (slot.subject_id.id * 3 + 1) % 12
            elif slot.section_id:
                slot.color = (slot.section_id.id * 2) % 12
            else:
                slot.color = (slot.id or 1) % 12

    @api.depends("teacher_id", "teacher_id.title", "teacher_id.position", "subject_id")
    def _compute_role(self):
        for slot in self:
            if slot.teacher_id and slot.teacher_id.position:
                slot.role = slot.teacher_id.position.replace("_", " ").title()
            elif slot.teacher_id and slot.teacher_id.title:
                slot.role = slot.teacher_id.title.upper()
            elif slot.subject_id:
                slot.role = slot.subject_id.code or slot.subject_id.name
            else:
                slot.role = "Instructor"
'''

if "def _compute_resource_id(self):" not in code:
    # Insert right before _compute_schedule_slot_display
    target = "    @api.depends(\"start_time\", \"end_time\", \"timeslot_id\")\n    def _compute_schedule_slot_display(self):"
    code = code.replace(target, compute_methods + "\n" + target, 1)

# 4. Add get_gantt_data and actions for weekly planning
gantt_api_methods = '''
    @api.model
    def get_gantt_data(self, date_start, date_stop, domain=None):
        """API for Odoo Schedule by Resource weekly Gantt matching target UI."""
        user = self.env.user
        tz_name = user.tz or "UTC"
        user_tz = pytz.timezone(tz_name)
        today_date = fields.Date.context_today(self)

        search_domain = [
            ("state", "!=", "cancelled"),
            ("start_time", ">=", f"{date_start} 00:00:00"),
            ("start_time", "<=", f"{date_stop} 23:59:59"),
        ]
        if domain:
            search_domain = expression.AND([search_domain, domain])

        slots = self.search(search_domain, order="start_time asc, id asc")

        # Sync resources for active teachers so each teacher appears in Gantt
        Teacher = self.env["university.teacher"].sudo()
        teachers = Teacher.search([("active", "=", True)])
        for t in teachers:
            t._get_or_create_resource()

        Resource = self.env["resource.resource"].sudo()
        all_resources = Resource.search([
            "|", ("teacher_id", "!=", False), ("id", "in", slots.mapped("resource_id").ids)
        ], order="name asc")

        open_shifts_list = []
        slot_dicts = []
        resource_hours_map = {r.id: 0.0 for r in all_resources}

        for slot in slots:
            st = slot.start_datetime or slot.start_time
            et = slot.end_datetime or slot.end_time
            if not st or not et:
                continue

            st_local = pytz.utc.localize(st).astimezone(user_tz)
            et_local = pytz.utc.localize(et).astimezone(user_tz)

            time_range_str = f"{st_local.strftime('%I:%M %p').lstrip('0')} - {et_local.strftime('%I:%M %p').lstrip('0')}"
            title = slot.subject_id.name or slot.name or "Session"
            pill_text = f"{time_range_str} {title}"

            hours = slot.allocated_hours or round((et - st).total_seconds() / 3600.0, 1)

            slot_data = {
                "id": slot.id,
                "name": title,
                "display_name": slot.display_name,
                "resource_id": slot.resource_id.id if slot.resource_id else False,
                "resource_name": slot.resource_id.name if slot.resource_id else "Open Shift",
                "start_datetime": fields.Datetime.to_string(st),
                "end_datetime": fields.Datetime.to_string(et),
                "start_date": st_local.strftime("%Y-%m-%d"),
                "end_date": et_local.strftime("%Y-%m-%d"),
                "start_time_str": st_local.strftime("%I:%M %p").lstrip("0"),
                "end_time_str": et_local.strftime("%I:%M %p").lstrip("0"),
                "time_range_str": time_range_str,
                "pill_text": pill_text,
                "allocated_hours": hours,
                "color": slot.color or 0,
                "state": slot.state or "draft",
                "is_published": (slot.generation_state == "published" or slot.state == "published"),
                "has_conflict": bool(slot.has_conflict),
                "is_holiday": bool(slot.is_holiday),
                "room_name": slot.classroom_id.name or slot.location or "",
                "section_name": slot.section_id.name or "",
                "subject_code": slot.subject_id.code or "",
            }

            slot_dicts.append(slot_data)

            if not slot.resource_id:
                open_shifts_list.append(slot_data)
            else:
                resource_hours_map[slot.resource_id.id] = resource_hours_map.get(slot.resource_id.id, 0.0) + hours

        resource_dicts = []
        for r in all_resources:
            allocated = round(resource_hours_map.get(r.id, 0.0), 1)
            capacity = round(r.weekly_capacity_hours or 35.0, 1)
            diff = capacity - allocated

            # Hours label logic matching screenshot:
            # If within capacity, shows allocated e.g. "8h", "33h"
            # If overloaded (allocated > capacity), shows negative diff e.g. "-21h"
            if diff < 0:
                hours_label = f"-{int(abs(diff))}h"
                is_overloaded = True
            elif allocated > 0:
                hours_label = f"{int(allocated)}h"
                is_overloaded = False
            else:
                hours_label = ""
                is_overloaded = False

            progress_pct = min(100.0, round((allocated / max(capacity, 1.0)) * 100.0, 1)) if allocated else 0.0

            teacher = r.teacher_id
            avatar_url = f"/web/image/university.teacher/{teacher.id}/avatar_128" if teacher and teacher.avatar_128 else ""

            resource_dicts.append({
                "id": r.id,
                "name": r.name,
                "role": r.role or (f"({teacher.position.title()})" if teacher and teacher.position else ""),
                "avatar_url": avatar_url,
                "allocated_hours": allocated,
                "capacity_hours": capacity,
                "hours_label": hours_label,
                "is_overloaded": is_overloaded,
                "progress_percentage": progress_pct,
            })

        # Count of shifts to schedule (open shifts + draft shifts)
        to_schedule_count = len([s for s in slot_dicts if not s["resource_id"] or not s["is_published"]])

        # Open Shifts row total hours
        open_hours = round(sum(s["allocated_hours"] for s in open_shifts_list), 1)
        open_hours_label = f"{int(open_hours)}h" if open_hours else ""

        return {
            "today": today_date,
            "open_shifts": {
                "total_hours": open_hours,
                "hours_label": open_hours_label,
                "slots": open_shifts_list,
            },
            "resources": resource_dicts,
            "slots": slot_dicts,
            "to_schedule_count": to_schedule_count,
        }

    @api.model
    def action_publish_week_shifts(self, date_start, date_stop):
        """Publish all draft slots in the specified date range."""
        slots = self.search([
            ("start_time", ">=", f"{date_start} 00:00:00"),
            ("start_time", "<=", f"{date_stop} 23:59:59"),
            ("state", "!=", "cancelled"),
        ])
        draft_slots = slots.filtered(lambda s: s.generation_state == "draft" or s.state == "draft")
        count = len(draft_slots)
        if count:
            draft_slots.write({"generation_state": "published", "state": "published"})
        return {"published_count": count}

    @api.model
    def action_copy_previous_week_shifts(self, date_start):
        """Duplicate previous week's shifts into current week as draft."""
        curr_start = fields.Date.from_string(date_start)
        prev_start = curr_start - timedelta(days=7)
        prev_end = prev_start + timedelta(days=6)

        prev_slots = self.search([
            ("start_time", ">=", f"{prev_start} 00:00:00"),
            ("start_time", "<=", f"{prev_end} 23:59:59"),
            ("state", "!=", "cancelled"),
        ])
        copied_count = 0
        for slot in prev_slots:
            new_st = slot.start_time + timedelta(days=7)
            new_et = slot.end_time + timedelta(days=7)
            self.create({
                "section_id": slot.section_id.id,
                "subject_id": slot.subject_id.id,
                "teacher_id": slot.teacher_id.id if slot.teacher_id else False,
                "classroom_id": slot.classroom_id.id if slot.classroom_id else False,
                "resource_id": slot.resource_id.id if slot.resource_id else False,
                "start_time": new_st,
                "end_time": new_et,
                "session_type": slot.session_type,
                "generation_state": "draft",
                "state": "draft",
            })
            copied_count += 1
        return {"copied_count": copied_count}
'''

if "def get_gantt_data(" not in code:
    code = code + "\n" + gantt_api_methods

with open(model_file, "w", encoding="utf-8") as f:
    f.write(code)
print("Updated timetable.py with Gantt model and view extensions successfully")
