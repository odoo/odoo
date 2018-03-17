# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ExamExam(models.Model):
    _name = 'exam.exam'
    _description = 'Exam Information'

    @api.model
    def create(self, vals):
        academic_year = self.env['school.academic.year'].browse(vals.get('academic_year_id'))
        term = self.env['school.academic.term'].browse(vals.get('academic_term_id'))
        vals.update({'reference': str(academic_year.code)+str(term.code),
                     })
        return super(ExamExam, self).create(vals)

    @api.multi
    def write(self, vals):
        academic_year = self.env['school.academic.year'].browse(vals.get('academic_year_id')) or self.academic_year_id
        term = self.env['school.academic.term'].browse(vals.get('academic_term_id')) or self.academic_term_id
        vals.update({'reference': str(academic_year.code)+str(term.code),
                     })
        return super(ExamExam, self).write(vals)

    @api.constrains('start_date', 'end_date')
    def check_date_exam(self):
        '''Method to check constraint of exam start date and end date'''
        for rec in self:
            if rec.end_date < rec.start_date:
                raise ValidationError(_('Exam end date should be \
                                  greater than start date!'))
            if rec.exam_timetable_id.timetable_ids:
                for line in rec.exam_timetable_id.timetable_ids:
                    if not rec.start_date <= line.start_datetime <= rec.end_date:
                        raise ValidationError(_('Invalid Exam Schedule\
                        \n\nExam Dates must be in between Start\
                        date and End date !'))

    @api.constrains('active')
    def check_active(self):
        '''if exam results is not in done state then raise an
        validation Warning'''
        result_obj = self.env['exam.result']
        if not self.active:
            for result in result_obj.search([('exam_id', '=', self.id)]):
                if result.state != 'done':
                    raise ValidationError(_('Kindly,mark as done %s\
                    examination results') % (self.name))

    @api.one
    @api.depends('academic_year_id', 'academic_term_id')
    def compute_name(self):
        for rec in self:
            if self.academic_term_id:
                rec.name = str(rec.academic_year_id.code)+" " + str(rec.academic_term_id.name) + " Exam"

    active = fields.Boolean('Active', default="True")
    name = fields.Char("Exam Name", compute='compute_name', store=True,
                       help="Name of Exam")
    exam_code = fields.Char('Exam Code', required=True, readonly=True,
                            help="Code of exam",
                            default=lambda obj:
                            obj.env['ir.sequence'].next_by_code('exam.exam'))
    start_date = fields.Date("Exam Start Date",
                             help="Exam will start from this date")
    end_date = fields.Date("Exam End date", help="Exam will end at this date")
    state = fields.Selection([('draft', 'Draft'),
                              ('running', 'Running'),
                              ('finished', 'Finished'),
                              ('cancelled', 'Cancelled')], 'State',
                             readonly=True, default='draft')
    grade_system = fields.Many2one('grade.master', "Grade System",
                                   help="Select Grade System")
    academic_year_id = fields.Many2one('school.academic.year', 'Academic Year',
                                    help="Select Academic Year", required=True)
    academic_term_id = fields.Many2one('school.academic.term', 'Academic Term',
                                    help="Select Academic Term", required=True)
    exam_timetable_id = fields.Many2one('time.table', "Exam Timetable")
    reference = fields.Char('Unique Reference', readonly=True, index=True)

    _sql_constraints = [
        ('reference_unique', 'UNIQUE (reference)', 'Exam must be unique.'),
    ]


    @api.multi
    def set_to_draft(self):
        '''Method to set state to draft'''
        self.write({'state': 'draft'})
        return True

    @api.multi
    def set_running(self):
        '''Method to set state to running'''
        self.write({'state': 'running'})
        return True

    @api.multi
    def set_finish(self):
        '''Method to set state to finish'''
        for rec in self:
            rec.write({'state': 'finished'})
        return True

    @api.multi
    def set_cancel(self):
        '''Method to set state to cancel'''
        for rec in self:
            rec.write({'state': 'cancelled'})
        return True

    @api.multi
    def _validate_date(self):
        '''Method to check start date should be less than end date'''
        for exm in self:
            if exm.start_date > exm.end_date:
                return False
        return True

    @api.multi
    def make_results(self):
        student_obj = self.env['school.student']
        result_obj = self.env['exam.result']
        result_list = []
        for rec in self:
            domain = [('state', '=', 'admitted'), ('can_take_exam', '=', True)]
            student_ids = student_obj.search(domain)
            for student in student_ids:
                if self.id not in [result.exam_id.id for result in student.exam_result_ids]:
                    result = result_obj.create({
                        'exam_id': rec.id,
                        'student_id': student.id,
                        'academic_year_id': self.academic_year_id.id,
                        'academic_term_id': self.academic_term_id.id,
                    })
                    result_list.append(result.id)
        return {'name': _('Result Info'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'exam.result',
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', result_list)]}


class ExamResult(models.Model):
    _name = 'exam.result'
    _rec_name = 'student_pid'
    _description = 'exam result Information'

    @api.multi
    @api.depends('result_ids', 'result_ids.obtain_marks')
    def _compute_total(self):
        '''Method to compute total'''
        for rec in self:
            total = 0.0
            if rec.result_ids:
                for line in rec.result_ids:
                    total += line.obtain_marks
            rec.total = total

    @api.multi
    @api.depends('total')
    def _compute_per(self):
        '''Method to compute percentage'''
        total = 0.0
        obtained_total = 0.0
        per = 0.0
        for result in self:
            for sub_line in result.result_ids:
                total += sub_line.maximum_marks or 0
                obtained_total += sub_line.obtain_marks
            if total > 1.0:
                per = (obtained_total / total) * 100
            result.percentage = per
        return True

    @api.multi
    @api.depends('percentage')
    def _compute_result(self):
        '''Method to compute result'''
        for rec in self:
            if rec.percentage >= rec.student_id.form_id.passing_mark:
                rec.result = 'pass'
            else:
                rec.result = 'fail'

    @api.model
    def create(self, vals):
        if vals.get('student_id'):
            student = self.env['school.student'].browse(vals.get('student_id'))
            vals.update({'student_pid': student.pid,
                         'form_id': student.form_id.id,
                         'class_id': student.class_id.id,
                         'classroom_id': student.classroom_id.id
                         })
        return super(ExamResult, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('student_id'):
            student = self.env['school.student'].browse(vals.get('student_id'
                                                                  ))
            vals.update({'student_pid': student.pid,
                         'form_id': student.form_id.id,
                         'class_id': student.class_id.id,
                         'classroom_id': student.classroom_id.id
                         })
        return super(ExamResult, self).write(vals)

    @api.onchange('student_id')
    def onchange_student(self):
        if self.student_id:
            self.form_id = self.student_id.form_id.id
            self.class_id = self.student_id.class_id.id
            self.student_pid = self.student_id.pid

    exam_id = fields.Many2one("exam.exam", "Examination", required=True,
                                 help="Select Exam")
    student_id = fields.Many2one("school.student", "Student Name",
                                 required=True,
                                 help="Select Student")
    student_pid = fields.Char(string="Student ID",
                                readonly=True)
    result_ids = fields.One2many("exam.subject", "exam_id", "Exam Subject Results")
    total = fields.Float(compute='_compute_total', string='Obtain Total',
                         store=True, help="Total of marks")
    percentage = fields.Float("Percentage", compute="_compute_per",
                              store=True,
                              help="Percentage Obtained")
    result = fields.Selection([('pass', 'Pass'),
                               ('fail', 'Fail')],
                              compute='_compute_result', string='Result',
                            store=True, help="Result Obtained")
    state = fields.Selection([('draft', 'Draft'),
                              ('confirm', 'Confirm'),
                              ('re-evaluation', 'Re-Evaluation'),
                              ('re-evaluation_confirm',
                               'Re-Evaluation Confirm'),
                              ('published', 'Published')],
                             'State', readonly=True, default='draft')
    color = fields.Integer('Color')
    grade_system = fields.Many2one('grade.master', "Grade System",
                                   help="Grade System selected")
    form_id = fields.Many2one('school.form', 'Form')
    class_id = fields.Many2one('school.class', 'Class')
    classroom_id = fields.Many2one('school.classroom', 'Class')
    academic_year_id = fields.Many2one('school.academic.year', 'Academic Year',
                                    help="Select Academic Year", required=True)
    academic_term_id = fields.Many2one('school.academic.term', 'Academic Term',
                                    help="Select Academic Term", required=True)
    school_type = fields.Selection([('primary', 'Primary'),
                                    ('secondary', 'Secondary')],
                                   default=lambda obj: obj.env.user.company_id.school_type,
                                   required=True,
                                   readonly=True
                                   )

    @api.multi
    def result_confirm(self):
        '''Method to confirm result'''
        for rec in self:
            delta = list(set([subject for subject in rec.student_id.subject_ids]) - set([result.subject_id for result in rec.result_ids]))
            if len(delta) == 0:
                for line in rec.result_ids:
                    if line.maximum_marks == 0:
                        # Check subject marks not greater than maximum marks
                        raise ValidationError(_('Kindly add maximum\
                                marks of subject "%s".') % (line.subject_id.name))
                vals = {'percentage': rec.percentage,
                        'state': 'confirm'
                        }
                rec.write(vals)
            else:
                remaining = [subject.name for subject in delta]
                raise ValidationError('Student result is not complete! student needs result for '
                                      'the following subjetcs  - \n%s' % (', '.join(remaining)))
        return True

    @api.multi
    def re_evaluation_confirm(self):
        '''Method to change state to re_evaluation_confirm'''
        for rec in self:
            rec.state = 're-evaluation_confirm'
        return True

    @api.multi
    def result_re_evaluation(self):
        '''Method to set state to re-evaluation'''
        for rec in self:
            for line in rec.result_ids:
                line.marks_reeval = line.obtain_marks
            rec.state = 're-evaluation'
        return True

    @api.multi
    def set_done(self):
        '''Method to obtain history of student'''
        for rec in self:
            rec.write({'state': 'published'})
        return True


class ExamSubject(models.Model):
    _name = "exam.subject"
    _description = 'Exam Subject Information'
    _rec_name = 'subject_id'

    @api.constrains('obtain_marks', 'minimum_marks')
    def _validate_marks(self):
        # Method to validate marks
        min_mark = self.minimum_marks > self.maximum_marks
        if self.obtain_marks > self.maximum_marks or min_mark:
            raise ValidationError(_('The obtained marks and minimum marks\
                              should not extend maximum marks.'))

    exam_id = fields.Many2one('exam.result', 'Result', required=True)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'),
                              ('re-evaluation', 'Re-Evaluation'),
                              ('re-evaluation_confirm',
                               'Re-Evaluation Confirm')],
                             related='exam_id.state', string="State")
    subject_id = fields.Many2one("school.subject", "Subject Name", required=True)
    student_id = fields.Many2one("school.student", "Student Name",
                                 required=True,
                                 help="Select Student")
    form_id = fields.Many2one('school.form', related='student_id.form_id')
    obtain_marks = fields.Float("Obtain Marks", group_operator="avg", required=True)
    minimum_marks = fields.Float("Minimum Marks",
                                 help="Minimum Marks of subject")
    maximum_marks = fields.Float("Maximum Marks",
                                 help="Maximum Marks of subject")
    source = fields.Selection([('created', 'Created'),
                               ('imported', 'Imported')],
                              default='created', readonly=True)


class SchoolStudent(models.Model):
    _inherit = 'school.student'
    exam_result_ids = fields.One2many('exam.result', 'student_id', 'Exam Results')


class ExamResultImport(models.Model):
    _name = 'exam.result.import'
    student_id = fields.Char('Student ID', required=True)
    exam_code = fields.Char('Exam code', required=True)
    subject_code = fields.Char('Subject Code', required=True)
    score = fields.Float('Score', required=True)
    imported = fields.Boolean('Imported', default=False, readonly=True)
