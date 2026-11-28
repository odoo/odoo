student_user = env['res.users'].search([('login', '=', 'student')], limit=1)
student = env['university.student'].search([('user_id', '=', student_user.id)], limit=1)
enrollments = env['university.enrollment'].search([('student_id', '=', student.id), ('status', '=', 'enrolled')])
enrolled_sec_ids = enrollments.mapped('class_section_id').ids or enrollments.mapped('section_id').ids

slots = env['university.timetable.slot'].search([
    ('section_id', 'in', enrolled_sec_ids),
    ('start_time', '>=', '2026-10-18 00:00:00'),
    ('start_time', '<=', '2026-10-24 23:59:59'),
    ('state', '!=', 'cancelled'),
], order='start_time asc')

print(f'Total slots this week for {student.name}: {len(slots)}')
for s in slots:
    print(f'   {s.start_time.strftime("%a %b %d %H:%M")}: {s.subject_id.name} ({s.section_id.name}) in {s.classroom_id.name} - {s.teacher_id.name}')
