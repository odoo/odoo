
for code in ['NUR101-SEC01', 'NUR201-SEC01', 'NUR102-SEC01', 'NUR103-SEC01', 'CHEM101-SEC01']:
    sec = env['university.class.section'].search([('name', '=', code)], limit=1)
    print(f'=== {sec.name}: {sec.subject_id.name} ===')
    print('day_summary:', sec.day_summary, '| time_summary:', sec.time_summary)
    for l in sec.schedule_line_ids:
        print(f'   Line: weekday={l.weekday}, timeslot={l.timeslot_id.name} ({l.timeslot_id.start_hour}-{l.timeslot_id.end_hour}), room={l.room_id.name}, teacher={l.teacher_id.name}')
