slots = env['university.timetable.slot'].search([
    ('start_time', '>=', '2026-10-19 00:00:00'),
    ('start_time', '<=', '2026-10-19 23:59:59'),
])
print(f'Total slots on 2026-10-19: {len(slots)}')
for s in slots:
    print(f'   {s.start_time.strftime("%H:%M")}-{s.end_time.strftime("%H:%M")}: {s.section_id.name} ({s.subject_id.name}), Room={s.classroom_id.name}, Teacher={s.teacher_id.name}')
