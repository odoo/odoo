path = 'custom/school_management/models/exam.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = '''    def action_download_marksheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/university/marksheet/{self.id}/xlsx',
            'target': 'self',
        }'''

replacement = '''    def action_download_marksheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/university/marksheet/{self.id}/xlsx',
            'target': 'self',
        }

    def action_print_marksheet_pdf(self):
        self.ensure_one()
        return self.env.ref("school_management.action_report_university_exam_marksheet").report_action(self)

    def action_download_marksheet_pdf(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/university/marksheet/{self.id}/pdf',
            'target': 'self',
        }'''

if 'def action_print_marksheet_pdf' not in content:
    assert target in content, "target not found in exam.py"
    content = content.replace(target, replacement, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Successfully added action_print_marksheet_pdf to exam.py')
else:
    print('Already present in exam.py')
