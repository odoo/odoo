from odoo import models, api, fields, _
from odoo.exceptions import Warning


class GradeImporter(models.TransientModel):
    _name = 'wiz.grade.importer'

    student_ids = fields.Many2many('school.student')
    form_ids = fields.Many2many('school.form')
    classroom_ids = fields.Many2many('school.classroom')
    subject_ids = fields.Many2many('school.subject')
    exam_id = fields.Many2one('exam.exam', string='Examination',
                              required=True,
                              help='Select Examination to import grade for')

    @api.onchange('student_ids')
    def onchange_student(self):
        self.form_ids = False
        self.classroom_ids = False
        self.subject_ids = False

    @api.onchange('form_ids')
    def onchange_form(self):
        self.student_ids = False
        self.classroom_ids = False
        self.subject_ids = False

    @api.onchange('classroom_ids')
    def onchange_classroom(self):
        self.student_ids = False
        self.form_ids = False
        self.subject_ids = False

    @api.onchange('subject_ids')
    def onchange_subject(self):
        self.student_ids = False
        self.form_ids = False
        self.classroom_ids = False

    @api.multi
    def import_grades(self):
        self.ensure_one()
        import_obj = self.env['exam.result.import']
        subject_obj = self.env['exam.subject']
        result_object = self.env['exam.result']
        subject_object = self.env['school.subject']

        for rec in self:
            if rec.student_ids:
                for student in rec.student_ids:
                    domain = [('exam_code', '=', self.exam_id.exam_code),
                              ('student_id', '=', student.pid),
                              ('imported', '=', False)]
                    grades = import_obj.search(domain)
                    exam_result = result_object.search([('exam_id', '=', self.exam_id.id), ('student_id', '=', student.id)])
                    for grade in grades:
                        subject_id = subject_object.search([('code', '=', grade.subject_code)])
                        if subject_id in [result.subject_id for result in exam_result.result_ids]:
                            pass
                        if subject_id in student.subject_ids:
                            subject_obj.create({
                                'exam_id': exam_result.id,
                                'subject_id': subject_id.id,
                                'student_id': student.id,
                                'obtain_marks': grade.score,
                                'minimum_marks': subject_id.minimum_marks,
                                'maximum_marks': subject_id.maximum_marks,
                                'source': 'imported'

                            })
                            grade.imported = True
            if rec.form_ids:
                student_ids = []
                for form in rec.form_ids:
                    for student in form.student_ids:
                        student_ids.append(student)
                for students in student_ids:
                    for student in students:
                        domain = [('exam_code', '=', self.exam_id.exam_code),
                                  ('student_id', '=', student.pid),
                                  ('imported', '=', False)]
                        grades = import_obj.search(domain)
                        exam_result = result_object.search([('exam_id', '=', self.exam_id.id), ('student_id', '=', student.id)])
                        for grade in grades:
                            subject_id = subject_object.search([('code', '=', grade.subject_code)])
                            if subject_id in [result.subject_id for result in exam_result.result_ids]:
                                pass
                            if subject_id in student.subject_ids:
                                subject_obj.create({
                                    'exam_id': exam_result.id,
                                    'subject_id': subject_id.id,
                                    'student_id': student.id,
                                    'obtain_marks': grade.score,
                                    'minimum_marks': subject_id.minimum_marks,
                                    'maximum_marks': subject_id.maximum_marks,
                                    'source': 'imported'

                                })
                                grade.imported = True
            if rec.classroom_ids:
                student_ids = []
                for classroom in rec.classroom_ids:
                    for student in classroom.student_ids:
                        student_ids.append(student)
                for students in student_ids:
                    for student in students:
                        domain = [('exam_code', '=', self.exam_id.exam_code),
                                  ('student_id', '=', student.pid),
                                  ('imported', '=', False)]
                        grades = import_obj.search(domain)
                        exam_result = result_object.search([('exam_id', '=', self.exam_id.id), ('student_id', '=', student.id)])
                        for grade in grades:
                            subject_id = subject_object.search([('code', '=', grade.subject_code)])
                            if subject_id in [result.subject_id for result in exam_result.result_ids]:
                                pass
                            if subject_id in student.subject_ids:
                                subject_obj.create({
                                    'exam_id': exam_result.id,
                                    'subject_id': subject_id.id,
                                    'student_id': student.id,
                                    'obtain_marks': grade.score,
                                    'minimum_marks': subject_id.minimum_marks,
                                    'maximum_marks': subject_id.maximum_marks,
                                    'source': 'imported'

                                })
                                grade.imported = True
            if rec.subject_ids:
                student_ids = []
                for subject in rec.subject_ids:
                    for student in subject.student_ids:
                        student_ids.append(student)
                for students in student_ids:
                    for student in students:
                        domain = [('exam_code', '=', self.exam_id.exam_code),
                                  ('student_id', '=', student.pid),
                                  ('imported', '=', False)]
                        grades = import_obj.search(domain)
                        exam_result = result_object.search([('exam_id', '=', self.exam_id.id), ('student_id', '=', student.id)])
                        for grade in grades:
                            subject_id = subject_object.search([('code', '=', grade.subject_code)])
                            if subject_id in [result.subject_id for result in exam_result.result_ids]:
                                pass
                            if subject_id in student.subject_ids:
                                subject_obj.create({
                                    'exam_id': exam_result.id,
                                    'subject_id': subject_id.id,
                                    'student_id': student.id,
                                    'obtain_marks': grade.score,
                                    'minimum_marks': subject_id.minimum_marks,
                                    'maximum_marks': subject_id.maximum_marks,
                                    'source': 'imported'

                                })
                                grade.imported = True
