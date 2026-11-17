# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.survey.controllers.main import Survey
from odoo.http import request


class SurveySurveyController(Survey):

    def _extract_answer_additional_vals(self, post):
        # Override
        additional_values = super()._extract_answer_additional_vals(post)
        mass_mailing_id = post.get('mass_mailing_id', '')
        mailing = request.env['mailing.mailing'].sudo().browse(int(mass_mailing_id)).exists() if mass_mailing_id.isdigit() else False
        return {
            **additional_values,
            'mass_mailing_id': mailing.id if mailing else False,
        }
