# -*- coding: utf-8 -*-

from odoo import http, SUPERUSER_ID
from odoo.http import request, Response
from datetime import datetime, timedelta
import json


class CamsAttendance(http.Controller):
    @http.route('/cams/biometric-api3.0/', method=["POST"], csrf=False, auth='public', type='http')
    def generate_attendance(self, **params):

        machine_id = params.get('stgid')
        param_direction = params.get('direction')
        db_name = params.get('db')
		

        if db_name is not None:
            if not is_db_exist(db_name):
                return Response('{"status":"error","message": "Invalid db"}', status=400)
            else:
                if request.session.db != db_name:
                    request.session.db = db_name
                    return Response('{"status":"done","message":"Database changed to new DB"}', status=403)

        if machine_id is None or len(machine_id) == 0:
            return Response('{"status":"error","message":"stgid is empty"}', status=400)

        if param_direction is not None:
            if int(param_direction) > 3 or int(param_direction) < 1:
                return Response('{"status":"error","message": "Given direction is invalid"  }', status=400)
            direction = param_direction
        else:
            params = request.env['ir.config_parameter'].sudo()
            direction = params.get_param('cams-attendance.entry_strategy') or '2'
        if not direction:
            direction = '2'

        try:
            data = json.loads(request.httprequest.data)
            json_object = json.dumps(data)
            real_time = json.loads(json_object)
        except ValueError:
            return Response('{"status":"error","message": "Invalid format of raw data"  }', status=400)

        punch_state = 'check_in'

        try:
            employee_ref = real_time['RealTime']['PunchLog']['UserId']
            request.env.uid = SUPERUSER_ID
            employee = request.env['hr.employee'].sudo().search([('employee_ref', '=', employee_ref)])
            if not employee:
                return Response('{"status": "done", "message": "Invalid employee Id" }', status=200)

            attendance_type = real_time['RealTime']['PunchLog']['Type']
            attendance_time_with_gmt = real_time['RealTime']['PunchLog']['LogTime']
            auth_token = real_time['RealTime']['AuthToken']

            if attendance_type == 'BreakOut' or attendance_type == 'CheckOut':
                punch_state = 'check_out'

        except:
            return Response('{"status":"error","message": "Expected json key is missing"  }', status=400)

        attendance_time = attendance_time_with_gmt.split(" GMT ")
        gmt_time = get_gmt_delta(attendance_time)
        att_time_obj = datetime.strptime(attendance_time[0].rstrip(), "%Y-%m-%d %H:%M:%S")
        att_time_obj_gmt = att_time_obj + gmt_time

        service_tag_id = request.env['device.service.tag'].sudo().search([('service_tag_id', '=', machine_id)])
        if service_tag_id:
            stg_auth_token = service_tag_id[0].auth_token
            if stg_auth_token != auth_token:
                return Response('{"status":"error","message": "Given auth_token is invalid"  }', status=403)
        else:
            return Response('{"status":"error","message": "Given stgid is not exist"  }', status=403)

        check_dup_in = request.env['hr.attendance'].sudo().search(
            [('employee_id', '=', employee.id), ('check_in', '=', att_time_obj_gmt)], limit=1)

        check_dup_out = request.env['hr.attendance'].sudo().search(
            [('employee_id', '=', employee.id), ('check_out', '=', att_time_obj_gmt)], limit=1)

        if check_dup_in or check_dup_out:
            return Response('{"status": "done", "message": "duplicate punch" }', status=200)

        handle_direction = getattr(self, 'handle_direction_' + direction)
        get_punch = self.get_db_punch(employee.id, attendance_time, punch_state, att_time_obj)

        return handle_direction(employee.id, attendance_time, machine_id, get_punch, att_time_obj)

    @staticmethod
    def handle_direction_1(employee_id, attendance_time, machine_id, get_punch, att_time_obj):
        start_day = start_day_gmt(att_time_obj, attendance_time)
        end_day = end_day_gmt(att_time_obj, attendance_time)

        for date in sorted(get_punch.keys()):
            attendance = request.env['hr.attendance'].sudo().search(
                [('employee_id', '=', employee_id),
                 ('check_in', '>=', start_day),
                 ('check_in', '<=', end_day)
                 ], order='id desc',
                limit=1)
            if not attendance:
                vals = {'employee_id': employee_id, 'check_in': date, 'machine_id': machine_id}
                request.env['hr.attendance'].create(vals)
            elif attendance.check_in:
                attendance.check_out = date
        return Response('{"status": "done" }', status=200)

    @staticmethod
    def handle_direction_2(employee_id, attendance_time, machine_id, get_punch, att_time_obj):
        start_day = start_day_gmt(att_time_obj, attendance_time)
        end_day = end_day_gmt(att_time_obj, attendance_time)

        for date in sorted(get_punch.keys()):
            if get_punch[date] == "check_in":
                request.env['hr.attendance']
                vals = {'employee_id': employee_id, 'check_in': date, 'machine_id': machine_id}
                request.env['hr.attendance'].create(vals)

            if get_punch[date] == "check_out":
                attendance = request.env['hr.attendance'].sudo().search(
                    [('employee_id', '=', employee_id),
                     ('check_in', '>=', start_day),
                     ('check_in', '<=', end_day)
                     ], order='id desc',
                    limit=1)  # create_date

                if attendance.check_in and not attendance.check_out:
                    attendance.check_out = date

                else:
                    vals = {'employee_id': employee_id, 'check_out': date, 'machine_id': machine_id}
                    request.env['hr.attendance'].create(vals)
        return Response('{"status": "done" }', status=200)

    @staticmethod
    def handle_direction_3(employee_id, attendance_time, machine_id, get_punch, att_time_obj):
        start_day = start_day_gmt(att_time_obj, attendance_time)
        end_day = end_day_gmt(att_time_obj, attendance_time)

        for date in sorted(get_punch.keys()):
            attendance = request.env['hr.attendance'].sudo().search(
                [('employee_id', '=', employee_id),
                 ('check_in', '>=', start_day),
                 ('check_in', '<=', end_day)
                 ], order='id desc',
                limit=1)
            if (attendance.check_in and attendance.check_out) or not attendance:
                vals = {'employee_id': employee_id, 'check_in': date, 'machine_id': machine_id}
                request.env['hr.attendance'].create(vals)
            elif attendance.check_in and not attendance.check_out:
                attendance.check_out = date
        return Response('{"status": "done" }', status=200)

    @staticmethod
    def get_db_punch(employee_id, attendance_time, punch_state, att_time_obj):
        start_day = start_day_gmt(att_time_obj, attendance_time)
        end_day = end_day_gmt(att_time_obj, attendance_time)
        att_time_obj_db = att_time_obj + get_gmt_delta(attendance_time)

        in_att = request.env['hr.attendance'].sudo().search([('employee_id', '=', employee_id),
                                                             ('check_in', '>=', start_day),
                                                             ('check_in', '<=', end_day)])

        out_att = request.env['hr.attendance'].sudo().search([('employee_id', '=', employee_id),
                                                              ('check_out', '>=', start_day),
                                                              ('check_out', '<=', end_day)])
        attendance = in_att + out_att

        punch_list = {}
        punch_list.update({att_time_obj_db: punch_state})

        for att in attendance:
            if att.check_in is not False:
                punch_list.update({att.check_in: "check_in"})

            if att.check_out is not False:
                punch_list.update({att.check_out: "check_out"})

        attendance.unlink()

        return punch_list


def hour_diff(attendance_time):
    sign = '+'
    if attendance_time[1][0] == '+':
        sign = '-'

    hdiff = sign + attendance_time[1][1:3]

    return hdiff


def minute_diff(attendance_time):
    sign = '+'
    if attendance_time[1][0] == '+':
        sign = '-'

    mdiff = sign + attendance_time[1][3:5]

    return mdiff


def get_gmt_delta(attendance_time):
    hdiff = hour_diff(attendance_time) or '0'
    mdiff = minute_diff(attendance_time) or '0'
    return timedelta(hours=int(hdiff), minutes=int(mdiff))


def is_db_exist(db_name):
    request.env.cr.execute("SELECT 0 FROM pg_database where datname = '" + db_name + "'")
    check_db = request.env.cr.fetchone()
    if check_db:
        return True
    return False


def start_day_gmt(att_time_obj, attendance_time):
    start_day = datetime.strptime(str(att_time_obj.date()) + " 00:00:00", '%Y-%m-%d %H:%M:%S')
    return start_day + get_gmt_delta(attendance_time)


def end_day_gmt(att_time_obj, attendance_time):
    end_day = datetime.strptime(str(att_time_obj.date()) + " 23:59:59", '%Y-%m-%d %H:%M:%S')
    return end_day + get_gmt_delta(attendance_time)

