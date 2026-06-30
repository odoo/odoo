from odoo import fields, models


class SurveySurvey(models.Model):
    _inherit = 'survey.survey'

    is_job_match = fields.Boolean(
        'Job Matching Game',
        help="Turn this survey into a job-matching game: each answer adds points to "
             "one or more job profiles, and the best-matching profile is shown at the end.")
