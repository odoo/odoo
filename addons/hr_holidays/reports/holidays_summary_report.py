import calendar
from datetime import timedelta

import babel.dates
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.libs.colors import LEAVE_REPORT_COLORS, get_palette_color
from odoo.tools.misc import format_date, get_lang


def _color_of(record):
    return get_palette_color(record.color, LEAVE_REPORT_COLORS, wrap=True)


class ReportHr_HolidaysReport_Holidayssummary(models.AbstractModel):
    _name = "report.hr_holidays.report_holidayssummary"
    _description = "Holidays Summary Report"

    def _get_header_info(self, start_date, holiday_type):
        st_date = fields.Date.from_string(start_date)
        if holiday_type == "Confirmed":
            holiday_type = self.env._("Confirmed")
        elif holiday_type == "Approved":
            holiday_type = self.env._("Approved")
        else:
            holiday_type = self.env._("Confirmed and Approved")
        return {
            "start_date": format_date(self.env, st_date),
            "end_date": format_date(self.env, st_date + relativedelta(days=59)),
            "holiday_type": holiday_type,
        }

    def _date_is_day_off(self, date):
        return date.weekday() in (
            calendar.SATURDAY,
            calendar.SUNDAY,
        )

    def _get_day(self, start_date):
        res = []
        start_date = fields.Date.from_string(start_date)
        for _x in range(60):
            color = "#ababab" if self._date_is_day_off(start_date) else ""
            res.append(
                {
                    "day_str": babel.dates.get_day_names(
                        "abbreviated", locale=get_lang(self.env).code
                    )[start_date.weekday()],
                    "day": start_date.day,
                    "color": color,
                }
            )
            start_date += relativedelta(days=1)
        return res

    def _get_months(self, start_date):
        res = []
        start_date = fields.Date.from_string(start_date)
        end_date = start_date + relativedelta(days=59)
        while start_date <= end_date:
            last_date = start_date + relativedelta(day=1, months=+1, days=-1)
            last_date = min(last_date, end_date)
            month_days = (last_date - start_date).days + 1
            res.append(
                {
                    "month_name": babel.dates.get_month_names(
                        locale=get_lang(self.env).code
                    )[start_date.month],
                    "days": month_days,
                }
            )
            start_date += relativedelta(day=1, months=+1)
        return res

    def _get_leaves_summary(self, start_date, empid, holiday_type):
        res = []
        count = 0
        start_date = fields.Date.from_string(start_date)
        end_date = start_date + relativedelta(days=59)
        for index in range(60):
            current = start_date + timedelta(index)
            res.append({"day": current.day, "color": ""})
            if self._date_is_day_off(current):
                res[index]["color"] = "#ababab"

        holidays = self._get_leaves(
            start_date, self.env["hr.employee"].browse(empid), holiday_type
        )

        for holiday in holidays:
            date_from = fields.Datetime.from_string(holiday.date_from)
            date_from = fields.Datetime.context_timestamp(holiday, date_from).date()
            date_to = fields.Datetime.from_string(holiday.date_to)
            date_to = fields.Datetime.context_timestamp(holiday, date_to).date()
            for _index in range((date_to - date_from).days + 1):
                if start_date <= date_from <= end_date:
                    res[(date_from - start_date).days]["color"] = _color_of(
                        holiday.holiday_status_id
                    )
                date_from += timedelta(1)
            count += holiday.number_of_days
        employee = self.env["hr.employee"].browse(empid)
        return {"emp": employee.name, "display": res, "sum": count}

    def _get_employees(self, data):
        if "depts" in data:
            return self.env["hr.employee"].search(
                [("department_id", "in", data["depts"])]
            )
        elif "emp" in data:
            return self.env["hr.employee"].browse(data["emp"])
        return self.env["hr.employee"].search(
            [("company_id", "in", self.env.companies.ids)]
        )

    def _get_data_from_report(self, data):
        res = []
        if "depts" in data:
            employees = self._get_employees(data)
            departments = self.env["hr.department"].browse(data["depts"])
            res.extend(
                {
                    "dept": department.name,
                    "data": [
                        self._get_leaves_summary(
                            data["date_from"], emp.id, data["holiday_type"]
                        )
                        for emp in employees.filtered(
                            lambda emp, department=department: (
                                emp.department_id.id == department.id
                            )
                        )
                    ],
                    "color": self._get_day(data["date_from"]),
                }
                for department in departments
            )
        elif "emp" in data:
            res.append(
                {
                    "data": [
                        self._get_leaves_summary(
                            data["date_from"], emp.id, data["holiday_type"]
                        )
                        for emp in self._get_employees(data)
                    ]
                }
            )
        return res

    def _get_leaves(self, date_from, employees, holiday_type, date_to=None):
        state = (
            ["confirm", "validate"]
            if holiday_type == "both"
            else ["confirm"]
            if holiday_type == "Confirmed"
            else ["validate"]
        )

        if not date_to:
            date_to = date_from + relativedelta(days=59)

        return self.env["hr.leave"].search(
            [
                ("employee_id", "in", employees.ids),
                ("state", "in", state),
                ("date_from", "<=", str(date_to)),
                ("date_to", ">=", str(date_from)),
            ]
        )

    def _get_holidays_status(self, data):
        employees = self.env["hr.employee"]
        if {"depts", "emp"} & data.keys():
            employees = self._get_employees(data)

        holidays = self._get_leaves(
            fields.Date.from_string(data["date_from"]), employees, data["holiday_type"]
        )

        return [
            {"color": _color_of(leave_type), "name": leave_type.name}
            for leave_type in holidays.holiday_status_id
        ]

    @api.model
    def _get_report_values(self, docids, data=None):

        holidays_report = self.env["ir.actions.report"]._get_report_from_name(
            "hr_holidays.report_holidayssummary"
        )
        if data and data.get("form"):
            return {
                "doc_ids": docids,
                "doc_model": holidays_report.model,
                "get_header_info": self._get_header_info(
                    data["form"]["date_from"], data["form"]["holiday_type"]
                ),
                "get_day": self._get_day(data["form"]["date_from"]),
                "get_months": self._get_months(data["form"]["date_from"]),
                "get_data_from_report": self._get_data_from_report(data["form"]),
                "get_holidays_status": self._get_holidays_status(data["form"]),
            }

        return {
            "doc_ids": docids,
            "doc_model": holidays_report.model,
        }
