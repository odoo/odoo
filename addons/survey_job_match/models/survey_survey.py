from odoo import _, fields, models


class SurveySurvey(models.Model):
    _inherit = 'survey.survey'

    is_job_match = fields.Boolean(
        'Job Matching Game',
        help="Turn this survey into a job-matching game: each answer adds points to "
             "one or more job profiles, and the best-matching profile is shown at the end.")
    job_match_no_match_message = fields.Html(
        'No-match Message', translate=True,
        default=lambda self: self._default_job_match_no_match_message(),
        help="Shown at the end when every job profile has been eliminated by the "
             "participant's answers (e.g. a missing hard requirement).")
    job_match_jobs_url = fields.Char(
        'Jobs Website URL', default='https://www.odoo.com/jobs',
        help="Link shown as a call-to-action on the no-match screen.")

    def _default_job_match_no_match_message(self):
        return _(
            "<p>Sorry, we don't have a role for you in our Belgian offices right now. "
            "Feel free to explore our website and look for a role in one of our "
            "international offices!</p>")
