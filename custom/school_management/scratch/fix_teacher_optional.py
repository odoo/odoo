model_file = "custom/school_management/models/timetable.py"
with open(model_file, "r", encoding="utf-8") as f:
    text = f.read()

target = 'teacher_id = fields.Many2one("university.teacher", string="Teacher", required=True, index=True)'
replacement = 'teacher_id = fields.Many2one("university.teacher", string="Teacher", required=False, index=True)'

if target in text:
    text = text.replace(target, replacement, 1)
    with open(model_file, "w", encoding="utf-8") as f:
        f.write(text)
    print("Changed teacher_id required=False in timetable.py")
else:
    print("Warning: target teacher_id not found")
