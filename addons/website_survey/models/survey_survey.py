# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import html2plaintext


class SurveySurvey(models.Model):
    _name = 'survey.survey'
    _inherit = ['survey.survey', 'website.seo.metadata']

    def _default_website_meta(self):
        res = super()._default_website_meta()
        description = html2plaintext(self.description)
        res['default_opengraph']['og:title'] = self.title
        res['default_opengraph']['og:description'] = description
        res['default_meta_description'] = description
        return res

    def _get_website_layout_values(self):
        self.ensure_one()
        return {
            'main_object': self.sudo(False),  # sudo(False) to keep user's current rights
            'additional_title': self.title,
        }
