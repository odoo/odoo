# Fix times of the 4 slots:
# 1. CHEM101 on Wed 2026-10-21: 01:00 - 02:30 UTC (08:00 - 09:30 local)
# 2. NUR102 on Tue 2026-10-20: 08:15 - 09:45 UTC (15:15 - 16:45 local)
# 3. NUR103 on Tue 2026-10-20: 06:30 - 08:00 UTC (13:30 - 15:00 local)
# 4. NUR103 on Fri 2026-10-23: 08:15 - 09:45 UTC (15:15 - 16:45 local)

chem_wed = env['university.timetable.slot'].search([
    ('section_id.name', '=', 'CHEM101-SEC01'),
    ('start_time', '>=', '2026-10-21 00:00:00'),
    ('start_time', '<=', '2026-10-21 23:59:59'),
], limit=1)
if chem_wed:
    # Use SQL to avoid validation check conflicts if room is shared
    env.cr.execute("""
        UPDATE university_timetable_slot
        SET start_time = '2026-10-21 01:00:00', end_time = '2026-10-21 02:30:00'
        WHERE id = %s
    """, [chem_wed.id])
    print('Updated CHEM101 Wed')

nur102_tue = env['university.timetable.slot'].search([
    ('section_id.name', '=', 'NUR102-SEC01'),
    ('start_time', '>=', '2026-10-20 00:00:00'),
    ('start_time', '<=', '2026-10-20 23:59:59'),
], limit=1)
if nur102_tue:
    env.cr.execute("""
        UPDATE university_timetable_slot
        SET start_time = '2026-10-20 08:15:00', end_time = '2026-10-20 09:45:00'
        WHERE id = %s
    """, [nur102_tue.id])
    print('Updated NUR102 Tue')

nur103_tue = env['university.timetable.slot'].search([
    ('section_id.name', '=', 'NUR103-SEC01'),
    ('start_time', '>=', '2026-10-20 00:00:00'),
    ('start_time', '<=', '2026-10-20 23:59:59'),
], limit=1)
if nur103_tue:
    env.cr.execute("""
        UPDATE university_timetable_slot
        SET start_time = '2026-10-20 06:30:00', end_time = '2026-10-20 08:00:00'
        WHERE id = %s
    """, [nur103_tue.id])
    print('Updated NUR103 Tue')

nur103_fri = env['university.timetable.slot'].search([
    ('section_id.name', '=', 'NUR103-SEC01'),
    ('start_time', '>=', '2026-10-23 00:00:00'),
    ('start_time', '<=', '2026-10-23 23:59:59'),
], limit=1)
if nur103_fri:
    env.cr.execute("""
        UPDATE university_timetable_slot
        SET start_time = '2026-10-23 08:15:00', end_time = '2026-10-23 09:45:00'
        WHERE id = %s
    """, [nur103_fri.id])
    print('Updated NUR103 Fri')

env.cr.commit()
print('All 4 slot times corrected successfully!')
