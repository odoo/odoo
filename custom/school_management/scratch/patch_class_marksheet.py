# -*- coding: utf-8 -*-
with open('models/class_section.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = '    def action_view_exams(self):'
addition = '''    def action_download_class_marksheet(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/university/class_marksheet/{self.id}/xlsx",
            "target": "self",
        }

    def action_print_class_marksheet_pdf(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/university/class_marksheet/{self.id}/pdf",
            "target": "self",
        }

'''
if target in content and 'def action_download_class_marksheet' not in content:
    idx = content.find(target)
    new_content = content[:idx] + addition + content[idx:]
    with open('models/class_section.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Successfully added action_download_class_marksheet and action_print_class_marksheet_pdf')
else:
    print('Already present or target not found')
