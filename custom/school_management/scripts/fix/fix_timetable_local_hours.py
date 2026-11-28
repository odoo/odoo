import os
import sys
import datetime
import pytz

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID

def main():
    print("=== ADJUSTING TIMETABLE SLOTS TO PROPER LOCAL UNIVERSITY HOURS (ASIA/PHNOM_PENH UTC+7) ===")
    odoo.tools.config.parse_config(["-c", "odoo.conf", "-d", "odoo"])
    registry = Registry("odoo")
    tz_local = pytz.timezone("Asia/Phnom_Penh")
    
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        slots = env['university.timetable.slot'].search([])
        updated_count = 0
        
        for slot in slots:
            ts = slot.timeslot_id
            if not ts:
                continue
                
            slot_date = slot.date or slot.start_time.date()
            local_start = datetime.datetime.combine(slot_date, ts._hour_to_time(ts.start_hour))
            local_end = datetime.datetime.combine(slot_date, ts._hour_to_time(ts.end_hour))
            
            utc_start = tz_local.localize(local_start).astimezone(pytz.utc).replace(tzinfo=None)
            utc_end = tz_local.localize(local_end).astimezone(pytz.utc).replace(tzinfo=None)
            
            if slot.start_time != utc_start or slot.end_time != utc_end:
                # Update directly to avoid false conflict trigger during bulk update
                cr.execute("""
                    UPDATE university_timetable_slot 
                    SET start_time = %s, end_time = %s 
                    WHERE id = %s
                """, (utc_start, utc_end, slot.id))
                updated_count += 1
                
        cr.commit()
        print(f"Updated {updated_count} timetable slots to exact local daytime academic hours.")
        
        # Verify 5 samples
        sample_slots = env['university.timetable.slot'].search([('timeslot_id', '!=', False)], limit=5)
        print("\nSample converted slots:")
        for s in sample_slots:
            local_s = pytz.utc.localize(s.start_time).astimezone(tz_local)
            local_e = pytz.utc.localize(s.end_time).astimezone(tz_local)
            print(f"  Slot {s.id}: {s.section_id.name} | UTC: {s.start_time.strftime('%H:%M')} | Local: {local_s.strftime('%I:%M %p')} - {local_e.strftime('%I:%M %p')}")

if __name__ == "__main__":
    main()
