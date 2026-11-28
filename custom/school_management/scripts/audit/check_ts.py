
for name in ['NUR103-SEC01', 'NUR102-SEC01']:
    sec = env['university.class.section'].search([('name', '=', name)], limit=1)
    for l in sec.schedule_line_ids:
        ts = l.timeslot_id
        print(f'{sec.name}: ts={ts.name}, start_hour={ts.start_hour}, end_hour={ts.end_hour}')
