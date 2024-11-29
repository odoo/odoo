# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SurveySurvey(models.Model):
    _inherit = 'survey.survey'

    certification_validity_months = fields.Integer(
        'Validity', required=False,
        help='Specify the number of months the certification is valid after being awarded. '
             'Enter 0 for certifications that never expire.')
