import pytz
from datetime import datetime, date
from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class StudentPortalDashboard(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'student_courses_count' in counters:
            student = request.env['university.student'].sudo().search([
                ('user_id', '=', request.env.user.id)
            ], limit=1)
            if student:
                values['student_courses_count'] = request.env['university.enrollment'].sudo().search_count([
                    ('student_id', '=', student.id),
                    ('status', '=', 'enrolled'),
                ])
            else:
                values['student_courses_count'] = 0
        if 'student_books_count' in counters:
            student = request.env['university.student'].sudo().search([
                ('user_id', '=', request.env.user.id)
            ], limit=1)
            if student:
                enrollments = request.env['university.enrollment'].sudo().search([
                    ('student_id', '=', student.id),
                    ('status', '=', 'enrolled'),
                ])
                values['student_books_count'] = request.env['university.subject.book'].sudo().search_count([
                    ('subject_id', 'in', enrollments.mapped('subject_id').ids)
                ])
            else:
                values['student_books_count'] = 0
        return values

    def _get_student_for_current_user(self, student_id=None):
        """
        Retrieve student profile for current user.
        If user is administrator/staff, allow student_id override for testing/preview.
        """
        user = request.env.user
        Student = request.env['university.student'].sudo()

        if student_id and (user.has_group('base.group_system') or user.has_group('school_management.group_school_admin')):
            student = Student.browse(int(student_id))
            if student.exists():
                return student

        student = Student.search([('user_id', '=', user.id)], limit=1)
        if not student and (user.has_group('base.group_system') or user.has_group('school_management.group_school_admin')):
            # Fallback for admin preview mode
            student = Student.search([('status', '=', 'active')], limit=1)
        return student

    @http.route(['/my/student/dashboard'], type='http', auth='user', website=True)
    def student_portal_dashboard(self, student_id=None, **kw):
        student = self._get_student_for_current_user(student_id=student_id)
        if not student:
            return request.render('school_management.student_dashboard_no_profile', {
                'page_name': 'student_dashboard',
            })

        user_tz = pytz.timezone(request.env.user.tz or 'UTC')
        today_date = fields.Date.context_today(student)
        now_dt = datetime.now(user_tz)

        # 1. Profile Details
        initials = ''.join([part[:1].upper() for part in (student.name or '').split()[:2]]) or 'ST'
        year_levels = dict(student._fields['year_level'].selection) if hasattr(student._fields.get('year_level'), 'selection') else {}
        year_level_label = year_levels.get(student.year_level, 'Year 1') if student.year_level else 'Year 1'
        semester_label = student.current_semester_id.name if student.current_semester_id else 'Current Term'

        student_profile = {
            'id': student.id,
            'name': student.name,
            'student_id': student.student_id or 'STU-PENDING',
            'program_name': student.program_id.name if student.program_id else 'General Academic Program',
            'department_name': student.department_id.name if student.department_id else (student.program_id.department_id.name if student.program_id and student.program_id.department_id else 'Academic Department'),
            'faculty_name': student.faculty_id.name if student.faculty_id else '',
            'year_level_label': year_level_label,
            'semester_label': semester_label,
            'avatar_text': initials,
            'has_image': bool(student.image_1920),
            'image_url': f'/web/image/university.student/{student.id}/image_1920' if student.image_1920 else None,
            'email': student.email or '',
        }

        # 2. Academic Metrics
        gpa = round(student.gpa or 0.0, 2)
        is_deans_list = gpa >= 3.5
        attendance_rate = round(student.attendance_rate or 0.0, 1)
        is_attendance_at_risk = attendance_rate < 80.0

        completed_credits = int(student.completed_credits or 0)
        total_credits = int(student.program_id.total_credits or 120) if student.program_id else 120
        credit_progress = min(100, int((completed_credits / total_credits * 100))) if total_credits > 0 else 0

        fee_balance = round(student.fee_balance or 0.0, 2)
        is_fee_paid = fee_balance <= 0.01
        currency_symbol = student.currency_id.symbol if student.currency_id else '$'

        academic_metrics = {
            'gpa': gpa,
            'is_deans_list': is_deans_list,
            'attendance_rate': attendance_rate,
            'is_attendance_at_risk': is_attendance_at_risk,
            'completed_credits': completed_credits,
            'total_credits': total_credits,
            'credit_progress': credit_progress,
            'fee_balance': fee_balance,
            'fee_balance_formatted': f"{currency_symbol}{fee_balance:,.2f}",
            'is_fee_paid': is_fee_paid,
            'at_risk_courses_count': max(1, student.failed_subject_count or 1) if is_attendance_at_risk else 0,
        }

        # 3. Enrolled Courses List
        enrollments = request.env['university.enrollment'].sudo().search([
            ('student_id', '=', student.id),
            ('status', '=', 'enrolled')
        ], order='id asc')

        enrolled_courses = []
        enrolled_section_ids = []
        for en in enrollments:
            sec = en.class_section_id
            if sec:
                enrolled_section_ids.append(sec.id)
            teacher = en.teacher_id or (sec.teacher_id if sec else False)
            classroom = sec.classroom_id if sec else False
            subject = en.subject_id or (sec.subject_id if sec else False)

            enrolled_courses.append({
                'enrollment_id': en.id,
                'subject_id': subject.id if subject else False,
                'course_code': getattr(subject, 'code', '') or 'CRS',
                'name': getattr(subject, 'name', '') or 'Course',
                'instructor_name': teacher.name if teacher else 'Assigned Faculty',
                'instructor_email': teacher.email if teacher and teacher.email else '',
                'section_name': sec.name if sec else 'Section',
                'classroom_name': classroom.name if classroom else 'Room TBA',
                'building_name': getattr(classroom, 'building', '') or 'Main Campus',
                'credit_hours': getattr(subject, 'credit_hours', 3) or 3,
                'syllabus_url': f'/report/pdf/school_management.action_report_curriculum/{student.program_id.id}' if student.program_id else '#',
            })

        # 4. Today's Schedule & Agenda Items
        today_slots = []
        live_or_next_class = None

        if enrolled_section_ids:
            slots = request.env['university.timetable.slot'].sudo().search([
                ('section_id', 'in', enrolled_section_ids),
                ('date', '=', today_date),
                ('generation_state', '=', 'published'),
            ], order='start_time asc')

            for slot in slots:
                start_dt = slot.start_time.astimezone(user_tz) if slot.start_time else None
                end_dt = slot.end_time.astimezone(user_tz) if slot.end_time else None

                # Strict Single Status Determination
                if slot.state == 'cancelled':
                    strict_status = 'Cancelled'
                    status_badge = 'badge bg-danger-subtle text-danger'
                elif start_dt and end_dt:
                    if start_dt <= now_dt <= end_dt:
                        strict_status = 'Live Now'
                        status_badge = 'badge bg-danger text-white pulse'
                    elif now_dt < start_dt:
                        strict_status = 'Upcoming'
                        status_badge = 'badge bg-primary-subtle text-primary'
                    else:
                        strict_status = 'Completed'
                        status_badge = 'badge bg-success-subtle text-success'
                else:
                    strict_status = 'Upcoming'
                    status_badge = 'badge bg-primary-subtle text-primary'

                time_formatted = f"{start_dt.strftime('%I:%M %p')} – {end_dt.strftime('%I:%M %p')}" if (start_dt and end_dt) else "Time TBA"

                slot_data = {
                    'id': slot.id,
                    'subject_name': slot.subject_id.name if slot.subject_id else (slot.section_id.subject_id.name if slot.section_id and slot.section_id.subject_id else 'Class Session'),
                    'course_code': slot.subject_id.code if slot.subject_id and slot.subject_id.code else '',
                    'instructor_name': slot.teacher_id.name if slot.teacher_id else (slot.section_id.teacher_id.name if slot.section_id and slot.section_id.teacher_id else 'Faculty'),
                    'classroom_name': slot.classroom_id.name if slot.classroom_id else 'Room TBA',
                    'building_name': getattr(slot.classroom_id, 'building', '') or 'Academic Wing',
                    'time_formatted': time_formatted,
                    'status': strict_status,
                    'status_badge': status_badge,
                    'start_dt': start_dt,
                    'end_dt': end_dt,
                }
                today_slots.append(slot_data)

            # Highlight Live Now class or next Upcoming class
            for s in today_slots:
                if s['status'] == 'Live Now':
                    live_or_next_class = s
                    break
            if not live_or_next_class:
                for s in today_slots:
                    if s['status'] == 'Upcoming':
                        live_or_next_class = s
                        break

        # Check for JSON API request
        if kw.get('json') or request.httprequest.headers.get('Accept') == 'application/json':
            return request.make_json_response({
                'student': student_profile,
                'metrics': academic_metrics,
                'courses': enrolled_courses,
                'today_slots': today_slots,
                'live_or_next_class': live_or_next_class,
            })

        latest_report = request.env['university.report.card'].sudo().search([
            ('student_id', '=', student.id),
            ('state', '=', 'approved'),
        ], order='id desc', limit=1)

        values = {
            'page_name': 'student_dashboard',
            'latest_report_card_id': latest_report.id if latest_report else None,
            'student': student_profile,
            'metrics': academic_metrics,
            'courses': enrolled_courses,
            'today_slots': today_slots,
            'live_or_next_class': live_or_next_class,
            'today_date_formatted': now_dt.strftime('%A, %B %d, %Y'),
            'transcript_success': kw.get('transcript_requested') == '1',
        }
        return request.render('school_management.student_dashboard_template', values)

    @http.route(['/my/student/transcript/request'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def request_transcript(self, **post):
        student = self._get_student_for_current_user()
        if student:
            request_type = post.get('request_type', 'unofficial')
            purpose = post.get('purpose', 'academic')
            try:
                copies = int(post.get('copies', 1))
            except (ValueError, TypeError):
                copies = 1

            request.env['university.transcript.request'].sudo().create({
                'student_id': student.id,
                'request_type': request_type,
                'purpose': purpose,
                'copies': max(1, copies),
            })
        return request.redirect('/my/student/dashboard?transcript_requested=1')


    @http.route(['/my/books'], type='http', auth='user', website=True)
    def portal_my_books(self, **kw):
        student = self._get_student_for_current_user()
        if not student:
            return request.render('school_management.student_dashboard_no_profile', {
                'page_name': 'student_books',
            })

        enrollments = request.env['university.enrollment'].sudo().search([
            ('student_id', '=', student.id),
            ('status', '=', 'enrolled'),
        ])
        subjects = enrollments.mapped('subject_id')

        books_by_subject = []
        for subject in subjects:
            links = request.env['university.subject.book'].sudo().search([
                ('subject_id', '=', subject.id),
            ], order='sequence asc, id asc')
            if links:
                books_by_subject.append({
                    'subject': subject,
                    'books': links,
                })

        values = {
            'page_name': 'student_books',
            'student': student,
            'books_by_subject': books_by_subject,
        }
        return request.render('school_management.portal_my_books', values)
