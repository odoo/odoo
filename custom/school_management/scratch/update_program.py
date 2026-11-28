with open('models/program.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '    total_credits = fields.Integer(string="Total Credits Required", default=120, tracking=True)\n'
replacement = target + '''    min_graduation_grade_id = fields.Many2one(
        "university.grade.scale.line",
        string="Minimum Graduation Grade",
        help="Minimum passing grade required for graduation. If not set, falls back to the lowest passing scale line.",
        tracking=True,
    )\n'''
assert target in text, 'target not found'
text = text.replace(target, replacement, 1)
with open('models/program.py', 'w', encoding='utf-8', newline='') as f:
    f.write(text)
print('Updated models/program.py successfully')
