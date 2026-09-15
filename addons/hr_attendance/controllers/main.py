from datetime import UTC

from requests.exceptions import RequestException

from odoo import _, fields, http
from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain
from odoo.http import request
from odoo.libs.datetime import timezone
from odoo.service.common import exp_version
from odoo.tools import SQL, float_round, py_to_js_locale
from odoo.tools.image import image_data_uri

from ..tools import debug_log as dbg


class HrAttendance(http.Controller):
    # Every kiosk route answers the same way when it cannot act: a mapping
    # carrying a status the caller can branch on. Four shapes were in use --
    # a bare `{}`, a bare `[]`, `{"status": "error"}` and an uncaught
    # `AccessError` reaching the client as an HTTP 500 -- for one situation,
    # "the token does not entitle you to this".
    @staticmethod
    def _refuse(message=None):
        return (
            {"status": "error", "message": message} if message else {"status": "error"}
        )

    @classmethod
    def _employee_of(cls, token, employee_id):
        """The employee the kiosk at `token` may act for, or an empty recordset.

        One check in one place: three routes each re-derived "exists, and
        belongs to this token's company" inline, and the shape of the answer
        when it did not hold differed between them.
        """
        company = cls._get_company(token)
        if not company:
            return request.env["hr.employee"].sudo().browse()
        employee = request.env["hr.employee"].sudo().browse(employee_id).exists()
        return employee if employee.company_id == company else employee.browse()

    @staticmethod
    def _get_company(token):
        """The company whose kiosk key is `token`, or an empty recordset.

        A FALSY token is refused before the search, and that is not defensive
        tidiness. Every kiosk route is `auth="public"` and takes its token from
        the client, so a caller can send `null`, `false` or `""` -- and an Odoo
        domain turns all three into `attendance_kiosk_key IS NULL`. Against a
        company whose key was NULL, `/hr_attendance/attendance_employee_data`
        with `"token": null` returned that company's employee names, avatars
        and hours to an unauthenticated caller, and the sibling routes would
        have checked them in, created employees and assigned badges.

        The key is `required` now and unique, so a NULL should be unreachable.
        This guard is the half that does not depend on that being true of every
        database the code meets: a restore, a migration that added the column
        without the back-fill, or a future field change all reintroduce it, and
        none of them would look like a security change.
        """
        if not token:
            dbg.logic.debug("[kiosk] refusing a falsy token")
            return request.env["res.company"].sudo().browse()
        company = (
            request.env["res.company"]
            .sudo()
            .search([("attendance_kiosk_key", "=", token)])
        )
        dbg.pipeline.debug(
            "[kiosk:%s] token resolves to %s",
            dbg.lazy(lambda: (token or "")[:8]),
            dbg.rec(company),
        )
        return company

    @staticmethod
    def _get_overtime_today(employee):
        today = (
            fields.Datetime.now()
            .replace(tzinfo=UTC)
            .astimezone(timezone(employee._get_schedule_tz()))
            .date()
        )
        # `manual_duration`, not `duration`: it is what `hr.attendance`'s
        # `overtime_hours`, the employee's `total_overtime` and the backend list
        # all sum, so reading the raw `duration` here made the kiosk the one
        # place where a manager's correction to an overtime line was invisible.
        groups = (
            employee.env["hr.attendance.overtime.line"]
            .sudo()
            ._read_group(
                domain=[("employee_id", "=", employee.id), ("date", "=", today)],
                aggregates=["manual_duration:sum"],
            )
        )
        return groups[0][0] or 0

    @staticmethod
    def _get_employee_info_response(employee):
        response = {}
        if employee:
            response = {
                **employee._get_attendance_systray_data(),
                "employee_name": employee.name,
                "employee_avatar": employee.image_256
                and image_data_uri(employee.image_256),
                "total_overtime": float_round(
                    employee.total_overtime, precision_digits=2
                ),
                "kiosk_delay": employee.company_id.attendance_kiosk_delay * 1000,
                "attendance": {
                    "check_in": employee.last_attendance_id.check_in,
                    "check_out": employee.last_attendance_id.check_out,
                },
                "overtime_today": HrAttendance._get_overtime_today(employee),
                "use_pin": employee.company_id.attendance_kiosk_use_pin,
                "display_overtime": employee.company_id.hr_attendance_display_overtime,
                "device_tracking_enabled": employee.company_id.attendance_device_tracking,
            }
        return response

    @staticmethod
    def _get_geoip_response(
        mode, latitude=False, longitude=False, device_tracking_enabled=True
    ):
        response = {"mode": mode}

        if not device_tracking_enabled:
            return response
        # The IP's coordinates stand in for missing GPS ones, so they have to
        # be settled before the coordinates are turned into a place name.
        if latitude is False or latitude is None:
            latitude = request.geoip.location.latitude
        if longitude is False or longitude is None:
            longitude = request.geoip.location.longitude
        try:
            location = request.env["geocoder"]._get_localisation(latitude, longitude)
        except UserError, RequestException:
            dbg.logic.debug(
                "_get_geoip_response: no place name for %s,%s", latitude, longitude
            )
            location = _("Unknown")
        response.update(
            {
                "location": location,
                "latitude": latitude if latitude is not None else False,
                "longitude": longitude if longitude is not None else False,
                "ip_address": request.geoip.ip,
                "browser": request.httprequest.user_agent.browser,
            }
        )

        return response

    @http.route(
        "/hr_attendance/kiosk_mode_menu/<int:company_id>", auth="user", type="http"
    )
    def kiosk_menu_item_action(self, company_id):
        if request.env.user.has_group("hr_attendance.group_hr_attendance_user"):
            if self.has_password():
                request.session.logout(keep_db=True)
            return request.redirect(
                request.env["res.company"].browse(company_id).attendance_kiosk_url
            )
        else:
            return request.prepare_not_found_error()

    @http.route(
        "/hr_attendance/get_employees_without_badge", type="jsonrpc", auth="public"
    )
    def get_employees_without_badge(self, token, name=None, limit=20):
        company = self._get_company(token)
        if not company:
            return self._refuse()
        domain = Domain("barcode", "=", False) & Domain("company_id", "=", company.id)
        if name:
            domain &= Domain("name", "ilike", name)
        try:
            employee_list = request.env["hr.employee"].search_read(
                domain,
                ["id", "name"],
                limit=limit,
            )
        except AccessError:
            # The route is `auth="public"` and the listing is deliberately NOT
            # sudo: only the signed-in setup session may see who has no badge.
            return self._refuse(_("You are not allowed to list employees."))
        return {"status": "success", "employees": employee_list}

    @http.route("/hr_attendance/set_badge", type="jsonrpc", auth="public")
    def set_badge(self, employee_id, badge, token):
        employee = self._employee_of(token, employee_id)
        if not employee:
            return self._refuse()
        if employee.barcode:
            return self._refuse(_("This employee already has a badge."))
        try:
            request.env["hr.employee"].browse(employee.id).barcode = badge
        except AccessError:
            return self._refuse(_("You are not allowed to assign badges."))
        return {"status": "success"}

    @http.route("/hr_attendance/create_employee", type="jsonrpc", auth="public")
    def create_employee(self, name, token):
        company = self._get_company(token)
        if not company:
            return self._refuse()
        try:
            request.env["hr.employee"].create(
                {
                    "name": name,
                    "company_id": company.id,
                }
            )
        except AccessError:
            return self._refuse(_("You are not allowed to create employees."))
        return {"status": "success"}

    @http.route("/hr_attendance/kiosk_keepalive", auth="user", type="jsonrpc")
    def kiosk_keepalive(self):
        request.session.mark_dirty()
        return {}

    @http.route(
        ["/hr_attendance/<token>"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def open_kiosk_mode(self, token, from_trial_mode=False):
        company = self._get_company(token)
        if not company:
            return request.prepare_not_found_error()
        else:
            department_list = [
                {"id": dep["id"], "name": dep["name"], "count": dep["total_employee"]}
                for dep in request.env["hr.department"]
                .with_context(allowed_company_ids=[company.id])
                .sudo()
                .search_read(
                    domain=[("company_id", "=", company.id)],
                    fields=["id", "name", "total_employee"],
                )
            ]
            has_password = self.has_password()
            if not from_trial_mode and has_password:
                request.session.logout(keep_db=True)
            if from_trial_mode or (not has_password and not request.env.user.is_public):
                kiosk_mode = "settings"
            else:
                kiosk_mode = company.attendance_kiosk_mode
            version_info = exp_version()
            return request.render(
                "hr_attendance.public_kiosk_mode",
                {
                    "kiosk_backend_info": {
                        "token": token,
                        "company_id": company.id,
                        "company_name": company.name,
                        "departments": department_list,
                        "kiosk_mode": kiosk_mode,
                        "from_trial_mode": from_trial_mode,
                        "barcode_source": company.attendance_barcode_source,
                        "device_tracking_enabled": company.attendance_device_tracking,
                        "lang": py_to_js_locale(
                            company.partner_id.lang or company.env.lang
                        ),
                        "server_version_info": version_info.get("server_version_info"),
                    },
                },
            )

    @http.route(
        "/hr_attendance/attendance_employee_data", type="jsonrpc", auth="public"
    )
    def employee_attendance_data(self, token, employee_id):
        employee = self._employee_of(token, employee_id)
        return (
            self._get_employee_info_response(employee) if employee else self._refuse()
        )

    @http.route(
        "/hr_attendance/attendance_barcode_scanned", type="jsonrpc", auth="public"
    )
    def change_attendance_by_barcode(self, token, barcode):
        dbg.pipeline.debug("[kiosk] barcode scan")
        company = self._get_company(token)
        if not company:
            return self._refuse()
        employee = (
            request.env["hr.employee"]
            .sudo()
            .search(
                [("barcode", "=", barcode), ("company_id", "=", company.id)],
                limit=1,
            )
        )
        if not employee:
            return self._refuse()
        employee._attendance_action_change(
            self._get_geoip_response(
                "kiosk",
                device_tracking_enabled=company.attendance_device_tracking,
            )
        )
        return self._get_employee_info_response(employee)

    @http.route("/hr_attendance/manual_selection", type="jsonrpc", auth="public")
    def manual_selection(
        self, token, employee_id, pin_code, latitude=False, longitude=False
    ):
        dbg.pipeline.debug(
            "[kiosk] manual selection of employee %s, pin %s",
            employee_id,
            "given" if pin_code else "absent",
        )
        employee = self._employee_of(token, employee_id)
        if not employee:
            return self._refuse()
        company = employee.company_id
        if company.attendance_kiosk_use_pin and not employee._check_attendance_pin(
            pin_code
        ):
            return self._refuse()
        employee._attendance_action_change(
            self._get_geoip_response(
                "kiosk",
                latitude=latitude,
                longitude=longitude,
                device_tracking_enabled=company.attendance_device_tracking,
            )
        )
        return self._get_employee_info_response(employee)

    @http.route("/hr_attendance/employees_infos", type="jsonrpc", auth="public")
    def employees_infos(self, token, limit, offset, domain):
        # The search runs as superuser, so this list is the whole of the access
        # control on it. Anything the allowlist does not positively recognise
        # is refused: skipping what it did not understand let a malformed
        # condition through to `Domain()`, which raised out of the route as a
        # server error rather than as this message.
        for condition in domain:
            if condition in ("&", "|", "!"):
                continue
            if (
                not isinstance(condition, (list, tuple))
                or len(condition) != 3
                or condition[0] not in ("name", "department_id")
                or condition[1] not in ("=", "ilike")
            ):
                raise UserError(
                    _(
                        "Invalid domain, use 'name' and/or 'department_id' fields "
                        "with '=' and/or 'ilike' operators.",
                    )
                )

        company = self._get_company(token)
        if not company:
            return self._refuse()
        domain = Domain(domain) & Domain("company_id", "=", company.id)
        Employee = request.env["hr.employee"].sudo()
        employees = Employee.search_fetch(
            domain,
            ["id", "display_name", "job_id"],
            limit=limit,
            offset=offset,
            order="name, id",
        )
        return {
            "status": "success",
            "records": [
                {
                    "id": employee.id,
                    "display_name": employee.display_name,
                    "job_id": employee.job_id.name,
                    "avatar": image_data_uri(employee.avatar_128),
                    "status": employee.attendance_state,
                    "mode": employee.last_attendance_id.in_mode,
                }
                for employee in employees
            ],
            "length": Employee.search_count(domain),
        }

    @http.route("/hr_attendance/systray_check_in_out", type="jsonrpc", auth="user")
    def systray_attendance(self, latitude=False, longitude=False):
        employee = request.env.user.employee_id
        dbg.pipeline.debug(
            "[systray] check in/out by user %s as %s",
            request.env.user.id,
            dbg.rec(employee),
        )
        geo_ip_response = self._get_geoip_response(
            mode="systray",
            latitude=latitude,
            longitude=longitude,
            device_tracking_enabled=employee.company_id.attendance_device_tracking,
        )
        employee._attendance_action_change(geo_ip_response)
        return self._get_employee_info_response(employee)

    @http.route(
        "/hr_attendance/attendance_user_data",
        type="jsonrpc",
        auth="user",
        readonly=True,
    )
    def user_attendance_data(self):
        return request.env.user.employee_id._get_attendance_systray_data()

    def has_password(self):
        request.env.cr.execute(
            SQL(
                "SELECT password IS NOT NULL FROM res_users WHERE id = %(user_id)s",
                user_id=request.env.user.id,
            )
        )
        row = request.env.cr.fetchone()
        return bool(row and row[0])

    @http.route("/hr_attendance/set_settings", type="jsonrpc", auth="public")
    def set_attendance_settings(self, token, mode):
        company = self._get_company(token)
        if not company:
            return self._refuse()
        modes = dict(
            request.env["res.company"]._fields["attendance_kiosk_mode"].selection
        )
        if mode not in modes:
            return self._refuse(_("Unknown kiosk mode."))
        try:
            request.env["res.company"].browse(company.id).attendance_kiosk_mode = mode
        except AccessError:
            return self._refuse(_("You are not allowed to change the kiosk settings."))
        return {"status": "success"}
