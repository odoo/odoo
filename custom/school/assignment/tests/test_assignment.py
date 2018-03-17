# See LICENSE file for full copyright and licensing details.

from odoo.tests import common
import time


class TestAssignment(common.TransactionCase):

    def setUp(self):
        super(TestAssignment, self).setUp()
        self.teacher_assignment_obj = self.env['school.teacher.assignment']
        self.student_assignment_obj = self.env['school.student.assignment']
        self.teacher_id = self.env.ref('hr.employee_qdp')
        self.subject_id = self.env.ref('school.demo_subject_subject_3')
        self.stander_id = self.env.ref('school.demo_standard_standard_1')

#        Create Teacher Assignment
        self.school_teacher_assignment = self.teacher_assignment_obj.\
            create({'name': 'Test Product Packaging',
                    'teacher_id': self.teacher_id.id,
                    'subject_id': self.subject_id.id,
                    'standard_id': self.stander_id.id,
                    'assign_date': time.strftime('%Y-%m-%d'),
                    'due_date': time.strftime('%Y-%m-%d'),
                    })
        self.school_teacher_assignment.active_assignment()

    def test_assignment(self):
        self.assertEqual(self.school_teacher_assignment.teacher_id.subject_ids,
                         self.subject_id)
        student_assign_ids = self.school_teacher_assignment.student_assign_ids
        for student in student_assign_ids:
            student.done_assignment()
            self.assertEqual('done', student.state)
