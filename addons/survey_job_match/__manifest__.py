{
    'name': 'Survey Job Matching',
    'version': '1.0',
    'category': 'Marketing/Surveys',
    'author': 'Odoo',
    'summary': 'Turn a survey into a job-matching game (each answer scores several job profiles)',
    'description': """
Survey Job Matching
===================

Adds a multi-dimensional scoring layer on top of the Survey app. Each suggested
answer can grant points to one or more *job profiles*. When a participant
finishes the survey, the best-matching profile is shown with a "match meter"
and a link to the related job/internship posting.

Designed for booths and job fairs: public, mobile-friendly, QR-shareable.
""",
    'depends': ['survey'],
    'data': [
        'security/ir.access.csv',
        'views/job_match_profile_views.xml',
        'views/survey_survey_views.xml',
        'views/survey_templates.xml',
    ],
    'demo': [
        'demo/demo_job_match.xml',
    ],
    'license': 'LGPL-3',
}
