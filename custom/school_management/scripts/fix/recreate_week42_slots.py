import pytz
from datetime import datetime

tz = pytz.timezone("Asia/Phnom_Penh")

student_user = env['res.users'].search([('login', '=', 'student')], limit=1)
student = env['university.student'].search([('user_id', '=', student_user.id)], limit=1)
enrollments = env['university.enrollment'].search([('student_id', '=', student.id), ('status', '=', 'enrolled')])
enrolled_sec_ids = enrollments.mapped('class_section_id').ids or enrollments.mapped('section_id').ids
sections = env['university.class.section'].browse(enrolled_sec_ids)

dates = {
    '0': '2026-10-19',
    '1': '2026-10-20',
    '2': '2026-10-21',
    '3': '2026-10-22',
    '4': '2026-10-23',
    '5': '2026-10-24',
}

def get_free_room(start_utc, end_utc, preferred_room, current_slot_id=None):
    domain = [
        ('start_time', '<', end_utc),
        ('end_time', '>', start_utc),
        ('classroom_id', '=', preferred_room.id),
        ('state', '!=', 'cancelled'),
    ]
    if current_slot_id:
        domain.append(('id', '!=', current_slot_id))
    conflict = env['university.timetable.slot'].search(domain)
    if not conflict:
        return preferred_room
    
    occupied_domain = [
        ('start_time', '<', end_utc),
        ('end_time', '>', start_utc),
        ('state', '!=', 'cancelled'),
    ]
    if current_slot_id:
        occupied_domain.append(('id', '!=', current_slot_id))
    occupied_ids = env['university.timetable.slot'].search(occupied_domain).mapped('classroom_id').ids
    free = env['university.classroom'].search([('id', 'not in', occupied_ids)], limit=1)
    return free or preferred_room

for sec in sections:
    for line in sec.schedule_line_ids:
        if not line.active or line.weekday not in dates:
            continue
        target_date_str = dates[line.weekday]
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        ts = line.timeslot_id
        
        start_h = int(ts.start_hour)
        start_m = int(round((ts.start_hour - start_h) * 60))
        end_h = int(ts.end_hour)
        end_m = int(round((ts.end_hour - end_h) * 60))
        
        local_start = datetime(target_date.year, target_date.month, target_date.day, start_h, start_m)
        local_end = datetime(target_date.year, target_date.month, target_date.day, end_h, end_m)
        
        utc_start = tz.localize(local_start).astimezone(pytz.utc).replace(tzinfo=None)
        utc_end = tz.localize(local_end).astimezone(pytz.utc).replace(tzinfo=None)
        
        room = line.room_id or sec.room_id
        teacher = line.teacher_id or sec.teacher_id

        # Find existing slots for this section on this day
        existing = env['university.timetable.slot'].search([
            ('section_id', '=', sec.id),
            ('start_time', '>=', f'{target_date_str} 00:00:00'),
            ('start_time', '<=', f'{target_date_str} 23:59:59'),
        ])
        
        matched = False
        for ex in existing:
            ex_local_start = pytz.utc.localize(ex.start_time).astimezone(tz)
            if abs(ex_local_start.hour - start_h) <= 1 and abs(ex_local_start.minute - start_m) <= 15:
                actual_room = get_free_room(utc_start, utc_end, room, current_slot_id=ex.id)
                ex.write({
                    'start_time': utc_start,
                    'end_time': utc_end,
                    'classroom_id': actual_room.id,
                    'teacher_id': teacher.id,
                })
                matched = True
                print(f'Updated: {target_date_str} {sec.name} {sec.subject_id.name} in {actual_room.name}')
                break
        
        if not matched:
            wrong_utc = existing.filtered(lambda s: s.start_time.hour >= 10)
            if wrong_utc:
                target_slot = wrong_utc[0]
                actual_room = get_free_room(utc_start, utc_end, room, current_slot_id=target_slot.id)
                target_slot.write({
                    'start_time': utc_start,
                    'end_time': utc_end,
                    'classroom_id': actual_room.id,
                    'teacher_id': teacher.id,
                })
                print(f'Fixed wrong UTC: {target_date_str} {sec.name} {sec.subject_id.name} in {actual_room.name}')
            else:
                actual_room = get_free_room(utc_start, utc_end, room)
                new_s = env['university.timetable.slot'].create({
                    'name': f'{sec.name}-{sec.subject_id.name} ({target_date_str})',
                    'section_id': sec.id,
                    'subject_id': sec.subject_id.id,
                    'academic_year_id': sec.academic_year_id.id,
                    'semester_id': sec.semester_id.id,
                    'teacher_id': teacher.id,
                    'classroom_id': actual_room.id,
                    'start_time': utc_start,
                    'end_time': utc_end,
                    'session_type': 'lecture',
                    'generation_state': 'published',
                    'state': 'scheduled',
                    'status': 'upcoming' if target_date_str >= '2026-10-21' else 'completed',
                })
                print(f'Created: {target_date_str} {sec.name} {sec.subject_id.name} in {actual_room.name}')

env.cr.commit()
print('All week 42 slots synced successfully!')
