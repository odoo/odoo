# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Exam Management',
    'version': "10.0.1.0.15",
    'author': '''Francis Bangura. <francisbnagura@gmail.com>''',
    'website': 'https://www.byteltd.com/',
    'category': 'School Management',
    'license': "AGPL-3",
    'summary': 'A Module For Exams Management Taken In School',
    'complexity': 'easy',
    'depends': ['school', 'timetable'],
    'data': [
             'security/exam_security.xml',
             'security/ir.model.access.csv',
             'views/exam_view.xml',
             'views/exam_sequence.xml',
             #'views/exam_result_report.xml',
             #'views/additional_exam_report.xml',
             #'views/result_information_report.xml',
             #'views/batch_exam.xml',
             #'views/report_view.xml',
             #'wizard/subject_result.xml',
             #'wizard/batch_result.xml'
             'wizard/grade_import_wizard_view.xml'
              ],
    'demo': [
        #'demo/exam_demo.xml'
    ],
    'installable': True,
    'application': True,
}
