path = 'custom/school_management/controllers/exam_marksheet.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

pdf_method = '''
    @http.route(['/university/marksheet/<int:exam_id>/pdf'],
                type='http', auth='user', methods=['GET'])
    def download_marksheet_pdf(self, exam_id, **kwargs):
        exam = request.env['university.exam'].browse(exam_id).exists()
        if not exam:
            return request.not_found()
        try:
            exam.check_access('read')
        except AccessError:
            return request.not_found()

        pdf_content, _ct = request.env['ir.actions.report']._render_qweb_pdf(
            'school_management.action_report_university_exam_marksheet',
            res_ids=[exam.id],
        )

        clean_name = "".join(c for c in (exam.name or f"exam_{exam_id}") if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
        filename = f"marksheet_{clean_name}_{exam_id}.pdf"

        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
                ('Content-Length', str(len(pdf_content))),
            ],
        )
'''

if 'def download_marksheet_pdf' not in content:
    content = content + '\n' + pdf_method
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Successfully added download_marksheet_pdf')
else:
    print('Already present')
