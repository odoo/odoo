path = r"custom\school_management\models\student.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = '    @api.constrains("program_id", "department_id")'
addition = '''    @api.constrains("date_of_birth")
    def _check_date_of_birth(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.date_of_birth:
                if rec.date_of_birth > today:
                    raise ValidationError(_("Date of birth cannot be in the future."))
                try:
                    min_birth_date = today.replace(year=today.year - 15)
                except ValueError:
                    min_birth_date = today.replace(year=today.year - 15, day=28)
                if rec.date_of_birth > min_birth_date:
                    raise ValidationError(_("Student must be at least 15 years old for admission."))

    @api.constrains("program_id", "department_id")'''

if target in content:
    content = content.replace(target, addition, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("student.py updated successfully!")
else:
    print("Target not found!")
