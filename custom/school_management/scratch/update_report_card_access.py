with open('custom/school_management/security/ir.model.access.csv', 'r', encoding='utf-8') as f:
    csv_text = f.read()

new_rows = """access_university_report_card_teacher,university.report.card.teacher,model_university_report_card,school_management.group_university_teacher,1,0,0,0
access_university_report_card_line_teacher,university.report.card.line.teacher,model_university_report_card_line,school_management.group_university_teacher,1,0,0,0
"""

if 'access_university_report_card_teacher' not in csv_text:
    csv_text = csv_text.strip() + '\n' + new_rows
    with open('custom/school_management/security/ir.model.access.csv', 'w', encoding='utf-8', newline='') as f:
        f.write(csv_text)
    print('Added report card read access to CSV')

with open('custom/school_management/models/student.py', 'r', encoding='utf-8') as f:
    st_text = f.read()

old_needle = 'self.env["university.report.card"]._read_group('
new_needle = 'self.env["university.report.card"].sudo()._read_group('
if old_needle in st_text:
    st_text = st_text.replace(old_needle, new_needle)
    with open('custom/school_management/models/student.py', 'w', encoding='utf-8', newline='') as f:
        f.write(st_text)
    print('Updated student.py to use sudo on report card read_group')
