from odoo.tests import common
from odoo.report import render_report
from odoo.tools import config
import os
import time


class TestExam(common.TransactionCase):

    def setUp(self):
        super(TestExam, self).setUp()
        self.additional_exam_obj = self.env['additional.exam']
        self.additional_exam_result_obj = self.env['additional.exam.result']
        self.exam_exam_obj = self.env['exam.exam']
        self.time_table_obj = self.env['time.table']
        self.exam_result_obj = self.env['exam.result']
        self.time_table_line_obj = self.env['time.table.line']
        self.exam_schedule_line_obj = self.env['exam.schedule.line']
        self.exam_subject_obj = self.env['exam.subject']
        self.hr_employee = self.env.ref('hr.employee_al')
        self.subject_id = self.env.ref('school.demo_subject_subject_1')
        self.std = self.env.ref('school.demo_standard_standard_1')
        self.standards = self.env.ref('school.demo_school_standard_1')
        self.student = self.env.ref('school.demo_student_student_7')
        self.subject_id = self.env.ref('school.demo_subject_subject_1')
        self.year_id = self.env.ref('school.demo_academic_year_2')
        self.grade_system = self.env.ref('school.demo_student_grade_1')
        self.standard_std = self.env.ref('school.demo_standard_standard_2')
        self.school_standard = self.env.ref('school.demo_school_standard_2')
        self.student_student = self.env.ref('school.demo_student_student_5')
        self.grade_line = self.env.ref('school.demo_student_grade_line_6')
        # Create Exam Timetable
        self.time_table = self.time_table_obj.\
            create({'name': 'Mid Term Exam',
                    'year_id': self.year_id.id,
                    'timetable_type': 'exam',
                    'standard_id': self.school_standard.id,
                    })
        # Create timetable line
        self.time_table_line = self.time_table_line_obj.\
            create({'exm_date': time.strftime('06-01-2017'),
                    'day_of_week': 'Thursday',
                    'subject_id': self.subject_id.id,
                    'start_time': 10.00,
                    'end_time': 12.00,
                    'teacher_id': self.hr_employee.id,
                    'table_id': self.time_table.id
                    })
        self.time_table_line.onchange_date_day()
        self.time_table_line._check_date()
        # Create Exam
        self.exam_exam = self.exam_exam_obj.\
            create({'exam_code': '2017/06/097',
                    'name': 'Mid Term Exam',
                    'academic_year': self.year_id.id,
                    'grade_system': self.grade_system.id,
                    'start_date': time.strftime('06-01-2017'),
                    'end_date': time.strftime('06-4-2017'),
                    'standard_id': [(6, 0, (self.standard_std.ids))]
                    })
        self.exam_schedule_line = self.exam_schedule_line_obj.\
            create({'standard_id': self.school_standard.id,
                    'timetable_id': self.time_table.id,
                    'exam_id': self.exam_exam.id
                    })
        self.exam_schedule_line.onchange_standard()
        self.exam_exam.check_date_exam()
        self.exam_exam.check_active()
        self.exam_exam.set_to_draft()
        self.exam_exam.set_running()
        self.exam_exam.set_finish()
        self.exam_exam.set_cancel()
        self.exam_exam._validate_date()
        self.exam_exam.generate_result()
        # Create exam result
        self.exam_result = self.exam_result_obj.\
            create({'s_exam_ids': self.exam_exam.id,
                    'student_id': self.student_student.id,
                    'standard_id': self.school_standard.id,
                    'roll_no_id': 2,
                    'grade_system': self.grade_system.id,
                    'total': 80,
                    'percentage': 40,
                    'grade': 'B-',
                    'result': 'Pass'
                    })
        self.exam_result. _compute_total()
        self.exam_result._compute_per()
        self.exam_result._compute_result()
        self.exam_result.onchange_student()
        self.exam_result.result_confirm()
        self.exam_result.re_evaluation_confirm()
        self.exam_result.result_re_evaluation()
        self.exam_result.set_done()
        # Create Subject
        self.exam_subject = self.exam_subject_obj.\
            create({'subject_id': self.subject_id.id,
                    'maximum_marks': 100,
                    'minimum_marks': 35,
                    'obtain_marks': 40,
                    'grade_line_id': self.grade_line.id,
                    'marks_reeval': 40,
                    'exam_id': self.exam_result.id
                    })
        self.exam_subject._compute_grade()
        self.exam_subject._validate_marks()
        # Create additional exam
        self.additional_exam = self.additional_exam_obj.\
            create({'additional_exam_code': '2017/06/098',
                    'standard_id': self.std.id,
                    'name': 'New Additional Exam',
                    'subject_id': self.subject_id.id,
                    'maximum_marks': 100,
                    'minimum_marks': 35,
                    'exam_date': time.strftime('06-30-2012'),
                    'create_date': time.strftime('03-31-2012'),
                    'write_date': time.strftime('05-30-2012'),
                    })
        # Create additional exam result
        self.additional_exam_result = self.additional_exam_result_obj.\
            create({'a_exam_id': self.additional_exam.id,
                    'student_id': self.student.id,
                    'obtain_marks': 65,
                    'result': 'Pass'
                    })
        self.additional_exam_result.onchange_student()
        self.additional_exam_result._validate_marks()
        self.additional_exam_result._compute_student_result()
        data, format = render_report(self.env.cr, self.env.uid,
                                     self.additional_exam_result.ids,
                                     'exam.additional_exam_result_report', {},
                                     {})
        if config.get('test_report_directory'):
            file(os.path.join(config['test_report_directory'],
                 'Additional Exam Result.' + format),
                 'wb+').write(data)

    def test_exam(self):
        self.assertEqual(self.additional_exam_result.student_id.state, 'done')
        self.assertEqual(self.exam_result.student_id.state, 'done')
        self.assertEqual(self.exam_schedule_line.timetable_id.timetable_type,
                         'exam')
        self.assertEqual(self.exam_schedule_line.timetable_id.year_id.id,
                         self.exam_exam.academic_year.id)
        self.assertEqual(self.exam_schedule_line.timetable_id.standard_id.id,
                         self.exam_schedule_line.standard_id.id)
        self.assertIn(self.exam_schedule_line.standard_id.id,
                      self.exam_exam.standard_id.ids)
