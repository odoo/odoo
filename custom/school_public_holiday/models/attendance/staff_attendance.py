from odoo import api, fields, models


class UniversityStaffAttendance(models.Model):
    _inherit = "university.staff.attendance"

    status = fields.Selection(
        selection_add=[("holiday", "Public Holiday")],
        ondelete={"holiday": "set default"},
    )
    is_holiday_work = fields.Boolean(
        string="Worked on Holiday",
        compute="_compute_holiday_work_payroll",
        store=True,
    )
    holiday_work_pay_multiplier = fields.Float(
        string="Holiday Pay Multiplier",
        compute="_compute_holiday_work_payroll",
        store=True,
        default=1.0,
        help="Pay multiplier applied for working on this public holiday.",
    )
    payable_hours = fields.Float(
        string="Payable Hours",
        compute="_compute_holiday_work_payroll",
        store=True,
        help="Factored hours for payroll calculations (Worked Hours × Pay Multiplier).",
    )

    def _is_non_working_day(self, day):
        """Override school_management hook to check against public holidays and school breaks."""
        if not day:
            return False
        day_date = fields.Date.to_date(day)
        # 1. Canonical check via public.holiday (which checks public holidays and institutional closures)
        if self.env["public.holiday"].is_holiday(day_date):
            return True
        # 2. Check scoped institutional closures (faculty / department / program)
        if "university.holiday" in self.env:
            holidays = self.env["university.holiday"].search([
                ("active", "=", True),
                "|",
                "&", ("date_start", "<=", day_date), ("date_end", ">=", day_date),
                "&", ("date_from", "<=", day_date), ("date_to", ">=", day_date),
            ])
            for h in holidays:
                if h.applies_to == "all":
                    return True
                if h.applies_to == "faculty" and self.faculty_id and (self.faculty_id in h.faculty_ids or self.faculty_id == h.faculty_id):
                    return True
                if h.applies_to == "department" and self.department_id and self.department_id in h.department_ids:
                    return True
        return False

    def _get_day_label(self, day):
        """Override school_management hook to get public holiday name."""
        if not day:
            return False
        day_date = fields.Date.to_date(day)
        pub_h = self.env["public.holiday"].get_holiday_on(day_date)
        if pub_h:
            return pub_h.name
        if "university.holiday" in self.env:
            holidays = self.env["university.holiday"].search([
                ("active", "=", True),
                "|",
                "&", ("date_start", "<=", day_date), ("date_end", ">=", day_date),
                "&", ("date_from", "<=", day_date), ("date_to", ">=", day_date),
            ])
            for h in holidays:
                if h.applies_to == "all":
                    return h.name
                if h.applies_to == "faculty" and self.faculty_id and (self.faculty_id in h.faculty_ids or self.faculty_id == h.faculty_id):
                    return h.name
                if h.applies_to == "department" and self.department_id and self.department_id in h.department_ids:
                    return h.name
        return False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            d = vals.get("date") or fields.Date.context_today(self)
            dummy = self.new({"date": d, "staff_id": vals.get("staff_id")})
            if dummy._is_non_working_day(d):
                if not vals.get("check_in") and (not vals.get("status") or vals.get("status") in ("present", "absent")):
                    vals["status"] = "holiday"
        return super().create(vals_list)

    @api.depends("date", "faculty_id", "department_id")
    def _compute_is_holiday(self):
        super()._compute_is_holiday()
        for rec in self:
            if rec.date and rec._is_non_working_day(rec.date):
                rec.is_holiday = True
                rec.holiday_name = rec._get_day_label(rec.date)
                if rec.status in ("absent", False) and not rec.check_in:
                    rec.status = "holiday"

    @api.depends("is_holiday", "worked_hours", "status", "check_in")
    def _compute_holiday_work_payroll(self):
        for rec in self:
            if rec.is_holiday and (rec.worked_hours > 0 or rec.check_in):
                mult = 2.0
                if "university.holiday" in self.env:
                    holiday = self.env["university.holiday"].search([
                        ("active", "=", True),
                        "|",
                        "&", ("date_start", "<=", rec.date), ("date_end", ">=", rec.date),
                        "&", ("date_from", "<=", rec.date), ("date_to", ">=", rec.date),
                    ], limit=1)
                    if holiday and holiday.work_pay_multiplier:
                        mult = holiday.work_pay_multiplier
                rec.is_holiday_work = True
                rec.holiday_work_pay_multiplier = mult
                rec.payable_hours = round(rec.worked_hours * mult, 2)
            else:
                rec.is_holiday_work = False
                rec.holiday_work_pay_multiplier = 1.0
                rec.payable_hours = round(rec.worked_hours, 2)
