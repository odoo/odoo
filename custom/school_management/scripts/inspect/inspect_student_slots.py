student_user = env['res.users'].search([('login', '=', 'student')], limit=1)
student = env['university.student'].search([('user_id', '=', student_user.id)], limit=1)
print('Student:', student.name, student.student_id)

enrollments = env['university.enrollment'].search([('student_id', '=', student.id), ('status', '=', 'enrolled')])
print(f'Total enrolled sections: {len(enrollments)}')
for e in enrollments:
    sec = e.class_section_id or e.section_id
    slots = env['university.timetable.slot'].search([('section_id', '=', sec.id)])
    week_slots = slots.filtered(lambda s: s.start_time and s.start_time.strftime('%Y-%m-%d') >= '2026-10-18' and s.start_time.strftime('%Y-%m-%d') <= '2026-10-24')
    print(f'Section {sec.name} ({sec.subject_id.name}): {len(slots)} total slots, {len(week_slots)} slots this week (Oct 18-24)')
    for s in week_slots:
        print(f'   -> {s.start_time} - {s.end_time}: {s.name} ({s.session_type}, state={s.state})')
