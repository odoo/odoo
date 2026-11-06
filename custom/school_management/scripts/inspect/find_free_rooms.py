
occupied = env['university.timetable.slot'].search([
    ('start_time', '<', '2026-10-19 02:30:00'),
    ('end_time', '>', '2026-10-19 01:00:00'),
    ('state', '!=', 'cancelled'),
]).mapped('classroom_id').ids
free_rooms = env['university.classroom'].search([('id', 'not in', occupied)])
print('Free classrooms at 08:00-09:30 on Monday Oct 19:')
for r in free_rooms:
    print(f'   {r.name} (Capacity: {r.capacity})')
