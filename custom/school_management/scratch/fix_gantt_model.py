import os

path = 'custom/school_management/models/timetable.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == 'Teacher = self.env["university.teacher"].sudo()':
        new_lines.append('        Resource = self.env["resource.resource"].sudo()\n')
        new_lines.append(line)
    else:
        new_lines.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Inserted Resource = self.env["resource.resource"].sudo()')
