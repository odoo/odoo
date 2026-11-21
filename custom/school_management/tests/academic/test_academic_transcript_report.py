import datetime
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestAcademicTranscriptReport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.faculty = cls.env['university.faculty'].create({
            'name': 'Faculty of Business Testing',
            'code': 'FBUSTEST',
        })
        cls.department = cls.env['university.department'].create({
            'name': 'Department of Accounting Testing',
            'code': 'DACCTTEST',
            'faculty_id': cls.faculty.id,
        })
        cls.program = cls.env['university.program'].create({
            'name': 'Bachelor of Accounting Testing',
            'code': 'BACCTEST',
            'faculty_id': cls.faculty.id,
            'department_id': cls.department.id,
            'total_credits': 120,
        })

        cls.year_1 = cls.env['university.academic.year'].create({
            'name': '2030-2031 (Test AY1)',
            'date_start': '2030-09-01',
            'date_end': '2031-06-30',
        })
        cls.year_2 = cls.env['university.academic.year'].create({
            'name': '2031-2032 (Test AY2)',
            'date_start': '2031-09-01',
            'date_end': '2032-06-30',
        })

        cls.y1_s1 = cls.env['university.semester'].create({
            'name': '2030-2031 Semester 1',
            'semester_type': 'semester_1',
            'academic_year_id': cls.year_1.id,
            'date_start': '2030-09-01',
            'date_end': '2031-01-15',
        })
        cls.y1_s2 = cls.env['university.semester'].create({
            'name': '2030-2031 Semester 2',
            'semester_type': 'semester_2',
            'academic_year_id': cls.year_1.id,
            'date_start': '2031-02-01',
            'date_end': '2031-06-30',
        })
        cls.y2_s1 = cls.env['university.semester'].create({
            'name': '2031-2032 Semester 1',
            'semester_type': 'semester_1',
            'academic_year_id': cls.year_2.id,
            'date_start': '2031-09-01',
            'date_end': '2032-01-15',
        })
        cls.y2_s2 = cls.env['university.semester'].create({
            'name': '2031-2032 Semester 2',
            'semester_type': 'semester_2',
            'academic_year_id': cls.year_2.id,
            'date_start': '2032-02-01',
            'date_end': '2032-06-30',
        })

        cls.course_a = cls.env['university.subject'].create({
            'name': 'Financial Accounting I Test',
            'code': 'ACCT101TEST',
            'credits': 3,
        })
        cls.course_b = cls.env['university.subject'].create({
            'name': 'Business Law Test',
            'code': 'LAW101TEST',
            'credits': 3,
        })

    def test_student_dob_validation(self):
        """Test minimum age and future birthdate validation."""
        today = fields.Date.context_today(self.env.user)
        future_date = today + datetime.timedelta(days=10)
        with self.assertRaises(ValidationError):
            self.env['university.student'].create({
                'name': 'Future Student',
                'program_id': self.program.id,
                'date_of_birth': future_date,
            })

        # Under 15 years old
        too_young_date = today.replace(year=today.year - 10)
        with self.assertRaises(ValidationError):
            self.env['university.student'].create({
                'name': 'Child Student',
                'program_id': self.program.id,
                'date_of_birth': too_young_date,
            })

        # Valid age (20 years old)
        valid_date = today.replace(year=today.year - 20)
        student = self.env['university.student'].create({
            'name': 'Valid Adult Student',
            'program_id': self.program.id,
            'date_of_birth': valid_date,
        })
        self.assertTrue(student.id)

    def test_student_no_grades(self):
        """Test transcript calculation and report values for student with no grades."""
        student = self.env['university.student'].create({
            'name': 'No Grades Student',
            'program_id': self.program.id,
        })
        transcript = self.env['university.transcript'].create({
            'student_id': student.id,
        })
        self.assertEqual(transcript.total_credits, 0)
        self.assertEqual(transcript.cumulative_gpa, 0.0)

        report_model = self.env['report.school_management.report_university_transcript_document']
        values = report_model._get_report_values([transcript.id])
        self.assertEqual(values['total_credits'], 0)
        self.assertEqual(values['unweighted_gpa'], 0.0)
        self.assertEqual(values['years_data'], [])

    def test_two_years_and_retaken_course(self):
        """Test two academic years chronological order and retake repeat policy."""
        student = self.env['university.student'].create({
            'name': 'Two Year Retake Student',
            'program_id': self.program.id,
        })
        transcript = self.env['university.transcript'].create({
            'student_id': student.id,
        })

        # Year 1 Sem 2: Course A (B, 3.0), Course B (A, 4.0) -> Sem 1 is empty
        # Year 2 Sem 1: Course A (A, 4.0) -> Course A is repeated!
        self.env['university.transcript.line'].create([
            {
                'transcript_id': transcript.id,
                'academic_year_id': self.year_1.id,
                'semester_id': self.y1_s2.id,
                'subject_id': self.course_a.id,
                'credits': 3,
                'grade': 'B',
                'grade_point': 3.0,
                'is_passing': True,
            },
            {
                'transcript_id': transcript.id,
                'academic_year_id': self.year_1.id,
                'semester_id': self.y1_s2.id,
                'subject_id': self.course_b.id,
                'credits': 3,
                'grade': 'A',
                'grade_point': 4.0,
                'is_passing': True,
            },
            {
                'transcript_id': transcript.id,
                'academic_year_id': self.year_2.id,
                'semester_id': self.y2_s1.id,
                'subject_id': self.course_a.id,
                'credits': 3,
                'grade': 'A',
                'grade_point': 4.0,
                'is_passing': True,
            },
        ])

        transcript._compute_cumulative_gpa()
        transcript._compute_academic_standing()

        # Cumulative credits should count Course A only ONCE (3) + Course B (3) = 6 credits total (NOT 9)
        self.assertEqual(transcript.total_credits, 6)
        # Cumulative GPA should take Course A (4.0) and Course B (4.0) = 4.00 (NOT (3*3+3*4+3*4)/9 = 3.67)
        self.assertAlmostEqual(transcript.cumulative_gpa, 4.00, places=2)

        # Check Report Values
        report_model = self.env['report.school_management.report_university_transcript_document']
        values = report_model._get_report_values([transcript.id])

        # Verify years_data structure
        years_data = values['years_data']
        self.assertEqual(len(years_data), 2)

        # Oldest year (2030-2031) should be first and numbered Year 1
        self.assertEqual(years_data[0]['year_number'], 1)
        self.assertEqual(years_data[0]['year'].name, '2030-2031 (Test AY1)')

        # Sem 2 of Year 1 should have 6 credits and GPA 3.50
        self.assertEqual(years_data[0]['s2_credits'], 6)
        self.assertAlmostEqual(years_data[0]['s2_gpa'], 3.50, places=2)

        # Second year (2031-2032) should be second and numbered Year 2
        self.assertEqual(years_data[1]['year_number'], 2)
        self.assertEqual(years_data[1]['year'].name, '2031-2032 (Test AY2)')
        self.assertEqual(years_data[1]['s1_credits'], 3)
        self.assertEqual(years_data[1]['s1_gpa'], 4.0)

        # Repeated course detection
        self.assertTrue(len(values['repeated_line_ids']) >= 1)
