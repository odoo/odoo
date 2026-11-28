
sec = env['university.class.section'].search([('name', '=', 'CHEM101-SEC01')], limit=1)
slots = env['university.timetable.slot'].search([('section_id', '=', sec.id)], order='start_time asc')
for s in slots:
    if s.start_time and s.start_time.strftime('%Y-%m-%d') >= '2026-10-15':
        print(f'{s.start_time}: {s.name}')
