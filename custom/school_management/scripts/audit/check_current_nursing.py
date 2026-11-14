
for name in ['CHEM101-SEC01', 'NUR102-SEC01', 'NUR103-SEC01']:
    sec = env['university.class.section'].search([('name', '=', name)], limit=1)
    slots = env['university.timetable.slot'].search([
        ('section_id', '=', sec.id),
        ('start_time', '>=', '2026-10-18 00:00:00'),
        ('start_time', '<=', '2026-10-24 23:59:59'),
    ], order='start_time asc')
    print(f'=== {sec.name} ({len(slots)} slots) ===')
    for s in slots:
        print(f'   {s.start_time} - {s.end_time}: in {s.classroom_id.name}')
