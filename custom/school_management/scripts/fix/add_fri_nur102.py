sec = env['university.class.section'].search([('name', '=', 'NUR102-SEC01')], limit=1)
room = env['university.classroom'].search([('name', '=', 'B201')], limit=1)
existing = env['university.timetable.slot'].search([
    ('section_id', '=', sec.id),
    ('start_time', '>=', '2026-10-23 00:00:00'),
    ('start_time', '<=', '2026-10-23 23:59:59'),
])
if not existing:
    slot = env['university.timetable.slot'].create({
        'name': f'{sec.name}-{sec.subject_id.name} (2026-10-23)',
        'section_id': sec.id,
        'subject_id': sec.subject_id.id,
        'academic_year_id': sec.academic_year_id.id,
        'semester_id': sec.semester_id.id,
        'teacher_id': sec.teacher_id.id,
        'classroom_id': room.id,
        'start_time': '2026-10-23 01:00:00', # 08:00 local time
        'end_time': '2026-10-23 02:30:00',   # 09:30 local time
        'session_type': 'lecture',
        'generation_state': 'published',
        'state': 'scheduled',
        'status': 'upcoming',
    })
    print('Created Friday slot:', slot.id, slot.name)
    env.cr.commit()
else:
    print('Already exists:', existing.ids)
