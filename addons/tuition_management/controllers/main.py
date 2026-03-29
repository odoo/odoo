# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class TuitionPortal(http.Controller):
    """Portal controllers for students, parents, and tutors"""

    def _prepare_portal_layout_values(self):
        """Prepare common layout values for portal pages"""
        partner = request.env.user.partner_id
        return {
            'partner': partner,
            'page_name': 'tuition',
        }

    # ========== STUDENT PORTAL ==========
    @http.route('/my/courses', auth='user', website=True)
    def portal_my_courses(self):
        """Student view: My enrolled courses"""
        values = self._prepare_portal_layout_values()
        student = request.env['student.profile'].search([
            ('partner_id', '=', request.env.user.partner_id.id)
        ], limit=1)
        
        enrollments = request.env['course.enrollment'].search([
            ('student_id', '=', student.id)
        ]) if student else []
        
        values.update({
            'enrollments': enrollments,
            'student': student,
        })
        return request.render('tuition_management.portal_my_courses', values)

    @http.route('/my/class-schedules', auth='user', website=True)
    def portal_my_class_schedules(self):
        """Student view: My class schedules"""
        values = self._prepare_portal_layout_values()
        student = request.env['student.profile'].search([
            ('partner_id', '=', request.env.user.partner_id.id)
        ], limit=1)
        
        # Get schedules for enrolled courses
        enrollments = request.env['course.enrollment'].search([
            ('student_id', '=', student.id)
        ]) if student else []
        course_ids = enrollments.mapped('course_id.id')
        
        schedules = request.env['class.schedule'].search([
            ('course_id', 'in', course_ids)
        ]) if course_ids else []
        
        values.update({
            'schedules': schedules,
            'student': student,
        })
        return request.render('tuition_management.portal_my_class_schedules', values)

    @http.route('/my/attendance', auth='user', website=True)
    def portal_my_attendance(self):
        """Student view: My attendance records"""
        values = self._prepare_portal_layout_values()
        student = request.env['student.profile'].search([
            ('partner_id', '=', request.env.user.partner_id.id)
        ], limit=1)
        
        attendance_records = request.env['attendance.record'].search([
            ('student_id', '=', student.id)
        ]) if student else []
        
        values.update({
            'attendance_records': attendance_records,
            'student': student,
        })
        return request.render('tuition_management.portal_my_attendance', values)

    # ========== TUTOR PORTAL ==========
    @http.route('/my/teaching-schedules', auth='user', website=True)
    def portal_my_teaching_schedules(self):
        """Tutor view: My teaching schedules"""
        values = self._prepare_portal_layout_values()
        tutor = request.env['tutor.profile'].search([
            ('partner_id', '=', request.env.user.partner_id.id)
        ], limit=1)
        
        schedules = request.env['class.schedule'].search([
            ('tutor_id', '=', tutor.id)
        ]) if tutor else []
        
        values.update({
            'schedules': schedules,
            'tutor': tutor,
        })
        return request.render('tuition_management.portal_my_teaching_schedules', values)

    @http.route('/my/student-attendance/<int:schedule_id>', auth='user', website=True)
    def portal_student_attendance(self, schedule_id):
        """Tutor view: Manage student attendance for a class"""
        schedule = request.env['class.schedule'].browse(schedule_id)
        
        # Check if user is the tutor
        tutor = request.env['tutor.profile'].search([
            ('partner_id', '=', request.env.user.partner_id.id)
        ], limit=1)
        if schedule.tutor_id != tutor:
            return request.not_found()
        
        values = self._prepare_portal_layout_values()
        attendance_records = request.env['attendance.record'].search([
            ('class_schedule_id', '=', schedule_id)
        ])
        
        values.update({
            'schedule': schedule,
            'attendance_records': attendance_records,
            'tutor': tutor,
        })
        return request.render('tuition_management.portal_student_attendance', values)

    @http.route('/my/courses-taught', auth='user', website=True)
    def portal_my_courses_taught(self):
        """Tutor view: My courses"""
        values = self._prepare_portal_layout_values()
        tutor = request.env['tutor.profile'].search([
            ('partner_id', '=', request.env.user.partner_id.id)
        ], limit=1)
        
        courses = request.env['course.master'].search([
            ('tutor_id', '=', tutor.id)
        ]) if tutor else []
        
        values.update({
            'courses': courses,
            'tutor': tutor,
        })
        return request.render('tuition_management.portal_my_courses_taught', values)

    # ========== PARENT PORTAL ==========
    @http.route('/my/children-courses', auth='user', website=True)
    def portal_children_courses(self):
        """Parent view: Children's courses"""
        values = self._prepare_portal_layout_values()
        
        # Get all students linked to this parent's contact (via same company or custom relation)
        partner = request.env.user.partner_id
        students = request.env['student.profile'].search([
            ('partner_id', '=', partner.id)
        ])
        
        enrollments = request.env['course.enrollment'].search([
            ('student_id', 'in', students.ids)
        ]) if students else []
        
        values.update({
            'enrollments': enrollments,
            'students': students,
        })
        return request.render('tuition_management.portal_children_courses', values)

    @http.route('/my/children-attendance', auth='user', website=True)
    def portal_children_attendance(self):
        """Parent view: Children's attendance"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        students = request.env['student.profile'].search([
            ('partner_id', '=', partner.id)
        ])
        
        attendance_records = request.env['attendance.record'].search([
            ('student_id', 'in', students.ids)
        ]) if students else []
        
        values.update({
            'attendance_records': attendance_records,
            'students': students,
        })
        return request.render('tuition_management.portal_children_attendance', values)

    @http.route('/tuition/status', auth='public', type='jsonrpc')
    def status(self):
        return {'status': 'ok', 'message': 'Tuition Management API is running'}
