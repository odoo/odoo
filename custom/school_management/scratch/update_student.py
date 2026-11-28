with open('models/student.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''            # 2. Failed Subjects
            cards = student.report_card_ids.filtered(lambda c: c.state in ("generated", "approved"))
            failed_count = sum(1 for c in cards for line in c.line_ids if not line.is_passing)'''

replacement = '''            # 2. Failed Subjects & Graduation Standard
            cards = student.report_card_ids.filtered(lambda c: c.state in ("generated", "approved"))
            min_grad = student.program_id.min_graduation_grade_id
            if min_grad:
                failed_count = sum(1 for c in cards for line in c.line_ids if not line.is_passing or line.grade_point < min_grad.grade_point)
            else:
                failed_count = sum(1 for c in cards for line in c.line_ids if not line.is_passing)'''

assert target in text, 'target not found'
text = text.replace(target, replacement, 1)

with open('models/student.py', 'w', encoding='utf-8', newline='') as f:
    f.write(text)
print('Updated models/student.py successfully')
