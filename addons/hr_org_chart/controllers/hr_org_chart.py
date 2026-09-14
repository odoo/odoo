from odoo import http
from odoo.http import request
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrOrgChartController(http.Controller):
    _managers_level = 5

    def _get_employee(self, employee_id, **kw):
        employee_id = int(employee_id) if employee_id else False

        context = kw.get("context", request.env.context)
        if "allowed_company_ids" in context:
            cids = context["allowed_company_ids"]
        else:
            cids = [request.env.company.id]

        Employee = request.env["hr.employee"].with_context(allowed_company_ids=cids)
        employee = Employee.browse(employee_id)
        _debug.logic("org_chart_employee", requested=employee_id, companies=len(cids))
        return employee if employee.has_access("read") else Employee.browse()

    def _prepare_employee_data(self, employee):
        job = employee.sudo().job_id
        return {
            "id": employee.id,
            "name": employee.name,
            "link": "/mail/view?model=%s&res_id=%s"
            % (
                "hr.employee",
                employee.id,
            ),
            "job_id": job.id,
            "job_name": job.name or "",
            "direct_sub_count": len(employee.child_ids - employee),
            "indirect_sub_count": employee.child_all_count,
        }

    @http.route("/hr/get_redirect_model", type="jsonrpc", auth="user")
    def get_redirect_model(self):
        return "hr.employee"

    @http.route("/hr/get_org_chart", type="jsonrpc", auth="user")
    def get_org_chart(self, employee_id, new_parent_id=None, **kw):
        employee = self._get_employee(employee_id, **kw)
        new_parent = self._get_employee(new_parent_id, **kw).sudo()
        if not employee:
            return {
                "managers": [],
                "children": [],
            }

        ancestors, current = request.env["hr.employee"].sudo(), employee.sudo()
        current_parent = new_parent if new_parent_id is not None else current.parent_id
        max_level = (kw.get("context")["max_level"] or self._managers_level) + 1
        while (
            current_parent
            and current != current_parent
            and employee.sudo() != current_parent
            and len(ancestors) < max_level
        ):
            current = current_parent
            current_parent = (
                current.parent_id
                if current != employee or not new_parent
                else new_parent
            )
            if current_parent in ancestors:
                break
            ancestors += current

        values = {
            "self": self._prepare_employee_data(employee),
            "managers": [
                self._prepare_employee_data(ancestor)
                for idx, ancestor in enumerate(ancestors)
                if idx < max_level - 1
            ],
            "managers_more": len(ancestors) > self._managers_level,
            "children": [
                self._prepare_employee_data(child)
                for child in employee.child_ids
                if child != employee
            ],
        }
        _debug.pipeline(
            "org_chart",
            employee=employee,
            ancestors=ancestors,
            children=len(values["children"]),
            max_level=max_level,
        )
        values["managers"].reverse()
        return values

    @http.route("/hr/get_subordinates", type="jsonrpc", auth="user")
    def get_subordinates(self, employee_id, subordinates_type=None, **kw):
        """
        Get employee subordinates.
        Possible values for 'subordinates_type':
            - 'indirect'
            - 'direct'
            - None (default): all subordinates
        """
        employee = self._get_employee(employee_id, **kw)
        if not employee:
            return {}

        if subordinates_type == "direct":
            res = (employee.child_ids - employee).ids
        elif subordinates_type == "indirect":
            res = (employee.subordinate_ids - employee.child_ids.employee_id).ids
        else:
            res = employee.subordinate_ids.ids

        _debug.logic(
            "subordinates",
            employee=employee,
            kind=subordinates_type or "all",
            count=len(res),
        )
        return res
