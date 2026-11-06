path = 'custom/school_management/views/exam_views.xml'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

target = '''                    <button name="%(school_management.action_report_university_exam_marksheet)d"
                            string="Print PDF"
                            type="action"'''

replacement = '''                    <button name="action_print_marksheet_pdf"
                            string="Print PDF"
                            type="object"'''

if target in text:
    text = text.replace(target, replacement, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    print('Updated Print PDF button to type=object')
else:
    print('Target not found or already updated')
