
for code in ['CHEM101-SEC01', 'NUR103-SEC01', 'NUR102-SEC01']:
    sec = env['university.class.section'].search([('name', '=', code)], limit=1)
    slots = env['university.timetable.slot'].search([('section_id', '=', sec.id)], order='start_time asc')
    if slots:
        print(f'{code}: {len(slots)} slots from {slots[0].start_time} to {slots[-1].start_time}')
    else:
        print(f'{code}: No slots')
