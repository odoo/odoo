# -*- coding: utf-8 -*-
with open('views/class_section_views.xml', 'r', encoding='utf-8') as f:
    content = f.read()

target = '''                    <button name="action_view_schedule"
                            string="View Interactive Schedule"
                            type="object"
                            class="btn-outline-primary"
                            icon="fa-calendar"/>'''

addition = '''
                    <button name="action_download_class_marksheet"
                            string="Marksheet (Excel)"
                            type="object"
                            class="btn-outline-success"
                            icon="fa-file-excel-o"/>
                    <button name="action_print_class_marksheet_pdf"
                            string="Marksheet (PDF)"
                            type="object"
                            class="btn-outline-danger"
                            icon="fa-file-pdf-o"/>'''

if target in content and 'name="action_download_class_marksheet"' not in content:
    idx = content.find(target) + len(target)
    new_content = content[:idx] + addition + content[idx:]
    with open('views/class_section_views.xml', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Successfully added marksheet buttons to class_section_views.xml')
else:
    print('Target not found or already present')
