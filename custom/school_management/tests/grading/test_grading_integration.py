from datetime import date, timedelta
from odoo.tests.common import TransactionCase


class TestGradingIntegration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.AcademicYear = self.env["university.academic.year"]
        self.Semester = self.env["university.semester"]
        self.GradeScale = self.env["university.grade.scale"]
        self.GradeScaleLine = self.env["university.grade.scale.line"]
        self.Category = self.env["university.assessment.category"]
        self.Faculty = self.env["university.faculty"]
        self.Department = self.env["university.department"]
        self.Program = self.env["university.program"]
        self.Subject = self.env["university.subject"]
        self.Student = self.env["university.student"]
        self.Section = self.env["university.class.section"]
        self.Enrollment = self.env["university.enrollment"]
        self.Attendance = self.env["university.attendance"]
        self.AssessmentResult = self.env["university.assessment.result"]
        self.ReportCard = self.env["university.report.card"]
        self.Transcript = self.env["university.transcript"]

        # Academic Year & Semester
        self.academic_year = self.AcademicYear.create({
            "name": "2026-2027 Test",
            "date_start": "2026-01-01",
            "date_end": "2026-12-31",
        })
        self.semester = self.Semester.create({
            "name": "Semester 1 Test",
            "academic_year_id": self.academic_year.id,
            "semester_type": "semester_1",
            "date_start": "2026-01-01",
            "date_end": "2026-04-23",
        })

        # Grade Scale
        self.grade_scale = self.GradeScale.create({"name": "Standard Test 4.0 Scale"})
        lines = [
            ("A+", 95.0, 100.0, 4.0, True),
            ("A", 90.0, 94.99, 4.0, True),
            ("A-", 85.0, 89.99, 3.67, True),
            ("B+", 80.0, 84.99, 3.33, True),
            ("B", 75.0, 79.99, 3.0, True),
            ("B-", 70.0, 74.99, 2.67, True),
            ("C+", 65.0, 69.99, 2.33, True),
            ("C", 60.0, 64.99, 2.0, True),
            ("C-", 55.0, 59.99, 1.67, False),
            ("D+", 50.0, 54.99, 1.33, False),
            ("D", 45.0, 49.99, 1.0, False),
            ("F", 0.0, 44.99, 0.0, False),
        ]
        for name, min_s, max_s, gp, passing in lines:
            self.GradeScaleLine.create({
                "scale_id": self.grade_scale.id,
                "name": name,
                "min_score": min_s,
                "max_score": max_s,
                "grade_point": gp,
                "is_passing": passing,
            })

        # Categories
        self.cat_quiz = self.Category.create({"name": "Quiz", "code": "QUIZ", "weight": 10.0})
        self.cat_mid = self.Category.create({"name": "Midterm Exam", "code": "MID", "weight": 20.0})
        self.cat_assign = self.Category.create({"name": "Assignment", "code": "ASSIGN", "weight": 10.0})
        self.cat_final = self.Category.create({"name": "Final Exam", "code": "FINAL", "weight": 50.0})

        # Academic hierarchy
        self.faculty = self.Faculty.create({"name": "Engineering Faculty", "code": "ENG-TEST"})
        self.dept = self.Department.create({"name": "CS Dept", "code": "CSD-TEST", "faculty_id": self.faculty.id})
        self.program = self.Program.create({"name": "Software Engineering", "code": "SE-TEST", "department_id": self.dept.id})
        self.subject = self.Subject.create({
            "name": "Advanced Software Architecture",
            "code": "CS401-T",
            "department_id": self.dept.id,
            "credits": 3,
        })

        # Student & Section & Enrollment
        self.student = self.Student.create({
            "name": "Alex Test Student",
            "program_id": self.program.id,
            "email": "alex_test@univ.edu",
        })
        self.section = self.Section.create({
            "name": "CS401-T-Sec01",
            "subject_id": self.subject.id,
            "program_id": self.program.id,
            "semester_id": self.semester.id,
        })
        self.enrollment = self.Enrollment.create({
            "student_id": self.student.id,
            "program_id": self.program.id,
            "section_id": self.section.id,
            "semester_id": self.semester.id,
            "academic_year_id": self.academic_year.id,
            "status": "enrolled",
        })

    def test_attendance_weighted_grading_and_report_card(self):
        """Test full attendance-to-grade equivalence, multi-quiz averaging, and report card rollup."""
        # Setup Attendance: 3 absents, 5 excused, 7 lates
        # Formula: 3 + (5//2 = 2) + (7//4 = 1) = 6 effective absences
        # Attendance score: 10 - 6 = 4.0 / 10.0
        base_date = date.today()
        day_offset = 0

        for _ in range(3):
            day_offset += 1
            self.Attendance.create({
                "student_id": self.student.id,
                "section_id": self.section.id,
                "date": base_date - timedelta(days=day_offset),
                "status": "absent",
            })
        for _ in range(5):
            day_offset += 1
            self.Attendance.create({
                "student_id": self.student.id,
                "section_id": self.section.id,
                "date": base_date - timedelta(days=day_offset),
                "status": "excused",
            })
        for _ in range(7):
            day_offset += 1
            self.Attendance.create({
                "student_id": self.student.id,
                "section_id": self.section.id,
                "date": base_date - timedelta(days=day_offset),
                "status": "late",
            })

        # Assessment Results:
        # Quiz 1: 80%, Quiz 2: 90% -> avg 85% -> 8.5 / 10
        self.AssessmentResult.create({
            "student_id": self.student.id,
            "subject_id": self.subject.id,
            "section_id": self.section.id,
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester.id,
            "category_id": self.cat_quiz.id,
            "score": 80.0,
            "max_score": 100.0,
            "state": "published",
        })
        self.AssessmentResult.create({
            "student_id": self.student.id,
            "subject_id": self.subject.id,
            "section_id": self.section.id,
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester.id,
            "category_id": self.cat_quiz.id,
            "score": 90.0,
            "max_score": 100.0,
            "state": "published",
        })
        # Midterm: 90% -> 18.0 / 20
        self.AssessmentResult.create({
            "student_id": self.student.id,
            "subject_id": self.subject.id,
            "section_id": self.section.id,
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester.id,
            "category_id": self.cat_mid.id,
            "score": 90.0,
            "max_score": 100.0,
            "state": "published",
        })
        # Assignment: 75% -> 7.5 / 10
        self.AssessmentResult.create({
            "student_id": self.student.id,
            "subject_id": self.subject.id,
            "section_id": self.section.id,
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester.id,
            "category_id": self.cat_assign.id,
            "score": 75.0,
            "max_score": 100.0,
            "state": "published",
        })
        # Final Exam: 82% -> 41.0 / 50
        self.AssessmentResult.create({
            "student_id": self.student.id,
            "subject_id": self.subject.id,
            "section_id": self.section.id,
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester.id,
            "category_id": self.cat_final.id,
            "score": 82.0,
            "max_score": 100.0,
            "state": "published",
        })

        # Generate Report Card
        card = self.ReportCard.create({
            "student_id": self.student.id,
            "academic_year_id": self.academic_year.id,
            "semester_id": self.semester.id,
            "grade_scale_id": self.grade_scale.id,
        })
        card.action_generate_lines()

        self.assertEqual(len(card.line_ids), 1)
        line = card.line_ids[0]
        self.assertAlmostEqual(line.attendance_score, 4.0, places=2)
        self.assertAlmostEqual(line.quiz_score, 8.5, places=2)
        self.assertAlmostEqual(line.midterm_score, 18.0, places=2)
        self.assertAlmostEqual(line.assignment_score, 7.5, places=2)
        self.assertAlmostEqual(line.final_exam_score, 41.0, places=2)
        self.assertAlmostEqual(line.final_score, 79.0, places=2)
        self.assertEqual(line.grade, "B")
        self.assertAlmostEqual(line.grade_point, 3.0, places=2)
        self.assertTrue(line.is_passing)
        self.assertEqual(line.evaluation_status, "completed")

        self.assertAlmostEqual(card.gpa, 3.0, places=2)
        self.assertEqual(card.total_credits, 3)
        self.assertEqual(card.passed_credits, 3)
        self.assertEqual(card.academic_standing, "good")
        self.assertEqual(card.evaluation_status, "completed")

        # Generate Transcript
        transcript = self.Transcript.create({"student_id": self.student.id})
        transcript.action_generate_lines()
        self.assertAlmostEqual(transcript.cumulative_gpa, 3.0, places=2)
        self.assertEqual(transcript.total_credits, 3)
