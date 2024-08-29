# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import survey

from odoo import fields, models

class SurveySurvey(models.Model, survey.SurveySurvey):

    certification_validity_months = fields.Integer(
        'Validity', required=False,
        help='Specify the number of months the certification is valid after being awarded. '
             'Enter 0 for certifications that never expire.')
