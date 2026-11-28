import os
import sys
import datetime
import base64
import io
import random
from PIL import Image, ImageDraw, ImageFont

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID

def create_notice_banner(title, category, priority, bg_c1, bg_c2, width=640, height=280):
    img = Image.new("RGBA", (width, height), bg_c1)
    draw = ImageDraw.Draw(img)
    
    # Smooth gradient
    for y in range(height):
        r = int(bg_c1[0] + (bg_c2[0] - bg_c1[0]) * (y / height))
        g = int(bg_c1[1] + (bg_c2[1] - bg_c1[1]) * (y / height))
        b = int(bg_c1[2] + (bg_c2[2] - bg_c1[2]) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
        
    # Decorative shapes
    draw.ellipse([(width - 180, -40), (width + 60, 200)], fill=(255, 255, 255, 18))
    draw.ellipse([(-60, height - 120), (120, height + 60)], fill=(255, 255, 255, 12))
    draw.rectangle([(0, height - 6), (width, height)], fill=(255, 255, 255, 160))

    try:
        f_badge = ImageFont.truetype("arialbd.ttf", 15)
        f_title = ImageFont.truetype("arialbd.ttf", 26)
        f_sub = ImageFont.truetype("arial.ttf", 17)
    except Exception:
        f_badge = f_title = f_sub = ImageFont.load_default()
        
    # Priority Tag Pill
    p_color = (220, 38, 38) if priority == "high" else ((217, 119, 6) if priority == "medium" else (71, 85, 105))
    draw.rounded_rectangle([(30, 25), (160, 58)], radius=14, fill=p_color)
    p_text = f"• {priority.upper()}"
    draw.text((45, 33), p_text, fill=(255, 255, 255), font=f_badge)
    
    # Category Tag
    draw.rounded_rectangle([(170, 25), (320, 58)], radius=14, fill=(255, 255, 255, 45), outline=(255, 255, 255, 140), width=1)
    draw.text((185, 33), category.upper(), fill=(255, 255, 255), font=f_badge)
    
    # Title multi-line
    words = title.split()
    line1 = []
    line2 = []
    for w in words:
        if len(" ".join(line1 + [w])) <= 32:
            line1.append(w)
        else:
            line2.append(w)
            
    t1 = " ".join(line1)
    t2 = " ".join(line2)
    draw.text((30, 100), t1, fill=(255, 255, 255), font=f_title)
    if t2:
        draw.text((30, 138), t2, fill=(241, 245, 249), font=f_title)
        
    draw.text((30, 220), "OFFICIAL UNIVERSITY NOTIFICATION BULLETIN", fill=(203, 213, 225, 200), font=f_sub)
    
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def main():
    print("=== SEEDING COMPREHENSIVE CAMPUS NOTICE BOARD DATA ===")
    odoo.tools.config.parse_config(["-c", "odoo.conf", "-d", "odoo"])
    registry = Registry("odoo")
    
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Get active academic year
        ay = env['university.academic.year'].search([('current', '=', True)], limit=1)
        if not ay:
            ay = env['university.academic.year'].search([], order='date_start desc', limit=1)
            
        # Get departments for matching
        dept_cs = env['university.department'].search([('code', '=', 'CS')], limit=1)
        dept_se = env['university.department'].search([('code', '=', 'SE')], limit=1)
        dept_ai = env['university.department'].search([('code', '=', 'AI')], limit=1)
        dept_mgt = env['university.department'].search([('code', '=', 'MGT')], limit=1)
        dept_med = env['university.department'].search([('code', '=', 'MED')], limit=1)
        dept_ee = env['university.department'].search([('code', '=', 'EE')], limit=1)
        dept_nur = env['university.department'].search([('code', '=', 'NUR')], limit=1)

        palettes = [
            ((15, 23, 42), (30, 41, 59)),     # Dark slate
            ((30, 58, 138), (37, 99, 235)),   # Royal Blue
            ((6, 78, 59), (16, 185, 129)),     # Emerald
            ((120, 53, 15), (217, 119, 6)),    # Amber/Gold
            ((88, 28, 135), (147, 51, 234)),   # Purple
            ((136, 19, 55), (225, 29, 72)),    # Crimson Red
            ((19, 78, 74), (20, 184, 166)),    # Teal
            ((67, 56, 202), (99, 102, 241)),   # Indigo
        ]

        notices_data = [
            # Pinned Urgent Announcements
            {
                "name": "Midterm Examination Timetable & Hall Allocations - Fall 2026",
                "date": datetime.date(2026, 10, 16),
                "notice_type": "exam",
                "priority": "high",
                "target_audience": "all",
                "pinned": True,
                "department_id": dept_cs.id if dept_cs else False,
                "author_name": "Office of Academic Affairs & Examinations",
                "content": """
                    <div class="lead text-primary mb-3"><strong>Official Notice to All Registered Students and Faculty</strong></div>
                    <p>The Midterm Examinations for <strong>Academic Year 2026–2027 (Semester 1)</strong> will formally commence on <strong>Monday, October 26, 2026</strong> and conclude on <strong>Saturday, November 7, 2026</strong>.</p>
                    <div class="alert alert-info py-2">
                        <strong>Mandatory Requirements:</strong>
                        <ul class="mb-0">
                            <li>All candidates must carry their official Student ID cards and Hall Admit Slips.</li>
                            <li>Electronic smart devices, mobile phones, and unapproved programmable calculators are strictly prohibited in examination halls.</li>
                            <li>Students must arrive at designated lecture halls/examination centers at least 20 minutes prior to session start.</li>
                        </ul>
                    </div>
                    <p>Room allocations and invigilator rosters are displayed on department bulletin boards and available on the University Student Portal.</p>
                """,
            },
            {
                "name": "Pchum Ben Festival Campus Recess & Session Rescheduling",
                "date": datetime.date(2026, 10, 8),
                "notice_type": "holiday",
                "priority": "high",
                "target_audience": "all",
                "pinned": True,
                "department_id": False,
                "author_name": "Office of the Vice Chancellor",
                "content": """
                    <p>On the auspicious occasion of the <strong>Pchum Ben Festival</strong>, the University will remain closed from <strong>October 10, 2026 to October 12, 2026</strong>.</p>
                    <p>Administrative offices, libraries, and laboratories will resume regular operations on <strong>Tuesday, October 13, 2026</strong>. Teaching sessions falling within the holiday period have been rescheduled in coordination with course instructors.</p>
                    <p>We wish all students, faculty members, and administrative staff a safe, joyous, and blessed Pchum Ben holiday with family and loved ones.</p>
                """,
            },
            {
                "name": "Annual AI & Robotics Innovation Summit 2026: Registration Open",
                "date": datetime.date(2026, 10, 14),
                "notice_type": "event",
                "priority": "high",
                "target_audience": "all",
                "pinned": True,
                "department_id": dept_ai.id if dept_ai else False,
                "author_name": "Department of Artificial Intelligence & Robotics Lab",
                "content": """
                    <p>The Faculty of Computing & Engineering is thrilled to announce the <strong>Annual AI & Robotics Innovation Summit 2026</strong>, scheduled for <strong>November 14–15, 2026</strong> at the Tech Auditorium 101.</p>
                    <h5>Summit Highlights:</h5>
                    <ul>
                        <li>Keynote presentations from international AI researchers and tech industry leaders.</li>
                        <li>Autonomous robotics demonstration track & student hackathon ($5,000 in grand prizes).</li>
                        <li>Industry recruitment booths and research poster showcase.</li>
                    </ul>
                    <p>All undergraduate and postgraduate students are invited to register projects before <strong>November 1, 2026</strong>.</p>
                """,
            },
            # Academic & Department Notices
            {
                "name": "Software Engineering Capstone Project Briefing & Industry Mentors",
                "date": datetime.date(2026, 10, 15),
                "notice_type": "academic",
                "priority": "medium",
                "target_audience": "graduating",
                "pinned": False,
                "department_id": dept_se.id if dept_se else False,
                "author_name": "Department of Software Engineering",
                "content": """
                    <p>Final-year Software Engineering students are notified that the mandatory briefing session for <strong>Capstone Project (SE499)</strong> will take place on <strong>Wednesday, October 21, 2026 at 02:00 PM</strong> in <em>Software Engineering Lab 202</em>.</p>
                    <p>Students must form project teams of 3–4 members and review the approved list of enterprise software and mobile app problem statements before the briefing.</p>
                """,
            },
            {
                "name": "Semester 1 Course Add/Drop & Elective Confirmation Deadline",
                "date": datetime.date(2026, 10, 12),
                "notice_type": "administrative",
                "priority": "high",
                "target_audience": "students",
                "pinned": False,
                "department_id": False,
                "author_name": "University Registrar Office",
                "content": """
                    <p>The final deadline for <strong>Course Add/Drop, Section Changes, and Elective Subject Confirmation</strong> for Semester 1 (2026–2027) is <strong>Friday, October 23, 2026 at 05:00 PM</strong>.</p>
                    <p>No further enrollment modifications will be entertained after this deadline. Please review your enrolled course list via the Student Portal to verify credit registrations.</p>
                """,
            },
            {
                "name": "Dean's Honor List & Merit Academic Scholarship Applications Open",
                "date": datetime.date(2026, 10, 11),
                "notice_type": "academic",
                "priority": "medium",
                "target_audience": "students",
                "pinned": False,
                "department_id": False,
                "author_name": "Scholarship & Student Welfare Board",
                "content": """
                    <p>Applications for the <strong>Dean's Honor List Merit Scholarships</strong> for the 2026–2027 academic year are now open. Undergraduate students with a cumulative GPA of <strong>3.75 or above</strong> are eligible to apply.</p>
                    <p>Selected recipients will receive a 50% to 100% tuition waiver. Completed application forms and academic transcripts must be submitted to the Student Affairs Desk by <strong>November 5, 2026</strong>.</p>
                """,
            },
            {
                "name": "Clinical Medicine & Nursing Hospital Rotation Schedule Announced",
                "date": datetime.date(2026, 10, 10),
                "notice_type": "academic",
                "priority": "medium",
                "target_audience": "students",
                "pinned": False,
                "department_id": dept_med.id if dept_med else False,
                "author_name": "Faculty of Medicine & Health Sciences",
                "content": """
                    <p>Clinical Medicine (Year 3 & 4) and Nursing cohorts are advised that the Semester 1 hospital clinical rotations will begin on <strong>Monday, October 19, 2026</strong> across partner teaching hospitals.</p>
                    <p>All students must attend the clinical safety orientation and present up-to-date medical immunization certificates at the Clinical Skills Lab on Friday.</p>
                """,
            },
            {
                "name": "Extended Library Hours & IEEE / ACM Research Database Access",
                "date": datetime.date(2026, 10, 9),
                "notice_type": "facility",
                "priority": "low",
                "target_audience": "all",
                "pinned": False,
                "department_id": False,
                "author_name": "University Main Library",
                "content": """
                    <p>In preparation for midterm examinations and semester research projects, the Central University Library will extend its operating hours:</p>
                    <ul>
                        <li><strong>Monday to Friday:</strong> 07:00 AM – 11:00 PM</li>
                        <li><strong>Saturday & Sunday:</strong> 08:00 AM – 09:00 PM</li>
                    </ul>
                    <p>Remote access to digital libraries (IEEE Xplore, ScienceDirect, ACM Digital Library, and SpringerLink) is active for all students via campus SSO credentials.</p>
                """,
            },
            {
                "name": "Department of Electrical Engineering: Smart Grid Lab Safety Briefing",
                "date": datetime.date(2026, 10, 7),
                "notice_type": "facility",
                "priority": "medium",
                "target_audience": "students",
                "pinned": False,
                "department_id": dept_ee.id if dept_ee else False,
                "author_name": "Department of Electrical Engineering",
                "content": """
                    <p>All students registered in <strong>EE301: Power Systems</strong> and <strong>EE501: Smart Grids</strong> are required to attend the mandatory High-Voltage Lab Safety Briefing in <em>Power Lab E102</em> before conducting hardware experiments.</p>
                    <p>Proper protective equipment (safety footwear and insulated lab gear) is strictly enforced at all times.</p>
                """,
            },
            {
                "name": "Management & Strategy Case Study Competition: Fall 2026",
                "date": datetime.date(2026, 10, 6),
                "notice_type": "event",
                "priority": "medium",
                "target_audience": "students",
                "pinned": False,
                "department_id": dept_mgt.id if dept_mgt else False,
                "author_name": "Department of Management & Strategy",
                "content": """
                    <p>The Department of Management invites all business, marketing, and finance students to participate in the <strong>Fall 2026 Business Case Competition</strong>.</p>
                    <p>Teams will analyze real-world ASEAN market expansion strategies and present solutions before a panel of corporate executives. Registration closes on <strong>October 25, 2026</strong>.</p>
                """,
            },
            {
                "name": "Campus Cybersecurity Advisory: Phishing Awareness & Two-Factor Auth",
                "date": datetime.date(2026, 10, 4),
                "notice_type": "facility",
                "priority": "high",
                "target_audience": "all",
                "pinned": False,
                "department_id": False,
                "author_name": "Information Technology Services (ITS)",
                "content": """
                    <p>The University IT Security Office reminds all staff and students to remain vigilant against phishing attempts imitating university credential reset notices.</p>
                    <div class="alert alert-warning py-2">
                        <strong>Security Guidelines:</strong>
                        <ul class="mb-0">
                            <li>The university will never request your account password via email or SMS.</li>
                            <li>Two-Factor Authentication (2FA) is now mandatory on all portal logins.</li>
                            <li>Report suspicious emails immediately to <code>security@university.edu.kh</code>.</li>
                        </ul>
                    </div>
                """,
            },
            {
                "name": "Nursing & Public Health Community Health Outreach Campaign",
                "date": datetime.date(2026, 10, 3),
                "notice_type": "event",
                "priority": "low",
                "target_audience": "students",
                "pinned": False,
                "department_id": dept_nur.id if dept_nur else False,
                "author_name": "Department of Nursing & Public Health",
                "content": """
                    <p>Students from the Department of Nursing will conduct a free community health screening and public health awareness drive in surrounding districts on <strong>Saturday, October 24, 2026</strong>.</p>
                    <p>Student volunteers will earn recognized service hours towards graduation requirements.</p>
                """,
            },
            {
                "name": "Commemoration Day of the King's Father: Official Public Holiday",
                "date": datetime.date(2026, 10, 2),
                "notice_type": "holiday",
                "priority": "medium",
                "target_audience": "all",
                "pinned": False,
                "department_id": False,
                "author_name": "University Administration",
                "content": """
                    <p>In solemn commemoration of the <strong>King's Father, His Majesty Preah Bat Samdech Preah Norodom Sihanouk</strong>, the university will observe a public holiday on <strong>Thursday, October 15, 2026</strong>.</p>
                    <p>All classes and administrative services will be suspended on this day and resume on Friday, October 16, 2026.</p>
                """,
            },
            {
                "name": "Undergraduate Research Grant Funding: Call for Student Proposals",
                "date": datetime.date(2026, 10, 1),
                "notice_type": "academic",
                "priority": "medium",
                "target_audience": "students",
                "pinned": False,
                "department_id": dept_cs.id if dept_cs else False,
                "author_name": "University Research & Development Directorate",
                "content": """
                    <p>The Directorate of Research is pleased to announce seed funding grants (up to $2,500 per project) for student-led research initiatives in Software Engineering, Artificial Intelligence, Medical Technology, and Sustainable Energy.</p>
                    <p>Proposals endorsed by a faculty mentor must be submitted by <strong>November 10, 2026</strong>.</p>
                """,
            },
            {
                "name": "Annual Career Fair & Employer Networking Summit 2026",
                "date": datetime.date(2026, 9, 29),
                "notice_type": "event",
                "priority": "medium",
                "target_audience": "all",
                "pinned": False,
                "department_id": False,
                "author_name": "Career Guidance & Alumni Affairs Office",
                "content": """
                    <p>Over 45 leading multinational corporations, banks, tech companies, and NGOs will visit campus for the <strong>Annual Career Fair 2026</strong> on <strong>October 30, 2026</strong>.</p>
                    <p>Students are encouraged to bring updated CVs and dress in professional business attire. On-the-spot internship and graduate trainee interviews will be conducted.</p>
                """,
            },
            {
                "name": "Student Health Center: Seasonal Flu Vaccination & Health Checkups",
                "date": datetime.date(2026, 9, 26),
                "notice_type": "facility",
                "priority": "low",
                "target_audience": "all",
                "pinned": False,
                "department_id": False,
                "author_name": "Campus Medical Center",
                "content": """
                    <p>The University Health & Wellness Center is providing free seasonal influenza vaccinations and basic physical examinations for all registered students and university employees throughout the month of October.</p>
                    <p>Walk-in consultations are available daily from 08:30 AM to 04:30 PM at Clinic Room 105.</p>
                """,
            },
            {
                "name": "Graduation Gown Measurements & Commencement Ceremony Registration",
                "date": datetime.date(2026, 9, 24),
                "notice_type": "administrative",
                "priority": "high",
                "target_audience": "graduating",
                "pinned": False,
                "department_id": False,
                "author_name": "Graduation Committee",
                "content": """
                    <p>Prospective graduates of the Class of 2026 must complete formal registration for the upcoming <strong>Commencement Ceremony</strong> and submit academic regalia gown sizing by <strong>November 15, 2026</strong>.</p>
                    <p>Ensure that all graduation audit clearances (library returns, financial accounting, and transcript verifications) are finalized beforehand.</p>
                """,
            },
            {
                "name": "King's Coronation Day Campus Observance Announcement",
                "date": datetime.date(2026, 9, 22),
                "notice_type": "holiday",
                "priority": "medium",
                "target_audience": "all",
                "pinned": False,
                "department_id": False,
                "author_name": "University Administration",
                "content": """
                    <p>The University announces that campus operations will be suspended on <strong>Thursday, October 29, 2026</strong> in observance of the <strong>Coronation Day of His Majesty King Norodom Sihamoni</strong>.</p>
                    <p>Regular academic schedules resume on Friday, October 30, 2026.</p>
                """,
            },
        ]

        # 1. Update existing notices if present
        existing_notices = env['university.notice.board'].search([])
        print(f"Existing notices in DB: {len(existing_notices)}")
        
        # Categorize the existing 4 notices
        name_updates = {
            "Datesheet Announcement": {
                "notice_type": "exam", "priority": "high", "target_audience": "all", "pinned": True,
                "date": datetime.date(2026, 10, 16), "author_name": "Office of Academic Affairs"
            },
            "Faculty General Assembly": {
                "notice_type": "event", "priority": "medium", "target_audience": "faculty", "pinned": False,
                "date": datetime.date(2026, 10, 14), "author_name": "Office of the Vice Chancellor"
            },
            "Midterm Examination Schedule": {
                "notice_type": "exam", "priority": "high", "target_audience": "students", "pinned": False,
                "date": datetime.date(2026, 10, 10), "author_name": "Examination Directorate"
            },
            "Spring Semester Course Registration": {
                "notice_type": "academic", "priority": "medium", "target_audience": "students", "pinned": False,
                "date": datetime.date(2026, 10, 5), "author_name": "University Registrar"
            },
        }

        for ex in existing_notices:
            if ex.name in name_updates:
                upd = name_updates[ex.name]
                ex.write(upd)
                c1, c2 = palettes[random.randint(0, len(palettes)-1)]
                ex.image_1920 = create_notice_banner(ex.name, upd["notice_type"], upd["priority"], c1, c2)
                print(f"  Enhanced existing notice: {ex.name}")

        # 2. Insert new comprehensive notices
        created_count = 0
        for idx, nd in enumerate(notices_data):
            already = env['university.notice.board'].search([('name', '=', nd["name"])], limit=1)
            if not already:
                c1, c2 = palettes[idx % len(palettes)]
                banner_b64 = create_notice_banner(nd["name"], nd["notice_type"], nd["priority"], c1, c2)
                
                vals = {
                    "name": nd["name"],
                    "date": nd["date"],
                    "notice_type": nd["notice_type"],
                    "priority": nd["priority"],
                    "target_audience": nd["target_audience"],
                    "pinned": nd.get("pinned", False),
                    "department_id": nd.get("department_id", False),
                    "author_name": nd.get("author_name", "University Administration"),
                    "content": nd["content"],
                    "academic_year_id": ay.id if ay else False,
                    "image_1920": banner_b64,
                    "color": (idx % 11) + 1,
                    "active": True,
                }
                rec = env['university.notice.board'].create(vals)
                created_count += 1
                print(f"  Created Notice [{rec.id}]: {rec.name} ({rec.notice_type}, {rec.priority})")

        cr.commit()
        total_now = env['university.notice.board'].search_count([])
        print(f"\n>>> SUCCESSFULLY CREATED {created_count} NEW NOTICES! Total on board now: {total_now} <<<")

if __name__ == "__main__":
    main()
