# See LICENSE file for full copyright and licensing details.

from odoo.tests import common
import time


class TestSchool(common.TransactionCase):

    def setUp(self):
        super(TestSchool, self).setUp()
        self.student_student_obj = self.env['student.student']
        self.school_school_obj = self.env['school.school']
        self.school_standard_obj = self.env['school.standard']
        self.res_company_obj = self.env['res.company']
        self.assign_roll_obj = self.env['assign.roll.no']
        self.school_id = self.env.ref('school.demo_school_1')
        self.standard_medium = self.env.ref('school.demo_standard_medium_1')
        self.year = self.env.ref('school.demo_academic_year_2')
        self.currency_id = self.env.ref('base.INR')
        self.sch = self.env.ref('school.demo_school_1')
        self.country_id = self.env.ref('base.in')
        self.std = self.env.ref('school.demo_standard_standard_1')
        self.state_id = self.env.ref('base.state_in_gj')
        # Student created
        self.student_student = self.student_student_obj.\
            create({'pid': '2017/06/099',
                    'name': 'Jayesh',
                    'middle': 'R',
                    'last': 'Seth',
                    'school_id': self.school_id.id,
                    'year': self.year.id,
                    'standard_id': self.std.id,
                    'country_id': self.country_id.id,
                    'state_id': self.state_id.id,
                    'city': 'Gandhinagar',
                    'gender': 'male',
                    'date_of_birth': time.strftime('05-30-1993'),
                    'state': 'draft'
                    })
        self.student_student._compute_student_age()
        self.student_student.check_age()
        self.student_student.admission_done()
        self.student_student.set_alumni()
        self.hr_employee_obj = self.env['hr.employee']
        # Teacher created
        self.hr_employee = self.hr_employee_obj.\
            create({'name': 'Robert Smith',
                    'is_school_teacher': True,
                    'school': self.school_id.id,
                    'work_email': 'roberts@gmail.com'
                    })
        self.res_partner_obj = self.env['res.partner']
        # Partner Created
        self.res_partner = self.res_partner_obj.\
            create({'parent_school': True,
                    'name': 'Robert Martin',
                    'country_id': self.country_id.id,
                    'state_id': self.state_id.id,
                    'city': 'Gandhinagar',
                    'email': 'robertmartin@gmail.com'
                    })
        # Create academic Year
        self.academic_year_obj = self.env['academic.year']
        self.academic_year = self.academic_year_obj.\
            create({'sequence': 7,
                    'code': '2012',
                    'name': '2012 Year',
                    'date_start': time.strftime('01-01-2012'),
                    'date_stop': time.strftime('12-31-2012')
                    })
        self.academic_year._check_academic_year()
        self.academic_month_obj = self.env['academic.month']
        # Academic month created
        self.academic_month = self.academic_month_obj.\
            create({'name': 'May',
                    'code': 'may',
                    'date_start': time.strftime('05-01-2012'),
                    'date_stop': time.strftime('05-31-2012'),
                    'year_id': self.academic_year.id
                    })
        self.academic_month._check_duration()
        self.academic_month._check_year_limit()
        self.assign_roll_no = self.assign_roll_obj.\
            create({'standard_id': self.std.id,
                    'medium_id': self.standard_medium.id
                    })
        self.assign_roll_no.assign_rollno()

    def test_school(self):
        self.assertEqual(self.student_student.school_id,
                         self.student_student.standard_id.school_id)
