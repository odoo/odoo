import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID

def verify():
    odoo.tools.config.parse_config(["-c", "odoo.conf", "-d", "odoo"])
    registry = Registry("odoo")
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        dashboard = env["school.dashboard"]
        data = dashboard.get_dashboard_data()
        
        print("=== DASHBOARD VERIFICATION RESULT ===")
        print(f"Total Students: {data.get('total_students')}")
        print(f"Total Faculty: {data.get('total_faculty')}")
        print(f"Total Programs: {data.get('total_programs')}")
        print(f"Total Sections: {data.get('total_sections')}")
        print(f"Student Attendance Metric: {data.get('student_attendance')}")
        print(f"Faculty Attendance Metric: {data.get('faculty_attendance')}")
        print(f"Risk Distribution: {data.get('risk_distribution')}")
        print(f"High Risk Students Count: {len(data.get('high_risk_students', []))}")
        for st in data.get('high_risk_students', []):
            print(f"  - {st.get('name')}: GPA={st.get('gpa')}, Attendance={st.get('attendance_rate')}%, Reason={st.get('risk_reason')[:40]}...")
        print(f"Upcoming Events Count: {len(data.get('upcoming_events', []))}")
        print(f"Pending Followup Count: {data.get('pending_followup_count')}")
        
        # Verify Kanban views exist and are valid
        for model_name in ["university.lesson.plan", "university.service.hour", "university.assignment", "university.assignment.submission"]:
            view_arch = env[model_name].get_view(view_type="kanban")
            print(f"Verified Kanban view for {model_name}: OK (type={view_arch.get('type')})")

if __name__ == '__main__':
    verify()
