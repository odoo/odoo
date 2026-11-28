student_user = env['res.users'].search([('login', '=', 'student')], limit=1)
student = env['university.student'].search([('user_id', '=', student_user.id)], limit=1)
enrollments = env['university.enrollment'].search([('student_id', '=', student.id), ('status', '=', 'enrolled')])
enrolled_sec_ids = enrollments.mapped('class_section_id').ids or enrollments.mapped('section_id').ids
slots = env['university.timetable.slot'].search([
    ('section_id', 'in', enrolled_sec_ids),
    ('start_time', '>=', '2026-10-18 00:00:00'),
    ('start_time', '<=', '2026-10-24 23:59:59'),
])
for s in slots:
    print(f'{s.start_time.strftime("%a %H:%M")}: {s.subject_id.name} -> gen_state={s.generation_state}, state={s.state}')
