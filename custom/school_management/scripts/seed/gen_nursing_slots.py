sections = env['university.class.section'].search([('name', 'in', ['CHEM101-SEC01', 'NUR102-SEC01', 'NUR103-SEC01'])])
wiz = env['university.timetable.generation.wizard'].create({
    'academic_year_id': sections[0].academic_year_id.id,
    'semester_id': sections[0].semester_id.id,
    'section_ids': [(6, 0, sections.ids)],
    'start_date': '2026-10-01',
    'week_count': 16,
    'replace_existing_drafts': False,
})
res = wiz.action_generate_timetable()
print('Generation result:', res)

# Check slots for week 42
for sec in sections:
    slots = env['university.timetable.slot'].search([('section_id', '=', sec.id)])
    week_slots = slots.filtered(lambda s: s.start_time and s.start_time.strftime('%Y-%m-%d') >= '2026-10-18' and s.start_time.strftime('%Y-%m-%d') <= '2026-10-24')
    print(f'{sec.name}: {len(week_slots)} slots this week')
    for s in week_slots:
        print(f'   -> {s.start_time.strftime("%a %H:%M")}: {s.name}')
env.cr.commit()
