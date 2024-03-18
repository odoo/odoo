# -*- coding: utf-8 -*-

import enum
import json

from odoo import http, SUPERUSER_ID
from odoo.http import request, Response
from datetime import datetime, timedelta


class Status(enum.Enum):
    DONE = "done"
    ERROR = "error"

    def __str__(self):
        return self.value


class CamsAttendance(http.Controller):
    @http.route(
        "/cams/biometric-api3.0/",
        methods=["POST"],
        type="http",
        csrf=False,
        auth="public",
    )
    def generate_attendance(self, **params):
        database_name = params.get("db")
        if res := self._validate_database_name(database_name):
            return res
        machine_id = params.get("stgid")
        if res := self._validate_machine_id(machine_id):
            return res
        direction_param = params.get("direction")
        direction = self._validate_and_get_direction(direction_param)
        if direction and isinstance(direction, Response):
            return direction
        data = self._validate_and_parse_data()
        if data and isinstance(data, Response):
            return data
        punch_log = self._process_punch_log(data)
        (
            employee,
            punch_state,
            attendance_time_with_gmt,
            authentication_token,
            error_response,
        ) = (
            punch_log["employee"],
            punch_log["punch_state"],
            punch_log["attendance_time_with_gmt"],
            punch_log["authentication_token"],
            punch_log["error_response"],
        )
        if error_response:
            return error_response
        split_attendance_time = self._split_attendance_time(attendance_time_with_gmt)
        att_time_obj_gmt = self._process_time_data(split_attendance_time)
        if att_time_obj_gmt and isinstance(att_time_obj_gmt, Response):
            return att_time_obj_gmt
        service_tag = self._validate_and_retrieve_service_tag_id(
            machine_id, authentication_token
        )
        if service_tag and isinstance(service_tag, Response):
            return service_tag
        if res := self._has_duplicate_punch(employee.id, att_time_obj_gmt, punch_state):
            return res
        handle_direction = getattr(self, f"handle_direction_{direction}")
        punch = self._get_punch(
            employee.id, split_attendance_time, punch_state, att_time_obj_gmt
        )

        return handle_direction(
            employee.id,
            punch,
            split_attendance_time,
            machine_id,
            att_time_obj_gmt,
        )

    @staticmethod
    def _create_response(status, http_status, message=None):
        response_dict = {
            "status": status,
            "message": message
        }

        return (
            Response(f'{{"status": "{response_dict["status"]}", "message": "{response_dict["message"]}"}}', status=http_status)
            if message
            else Response(f'{{"status": "{response_dict["status"]}"}}', status=http_status)
        )

    def _database_exists(self, database_name):
        query = "SELECT 0 FROM pg_database where datname = '%s'" % database_name
        request.env.cr.execute(query)
        return request.env.cr.fetchone()

    def _validate_database_name(self, database_name):
        if not database_name:
            return None
        if not self._database_exists(database_name):
            return self._create_response(
                status=Status.ERROR,
                http_status=400,
                message="The provided database does not exist",
            )
        if request.session.db != database_name:
            request.session.db = database_name
            return self._create_response(
                status=Status.DONE,
                http_status=403,
                message="Database changed from %s to %s"
                % (request.session.db, database_name),
            )
        return None

    def _validate_machine_id(self, machine_id):
        if machine_id is None or len(machine_id) == 0:
            return self._create_response(
                status=Status.ERROR,
                http_status=400,
                message="Invalid stgid value. Must be a non-empty value",
            )
        return None

    def _validate_and_get_direction(self, direction_param):
        if not direction_param:
            default_direction = "2"
            # Check in the settings
            direction = (
                request.env["ir.config_parameter"]
                .sudo()
                .get_param("odoo-biometric-attendance.entry_strategy")
                or default_direction
            )
            return direction
        if not direction_param.isdigit():
            return self._create_response(
                status=Status.ERROR,
                http_status=400,
                message="Direction must be a number.",
            )
        if not 1 <= int(direction_param) <= 3:
            return self._create_response(
                status=Status.ERROR,
                http_status=400,
                message="Invalid direction value " "(must be between 1 and 3)",
            )
        return direction_param

    def _validate_and_parse_data(self):
        try:
            return json.loads(request.httprequest.data)
        except json.JSONDecodeError:
            return self._create_response(
                status=Status.ERROR,
                http_status=400,
                message="Invalid format of the raw data",
            )

    def _process_punch_log(self, data):
        response = {
            "employee": None,
            "punch_state": None,
            "attendance_time_with_gmt": None,
            "authentication_token": None,
            "error_response": None,
        }

        try:
            punch_log = data["RealTime"]["PunchLog"]
            biometric_user_id = punch_log["UserId"]
            request.env.uid = SUPERUSER_ID
            employee = (
                request.env["hr.employee"]
                .sudo()
                .search([("biometric_user_id", "=", biometric_user_id)], limit=1)
            )

            if not employee:
                response["error_response"] = self._create_response(
                    status=Status.DONE,
                    http_status=200,
                    message="Employee not found",
                )
                return response

            response["employee"] = employee
            response["punch_state"] = (
                "check_out"
                if punch_log["Type"] in ("BreakOut", "CheckOut")
                else "check_in"
            )
            response["attendance_time_with_gmt"] = punch_log["LogTime"]
            response["authentication_token"] = data["RealTime"]["AuthToken"]

            return response

        except KeyError:
            response["error_response"] = self._create_response(
                status=Status.ERROR,
                http_status=400,
                message="Expected JSON key not found in the raw data",
            )
            return response

    @staticmethod
    def _parse_gmt_offset(gmt_offset):
        sign = -1 if gmt_offset.startswith("+") else 1
        hours = int(gmt_offset[1:3]) * sign
        minutes = int(gmt_offset[3:5]) * sign
        return hours, minutes

    @staticmethod
    def _get_gmt_delta(attendance_time):
        gmt_offset = attendance_time[1]
        hours, minutes = CamsAttendance._parse_gmt_offset(gmt_offset)
        return timedelta(hours=hours, minutes=minutes)

    def _split_attendance_time(self, attendance_time):
        return attendance_time.split(" GMT ")

    def _process_time_data(self, attendance_time):
        try:
            gmt_time = self._get_gmt_delta(attendance_time)
            att_time_obj = datetime.strptime(
                attendance_time[0].rstrip(), "%Y-%m-%d %H:%M:%S"
            )
            return att_time_obj 
            #return att_time_obj + gmt_time
        except Exception:
            return self._create_response(
                status=Status.ERROR,
                http_status=400,
                message="Invalid time format",
            )

    def _validate_and_retrieve_service_tag_id(self, machine_id, authentication_token):
        service_tag = (
            request.env["device.service.tag"]
            .sudo()
            .search([("service_tag_id", "=", machine_id)], limit=1)
        )
        if not service_tag:
            return self._create_response(
                status=Status.ERROR,
                http_status=403,
                message="The given service tag ID does not exist",
            )
        if service_tag[0].authentication_token != authentication_token:
            return self._create_response(
                status=Status.ERROR,
                http_status=403,
                message="Invalid authentication token for the given service tag ID",
            )
        return service_tag

    def _has_duplicate_punch(self, employee_id, att_time_obj_gmt, punch_state):
        search_domain = [
            ("employee_id", "=", employee_id),
            "|",
            ("check_in", "=", att_time_obj_gmt),
            ("check_out", "=", att_time_obj_gmt),
        ]
        is_duplicate = (
            request.env["hr.attendance"].sudo().search_count(search_domain) > 0
        )
        if is_duplicate:
            return self._create_response(
                status=Status.DONE,
                http_status=200,
                message="Duplicate punch",
            )

    @staticmethod
    def _get_day_gmt(att_time_obj, attendance_time, start=True):
        """
        Get the start or end of the day in GMT.
        :param att_time_obj: The attendance time object.
        :param attendance_time: The attendance time string with GMT offset.
        :param start: Boolean indicating whether to get the start or end of the day.
        :return: A datetime object representing the start or end of the day in GMT.
        """
        day_str = str(att_time_obj.date()) + (" 00:00:00" if start else " 23:59:59")
        day_time = datetime.strptime(day_str, "%Y-%m-%d %H:%M:%S")
        return day_time + CamsAttendance._get_gmt_delta(attendance_time)

    def _get_punch(self, employee_id, attendance_time, punch_state, att_time_obj):
        start_day = self._get_day_gmt(att_time_obj, attendance_time)
        end_day = self._get_day_gmt(att_time_obj, attendance_time, start=False)
        att_time_obj_gmt = att_time_obj + self._get_gmt_delta(attendance_time)

        attendances = (
            request.env["hr.attendance"]
            .sudo()
            .search(
                [
                    ("employee_id", "=", employee_id),
                    "|",
                    "&",
                    ("check_in", ">=", start_day),
                    ("check_in", "<=", end_day),
                    "&",
                    ("check_out", ">=", start_day),
                    ("check_out", "<=", end_day),
                ]
            )
        )
        
        punch_list = {att_time_obj_gmt: punch_state}
        for att in attendances:
            if att.check_in:
                punch_list[att.check_in] = "check_in"
            if att.check_out:
                punch_list[att.check_out] = "check_out"

        attendances.unlink()
        return punch_list

    def handle_direction_1(
        self,
        employee_id,
        punch,
        attendance_time,
        machine_id,
        att_time_obj_gmt,
    ):
        (start_day, end_day) = (
            self._get_day_gmt(att_time_obj_gmt, attendance_time),
            self._get_day_gmt(att_time_obj_gmt, attendance_time, start=False),
        )

        for date in sorted(punch.keys()):
            attendance = (
                request.env["hr.attendance"]
                .sudo()
                .search(
                    [
                        ("employee_id", "=", employee_id),
                        ("check_in", ">=", start_day),
                        ("check_in", "<=", end_day),
                    ],
                    order="id desc",
                    limit=1,
                )
            )

            if not attendance:
                request.env["hr.attendance"].create(
                    {
                        "employee_id": employee_id,
                        "check_in": date,
                        "biometric_device_id": machine_id,
                    }
                )
            elif attendance.check_in:
                attendance.check_out = date

        return self._create_response(Status.DONE, 200)

    def handle_direction_2(
        self,
        employee_id,
        punch,
        attendance_time,
        machine_id,
        att_time_obj_gmt,
    ):
        (start_day, end_day) = (
            self._get_day_gmt(att_time_obj_gmt, attendance_time),
            self._get_day_gmt(att_time_obj_gmt, attendance_time, start=False),
        )

        for date in sorted(punch.keys()):
            if punch[date] == "check_in":
                request.env["hr.attendance"].create(
                    {
                        "employee_id": employee_id,
                        "check_in": date,
                        "biometric_device_id": machine_id,
                    }
                )
            elif punch[date] == "check_out":
                attendance = (
                    request.env["hr.attendance"]
                    .sudo()
                    .search(
                        [
                            ("employee_id", "=", employee_id),
                            ("check_in", ">=", start_day),
                            ("check_in", "<=", end_day),
                        ],
                        order="id desc",
                        limit=1,
                    )
                )

                if attendance and attendance.check_in and not attendance.check_out:
                    attendance.check_out = date
                else:
                    request.env["hr.attendance"].create(
                        {
                            "employee_id": employee_id,
                            "check_out": date,
                            "biometric_device_id": machine_id,
                        }
                    )
        return self._create_response(Status.DONE, 200)

    def handle_direction_3(
        self,
        employee_id,
        punch,
        attendance_time,
        machine_id,
        att_time_obj_gmt,
    ):
        (start_day, end_day) = (
            self._get_day_gmt(att_time_obj_gmt, attendance_time),
            self._get_day_gmt(att_time_obj_gmt, attendance_time, start=False),
        )

        for date in sorted(punch.keys()):
            attendance = (
                request.env["hr.attendance"]
                .sudo()
                .search(
                    [
                        ("employee_id", "=", employee_id),
                        ("check_in", ">=", start_day),
                        ("check_in", "<=", end_day),
                    ],
                    order="id desc",
                    limit=1,
                )
            )

            if not attendance or (attendance.check_in and attendance.check_out):
                request.env["hr.attendance"].create(
                    {
                        "employee_id": employee_id,
                        "check_in": date,
                        "biometric_device_id": machine_id,
                    }
                )
            elif attendance.check_in and not attendance.check_out:
                attendance.check_out = date

        return self._create_response(Status.DONE, 200)
