with open('views/program_views.xml', 'r', encoding='utf-8') as f:
    text = f.read()

target = '<field name="total_credits"/>\n                            <field name="active" widget="boolean_toggle"/>'
replacement = '<field name="total_credits"/>\n                            <field name="min_graduation_grade_id"/>\n                            <field name="active" widget="boolean_toggle"/>'
assert target in text, 'target not found'
text = text.replace(target, replacement, 1)
with open('views/program_views.xml', 'w', encoding='utf-8', newline='') as f:
    f.write(text)
print('Updated views/program_views.xml successfully')
