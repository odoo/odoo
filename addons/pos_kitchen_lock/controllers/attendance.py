from odoo import http, fields
from odoo.http import request


class PosAttendanceController(http.Controller):

    @http.route("/pos/attendance/employees", type="jsonrpc", auth="user")
    def get_employees(self):
        employees = request.env["hr.employee"].search(
            [("active", "=", True)], order="name"
        )
        result = []
        for emp in employees:
            open_att = request.env["hr.attendance"].search(
                [("employee_id", "=", emp.id), ("check_out", "=", False)], limit=1
            )
            result.append(
                {
                    "id": emp.id,
                    "name": emp.name,
                    "job_title": emp.job_title
                    or (emp.job_id.name if emp.job_id else ""),
                    "department": emp.department_id.name
                    if emp.department_id
                    else "",
                    "is_checked_in": bool(open_att),
                    "image": emp.image_128.decode() if emp.image_128 else False,
                }
            )
        return result

    @http.route("/pos/attendance/action", type="jsonrpc", auth="user")
    def attendance_action(self, employee_id):
        employee = request.env["hr.employee"].browse(int(employee_id))
        if not employee.exists():
            return {"error": "Employee not found"}

        now = fields.Datetime.now()
        open_att = request.env["hr.attendance"].search(
            [("employee_id", "=", employee.id), ("check_out", "=", False)], limit=1
        )

        if open_att:
            open_att.write({"check_out": now})
            action = "check_out"
        else:
            request.env["hr.attendance"].create(
                {"employee_id": employee.id, "check_in": now}
            )
            action = "check_in"

        return {"action": action, "employee_name": employee.name}
